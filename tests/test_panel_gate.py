import json
import stat
import sys
from pathlib import Path

import pytest

from council.oauth import hash_password
from council.panel.gate import Gate, SESSION_TTL


def gate(tmp_path, password="dogru-sifre-123"):
    data = tmp_path / "data"
    data.mkdir(parents=True, exist_ok=True)
    if password:
        (data / "owner.json").write_text(json.dumps(hash_password(password)))
    return Gate(data)


def test_the_right_password_opens_a_session_that_ends_after_twelve_hours(tmp_path):
    g = gate(tmp_path)
    try:
        token = g.sign_in("dogru-sifre-123", now=1000.0)
        assert token and g.valid(token, now=1000.0 + SESSION_TTL - 1) and not g.valid(token, now=1000.0 + SESSION_TTL + 1)
        assert not g.valid("uydurma", now=1000.0) and not g.valid("", now=1000.0)
    finally:
        g.close()


def test_five_wrong_passwords_lock_the_door_for_fifteen_minutes_even_for_the_right_one(tmp_path):
    g = gate(tmp_path)
    for i in range(5):
        assert g.sign_in("yanlis", now=1000.0 + i) is None
    assert g.locked(now=1010.0) and g.sign_in("dogru-sifre-123", now=1010.0) is None
    g.close()
    again = Gate(tmp_path / "data")                                        # the lock survives a restart
    try:
        assert again.locked(now=1010.0) and not again.locked(now=1000.0 + 4 + 901)
        assert again.sign_in("dogru-sifre-123", now=1000.0 + 4 + 901)
    finally:
        again.close()


def test_signing_out_ends_the_session_and_no_password_set_opens_nothing(tmp_path):
    g = gate(tmp_path)
    bare = gate(tmp_path / "x", password=None)
    try:
        token = g.sign_in("dogru-sifre-123", now=5.0)
        g.sign_out(token)
        assert not g.valid(token, now=6.0)
        assert not bare.configured() and bare.sign_in("herhangi", now=1.0) is None and not bare.locked(now=2.0)
    finally:
        g.close()
        bare.close()


def test_only_hashes_of_tokens_are_stored_and_a_wrong_password_before_setup_counts_nothing(tmp_path):
    g = gate(tmp_path)
    bare = gate(tmp_path / "y", password=None)
    try:
        token = g.sign_in("dogru-sifre-123", now=1.0)
        rows = g.db.execute("SELECT hash FROM sessions").fetchall()
        assert rows and all(token not in r[0] and len(r[0]) == 64 for r in rows)
        bare.sign_in("x", now=1.0)
        assert bare.db.execute("SELECT COUNT(*) FROM failures").fetchone()[0] == 0
    finally:
        g.close()
        bare.close()


# ---------- changing the password, closing other sessions ----------

NEW = "yepyeni-sifre-456"


def two_sessions(g, now=1000.0):
    return g.sign_in("dogru-sifre-123", now=now), g.sign_in("dogru-sifre-123", now=now)


def test_every_result_of_a_password_change_in_the_order_of_its_checks(tmp_path):
    from council.oauth import MIN_PASSWORD

    g = gate(tmp_path)
    try:
        mine, _ = two_sessions(g)
        assert g.change_password("uydurma", "dogru-sifre-123", NEW, now=1001.0) == "signed_out"
        assert g.change_password(mine, "dogru-sifre-123", "k" * (MIN_PASSWORD - 1), now=1001.0) == "weak"
        assert g.change_password(mine, "yanlis", "k" * (MIN_PASSWORD - 1), now=1001.0) == "weak"  # strength first
        assert g.change_password(mine, "dogru-sifre-123", "k" * 201, now=1001.0) == "weak"
        assert g.change_password(mine, "yanlis", NEW, now=1001.0) == "wrong"
        assert g.change_password(mine, "yanlis", "dogru-sifre-123", now=1001.0) == "wrong"  # current before same
        assert g.change_password(mine, "dogru-sifre-123", "dogru-sifre-123", now=1001.0) == "same"
        assert g.db.execute("SELECT COUNT(*) FROM failures").fetchone()[0] == 2  # only the two wrong ones count
        assert g.change_password(mine, "dogru-sifre-123", NEW, now=1001.0) == "ok"
    finally:
        g.close()


def test_the_length_is_counted_in_characters_not_bytes(tmp_path):
    g = gate(tmp_path)
    try:
        mine = g.sign_in("dogru-sifre-123", now=1.0)
        assert g.change_password(mine, "dogru-sifre-123", "ğüşçöı" + "İ" * 3, now=2.0) == "weak"  # 9 letters, 17 bytes
        assert g.change_password(mine, "dogru-sifre-123", "ğüşçöı" + "İ" * 4, now=2.0) == "ok"     # 10 letters
        assert g.change_password(mine, "ğüşçöıİİİİ", "x" * 200, now=3.0) == "ok"                  # 200 is allowed
    finally:
        g.close()


