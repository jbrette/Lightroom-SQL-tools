"""SQLSmartColl: smart collection definitions translated to SQL and executed"""

import pytest

from lrtools.lrsmartcoll import SQLSmartColl, SmartException, select_smart


def run_smart(config, lrdb, *criteria, combine="intersect", columns="id"):
    """build smart collection from criteria dicts, return sorted distinct ids"""
    smart = dict(enumerate(criteria))
    smart["combine"] = combine
    sql = SQLSmartColl(config, lrdb, smart).build_sql(columns)
    return sorted({row[0] for row in lrdb.cursor.execute(sql).fetchall()})


def crit(criteria, operation, value=None, value2=None, **extra):
    """smart collection criterion as decoded from Lua"""
    func = {"criteria": criteria, "operation": operation, "value": value, **extra}
    if value2 is not None:
        func["value2"] = value2
    return func


@pytest.mark.parametrize(
    "criterion, expected",
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
        (crit("hasGPSData", "==", True), [1, 2, 5]),
        (crit("hasGPSData", "==", False), [3, 4, 6]),
        (crit("flashFired", "==", True), [2]),
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
def test_criterion(config, lrdb, criterion, expected):
    assert run_smart(config, lrdb, criterion) == expected


def test_combine_intersect(config, lrdb):
    ids = run_smart(config, lrdb, crit("camera", "any", "canon"), crit("rating", ">=", 4))
    assert ids == [1, 5]


def test_combine_union(config, lrdb):
    ids = run_smart(
        config, lrdb, crit("rating", "==", 5), crit("fileFormat", "==", "VIDEO"), combine="union"
    )
    assert ids == [1, 6]


def test_cropped_size_needs_dims_column(config, lrdb):
    criterion = crit("widthCropped", ">=", 5000)
    assert run_smart(config, lrdb, criterion, columns="id,dims") == [3, 4, 5]
    with pytest.raises(SmartException, match="dims"):
        run_smart(config, lrdb, crit("widthCropped", ">=", 5000))


@pytest.mark.parametrize(
    "criterion, message",
    [
        (crit("unknownCriteria", "=="), "criteria unsupported"),
        (crit("rating", "between", 1), "operation unsupported"),
        (crit("aspectRatio", "==", "round"), "value unsupported"),
    ],
)
def test_unsupported(config, lrdb, criterion, message):
    with pytest.raises(SmartException, match=message):
        run_smart(config, lrdb, criterion)


def test_unsupported_combine(config, lrdb):
    with pytest.raises(SmartException, match="combine"):
        run_smart(config, lrdb, crit("rating", "==", 5), crit("rating", "==", 3), combine="xor")


def test_smart_from_catalog(config, lrdb):
    smart = lrdb.get_smartcoll_data("Five Stars")
    assert smart == {0: {"criteria": "rating", "operation": ">=", "value": 5}, "combine": "intersect"}
    rows = select_smart(config, lrdb, "Five Stars", "id,rating")
    assert rows == [(1, 5)]


def test_select_smart_sort_and_sql(config, lrdb):
    rows = select_smart(config, lrdb, "Canon Family", "id", sort_column="-id")
    assert rows == [(2,), (1,)]
    sql = select_smart(config, lrdb, "Canon Family", "id", sql_only=True)
    assert sql.startswith("SELECT") and "INTERSECT" in sql


def test_select_smart_from_file(config, lrdb, tmp_path):
    exported = tmp_path / "export.lrsmcol"
    exported.write_text(
        's = {\n\tid = "x",\n\tinternalName = "Videos",\n\ttitle = "Videos",\n\ttype = "LibrarySmartCollection",\n'
        '\tvalue = {\n\t\t{\n\t\t\tcriteria = "fileFormat",\n\t\t\toperation = "==",\n\t\t\tvalue = "VIDEO",\n\t\t},\n'
        '\t\tcombine = "intersect",\n\t},\n\tversion = 0,\n}\n',
        encoding="utf-8",
    )
    assert select_smart(config, lrdb, str(exported), "id", is_file=True) == [(6,)]


def test_select_smart_not_found(config, lrdb):
    with pytest.raises(SmartException, match="not found"):
        select_smart(config, lrdb, "Nope", "id")
