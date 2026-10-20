"""LRCatDB: catalog opening and hand-written queries; LRKeywords; LRSelectCollection"""

import sqlite3

import pytest

from lrtools.lrcat import LRCatDB, LRCatException
from lrtools.lrkeyword import LRKeywords
from lrtools.lrselectcollection import LRSelectCollection


def test_open_reads_db_version(lrdb):
    assert lrdb.lrdb_version == "1303001"


def test_open_is_read_only(lrdb):
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        lrdb.cursor.execute("DELETE FROM Adobe_images")


def test_open_missing_catalog(config, tmp_path):
    with pytest.raises(LRCatException, match="doesn't exist"):
        LRCatDB(config, str(tmp_path / "missing.lrcat"))


def test_open_not_a_catalog(config, tmp_path):
    path = tmp_path / "other.lrcat"
    sqlite3.connect(path).execute("CREATE TABLE t (x)").connection.close()
    with pytest.raises(LRCatException, match="Unable to open"):
        LRCatDB(config, str(path))


def test_has_basename(lrdb):
    assert lrdb.has_basename("IMG_0001")
    assert not lrdb.has_basename("IMG_9999")


def test_select_vcopies_master(lrdb):
    rows = lrdb.select_vcopies_master(1, "id,vname").fetchall()
    assert rows == [(1, None), (5, "Copy 1")]


def test_select_collections(lrdb):
    assert [name for _, name, _ in lrdb.select_collections(lrdb.STND_COLL)] == ["Best", "Holidays"]
    assert [name for _, name, _ in lrdb.select_collections(lrdb.SMART_COLL)] == ["Canon Family", "Five Stars"]
    assert len(lrdb.select_collections(lrdb.ALL_COLL)) == 4
    assert [name for _, name, _ in lrdb.select_collections(lrdb.ALL_COLL, "h%")] == ["Holidays"]
    assert [name for _, name, _ in lrdb.select_collections(lrdb.ALL_COLL, "best")] == ["Best"]


def test_hierarchical_collections(lrdb):
    names = [hname for hname, _, _ in lrdb.hierarchical_collections()]
    assert names == [["Best"], ["Canon Family"], ["Five Stars"], ["Holidays"]]


def test_get_smartcoll_data(lrdb):
    assert lrdb.get_smartcoll_data(12) == lrdb.get_smartcoll_data("Five Stars")
    assert lrdb.get_smartcoll_data("Five Stars", raw_value=True).startswith("s = {")
    assert lrdb.get_smartcoll_data("Nope") is None


def test_select_imports(lrdb):
    assert lrdb.select_imports().fetchall() == [(1, "2018-08-01T10:00:00", 2)]
    assert lrdb.select_imports(1).fetchall() == [(1, "2018-08-01T10:00:00", 2)]


def test_select_duplicates_invalid_format(lrdb):
    with pytest.raises(LRCatException, match="Invalid format"):
        lrdb.select_duplicates("3")


def test_get_xmp(lrdb):
    assert lrdb.get_xmp(1) == [("<x:xmpmeta/>",)]
    assert lrdb.get_xmp("IMG_0002") == [("",)]


#
# keywords
#


def test_keywords_hierarchy(lrdb):
    keywords = LRKeywords(lrdb)
    assert keywords.get_hierarchical_list() == ["Alice", "Places", "Places|beach", "family"]
    assert keywords.get_hierarchical_name(3) == "Places|beach"
    assert keywords.get_name(3) == "beach"
    assert keywords.get_id("Places|beach") == 3


def test_keywords_photo_keys(lrdb):
    keywords = LRKeywords(lrdb)
    assert keywords.photo_keys(1) == (["Places|beach", "family"], ["beach", "family"])
    assert keywords.all_persons() == [("Alice",)]


@pytest.mark.parametrize(
    "key_part, operation, expected",
    [
        ("places", "any", [2, 3]),
        ("bea", "any", [3]),
        ("bea", "words", []),
        ("beach", "words", [3]),
        ("fam", "beginsWith", [4]),
        ("ily", "endsWith", [4]),
        ("none", "any", []),
    ],
)
def test_keywords_hierachical_indexes(lrdb, key_part, operation, expected):
    assert sorted(LRKeywords(lrdb).hierachical_indexes(key_part, operation)) == expected


#
# collections select
#


@pytest.mark.parametrize(
    "columns, criteria, expected",
    [
        ("name", "type=standard", [("Holidays",), ("Best",)]),
        ("name", "type=smart", [("Five Stars",), ("Canon Family",)]),
        ("id,name", "name=Best", [(11, "Best")]),
        ("name,type", "id=12", [("Five Stars", "com.adobe.ag.library.smart_collection")]),
        ("name", "type=all", [("Holidays",), ("Best",), ("Five Stars",), ("Canon Family",)]),
    ],
)
def test_select_collection(config, lrdb, columns, criteria, expected):
    rows = LRSelectCollection(config, lrdb).select_generic(columns, criteria).fetchall()
    assert rows == expected


def test_select_collection_smart_content(config, lrdb):
    rows = LRSelectCollection(config, lrdb).select_generic("name,smart", "name4smart=Five%").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "Five Stars"
    assert 'criteria = "rating"' in rows[0][1]
