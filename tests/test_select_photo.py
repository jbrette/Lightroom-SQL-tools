"""LRSelectPhoto: SQL generation from columns/criteria strings, executed on the synthetic catalog"""

import pytest

import lrtools.lrselectphoto
from lrtools.lrselectgeneric import LRSelectException
from lrtools.lrselectphoto import criteria_to_dict, dict_to_criteria

ALL_PHOTOS = [1, 2, 3, 4, 5, 6]

# columns needing a special value
SPECIAL_COLUMNS = {"exif"}


def photo_columns(lrdb):
    """every (column, value) pair declared by LRSelectPhoto"""
    return [
        (name, value)
        for name, values in lrdb.lrphoto.column_description.items()
        for value in values
        if name not in SPECIAL_COLUMNS
    ]


def test_every_column_executes(lrdb):
    for name, value in photo_columns(lrdb):
        column = name if value == "True" else f"{name}={value}"
        rows = lrdb.lrphoto.select_generic(f"id,{column}", "").fetchall()
        assert len(rows) == len(ALL_PHOTOS), column


@pytest.mark.parametrize(
    "column, expected",
    [
        ("name", "IMG_0001.JPG"),
        ("name=base", "IMG_0001"),
        ("name=basext", "IMG_0001.JPG"),
        ("name=full", "/photos/2018/IMG_0001.JPG"),
        ("folder", "/photos/2018/"),
        ("uuid", "UUID-1"),
        ("uuidfile", "file-1"),
        ("rating", 5),
        ("colorlabel", "Red"),
        ("flag", 1),
        ("datecapt", "2018-05-10T10:00:00"),
        ("modcount", 3),
        ("keywords", "beach,family"),
        ("collections", "Holidays"),
        ("camera", "Canon EOS 5D"),
        ("camerasn", "SN1234"),
        ("lens", "EF24-70mm f/2.8L"),
        ("iso", 100),
        ("focal", 50),
        ("dims", "3000x2000"),
        ("creator", "Alice"),
        ("caption", "sunset at the beach"),
        ("city", "Paris"),
        ("country", "France"),
        ("state", "Ile-de-France"),
        ("location", "Tour Eiffel"),
        ("pubcollection", "Flickr"),
        ("pubname", "remote-1"),
        ("digest", "digest-1"),
        ("xmp", "<x:xmpmeta/>"),
        ("extfile", "xmp"),
    ],
)
def test_column_value(lrdb, column, expected):
    (value,) = lrdb.lrphoto.select_generic(column, "id=1").fetchone()
    assert value == expected


def test_column_name_virtual_copy(lrdb):
    rows = lrdb.lrphoto.select_generic("name=basext_vc,vname", "id=5").fetchall()
    assert rows == [("IMG_0001Copy 1.JPG", "Copy 1")]


def test_column_dims_uses_orientation(lrdb):
    rows = lrdb.lrphoto.select_generic("id,dims", "sort=-id").fetchall()
    assert dict(rows) == {
        1: "3000x2000",  # cropped
        2: "4000x6000",  # rotated
        3: "6016x4016",
        4: "6016x4016",
        5: "6000x4000",
        6: "1920x1080",
    }


def test_column_exif_var(lrdb):
    (value,) = lrdb.lrphoto.select_generic("exif=var:em.isoSpeedRating", "id=2").fetchone()
    assert value == 1600


def test_column_count_and_countby(lrdb):
    rows = lrdb.lrphoto.select_generic("camera,countby(camera)", "camera=%").fetchall()
    assert sorted(rows) == [("Canon EOS 5D", 3), ("NIKON D750", 2)]


def test_default_column_is_basext(lrdb):
    rows = lrdb.lrphoto.select_generic("", "id=2").fetchall()
    assert rows == [("IMG_0002.CR2",)]


def test_selected_column_names(lrdb):
    lrdb.lrphoto.select_generic("name=full,id,rating", "")
    assert lrdb.lrphoto.selected_column_names() == ["name=full", "id", "rating"]


