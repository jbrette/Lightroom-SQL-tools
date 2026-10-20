"""
Existing bugs, kept as strict xfail: the test starts passing (and the suite fails)
once the bug is fixed, so the marker must then be removed.
"""

import subprocess
import sys

import pytest


@pytest.mark.xfail(strict=True, reason="circular import lrselectphoto -> lrselectgeneric -> lrcat -> lrselectphoto")
def test_import_lrselectphoto_first():
    result = subprocess.run(
        [sys.executable, "-c", "import lrtools.lrselectphoto"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.xfail(strict=True, reason="column extfile declares no JOIN on AgLibraryFile fi")
def test_column_extfile_alone(lrdb):
    assert lrdb.lrphoto.select_generic("extfile", "id=1").fetchall() == [("xmp",)]


@pytest.mark.xfail(strict=True, reason="count_by_date with a full date reads parts[3] instead of parts[2]")
def test_count_by_date_by_day(lrdb):
    rows = lrdb.lrphoto.select_generic("count_by_date(2019-1-5, 2019-1-6)", "").fetchall()
    assert rows == [("2019-01-05", 2)]


@pytest.mark.xfail(strict=True, reason="CriterLexer keeps spaces before an operator in unquoted values")
def test_space_before_operator(select_ids):
    # value becomes "beach " so photo 1 is not matched
    assert select_ids("keyword=beach | rating=3") == [1, 2]
