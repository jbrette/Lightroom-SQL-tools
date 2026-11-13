"""LRCatDB: catalog opening and hand-written queries; LRKeywords; LRSelectCollection."""

import sqlite3
from typing import TYPE_CHECKING

import pytest

from lrtools.lrcat import LRCatDB, LRCatException
from lrtools.lrkeyword import LRKeywords
from lrtools.lrselectcollection import LRSelectCollection

if TYPE_CHECKING:
    from pathlib import Path

    from lrtools.lrtoolconfig import LRToolConfig


def test_open_reads_db_version(lrdb: LRCatDB) -> None:
    """Opening reads the catalog version from Adobe_variablesTable."""
    assert lrdb.lrdb_version == "1303001"


def test_open_is_read_only(lrdb: LRCatDB) -> None:
    """The catalog is opened read-only."""
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        lrdb.cursor.execute("DELETE FROM Adobe_images")


def test_open_missing_catalog(config: LRToolConfig, tmp_path: Path) -> None:
    """Opening a missing file raises LRCatException."""
    with pytest.raises(LRCatException, match="doesn't exist"):
        LRCatDB(config, str(tmp_path / "missing.lrcat"))


def test_open_not_a_catalog(config: LRToolConfig, tmp_path: Path) -> None:
    """Opening an SQLite file that is not a catalog raises LRCatException."""
    path = tmp_path / "other.lrcat"
    sqlite3.connect(path).execute("CREATE TABLE t (x)").connection.close()
    with pytest.raises(LRCatException, match="Unable to open"):
        LRCatDB(config, str(path))


def test_has_basename(lrdb: LRCatDB) -> None:
    """has_basename tells whether a file base name exists."""
    assert lrdb.has_basename("IMG_0001")
    assert not lrdb.has_basename("IMG_9999")


def test_select_vcopies_master(lrdb: LRCatDB) -> None:
    """select_vcopies_master returns the master and its virtual copies."""
    rows = lrdb.select_vcopies_master(1, "id,vname").fetchall()
    assert rows == [(1, None), (5, "Copy 1")]


def test_select_collections(lrdb: LRCatDB) -> None:
    """select_collections filters by type and name."""
    assert [name for _, name, _ in lrdb.select_collections(lrdb.STND_COLL)] == ["Best", "Holidays"]
    assert [name for _, name, _ in lrdb.select_collections(lrdb.SMART_COLL)] == [
        "Canon Family",
        "Five Stars",
    ]
    assert len(lrdb.select_collections(lrdb.ALL_COLL)) == 4
    assert [name for _, name, _ in lrdb.select_collections(lrdb.ALL_COLL, "h%")] == ["Holidays"]
    assert [name for _, name, _ in lrdb.select_collections(lrdb.ALL_COLL, "best")] == ["Best"]


def test_hierarchical_collections(lrdb: LRCatDB) -> None:
    """hierarchical_collections returns name paths."""
    names = [hname for hname, _, _ in lrdb.hierarchical_collections()]
    assert names == [["Best"], ["Canon Family"], ["Five Stars"], ["Holidays"]]


def test_get_smartcoll_data(lrdb: LRCatDB) -> None:
    """get_smartcoll_data accepts an id or a name, decoded or raw."""
    assert lrdb.get_smartcoll_data(12) == lrdb.get_smartcoll_data("Five Stars")
    raw = lrdb.get_smartcoll_data("Five Stars", raw_value=True)
    assert isinstance(raw, str)
    assert raw.startswith("s = {")
    assert lrdb.get_smartcoll_data("Nope") is None


def test_select_imports(lrdb: LRCatDB) -> None:
    """select_imports lists imports with their photo count."""
    assert lrdb.select_imports().fetchall() == [(1, "2018-08-01T10:00:00", 2)]
    assert lrdb.select_imports(1).fetchall() == [(1, "2018-08-01T10:00:00", 2)]


def test_select_duplicates_invalid_format(lrdb: LRCatDB) -> None:
    """select_duplicates rejects an unknown format."""
    with pytest.raises(LRCatException, match="Invalid format"):
        lrdb.select_duplicates("3")


def test_get_xmp(lrdb: LRCatDB) -> None:
    """get_xmp accepts a photo id or a base name."""
    assert lrdb.get_xmp(1) == [("<x:xmpmeta/>",)]
    assert lrdb.get_xmp("IMG_0002") == [("",)]


#
# keywords
#


def test_keywords_hierarchy(lrdb: LRCatDB) -> None:
    """LRKeywords resolves hierarchical names and ids."""
    keywords = LRKeywords(lrdb)
    assert keywords.get_hierarchical_list() == ["Alice", "Places", "Places|beach", "family"]
    assert keywords.get_hierarchical_name(3) == "Places|beach"
    assert keywords.get_name(3) == "beach"
    assert keywords.get_id("Places|beach") == 3


def test_keywords_photo_keys(lrdb: LRCatDB) -> None:
    """LRKeywords lists a photo keywords and the persons."""
    keywords = LRKeywords(lrdb)
    assert keywords.photo_keys(1) == (["Places|beach", "family"], ["beach", "family"])
    assert keywords.all_persons() == [("Alice",)]


@pytest.mark.parametrize(
    ("key_part", "operation", "expected"),
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
def test_keywords_hierachical_indexes(
    lrdb: LRCatDB, key_part: str, operation: str, expected: list[int]
) -> None:
    """hierachical_indexes matches keyword names by operation."""
    assert sorted(LRKeywords(lrdb).hierachical_indexes(key_part, operation)) == expected


#
# collections select
#


@pytest.mark.parametrize(
    ("columns", "criteria", "expected"),
    [
        ("name", "type=standard", [("Holidays",), ("Best",)]),
        ("name", "type=smart", [("Five Stars",), ("Canon Family",)]),
        ("id,name", "name=Best", [(11, "Best")]),
        ("name,type", "id=12", [("Five Stars", "com.adobe.ag.library.smart_collection")]),
        ("name", "type=all", [("Holidays",), ("Best",), ("Five Stars",), ("Canon Family",)]),
    ],
)
def test_select_collection(
    config: LRToolConfig,
    lrdb: LRCatDB,
    columns: str,
    criteria: str,
    expected: list[tuple[str | int, ...]],
) -> None:
    """LRSelectCollection selects collections by columns and criteria."""
    rows = LRSelectCollection(config, lrdb).select_generic(columns, criteria).fetchall()
    assert rows == expected


def test_select_collection_smart_content(config: LRToolConfig, lrdb: LRCatDB) -> None:
    """The smart column returns the smart collection definition."""
    rows = (
        LRSelectCollection(config, lrdb).select_generic("name,smart", "name4smart=Five%").fetchall()
    )
    assert len(rows) == 1
    assert rows[0][0] == "Five Stars"
    assert 'criteria = "rating"' in rows[0][1]
