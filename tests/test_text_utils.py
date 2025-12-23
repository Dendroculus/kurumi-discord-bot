from utils.textUtils import TextUtils

def test_clean_description_spoilers_and_truncate():
    text = "Hello<br>~!secret! ~ and <i>italic</i>"
    cleaned = TextUtils.clean_description(text, preserve_spoilers=True, short_truncate=20)
    assert "secret" in cleaned
    assert "<" not in cleaned

def test_format_date_full():
    assert TextUtils.format_date_full({"year": 2020, "month": 1, "day": 2}) == "2020-01-02"
    assert TextUtils.format_date_full({"year": 2020, "month": 1}) == "N/A"
    assert TextUtils.format_date_full(None) == "N/A"

def test_format_date_loose():
    assert TextUtils.format_date_loose({"year": 2020, "month": 1, "day": 2}) == "2020-1-2"
    assert TextUtils.format_date_loose({"year": 2020}) == "2020-??-??"
    assert TextUtils.format_date_loose(None) == "N/A"

def test_opt_and_genres():
    assert TextUtils.opt(None) == "N/A"
    assert TextUtils.opt(5) == "5"
    assert TextUtils.genres_to_text(["A", "B"]) == "`A` `B`"
    assert TextUtils.genres_to_text([]) == "N/A"