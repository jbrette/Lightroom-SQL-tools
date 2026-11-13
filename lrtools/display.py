"""SQL results display functions."""

import re
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict, Unpack

import tzlocal

type DisplayFunc = Callable[[Any], str | int]
type ColumnSpec = tuple[str, str, DisplayFunc | None]

_KILO = 1000
_MEGA = _KILO * _KILO
_GIGA = _MEGA * _KILO
_TERA = _GIGA * _KILO


def smart_unit(value: float | str | None, unit: str) -> str:
    """Convert number in smart form : KB, MB, GB, TB."""
    if value is None:
        return f"- K{unit}"
    if isinstance(value, str):
        value = int(value)
    if value > _TERA:
        return f"{(value / float(_TERA)):.2f} T{unit}"
    if value > _GIGA:
        return f"{(value / float(_GIGA)):.2f} G{unit}"
    if value > _MEGA:
        return f"{(value / float(_MEGA)):.2f} M{unit}"
    if value > _KILO:
        return f"{(value / float(_KILO)):.2f} K{unit}"
    return f"{value:.2f} {unit}"


#
# specific functions for display datas
#


def display_keywords(value: str | None) -> str:
    """Remove None from keywords."""
    if value is None:
        value = ""
    return value


def display_aperture(value: float | str) -> str:
    """Format aperture in F value."""
    return f"F{2 ** (float(value) / 2):.1f}"


def display_iso(value: float) -> str:
    """Format iso value."""
    return f"{value:.0f}"


def display_speed(value: float | str) -> str:
    """Format shutter speed value."""
    speed = 2 ** (float(value))
    if speed > 1:
        return f"1/{speed:.0f}"
    return f"{1 / speed:.0f}"


def display_boolean(value: float | None) -> str:
    """Format boolean value."""
    if value == 0:
        return "no"
    if value == 1:
        return "yes"
    return "?"


def display_date(value: str) -> str:
    """Format date : remove sub-seconds."""
    return value[:19]


def display_lrtimestamp(value: float | str) -> str:
    """Format LR timestamp (2001 based)."""
    utc = datetime(2001, 1, 1, tzinfo=UTC) + timedelta(seconds=float(value))
    return utc.astimezone(tzlocal.get_localzone()).strftime("%Y-%m-%d %H:%M:%S")


def display_duration(value: str) -> str:
    """Format video duration."""
    num, den = value.split("/")
    return seconds_tostring(int(num, 16) / int(den, 16), fract=1)


def display_flag(value: float | str) -> str:
    """Format flag (pick) value."""
    dflags = {0: "unflagged", 1: "flagged", -1: "rejected"}
    return dflags[int(value)]


def display_int(value: float | str) -> int:
    """Format integer value."""
    return int(value)


def seconds_tostring(seconds: float | str, *, fract: int = 0) -> str:
    """
    Convert seconds to string.

    format returned :
        [H:]MM:SS[.pp]
    fract : control decimals number
    """
    stime = []
    seconds = float(seconds)
    if seconds // 3600 > 0:
        stime.append(f"{int(seconds // 3600)}:")
    stime.append(f"{int((seconds // 60) % 60):02}:")
    stime.append(f"{int(seconds % 60):02}")
    if fract:
        stime.append(f"{seconds % 1:.{fract}f}"[1:])
    return "".join(stime)


#
# default columns width and display functions
#
DEFAULT_SPEC: tuple[str, DisplayFunc | None] = ("%6s", None)
DEFAULT_SPECS: dict[str, tuple[str, DisplayFunc | None]] = {
    "name": ("%-20s", None),
    "name=full": ("%-80s", None),
    "name=base": ("%-20s", None),
    "name=basext": ("%-25s", None),
    "id": ("%8s", None),
    "uuid": ("%38s", None),
    "rating": ("%1s", display_int),
    "colorlabel": ("%8s", None),
    "flag": ("%6s", display_flag),
    "datemod": ("%19s", display_lrtimestamp),
    "datehist": ("%19s", display_lrtimestamp),
    "datecapt": ("%19s", display_date),
    "modcount": ("%2s", display_int),
    "master": ("%10s", None),
    "vname": ("%10s", None),
    "stackpos": ("%3s", display_int),
    "keywords": ("%-30s", display_keywords),
    "collections": ("%-30s", None),
    "camera": ("%-15s", None),
    "camerasn": ("%-8s", None),
    "lens": ("%-25s", None),
    "iso": ("%5s", display_iso),
    "focal": ("%6s", None),
    "aperture": ("%5s", display_aperture),
    "speed": ("%6s", display_speed),
    "flash": ("%3s", display_boolean),
    "monochrome": ("%3s", display_boolean),
    "creator": ("%-18s", None),
    "caption": ("%-30s", None),
    "dims": ("%-10s", None),
    "pubcollection": ("%30s", None),
    "pubname": ("%30s", None),
    "pubtime": ("%19s", display_lrtimestamp),
    "latitude": ("%-18s", None),
    "longitude": ("%-18s", None),
    "duration": ("%5s", display_duration),
    "filesize": ("%8s", None),  # pseudo column
}
DEFAULT_SEPARATOR = " | "