@pytest.mark.parametrize(
    "criteria, expected",
    [
        ("", ALL_PHOTOS),
        # identity
        ("id=4", [4]),
        ("uuid=UUID-3", [3]),
        ("uuidfile=file-2", [2]),
        # names and files
        ("name=IMG%", [1, 2, 5]),
        ("name=%Copy%", [5]),
        ("exactname=img_0001", []),
        ("exactname=IMG_0001", [1, 5]),
        ("ext=NEF", [3, 4]),
        ("exact_ext=MP4", [6]),
        ("folder=%2019%", [3, 4, 6]),
        ("idfolder=1", [1, 2, 5]),
        ("extfile=xmp", [1, 2, 5]),
        # rating, flag, label
        ("rating=5", [1]),
        ("rating=>=3", [1, 2, 5]),
        ("rating=<3", [3, 4, 6]),
        ("rating=0", [3, 6]),
        ("flag=flagged", [1]),
        ("flag=-1", [3]),
        ("flag=unflagged", [2, 4, 5, 6]),
        ("colorlabel=Red", [1]),
        ("colorlabel=true", [1]),
        ("colorlabel=false", [2, 3, 4, 5, 6]),
        # dates
        ("datecapt=>=1-1-2019", [3, 4, 6]),
        ("datecapt=<=31-5-2018", [1, 5]),
        ("datecapt==2018", [1, 2, 5]),
        ("datecapt==7-2018", [2]),
        ("datemod=>=1-1-2020", [2]),
        ("modcount=>=1", [1, 2]),
        ("pubtime=>=1-1-2020", [1]),
        # exif
        ("camera=%canon%", [1, 2, 5]),
        ("camerasn=SN1234", [1, 2, 5]),
        ("lens=%70-200%", [2]),
        ("iso=>=1600", [2, 3, 4]),
        ("focal=>100", [2]),
        ("aperture=>=8", [1, 5]),
        ("aperture=F5.6", [2]),
        ("speed=>=1/500", [1, 5]),
        ("speed=<=1/250", [2]),
        ("flash=1", [2]),
        ("orientation=BC", [2]),
        ("aspectratio=<1", [2]),
        ("monochrome=1", [3]),
        ("grayscale=true", [3]),
        ("videos=1", [6]),
        ("videos=0", [1, 2, 3, 4, 5]),
        ("vcopies=null", [1, 2, 3, 4, 6]),
        ("vcopies=!null", [5]),
        ("vcopies=1", [5]),
        # iptc
        ("caption=%sunset%", [1]),
        ("caption=null", [2, 3, 4, 5, 6]),
        ("copyright=%alice%", [1]),
        ("creator=Alice", [1]),
        ("city=paris", [1]),
        ("country=France", [1, 2]),
        ("state=%ile%", [1]),
        ("location=%eiffel%", [1]),
        ("title=sunset", [1]),
        ("exifindex=canon", [1]),
        ('exifindex="canon|nikon"', [1, 3]),
        ("exifindex=canon&nikon", []),
        # gps
        ("hasgps=1", [1, 2, 5]),
        ("hasgps=false", [3, 4, 6]),
        ("gps=48.8566;2.3522+10", [1, 5]),
        ("gps=45;4/46;5", [2]),
        ("gps=photo:IMG_0002+5", [2]),
        # keywords
        ("keyword=beach", [1]),
        ("keyword=family", [1, 2]),
        ("keyword=family, keyword=beach", [1]),
        ("keyword=beach|rating=3", [1, 2]),
        ("keyword=beach | rating=3", [1, 2]),
        ("(keyword=beach ), rating=5", [1]),
        ("idkeyword=4", [1, 2]),
        ("haskeywords=1", [1, 2]),
        ("haskeywords=0", [3, 4, 5, 6]),
        # collections, imports, publish
        ("collection=Holidays", [1, 2]),
        ("collection=Holidays, collection=Best", [2]),
        ("idcollection=11", [2]),
        ("idcollection=10, idcollection=11", [2]),
        ("import=1", [1, 2]),
        ("pubcollection=Flickr", [1]),
        ("idpubcollection=20", [1]),
        # stacks, metadata status
        ("stacks=yes", [3, 4]),
        ("stacks=top", [3]),
        ("stacks=no", [1, 2, 5, 6]),
        ("stacks=no+top", [1, 2, 3, 5, 6]),
        ("stacks=1", [3, 4]),
        ("metastatus=hasbeenchanged", [2]),
        ("metastatus=uptodate", [1, 3, 4, 5, 6]),
        # boolean operators
        ("(rating=5 | rating=3), camera=%canon%", [1, 2]),
        ("rating=5 | (iso=6400, flag=rejected)", [1, 3]),
        ('name="IMG_0002"', [2]),
    ],
)
def test_criteria(select_ids, criteria, expected):
    assert select_ids(criteria) == expected


def test_criteria_size_needs_dims_column(select_ids):
    assert select_ids("width=>=5000", "id,dims") == [3, 4, 5]
    assert select_ids("height=>=5000", "id,dims") == [2]


def test_criteria_gps_town(monkeypatch, select_ids):
    def fake_geocodage(_config, town):
        assert town == "paris"
        return (48.85, 2.35), "Paris, France"

    monkeypatch.setattr(lrtools.lrselectphoto, "geocodage", fake_geocodage)
    assert select_ids("gps=paris+10") == [1, 5]


