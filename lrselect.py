#!/usr/bin/env python
"""Select photos from Lightroom catalog."""

import argparse
import errno
import logging
import os
import sqlite3
import sys
from argparse import RawTextHelpFormatter
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lrtools._version import __version__
from lrtools.display import display_results
from lrtools.lrcat import LRCatDB, LRCatException
from lrtools.lrselectcollection import LRSelectCollection
from lrtools.lrselectgeneric import LRSelectException, LRSelectGeneric
from lrtools.lrselectphoto import LRSelectPhoto
from lrtools.lrtoolconfig import LRConfigException, LRToolConfig

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_COLUMNS = "name,datecapt"

log = logging.getLogger()


def doc_columns_criteria(func: Callable[..., Any]) -> str:
    """Return the columns and criteria part of the docstring of `func`."""
    doc_func = func.__doc__ or ""
    start = doc_func.find("columns :")
    start = doc_func.rfind("\n", 0, start)
    end = doc_func.find("kwargs :")
    return doc_func[start:end]


def build_parser(config: LRToolConfig) -> argparse.ArgumentParser:
    """Build the command line parser, its help based on doc strings."""
    description = (
        "Select elements from SQL table from Lightroom catalog.\n\n"
        'For photo : specify the "columns" to display and the "criteria of selection in :'
    )
    # add part of help for function LRSelectPhoto.select_generic
    description += doc_columns_criteria(LRSelectPhoto.select_generic)
    # add part of help for function LRSelectCollection.select_generic
    description += '\nFor collection (use "-t collection") : specify the "columns" to display and the "criteria" of selection in :'
    description += doc_columns_criteria(LRSelectCollection.select_generic)
    # complete help
    description += '\nFile sizes can be computed/displayed via the pseudo column "filesize", or option "--filesize".\n'
    description += (
        "\nExamples:\n"
        '\tlrselect.py --sql --results "name=basext,datecapt" "rating=>4,videos=0"\n'
        '\tlrselect.py  "name,datecapt,latitude,longitude,keywords" "rating=>4,videos=0" --results --count\n'
        '\tlrselect.py  "datecapt,filesize" "rating=>4,videos=0" --results'
    )

    parser = argparse.ArgumentParser(description=description, formatter_class=RawTextHelpFormatter)
    parser.add_argument("columns", help="Columns to display", default=DEFAULT_COLUMNS, nargs="?")
    parser.add_argument("criteria", help="Criteria of select", nargs="?")
    parser.add_argument(
        "-b",
        "--lrcat",
        default=config.default_lrcat,
        help='Ligthroom catalog file for database request (default:"%(default)s"), or INI file (lrtools.ini form)',
    )
    parser.add_argument("-s", "--sql", action="store_true", help="Display SQL request")
    parser.add_argument("-c", "--count", action="store_true", help="Display count of results")
    parser.add_argument("-r", "--results", action="store_true", help="Display datas results")
    parser.add_argument(
        "-z",
        "--filesize",
        action="store_true",
        help='Compute and display files size selection. Alternative: add a column "filesize"',
    )
    parser.add_argument(
        "-n",
        "--max-lines",
        type=int,
        default=-1,
        help="Max number of results to display (-1 means all results)",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="UUIDs photos file : replace the criteria parameter which is ignored",
    )
    parser.add_argument(
        "-t",
        "--table",
        choices=["photo", "collection"],
        default="photo",
        help="table to work on : photo or collection",
    )
    parser.add_argument(
        "-N",
        "--no-header",
        action="store_true",
        help="don't print header (photos count ans columns names)",
    )
    parser.add_argument(
        "-w",
        "--widths",
        help="Widths of columns to display widths (ex:30,-50,10)",
    )
    parser.add_argument(
        "-S",
        "--separator",
        default=" | ",
        help='separator string between columns (default:"%(default)s")',
    )
    parser.add_argument(
        "-I",
        "--indent",
        type=int,
        default=4,
        help='space indentation in output (default:"%(default)s")',
    )
    parser.add_argument(
        "--raw-print",
        action="store_true",
        help="print raw value (for speed, aperture columns)",
    )
    parser.add_argument("--log", help="log on file")
    parser.add_argument("--version", "-V", action="store_true", help="show version and exit")
    return parser


