import json
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
