"""De auto-review-teller moet een botherstart overleven (persistent op schijf)
en nooit de feedback-flow breken als het bestand niet schrijfbaar is."""
import feedback


def test_open_count_persists_across_restart(tmp_path, monkeypatch):
    countfile = tmp_path / "open_count.txt"
    monkeypatch.setattr(feedback, "_OPEN_COUNT_FILE", countfile)
    monkeypatch.setattr(feedback, "_open_count", 0)

    assert feedback.increment_and_check(3) is False   # 1
    assert feedback.increment_and_check(3) is False   # 2
    assert countfile.read_text().strip() == "2"

    # simuleer botherstart: geheugenteller weg, bestand blijft -> herlaad
    monkeypatch.setattr(feedback, "_open_count", feedback._read_open_count())
    assert feedback._open_count == 2

    assert feedback.increment_and_check(3) is True    # 3 -> trigger
    assert countfile.read_text().strip() == "0"       # reset na trigger


def test_open_count_survives_unwritable_file(tmp_path, monkeypatch):
    # parent-parent bestaat niet -> schrijven faalt stil, geen crash
    bad = tmp_path / "missing" / "deep" / "open_count.txt"
    monkeypatch.setattr(feedback, "_OPEN_COUNT_FILE", bad)
    monkeypatch.setattr(feedback, "_open_count", 0)

    assert feedback.increment_and_check(2) is False   # 1 (in-memory)
    assert feedback.increment_and_check(2) is True    # 2 -> trigger (in-memory)