def setup_logging(logfile: str | None) -> None:
    """Log to `logfile` if given."""
    if logfile:
        # a handler rather than basicConfig, to write the log file in utf-8
        log.setLevel(logging.INFO)
        handler = logging.FileHandler(logfile, "a", "utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        log.addHandler(handler)
    log.info("lrselect start")
    log.info("lrtools version : %s", __version__)
    log.info("arguments: %s", " ".join(sys.argv[1:]))


def prepare_columns(args: argparse.Namespace) -> tuple[list[str], list[str]]:
    """Return the columns to display and the columns to request from the catalog."""
    # default columns if empty
    if not args.columns:
        args.columns = "name=full,filesize" if args.filesize else DEFAULT_COLUMNS
    # prepare stuff when filesize wanted
    columns = [col.strip() for col in args.columns.split(",")]
    if "filesize" in columns:
        args.filesize = True
    if args.filesize:
        if "filesize" not in columns:
            columns.append("filesize")
        if "name=full" not in columns:
            columns.append("name=full")
    columns_lr = list(columns)
    if "filesize" in columns_lr:
        columns_lr.remove("filesize")
    return columns, columns_lr


def rows_from_uuids_file(
    lrobj: LRSelectGeneric, columns_lr: list[str], filename: str
) -> list[Any] | None:
    """Return the rows of the photos whose uuids are listed in `filename`, None on failure."""
    try:
        uuids = Path(filename).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as _e:
        print(
            f' ==> Failed to open input file "{_e.filename}"',
            file=sys.stderr,
        )
        return None
    # build rows ...
    bad_uuids = []
    rows = []
    for uuid in uuids:
        try:
            row = lrobj.select_generic(",".join(columns_lr), f'uuid="{uuid}"').fetchone()
        except LRSelectException as _e:
            print(" ==> FAILED:", _e, file=sys.stderr)
            return None
        except sqlite3.OperationalError as _e:
            print(" ==> FAILED SQL :", _e, file=sys.stderr)
            return None
        if row is None:
            # failed to get uuid fromm db
            bad_uuids.append(uuid)
            continue
        rows.append(row)
    if bad_uuids:
        print(
            f"=> WARNING found uuids invalid ({len(bad_uuids)}/{len(uuids)}) : {', '.join(bad_uuids)}"
        )
    return rows


def select_rows(
    lrobj: LRSelectGeneric, columns_lr: list[str], args: argparse.Namespace
) -> list[Any] | None:
    """Return the rows selected by the uuids file or the criteria, None on failure."""
    if args.file:
        # option file containing photo uuids
        return rows_from_uuids_file(lrobj, columns_lr, args.file)
    try:
        return lrobj.select_generic(",".join(columns_lr), args.criteria).fetchall()
    except LRSelectException as _e:
        # convert specific error caused by a limitation on build SQL with criteria width or height
        if _e.args[0] == "no such column: dims":
            _e.args = ('Try to add column "dims"',)
        print(" ==> FAILED:", _e, file=sys.stderr)
        return None


def display_rows(rows: list[Any], columns: list[str], args: argparse.Namespace) -> None:
    """Print the count, the rows and the files size wanted by the options."""
    if args.count:
        print(" * Count results:", len(rows))

    if args.results:
        display_results(
            rows,
            columns,
            max_lines=args.max_lines,
            header=not args.no_header,
            widths=args.widths,
            raw_print=args.raw_print,
            separator=args.separator,
            filesize=args.filesize,
            indent=args.indent,
        )
    elif args.filesize:
        # only compute total filesize
        display_results(
            rows,
            columns,
            max_lines=0,
            header=False,
            filesize=args.filesize,
        )


def main() -> None:
    """Run lrselect from the command line."""
    config = LRToolConfig()
    args = build_parser(config).parse_args()

    if args.version:
        print(
            f"lrselect version : {__version__} , using python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        return

    setup_logging(args.log)

    # --max_lines option implies --results
    if args.max_lines > 0:
        args.results = True
    columns, columns_lr = prepare_columns(args)

    # open database
    if not args.lrcat.endswith("lrcat"):
        # not a catalog but an INI file
        config.load(args.lrcat)
        args.lrcat = config.default_lrcat
    lrdb = LRCatDB(config, args.lrcat)

    # select on which table to work
    lrobj: LRSelectGeneric = (
        lrdb.lrphoto if args.table == "photo" else LRSelectCollection(config, lrdb)
    )

    if not (args.sql or args.count or args.results):
        print('WARNING: option "--count" forced')
        args.count = True

    if args.sql:
        print(
            " * SQL request = ",
            lrobj.select_generic(",".join(columns_lr), args.criteria, sql=True),
        )

    if not (args.count or args.results):
        return

    rows = select_rows(lrobj, columns_lr, args)
    if rows is None:
        return

    display_rows(rows, columns, args)


def run() -> None:
    """Console script entry point."""
    # protect main from IOError occuring with a pipe command
    try:
        main()
        # flush here so a closed pipe is handled below, not at interpreter exit
        sys.stdout.flush()
    except OSError as _e:
        if _e.errno not in {errno.EINVAL, errno.EPIPE}:
            raise
        # reader closed the pipe: discard pending output so the exit flush cannot fail
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
    except (LRConfigException, LRSelectException, LRCatException) as _e:
        print(" ==> FAILED:", _e, file=sys.stderr)
    except sqlite3.OperationalError as _e:
        print(" ==> FAILED SQL :", _e, file=sys.stderr)

    log.info("lrselect end")


if __name__ == "__main__":
    run()
