"""Pure functions: lexer, display formatting, dates, Lua decoding, GPS, config"""

from datetime import datetime, timezone

import pytest

from lrtools.criterlexer import CriterLexer
from lrtools.display import (
    display_aperture,
    display_boolean,
    display_date,
    display_duration,
    display_flag,
    display_iso,
    display_lrtimestamp,
    display_results,
    display_speed,
    prepare_display_columns,
    seconds_tostring,
    smart_unit,
)
from lrtools.gps import square_around_location
from lrtools.lrcat import date_to_lrstamp, lr_strptime
from lrtools.lrselectgeneric import LRSelectException, to_bool
from lrtools.lrtoolconfig import LRConfigException, LRToolConfig
from lrtools.slpp import SLPP

#
# criteria lexer
#


def test_lexer_tokens():
    lex = CriterLexer('(rating=>3| name="a,b"), videos')
    assert lex.parse()
    assert lex.tokens == [
        ("LPAR", None),
        ("KEYVAL", ("rating", ">3")),
        ("OR", None),
        ("KEYVAL", ("name", "a,b")),
        ("RPAR", None),
        ("AND", None),
        ("KEYVAL", ("videos", "True")),
    ]


def test_lexer_lowercases_keys():
    lex = CriterLexer("Rating=5")
    assert lex.parse()
    assert lex.tokens == [("KEYVAL", ("rating", "5"))]


@pytest.mark.parametrize(
    "criteria, error",
    [
        ("(rating=5", "unbalanced parenthesis"),
        ("rating=5)", "unbalanced parenthesis"),
        ("rating=5,,videos", '"AND" not allowed after "AND"'),
        ("| rating=5", '"OR" not allowed after "None"'),
        ("rating=", 'No value for criterion "rating"'),
        ("rating=5, #x", "Invalid token"),
    ],
)
def test_lexer_errors(criteria, error):
    lex = CriterLexer(criteria)
    assert not lex.parse()
    assert error in lex.last_error


def test_lexer_empty():
    assert not CriterLexer("").parse()


#
# display
#


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, "- KB"),
        (999, "999.00 B"),
        (1500, "1.50 KB"),
        (2_500_000, "2.50 MB"),
        ("3000000000", "3.00 GB"),
        (4 * 10**12 + 1, "4.00 TB"),
    ],
)
def test_smart_unit(value, expected):
    assert smart_unit(value, "B") == expected


@pytest.mark.parametrize(
    "func, value, expected",
    [
        (display_aperture, 6.0, "F8.0"),
        (display_aperture, 4.970854, "F5.6"),
        (display_speed, 9.965784, "1/1000"),
        (display_speed, -1.0, "2"),
        (display_iso, 1600.0, "1600"),
        (display_boolean, 0, "no"),
        (display_boolean, 1, "yes"),
        (display_boolean, None, "?"),
        (display_date, "2018-05-10T10:00:00.123", "2018-05-10T10:00:00"),
        (display_flag, -1, "rejected"),
        (display_flag, "1", "flagged"),
        (display_duration, "000000000000012c/000000000000000a", "00:30.0"),
    ],
)
def test_display_formatters(func, value, expected):
    assert func(value) == expected


