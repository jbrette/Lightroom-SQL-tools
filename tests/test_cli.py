"""lrselect / lrsmart run as subprocesses, as scripts and as installed console commands."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Protocol

import pytest

from lrtools import __version__

ROOT = Path(__file__).parent.parent
BIN_DIR = Path(sys.executable).parent

# each tool as repo script and as console entry point (installed by uv sync)
LRSELECT_SCRIPT = [sys.executable, str(ROOT / "lrselect.py")]
LRSMART_SCRIPT = [sys.executable, str(ROOT / "lrsmart.py")]
LRSELECT = [
    pytest.param(LRSELECT_SCRIPT, id="lrselect.py"),
    pytest.param([str(BIN_DIR / "lrselect")], id="lrselect"),
]
LRSMART = [
    pytest.param(LRSMART_SCRIPT, id="lrsmart.py"),
    pytest.param([str(BIN_DIR / "lrsmart")], id="lrsmart"),
]


class Runner(Protocol):
    """Signature of the run fixture."""

    def __call__(self, cmd: list[str], *args: str) -> subprocess.CompletedProcess[str]:
        """Run cmd with args and return the completed process."""
        ...


@pytest.fixture
def run(tmp_path: Path) -> Runner:
    """Run a command from an empty directory, with no user lrtools.ini."""
    env = {**os.environ, "HOME": str(tmp_path)}

    def _run(cmd: list[str], *args: str) -> subprocess.CompletedProcess[str]:
        if not Path(cmd[0]).exists():
            pytest.skip(f"{cmd[0]} not installed (run uv sync)")
        return subprocess.run(
            [*cmd, *args],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    return _run


@pytest.mark.parametrize("cmd", LRSELECT)
def test_lrselect_results(run: Runner, catalog_path: Path, cmd: list[str]) -> None:
    """Results and count are printed for a criteria with sort."""
    result = run(cmd, "-b", str(catalog_path), "name,rating", "rating=>=3, sort=rating", "-r", "-c")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == " * Count results: 3"
    assert lines[1] == " * Results (3 entries) :"
    assert "IMG_0001.JPG" in lines[4]
    assert lines[4].rstrip().endswith("5")
    assert "IMG_0002.CR2" in lines[6]


@pytest.mark.parametrize("cmd", LRSELECT)
def test_lrselect_sql(run: Runner, catalog_path: Path, cmd: list[str]) -> None:
    """--sql prints the generated SQL."""
    result = run(cmd, "-b", str(catalog_path), "id", "rating=5", "--sql")
    assert result.returncode == 0, result.stderr
    assert "i.rating = 5" in result.stdout


def test_lrselect_collections(run: Runner, catalog_path: Path) -> None:
    """-t collection selects standard collections only."""
    result = run(
        LRSELECT_SCRIPT,
        "-b",
        str(catalog_path),
        "-t",
        "collection",
        "name",
        "type=standard",
        "-r",
    )
    assert "Holidays" in result.stdout
    assert "Best" in result.stdout
    assert "Five Stars" not in result.stdout


def test_lrselect_catalog_from_ini(run: Runner, catalog_path: Path, tmp_path: Path) -> None:
    """-b accepts an INI file naming the catalog."""
    ini = tmp_path / "my.ini"
    ini.write_text(f"[Main]\nLRCatalog = {catalog_path}\nDayFirst = True\nGeoCoder = Nominatim\n")
    result = run(LRSELECT_SCRIPT, "-b", "my.ini", "id", "flag=rejected", "-r", "-N")
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["3"]


def test_lrselect_criteria_error(run: Runner, catalog_path: Path) -> None:
    """An unknown criterion is reported on stderr."""
    result = run(LRSELECT_SCRIPT, "-b", str(catalog_path), "id", "unknown=1", "-r")
    assert ' ==> FAILED: No existent criterion "unknown"' in result.stderr


def test_lrselect_version(run: Runner) -> None:
    """--version prints the package version."""
    result = run(LRSELECT_SCRIPT, "--version")
    assert __version__ in result.stdout


@pytest.mark.parametrize("cmd", LRSMART)
def test_lrsmart_count(run: Runner, catalog_path: Path, cmd: list[str]) -> None:
    """A smart collection selected by name is counted."""
    result = run(cmd, "-b", str(catalog_path), "Five Stars", "-c")
    assert result.returncode == 0, result.stderr
    assert 'Smart Collection "Five Stars"' in result.stdout
    assert " * Count results: 1" in result.stdout


def test_lrsmart_joker_and_columns(run: Runner, catalog_path: Path) -> None:
    """The % joker runs every smart collection, with -C columns."""
    result = run(LRSMART_SCRIPT, "-b", str(catalog_path), "%", "-C", "id,name", "-r", "-N")
    assert 'Smart Collection "Canon Family"' in result.stdout
    assert 'Smart Collection "Five Stars"' in result.stdout


def test_lrsmart_from_file(run: Runner, catalog_path: Path, tmp_path: Path) -> None:
    """--file runs an exported smart collection."""
    exported = tmp_path / "videos.lrsmcol"
    exported.write_text(
        's = {\n\ttitle = "Videos",\n\tvalue = {\n\t\t{\n\t\t\tcriteria = "fileFormat",\n'
        '\t\t\toperation = "==",\n\t\t\tvalue = "VIDEO",\n\t\t},\n\t\tcombine = "intersect",\n\t},\n}\n'
    )
    result = run(LRSMART_SCRIPT, "-b", str(catalog_path), "--file", str(exported), "-c")
    assert ' * Collection name : "Videos"' in result.stdout
    assert " * Count results: 1" in result.stdout


@pytest.mark.parametrize("cmd", LRSELECT + LRSMART)
def test_closed_pipe_is_silent(tmp_path: Path, catalog_path: Path, cmd: list[str]) -> None:
    """Reader closing the pipe early (ex: | head) must not print a traceback."""
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
        assert proc.stdout is not None
        assert proc.stderr is not None
        proc.stdout.close()
        stderr = proc.stderr.read().decode()
        assert proc.wait(timeout=60) == 0, stderr
    assert stderr == ""