def test_criteria_gps_town_not_found(monkeypatch, select_ids):
    monkeypatch.setattr(lrtools.lrselectphoto, "geocodage", lambda *_: None)
    with pytest.raises(LRSelectException, match="Town coordinates not found"):
        select_ids("gps=nowhere+10")


def test_sort_is_descending_by_default(lrdb):
    rows = lrdb.lrphoto.select_generic("id", "rating=>=1, sort=rating").fetchall()
    assert [row[0] for row in rows] == [1, 5, 2, 4]
    rows = lrdb.lrphoto.select_generic("id", "rating=>=1, sort=-rating").fetchall()
    assert [row[0] for row in rows] == [4, 2, 5, 1]


def test_distinct(lrdb):
    rows = lrdb.lrphoto.select_generic("camera", "camera=%").fetchall()
    assert len(rows) == 5
    rows = lrdb.lrphoto.select_generic("camera", "camera=%, distinct").fetchall()
    assert sorted(rows) == [("Canon EOS 5D",), ("NIKON D750",)]
    rows = lrdb.lrphoto.select_generic("camera", "camera=%", distinct=True).fetchall()
    assert len(rows) == 2


@pytest.mark.parametrize(
    "criteria",
    [
        "keyword=%",
        "keyword=beach|keyword=family",
        "keyword=%a%|keyword=family|rating=5",
        "idkeyword=3|idkeyword=4",
        "collection=%",
        "collection=Holidays|collection=Best",
        "idcollection=10|idcollection=11",
        "import=1|keyword=family",
    ],
)
def test_one_row_per_photo(lrdb, criteria):
    """criteria on keywords/collections/imports must not repeat a photo once per match"""
    ids = [row[0] for row in lrdb.lrphoto.select_generic("id", criteria).fetchall()]
    assert ids and len(ids) == len(set(ids))


def test_sql_kwargs(lrdb, capsys):
    sql = lrdb.lrphoto.select_generic("id", "rating=5", sql=True)
    assert isinstance(sql, str) and sql.startswith("SELECT")
    assert "i.rating = 5" in sql
    assert lrdb.lrphoto.select_generic("id", "rating=5", print=True) is None
    assert "SQL =" in capsys.readouterr().out


@pytest.mark.parametrize(
    "criteria, message",
    [
        ("unknown=1", 'No existent criterion "unknown"'),
        ("rating=5,,(", "Criteria syntax error"),
        ("(rating=5", "unbalanced parenthesis"),
        ("flag=maybe", "Incorrect flag value"),
        ("stacks=maybe", 'invalid "stacks" value'),
        ("metastatus=maybe", 'invalid "metastatus" value'),
        ("gps=somewhere", "Town coordinates not found|GPS coordinates malformed"),
        ("haskeywords=maybe", "invalid haskeywords value"),
        ("hasgps=maybe", "invalid hasgps criterion value"),
        ("datecapt=2018", "None operator for date"),
    ],
)
def test_criteria_errors(lrdb, monkeypatch, criteria, message):
    monkeypatch.setattr(lrtools.lrselectphoto, "geocodage", lambda *_: None)
    with pytest.raises(LRSelectException, match=message):
        lrdb.lrphoto.select_generic("id", criteria)


@pytest.mark.parametrize("columns", ["unknown", "name=other"])
def test_column_errors(lrdb, columns):
    with pytest.raises(LRSelectException):
        lrdb.lrphoto.select_generic(columns, "")


def test_predefined_duplicated_names(lrdb):
    # the only shared base name is a virtual copy, which is not a duplicate
    for fmt in ("", "1", "2", "2,novideos"):
        assert lrdb.lrphoto.select_generic(f"duplicated_names({fmt})", "").fetchall() == []
    sql = lrdb.lrphoto.select_generic("duplicated_names(2,novideos)", "", sql=True)
    assert 'i.fileFormat != "VIDEO"' in sql


def test_predefined_count_by_date(lrdb):
    rows = lrdb.lrphoto.select_generic("count_by_date(2018)", "").fetchall()
    assert rows == [("2018", 3), ("2019", 3)]
    rows = lrdb.lrphoto.select_generic("count_by_date(2018-1, 2019-1)", "").fetchall()
    assert rows == [("2018-05", 2), ("2018-07", 1)]
    rows = lrdb.lrphoto.select_generic("count_by_date(2019-1-5, 2019-1-6)", "").fetchall()
    assert rows == [("2019-01-05", 2)]


def test_criteria_dict_round_trip():
    criteria = "rating=>3, keyword=a,keyword=b,distinct"
    as_dict = criteria_to_dict(criteria)
    assert as_dict == {"rating": [">3"], "keyword": ["a", "b"], "distinct": [None]}
    assert dict_to_criteria(as_dict) == "rating=>3,keyword=a,keyword=b,distinct"