class DisplayOptions(TypedDict, total=False):
    """Keyword options of display_results."""

    max_lines: int
    header: bool
    indent: int
    widths: str | list[str] | None
    separator: str
    raw_print: bool
    filesize: bool


def prepare_display_columns(columns: Sequence[str], widths: Sequence[str]) -> dict[int, ColumnSpec]:
    """
    Prepare columns to display : set width and specific display functions.

    - columns : ([str]) columns names as defined by LRSelectPhotos
    - widths : ([str]) width of each column, comma separated (ex: "15,-50")
    """
    column_spec: dict[int, ColumnSpec] = {}
    for num_col, raw_name in enumerate(columns):
        name = raw_name.strip()
        if not name:
            continue
        width, func = DEFAULT_SPECS.get(name, DEFAULT_SPEC)
        # chance to change widths from outside
        if num_col < len(widths):
            width = f"%{widths[num_col].strip()}s"
        column_spec[num_col] = (name, width, func)
    return column_spec


def _file_size(fname: str) -> int | None:
    """Return size of file, None if not readable."""
    try:
        return Path(fname).stat().st_size
    except OSError:
        return None


def _filesize_indexes(columns: Sequence[str]) -> tuple[int, int]:
    """Return index of full name in rows, and index of the filesize column to insert."""
    columns_lr = list(columns)
    columns_lr.remove("filesize")
    return columns_lr.index("name=full"), list(columns).index("filesize")


def _print_header(column_spec: dict[int, ColumnSpec], indent: int, separator: str) -> None:
    """Print column names and underline."""
    total_width = 0
    line = []
    for name, width, _ in column_spec.values():
        match = re.search(r"(\d+)s", width)
        val_width = int(match.group(1)) if match else 8
        total_width += val_width
        line.append(width % name[:val_width])
    print(indent * " ", separator.join(line), sep="")
    print(
        indent * " ",
        (total_width + (len(column_spec) - 1) * len(separator)) * "=",
        sep="",
    )


def _format_row(
    row: Sequence[Any], column_spec: dict[int, ColumnSpec], *, raw_print: bool
) -> list[str]:
    """Format each visible value of a row."""
    line = []
    for num_col, value in enumerate(row):
        try:
            _, width, func_format = column_spec[num_col]
        except KeyError:
            # invisible column (ex: criteria width/heightCropped)
            continue
        display_value = value
        if not raw_print:
            if value is None:
                display_value = ""
            elif func_format:
                display_value = func_format(value)
        line.append(width % display_value)
    return line


def _to_list(value: str | Sequence[str]) -> list[str]:
    """Split a comma separated string, or copy a list."""
    if isinstance(value, str):
        return [a.strip() for a in value.split(",")]
    return list(value)


def _lines_to_display(wanted_lines: int, nrows: int, *, header: bool) -> int:
    """Return the number of rows to display, print the count header."""
    if wanted_lines < 0:
        wanted_lines = sys.maxsize
    if wanted_lines >= nrows:
        if header:
            print(f" * Results ({nrows} entries) :")
        return nrows
    if header:
        print(f" * Results (first {wanted_lines} entries of {nrows}) :")
    return wanted_lines


def display_results(
    rows: Sequence[Sequence[Any]],
    columns: str | Sequence[str],
    **kwargs: Unpack[DisplayOptions],
) -> None:
    """
    Display SQL results.

    - rows : SQL colummns
    - columns : column names to display ("filesize" column can be specified for compute filesize )
    - kwargs :
       * max_lines : max lines to display
       * header : display header (columns names)
       * indent : number of indentation space on each line
       * widths : widths of columns
       * separator : characters separator between columns
       * raw_print : print raw value (for columns aperture, shutter speed, ido, dates)
       * filesize : compute and add column filesize
    """
    header = kwargs.get("header", True)
    if not rows:
        if header:
            print(" * None data result")
        return

    columns = _to_list(columns)
    widths = _to_list(kwargs.get("widths") or [])
    indent = kwargs.get("indent", 4)
    separator = kwargs.get("separator", DEFAULT_SEPARATOR)
    max_lines = _lines_to_display(kwargs.get("max_lines", sys.maxsize), len(rows), header=header)

    column_spec = prepare_display_columns(columns, widths)

    # basic check : detect if suffisant column
    for i in range(len(rows[0])):
        if i < len(column_spec):
            continue
        column_spec[i] = (f"column{i}", DEFAULT_SPEC[0], DEFAULT_SPEC[1])

    if header:
        _print_header(column_spec, indent, separator)

    # display datas
    filesize = kwargs.get("filesize", False)
    total_filesize = 0
    id_fname, id_filesize = _filesize_indexes(columns) if filesize else (0, 0)
    for row in rows[:max_lines]:
        values: Sequence[Any] = row
        if filesize:
            size = _file_size(row[id_fname]) or 0
            total_filesize += size
            with_size = [*row]
            with_size.insert(id_filesize, size)
            values = with_size
        line = _format_row(values, column_spec, raw_print=kwargs.get("raw_print", False))
        print(indent * " ", separator.join(line), sep="")

    # datas displayed, but maybe still filesize to compute
    if filesize:
        total_filesize += sum(_file_size(row[id_fname]) or 0 for row in rows[max_lines:])
        print(f" * Total filesize : {smart_unit(total_filesize, 'B')} ({total_filesize} bytes)")