def test_display_lrtimestamp_is_local_time():
    expected = datetime(2001, 1, 1, tzinfo=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    assert display_lrtimestamp(0) == expected


@pytest.mark.parametrize(
    "seconds, kwargs, expected",
    [
        (5, {}, "00:05"),
        (65.25, {"fract": 2}, "01:05.25"),
        (3725, {}, "1:02:05"),
    ],
)
def test_seconds_tostring(seconds, kwargs, expected):
    assert seconds_tostring(seconds, **kwargs) == expected


def test_prepare_display_columns():
    spec = prepare_display_columns(["name", "aperture", "unknown"], ["-10"])
    assert spec[0] == ("name", "%-10s", None)
    assert spec[1] == ("aperture", "%5s", display_aperture)
    assert spec[2] == ("unknown", "%6s", None)


def test_display_results(capsys):
    rows = [("IMG_1.JPG", 6.0, None), ("IMG_2.JPG", 4.970854, 1)]
    display_results(rows, "name,aperture,flash", separator="|", indent=0)
    out = capsys.readouterr().out.splitlines()
    assert out[0] == " * Results (2 entries) :"
    # header names are truncated to the column width
    assert out[1] == "name                |apert|fla"
    assert out[3] == "IMG_1.JPG           | F8.0|   "
    assert out[4] == "IMG_2.JPG           | F5.6|yes"


def test_display_results_max_lines_and_raw(capsys):
    rows = [("a", 6.0), ("b", 6.0), ("c", 6.0)]
    display_results(rows, ["name", "aperture"], max_lines=1, raw_print=True, header=False)
    assert capsys.readouterr().out == "    a                    |   6.0\n"


def test_display_results_empty(capsys):
    display_results([], "name")
    assert capsys.readouterr().out == " * None data result\n"


#
# dates
#


@pytest.mark.parametrize(
    "lrdate, expected",
    [
        ("2019-08-13T19:47:33", datetime(2019, 8, 13, 19, 47, 33)),
        ("2019-08-13T19:47", datetime(2019, 8, 13, 19, 47)),
        ("2019-08-13T19:47:33.269", datetime(2019, 8, 13, 19, 47, 33, 269000)),
        ("2019-08-13T19:47:33Z", datetime(2019, 8, 13, 19, 47, 33, tzinfo=timezone.utc)),
    ],
)
def test_lr_strptime(lrdate, expected):
    assert lr_strptime(lrdate) == expected


def test_lr_strptime_with_offset():
    parsed = lr_strptime("2019-08-13T19:47:33.022+02:00")
    assert parsed.utcoffset().total_seconds() == 7200
    assert parsed.microsecond == 22000


def test_date_to_lrstamp(config):
    assert date_to_lrstamp(config, datetime(2001, 1, 2, tzinfo=timezone.utc)) == 86400
    assert date_to_lrstamp(config, "2-1-2001 00:00:00+00:00", localtz=False) == 86400
    assert date_to_lrstamp(config, datetime(1990, 1, 1, tzinfo=timezone.utc)) == 0
    assert date_to_lrstamp(config, 12) is None


def test_date_to_lrstamp_dayfirst(config):
    config.dayfirst = False
    assert date_to_lrstamp(config, "2001-01-02 00:00:00+00:00", localtz=False) == 86400


@pytest.mark.parametrize("value, expected", [("true", True), ("1", True), ("yes", True), ("False", False), ("0", False)])
def test_to_bool(value, expected):
    assert to_bool(value) is expected


def test_to_bool_invalid():
    with pytest.raises(LRSelectException):
        to_bool("maybe")


#
# Lua tables (smart collections)
#


def test_slpp_decode():
    data = SLPP().decode(
        "{\n"
        '\t{\n\t\tcriteria = "rating",\n\t\toperation = ">=",\n\t\tvalue = 5,\n\t},\n'
        '\t{\n\t\tcriteria = "hasGPSData",\n\t\tvalue = false,\n\t\tvalue2 = 1.5,\n\t}, --- comment\n'
        '\tcombine = "union",\n'
        "}"
    )
    assert data == {
        0: {"criteria": "rating", "operation": ">=", "value": 5},
        1: {"criteria": "hasGPSData", "value": False, "value2": 1.5},
        "combine": "union",
    }


def test_slpp_decode_invalid():
    assert SLPP().decode("") is None
    assert SLPP().decode(None) is None


def test_slpp_round_trip():
    lua = SLPP()
    data = {"title": "x", "values": [1, 2], "flag": True}
    assert lua.decode(lua.encode(data)) == {"title": "x", "values": [1, 2], "flag": True}


#
# GPS
#


def test_square_around_location():
    (lat1, lon1), (lat2, lon2) = square_around_location(45.0, 5.0, 10)
    assert lat1 < 45.0 < lat2 and lon1 < 5.0 < lon2
    assert lat2 - lat1 == pytest.approx(0.1797, abs=1e-4)
    # longitude degrees are shorter away from the equator
    assert (lon2 - lon1) > (lat2 - lat1)


#
# config
#

INI = "[Main]\nLRCatalog = {catalog}\nDayFirst = False\nGeoCoder = BanFrance\n"


def test_config_defaults():
    config = LRToolConfig(None)
    assert config.default_lrcat.endswith("My Lightroom Catalog.lrcat")
    assert config.dayfirst is True
    assert config.geocoder == "nominatim"


def test_config_load_full_path(tmp_path):
    ini = tmp_path / "custom.ini"
    ini.write_text(INI.format(catalog="/x/cat.lrcat"))
    config = LRToolConfig(str(ini))
    assert config.default_lrcat == "/x/cat.lrcat"
    assert config.dayfirst is False
    assert config.geocoder == "BanFrance"


def test_config_found_in_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "lrtools.ini").write_text(INI.format(catalog="/cwd/cat.lrcat"))
    assert LRToolConfig().default_lrcat == "/cwd/cat.lrcat"


def test_config_found_in_user_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    user_dir = tmp_path / "home" / ".config" / "lrtools"
    user_dir.mkdir(parents=True)
    (user_dir / "lrtools.ini").write_text(INI.format(catalog="/home/cat.lrcat"))
    assert LRToolConfig().default_lrcat == "/home/cat.lrcat"


def test_config_missing_is_silent(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("sys.argv", [str(tmp_path / "script.py")])
    config = LRToolConfig()
    assert config.dayfirst is True
    assert capsys.readouterr().err == ""


def test_config_invalid_warns(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "lrtools.ini").write_text("garbage\n")
    config = LRToolConfig()
    assert config.dayfirst is True
    assert "WARNING: failed to read config file" in capsys.readouterr().err


def test_config_load_raises(tmp_path):
    ini = tmp_path / "bad.ini"
    ini.write_text("[Other]\n")
    with pytest.raises(LRConfigException):
        LRToolConfig(None).load(str(ini))