def test_five_wrong_current_passwords_lock_sign_in_like_five_wrong_sign_ins(tmp_path):
    g = gate(tmp_path)
    try:
        mine = g.sign_in("dogru-sifre-123", now=1000.0)
        for i in range(5):
            assert g.change_password(mine, "yanlis", NEW, now=1001.0 + i) == "wrong"
        assert g.locked(now=1010.0) and g.sign_in("dogru-sifre-123", now=1010.0) is None
        assert g.change_password(mine, "dogru-sifre-123", NEW, now=1010.0) == "locked"
        assert g.change_password(mine, "dogru-sifre-123", "kisa", now=1010.0) == "locked"  # the lock comes first
        assert g.valid(mine, now=1010.0)                   # a lock closes the door, not the open session
    finally:
        g.close()


def test_three_wrong_sign_ins_and_two_wrong_changes_are_five_failures(tmp_path):
    g = gate(tmp_path)
    try:
        mine = g.sign_in("dogru-sifre-123", now=1000.0)
        for i in range(3):
            assert g.sign_in("yanlis", now=1001.0 + i) is None
        for i in range(2):
            assert g.change_password(mine, "yanlis", NEW, now=1005.0 + i) == "wrong"
        assert g.locked(now=1010.0)
    finally:
        g.close()


def test_after_a_change_the_new_password_opens_the_old_does_not_and_only_the_callers_session_stays(tmp_path):
    from council.oauth import check_password

    g = gate(tmp_path)
    try:
        mine, other = two_sessions(g)
        third = g.sign_in("dogru-sifre-123", now=1000.0)
        result = g.change_password(mine, "dogru-sifre-123", NEW, now=1001.0)
        assert result == "ok" and result.closed == 2
        assert g.valid(mine, now=1002.0) and not g.valid(other, now=1002.0) and not g.valid(third, now=1002.0)
        assert g.sign_in("dogru-sifre-123", now=1003.0) is None
        assert g.sign_in(NEW, now=1004.0)
        owner = tmp_path / "data" / "owner.json"
        record = json.loads(owner.read_text())                        # valid JSON, the scrypt record
        assert set(record) == {"salt", "hash", "n"} and NEW not in owner.read_text()
        assert check_password(NEW, record) and not check_password("dogru-sifre-123", record)
        if sys.platform != "win32":                                   # Windows only knows read-only
            assert stat.S_IMODE(owner.stat().st_mode) == 0o600
        assert sorted(p.name for p in owner.parent.iterdir() if not p.name.startswith("panel.sqlite3")) == ["owner.json"]
    finally:
        g.close()


def test_the_memory_service_accepts_the_new_password_from_the_same_file(tmp_path):
    from council.oauth import OwnerOAuthProvider, check_password

    g = gate(tmp_path)
    provider = OwnerOAuthProvider(tmp_path / "data", "http://127.0.0.1:8765", "t")
    try:
        mine = g.sign_in("dogru-sifre-123", now=1.0)
        assert check_password("dogru-sifre-123", provider.owner_record())
        assert g.change_password(mine, "dogru-sifre-123", NEW, now=2.0) == "ok"
        assert check_password(NEW, provider.owner_record())         # read again on every check: no restart
    finally:
        g.close()
        provider.db.close()


def test_a_change_that_fails_to_write_leaves_the_old_file_whole_and_no_temporary_file(tmp_path, monkeypatch):
    import os

    g = gate(tmp_path)
    owner = tmp_path / "data" / "owner.json"
    before = owner.read_bytes()
    try:
        mine, other = two_sessions(g)

        def refuse(*a, **k):
            raise OSError("disk full")

        monkeypatch.setattr(os, "replace", refuse)
        with pytest.raises(OSError):
            g.change_password(mine, "dogru-sifre-123", NEW, now=1001.0)
        monkeypatch.undo()
        assert owner.read_bytes() == before
        assert sorted(p.name for p in owner.parent.iterdir() if not p.name.startswith("panel.sqlite3")) == ["owner.json"]
        assert g.valid(other, now=1002.0)                            # nothing changed, nobody was signed out
        assert g.sign_in("dogru-sifre-123", now=1003.0)
    finally:
        g.close()


