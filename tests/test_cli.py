"""lrselect / lrsmart run as subprocesses, as scripts and as installed console commands"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
BIN_DIR = Path(sys.executable).parent

# each tool as repo script and as console entry point (installed by uv sync)
LRSELECT = [
    pytest.param([sys.executable, str(ROOT / "lrselect.py")], id="lrselect.py"),
    pytest.param([str(BIN_DIR / "lrselect")], id="lrselect"),
]
LRSMART = [
    pytest.param([sys.executable, str(ROOT / "lrsmart.py")], id="lrsmart.py"),
    pytest.param([str(BIN_DIR / "lrsmart")], id="lrsmart"),
]


@pytest.fixture
def run(tmp_path):
    """run a command from an empty directory, with no user lrtools.ini"""
    env = {**os.environ, "HOME": str(tmp_path)}

    def _run(cmd, *args):
        if not Path(cmd[0]).exists():
            pytest.skip(f"{cmd[0]} not installed (run uv sync)")
        return subprocess.run(
            [*cmd, *args], cwd=tmp_path, env=env, capture_output=True, text=True, check=False, timeout=60
        )

    return _run


@pytest.mark.parametrize("cmd", LRSELECT)
def test_lrselect_results(run, catalog_path, cmd):
    result = run(cmd, "-b", str(catalog_path), "name,rating", "rating=>=3, sort=rating", "-r", "-c")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == " * Count results: 3"
    assert lines[1] == " * Results (3 entries) :"
    assert "IMG_0001.JPG" in lines[4] and lines[4].rstrip().endswith("5")
    assert "IMG_0002.CR2" in lines[6]


@pytest.mark.parametrize("cmd", LRSELECT)
def test_lrselect_sql(run, catalog_path, cmd):
    result = run(cmd, "-b", str(catalog_path), "id", "rating=5", "--sql")
    assert result.returncode == 0, result.stderr
    assert "i.rating = 5" in result.stdout


def test_lrselect_collections(run, catalog_path):
    result = run(LRSELECT[0].values[0], "-b", str(catalog_path), "-t", "collection", "name", "type=standard", "-r")
    assert "Holidays" in result.stdout and "Best" in result.stdout
    assert "Five Stars" not in result.stdout


def test_lrselect_catalog_from_ini(run, catalog_path, tmp_path):
    ini = tmp_path / "my.ini"
    ini.write_text(f"[Main]\nLRCatalog = {catalog_path}\nDayFirst = True\nGeoCoder = Nominatim\n")
    result = run(LRSELECT[0].values[0], "-b", "my.ini", "id", "flag=rejected", "-r", "-N")
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["3"]


def test_lrselect_criteria_error(run, catalog_path):
    result = run(LRSELECT[0].values[0], "-b", str(catalog_path), "id", "unknown=1", "-r")
    assert ' ==> FAILED: No existent criterion "unknown"' in result.stderr


def test_lrselect_version(run):
    from lrtools import __version__  # pylint: disable=import-outside-toplevel

    result = run(LRSELECT[0].values[0], "--version")
    assert __version__ in result.stdout


@pytest.mark.parametrize("cmd", LRSMART)
def test_lrsmart_count(run, catalog_path, cmd):
    result = run(cmd, "-b", str(catalog_path), "Five Stars", "-c")
    assert result.returncode == 0, result.stderr
    assert 'Smart Collection "Five Stars"' in result.stdout
    assert " * Count results: 1" in result.stdout


def test_lrsmart_joker_and_columns(run, catalog_path):
    result = run(LRSMART[0].values[0], "-b", str(catalog_path), "%", "-C", "id,name", "-r", "-N")
    assert 'Smart Collection "Canon Family"' in result.stdout
    assert 'Smart Collection "Five Stars"' in result.stdout


def test_lrsmart_from_file(run, catalog_path, tmp_path):
    exported = tmp_path / "videos.lrsmcol"
    exported.write_text(
        's = {\n\ttitle = "Videos",\n\tvalue = {\n\t\t{\n\t\t\tcriteria = "fileFormat",\n'
        '\t\t\toperation = "==",\n\t\t\tvalue = "VIDEO",\n\t\t},\n\t\tcombine = "intersect",\n\t},\n}\n'
    )
    result = run(LRSMART[0].values[0], "-b", str(catalog_path), "--file", str(exported), "-c")
    assert ' * Collection name : "Videos"' in result.stdout
    assert " * Count results: 1" in result.stdout


@pytest.mark.parametrize("cmd", LRSELECT + LRSMART)
def test_closed_pipe_is_silent(tmp_path, catalog_path, cmd):
    """reader closing the pipe early (ex: | head) must not print a traceback"""
    if not Path(cmd[0]).exists():
        pytest.skip(f"{cmd[0]} not installed (run uv sync)")
    args = ["%", "-r"] if "lrsmart" in str(cmd[-1]) else ["name", "", "-r"]
    with subprocess.Popen(
        [*cmd, "-b", str(catalog_path), *args],
        cwd=tmp_path,
        env={**os.environ, "HOME": str(tmp_path)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        # close before the process writes anything
        proc.stdout.close()
        stderr = proc.stderr.read().decode()
        assert proc.wait(timeout=60) == 0, stderr
    assert stderr == ""
