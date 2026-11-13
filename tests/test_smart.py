"""SQLSmartColl: smart collection definitions translated to SQL and executed."""

from typing import TYPE_CHECKING

import pytest

from lrtools.lrsmartcoll import SmartException, SQLSmartColl, select_smart
from lrtools.slpp import LuaTable

if TYPE_CHECKING:
    from pathlib import Path

    from lrtools.lrcat import LRCatDB
    from lrtools.lrtoolconfig import LRToolConfig

# a smart collection criterion, as decoded from Lua
type Criterion = LuaTable


def run_smart(
    config: LRToolConfig,
    lrdb: LRCatDB,
    *criteria: Criterion,
    combine: str = "intersect",
    columns: str = "id",
) -> list[int]:
    """Build smart collection from criteria dicts, return sorted distinct ids."""
    smart: LuaTable = dict(enumerate(criteria))
    smart["combine"] = combine
    sql = SQLSmartColl(config, lrdb, smart).build_sql(columns)
    return sorted({row[0] for row in lrdb.cursor.execute(sql).fetchall()})


def crit(
    criteria: str,
    operation: str,
    value: str | float | None = None,
    value2: str | float | None = None,
    **extra: str | float,
) -> Criterion:
    """Return a smart collection criterion as decoded from Lua."""
    func: Criterion = {"criteria": criteria, "operation": operation, "value": value, **extra}
    if value2 is not None:
        func["value2"] = value2
    return func


@pytest.mark.parametrize(
    ("criterion", "expected"),
    [
        (crit("rating", ">=", 5), [1]),
        (crit("rating", "<", 3), [3, 4, 6]),
        (crit("rating", "==", 3), [2]),
        (crit("camera", "any", "canon"), [1, 2, 5]),
        (crit("camera", "==", "NIKON D750"), [3, 4]),
        (crit("lens", "any", "70-200mm"), [2]),
        (crit("isoSpeedRating", ">=", 1600), [2, 3, 4]),
        (crit("focalLength", "in", 40, 100), [1, 5]),
        (crit("aperture", "==", 6), [1, 5]),
        (crit("shutterSpeed", ">=", 9), [2]),  # operator inverted: slower than ~1/500
        (crit("hasGPSData", "==", value=True), [1, 2, 5]),
        (crit("hasGPSData", "==", value=False), [3, 4, 6]),
        (crit("flashFired", "==", value=True), [2]),
        (crit("fileFormat", "==", "VIDEO"), [6]),
        (crit("fileFormat", "!=", "VIDEO"), [1, 2, 3, 4, 5]),
        (crit("captureTime", "in", "2018-01-01", "2018-06-30"), [1, 5]),
        (crit("captureTime", ">", "2018-12-31"), [3, 4, 6]),
        (crit("touchTime", "in", "2019-08-01", "2019-08-31"), [1]),
        (crit("aspectRatio", "==", "portrait"), [2]),
        (crit("aspectRatio", "!=", "portrait"), [1, 3, 4, 5, 6]),
        (crit("keywords", "any", "family"), [1, 2]),
        (crit("keywords", "any", "places"), [1]),  # includes child keywords
        (crit("keywords", "all", "family beach"), [1]),
        (crit("keywords", "words", "beach"), [1]),
        (crit("keywords", "noneOf", "family"), [3, 4, 5, 6]),
        (crit("keywords", "empty"), [3, 4, 5, 6]),
        (crit("keywords", "notEmpty"), [1, 2]),
        (crit("collection", "all", "Holidays"), [1, 2]),
        (crit("collection", "beginsWith", "Be"), [2]),
        (crit("collection", "noneOf", "Best"), [1, 3, 4, 5, 6]),
        (crit("folder", "any", "2019"), [3, 4, 6]),
        (crit("copyname", "any", "copy"), [5]),
    ],
)
def test_criterion(
    config: LRToolConfig, lrdb: LRCatDB, criterion: Criterion, expected: list[int]
) -> None:
    """Each smart collection criterion selects the expected photos."""
    assert run_smart(config, lrdb, criterion) == expected