def test_closing_the_other_sessions_keeps_the_callers_and_says_how_many(tmp_path):
    g = gate(tmp_path)
    try:
        mine, other = two_sessions(g)
        assert g.session_info(mine, now=1001.0) == {"sessions": 2, "expires": 1000.0 + SESSION_TTL}
        assert g.sign_out_others("uydurma", now=1001.0) == 0 and g.valid(other, now=1001.0)
        assert g.sign_out_others(mine, now=1001.0) == 1
        assert g.valid(mine, now=1002.0) and not g.valid(other, now=1002.0)
        assert g.session_info(mine, now=1002.0) == {"sessions": 1, "expires": 1000.0 + SESSION_TTL}
        assert g.sign_out_others(mine, now=1002.0) == 0
        assert g.session_info("uydurma", now=1002.0) is None and g.session_info("", now=1002.0) is None
        assert g.session_info(mine, now=1000.0 + SESSION_TTL + 1) is None  # an ended session has no info
    finally:
        g.close()


def test_the_cli_and_the_gate_share_one_minimum(tmp_path, monkeypatch, capsys):
    import getpass

    from council import cli, oauth

    monkeypatch.setattr(oauth, "MIN_PASSWORD", 12)
    answers = iter(["on-bir-harf", "on-bir-harf"])  # 11 characters
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": next(answers))
    assert cli.main(["--data", str(tmp_path / "d"), "set-password"]) == 1
    answers = iter(["on-iki-harfl", "on-iki-harfl"])
    assert cli.main(["--data", str(tmp_path / "d"), "set-password"]) == 0
    assert oauth.check_password("on-iki-harfl", json.loads((tmp_path / "d" / "owner.json").read_text()))
    g = gate(tmp_path)
    try:
        mine = g.sign_in("dogru-sifre-123", now=1.0)
        assert g.change_password(mine, "dogru-sifre-123", "on-bir-harf", now=2.0) == "weak"
    finally:
        g.close()


def test_hashing_and_checking_never_raise_with_a_character_of_the_password(tmp_path, monkeypatch, capsys):
    import getpass

    from council import cli, oauth

    with pytest.raises(ValueError) as raised:
        oauth.hash_password("abcdefghij\ud800")
    assert "ud800" not in repr(raised.value) and "\ud800" not in str(raised.value) and "position" not in str(raised.value)
    assert raised.value.__cause__ is None and raised.value.__context__ is None  # no UnicodeEncodeError behind it
    assert oauth.check_password("x\udfff", oauth.hash_password("dogru-sifre-123")) is False
    answers = iter(["abcdefghij\ud800"] * 2)
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": next(answers))
    assert cli.main(["--data", str(tmp_path / "d"), "set-password"]) == 1
    assert "ud800" not in capsys.readouterr().err and not (tmp_path / "d" / "owner.json").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX owners only")
def test_a_new_owner_file_takes_the_old_files_owner_and_group_before_it_takes_its_place(tmp_path, monkeypatch):
    import os

    from council import oauth
    from council.oauth import check_password

    data = tmp_path / "data"
    data.mkdir()
    owner = data / "owner.json"
    owner.write_text(json.dumps(hash_password("dogru-sifre-123")))
    old = owner.stat()
    calls, replaced = [], []
    real_replace = os.replace

    def chown(path, uid, gid):
        calls.append((Path(path).name, uid, gid, bool(replaced)))

    def replace(src, dst):
        replaced.append(Path(src).name)
        real_replace(src, dst)

    monkeypatch.setattr(os, "chown", chown, raising=False)
    monkeypatch.setattr(os, "replace", replace)
    oauth.write_owner(data, NEW)
    assert len(calls) == 1
    name, uid, gid, after = calls[0]
    assert (uid, gid) == (old.st_uid, old.st_gid) and name == replaced[0] and not after
    assert check_password(NEW, json.loads(owner.read_text()))

    def refuse(path, uid, gid):
        raise PermissionError("not root")

    monkeypatch.setattr(os, "chown", refuse)
    oauth.write_owner(data, "ucuncu-sifre-789")                      # the write goes on with the file as it is
    assert check_password("ucuncu-sifre-789", json.loads(owner.read_text()))
    assert stat.S_IMODE(owner.stat().st_mode) == 0o600
    monkeypatch.delattr(os, "chown")                                 # a platform without chown
    oauth.write_owner(data, "dorduncu-sifre-0")
    assert check_password("dorduncu-sifre-0", json.loads(owner.read_text()))
    assert sorted(p.name for p in data.iterdir()) == ["owner.json"]


def test_a_first_owner_file_has_no_old_owner_to_copy(tmp_path, monkeypatch):
    import os

    from council import oauth

    data = tmp_path / "data"
    data.mkdir()
    calls = []
    monkeypatch.setattr(os, "chown", lambda *a: calls.append(a), raising=False)
    oauth.write_owner(data, NEW)
    assert calls == [] and (data / "owner.json").exists()
