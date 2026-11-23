from council import context, hook, learn, store
from council.panel import mechanism


def test_the_blocks_are_the_thirteen_of_the_spec_in_their_lanes():
    got = [(b["id"], b["lane"]) for b in mechanism.blocks()]
    assert got == [("h1", "start"), ("bas", "start"), ("diz", "start"), ("h2", "message"), ("ara", "message"), ("sec", "message"),
                   ("isa", "message"), ("h3", "end"), ("yaz", "end"), ("ogr", "end"), ("haf", "memory"), ("yed", "memory"), ("den", "memory")]
    assert all(b["name"] and b["what"] and b["rules"] and "{" not in b["what"] + "".join(b["rules"]) + b["sub"] for b in mechanism.blocks())


def test_every_number_in_a_rule_comes_from_the_code(monkeypatch):
    by = {b["id"]: b for b in mechanism.blocks()}
    assert "9.000" in by["bas"]["sub"] and "3.500" in " ".join(by["sec"]["rules"]) and "3.000" in by["diz"]["sub"]
    monkeypatch.setattr(context, "MESSAGE_BUDGET", 4200); monkeypatch.setattr(context, "MESSAGE_LIMIT", 7)
    monkeypatch.setattr(learn, "INDEX_BUDGET", 5000); monkeypatch.setattr(hook, "REVIEW_EVERY", 20)
    by = {b["id"]: b for b in mechanism.blocks()}
    assert "4.200" in " ".join(by["sec"]["rules"]) and "7 bölüm" in by["sec"]["sub"]
    assert "5.000" in by["diz"]["sub"] and "20 araç" in by["ogr"]["sub"]


def test_the_rest_of_the_numbers_are_read_from_the_code_too(monkeypatch):
    monkeypatch.setattr(store, "BACKUP_GRACE", 5 * 86400)
    monkeypatch.setattr(learn, "PROMOTE_AFTER", 4); monkeypatch.setattr(learn, "RETIRE_WRONG", 6)
    monkeypatch.setattr(learn, "RETIRE_NOT_HELPED", 7); monkeypatch.setattr(learn, "SKILL_LIMIT", 3)
    monkeypatch.setattr(learn, "MIN_HEAD_WORDS", 4)
    monkeypatch.setattr(context, "START_CARDS", 9); monkeypatch.setattr(context, "MIN_ROOM", 111)
    monkeypatch.setattr(context, "SECTION_CLIP", 1234)
    by = {b["id"]: b for b in mechanism.blocks()}
    assert "5 gün" in by["yed"]["rules"][0]
    ogr = " ".join(by["ogr"]["rules"])
    assert "4 ayrı oturumda" in ogr and "6 kez" in ogr and "7 oturum" in ogr
    assert "3 tarif" in by["isa"]["sub"] and "en az 4 kelimesi" in " ".join(by["isa"]["rules"])
    assert "son 9 oturumun" in by["bas"]["what"]
    sec = " ".join(by["sec"]["rules"])
    assert "1.234 karakter" in sec and "111 karakterin" in sec


def test_name_and_sub_split_at_the_first_middle_dot_only():
    by = {b["id"]: b for b in mechanism.blocks()}
    assert (by["h1"]["name"], by["h1"]["sub"]) == ("Hook", "oturum açıldı")
    assert (by["yaz"]["name"], by["yaz"]["sub"]) == ("Yazma", "kart · konu · günlük")
    assert all(by[i]["sub"] == "" for i in ("haf", "yed", "den"))