def test_combine_intersect(config: LRToolConfig, lrdb: LRCatDB) -> None:
    """combine=intersect keeps photos matching every criterion."""
    ids = run_smart(config, lrdb, crit("camera", "any", "canon"), crit("rating", ">=", 4))
    assert ids == [1, 5]


def test_combine_union(config: LRToolConfig, lrdb: LRCatDB) -> None:
    """combine=union keeps photos matching any criterion."""
    ids = run_smart(
        config, lrdb, crit("rating", "==", 5), crit("fileFormat", "==", "VIDEO"), combine="union"
    )
    assert ids == [1, 6]


def test_cropped_size_needs_dims_column(config: LRToolConfig, lrdb: LRCatDB) -> None:
    """Cropped size criteria need the dims column."""
    criterion = crit("widthCropped", ">=", 5000)
    assert run_smart(config, lrdb, criterion, columns="id,dims") == [3, 4, 5]
    with pytest.raises(SmartException, match="dims"):
        run_smart(config, lrdb, crit("widthCropped", ">=", 5000))


@pytest.mark.parametrize(
    ("criterion", "message"),
    [
        (crit("unknownCriteria", "=="), "criteria unsupported"),
        (crit("rating", "between", 1), "operation unsupported"),
        (crit("aspectRatio", "==", "round"), "value unsupported"),
    ],
)
def test_unsupported(
    config: LRToolConfig, lrdb: LRCatDB, criterion: Criterion, message: str
) -> None:
    """Unsupported criteria, operations and values raise SmartException."""
    with pytest.raises(SmartException, match=message):
        run_smart(config, lrdb, criterion)


def test_unsupported_combine(config: LRToolConfig, lrdb: LRCatDB) -> None:
    """An unknown combine raises SmartException."""
    with pytest.raises(SmartException, match="combine"):
        run_smart(config, lrdb, crit("rating", "==", 5), crit("rating", "==", 3), combine="xor")


def test_smart_from_catalog(config: LRToolConfig, lrdb: LRCatDB) -> None:
    """A smart collection is read from the catalog and executed."""
    smart = lrdb.get_smartcoll_data("Five Stars")
    assert smart == {
        0: {"criteria": "rating", "operation": ">=", "value": 5},
        "combine": "intersect",
    }
    rows = select_smart(config, lrdb, "Five Stars", "id,rating")
    assert rows == [(1, 5)]


def test_select_smart_sort_and_sql(config: LRToolConfig, lrdb: LRCatDB) -> None:
    """select_smart sorts rows and can return the SQL only."""
    rows = select_smart(config, lrdb, "Canon Family", "id", sort_column="-id")
    assert rows == [(2,), (1,)]
    sql = select_smart(config, lrdb, "Canon Family", "id", sql_only=True)
    assert sql.startswith("SELECT")
    assert "INTERSECT" in sql


def test_select_smart_from_file(config: LRToolConfig, lrdb: LRCatDB, tmp_path: Path) -> None:
    """select_smart runs an exported .lrsmcol file."""
    exported = tmp_path / "export.lrsmcol"
    exported.write_text(
        's = {\n\tid = "x",\n\tinternalName = "Videos",\n\ttitle = "Videos",\n\ttype = "LibrarySmartCollection",\n'
        '\tvalue = {\n\t\t{\n\t\t\tcriteria = "fileFormat",\n\t\t\toperation = "==",\n\t\t\tvalue = "VIDEO",\n\t\t},\n'
        '\t\tcombine = "intersect",\n\t},\n\tversion = 0,\n}\n',
        encoding="utf-8",
    )
    assert select_smart(config, lrdb, str(exported), "id", is_file=True) == [(6,)]


def test_select_smart_not_found(config: LRToolConfig, lrdb: LRCatDB) -> None:
    """An unknown smart collection raises SmartException."""
    with pytest.raises(SmartException, match="not found"):
        select_smart(config, lrdb, "Nope", "id")
