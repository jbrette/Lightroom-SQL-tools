#!/usr/bin/env python
"""Execute Lightroom smart collections from catalog or file."""

import argparse
import errno
import logging
import os
import sys
from pathlib import Path
from sqlite3 import OperationalError
from typing import Literal

from lrtools._version import __version__
from lrtools.display import display_results
from lrtools.lrcat import LRCatDB, LRCatException
from lrtools.lrselectgeneric import LRSelectException
from lrtools.lrsmartcoll import SmartException, SQLSmartColl
from lrtools.lrtoolconfig import LRConfigException, LRToolConfig
from lrtools.slpp import SLPP, LuaTable

log = logging.getLogger()


def build_parser(config: LRToolConfig) -> argparse.ArgumentParser:
    """Build the command line parser."""
    # prepare description
    criteria = ", ".join(
        [crit.split("_")[1] for crit in dir(SQLSmartColl) if crit.startswith("criteria_")]
    )
    description = (
        "Execute smart collections from Lightroom catalog or from a exported file.\n"
        "Supported criteria are : " + criteria
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "smart_name",
        help='name of smart(s) collection. Can be lightroom smart collections (joker "%%"), or filenames (joker "*") with option "--file",',
        nargs="*",
    )
    parser.add_argument(
        "-b",
        "--lrcat",
        default=config.default_lrcat,
        help='Lightroom catalog file for database request (default:"%(default)s")',
    )
    parser.add_argument(
        "-f",
        "--file",
        action="store_true",
        help="positional parameters are files, not smart collection names",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help='list smart collections of name "smart_name" from Lightroom catalog.'
        ' "smart_name" can include jokers "%%". Leave empty for all collections',
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="display description of smart collection as stored",
    )
    parser.add_argument(
        "-d",
        "--dict",
        action="store_true",
        help="display description of smart collection as python dictionnary",
    )
    parser.add_argument("-s", "--sql", action="store_true", help="display SQL request")
    parser.add_argument("-c", "--count", action="store_true", help="display count of results")
    parser.add_argument("--validation-file", default="", help=argparse.SUPPRESS)
    parser.add_argument("-r", "--results", action="store_true", help="display datas results")
    parser.add_argument(
        "-n",
        "--max-lines",
        type=int,
        default=0,
        help="max number of results to display",
    )
    parser.add_argument(
        "-C",
        "--columns",
        default="uuid,name",
        help='columns names to print (default:"%(default)s").'
        " For column names, see help of lrselect.py. "
        "(Note that to obtain a number of results identical to those obtained in LR,"
        " the uuid column must be present)",
    )
    parser.add_argument(
        "-o",
        "--sort-column",
        default="1",
        help='name or number (one based) of column to sort (default:"%(default)s").'
        ' Sort is ascending order by default, add "-" before colum name or number for descending order',
    )
    parser.add_argument(
        "-N",
        "--no-header",
        action="store_true",
        help="don't print header (columns names)",
    )
    parser.add_argument(
        "-w",
        "--widths",
        help="widths of columns to display (ex:30,-50,10)",
    )
    parser.add_argument(
        "-S",
        "--separator",
        default=" | ",
        help='separator string between columns (default:"%(default)s")',
    )
    parser.add_argument(
        "--raw-print",
        action="store_true",
        help="print raw value (for speed, aperture columns)",
    )
    parser.add_argument("--log", help="log to file")

    return parser


def setup_logging(logfile: str | None) -> None:
    """Log to `logfile` if given."""
    if logfile:
        # a handler rather than basicConfig, to write the log file in utf-8
        log.setLevel(logging.INFO)
        handler = logging.FileHandler(logfile, "a", "utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
        log.addHandler(handler)
    log.info("lrsmart start")
    log.info("lrtools version : %s", __version__)


def load_validation_file(filename: str) -> dict[str, int]:
    """Return the photos number by smart collection name, as extracted from Lightroom.

    For lrsmart validation: the file is written by a specific Lightroom plugin,
    one "name ==> count" line per smart collection.
    """
    count_smart: dict[str, int] = {}
    if not filename:
        return count_smart
    try:
        lines = Path(filename).read_text(encoding="utf8").splitlines()
    except FileNotFoundError:
        sys.exit("Validation file not found")
    for line in lines:
        values = line.split("==>")
        if len(values) != 2:  # noqa: PLR2004 - "name ==> count"
            continue
        count_smart[values[0].strip()] = int(values[1].strip())
    return count_smart


def print_raw(
    lrdb: LRCatDB, smart_name: str, *, from_file: bool
) -> Literal["done", "skip", "stop"]:
    """Print the smart collection definition as stored.

    Return "skip" for a file not found (next file), "stop" for a collection not found.
    """
    if from_file:
        try:
            for line in Path(smart_name).read_text(encoding="utf-8").splitlines():
                print(line)
        except OSError:
            print("  ==> FAILED : Not found")
            return "skip"
        return "done"
    print(" * Raw definition as stored :")
    smart = lrdb.get_smartcoll_data(smart_name, raw_value=True)
    if not smart:
        print("  ==> FAILED : Not found")
        return "stop"
    for _s in smart.splitlines():
        print("\t", _s)
    return "done"


def load_smart_file(filename: str) -> LuaTable | None:
    """Return the definition of the smart collection exported in `filename`, None on failure."""
    print(f'Smart Collection filename "{filename}"')
    try:
        content = Path(filename).read_text(encoding="utf-8")
    except OSError:
        print("  ==> FAILED : Not found")
        return None
    try:
        smart = SLPP().decode(content[content.find("{") :])
    except KeyError, TypeError:
        smart = None
    value = smart.get("value") if isinstance(smart, dict) else None
    if not isinstance(smart, dict) or not isinstance(value, dict):
        print("  ==> FAILED : Invalid syntax")
        return None
    smart_title = smart.get("title", filename)
    print(f' * Collection name : "{smart_title}"')
    return value


def print_count(count: int, expected: int | None) -> None:
    """Print the results count, compared to the Lightroom one when known."""
    print(" * Count results:", count, end="  ")
    if expected is not None:
        if expected == count:
            print("=> conform to LR", end="")
        else:
            print(f"=> NOT_CONFORM to LR : {expected}", end="")
    print()


def smart_sql(
    config: LRToolConfig, lrdb: LRCatDB, smart: LuaTable, args: argparse.Namespace
) -> str | None:
    """Return the SQL request of one smart collection, None if no request is wanted or possible."""
    builder = SQLSmartColl(config, lrdb, smart)

    if args.dict:
        print(" * Definition as python dictionary :")
        for _s in builder.to_string().splitlines():
            print("\t", _s)

    if not (args.results or args.count or args.sql):
        return None

    try:
        sql = builder.build_sql(args.columns)
    except (LRSelectException, SmartException) as _e:
        print(" ==> FAILED : ", _e)
        return None
    # add sort on column
    sort_column = args.sort_column.strip()
    way = "ASC"
    if sort_column[0] == "-":
        way = "DESC"
        sort_column = sort_column[1:]
    sql += f" ORDER BY {sort_column} {way}"

    if args.sql:
        print(" * SQL Request: ", sql)
    return sql


def execute_smart(
    lrdb: LRCatDB,
    sql: str,
    smart_name: str,
    args: argparse.Namespace,
    count_smart: dict[str, int],
) -> None:
    """Execute the SQL request of one smart collection, print its count and results."""
    if not (args.results or args.count):
        return

    log.info('start smart "%s"', smart_name)
    try:
        lrdb.cursor.execute(sql)
        rows = lrdb.cursor.fetchall()
        log.info("end smart : %s rows", len(rows))
    except OperationalError as _e:
        log.info("end smart : FAILED : %s", _e)
        print(" ==> FAILED : ", _e)
        return

    if args.count:
        print_count(len(rows), count_smart.get(smart_name))

    if args.results:
        display_results(
            rows,
            [d[0] for d in lrdb.cursor.description],
            max_lines=args.max_lines,
            header=not args.no_header,
            raw_print=args.raw_print,
            separator=args.separator,
        )


def smart_names(lrdb: LRCatDB, args: argparse.Namespace) -> list[str]:
    """Return the files, or the smart collections matching the names (joker '%')."""
    if args.list and not args.smart_name:
        args.smart_name = ["%"]
    if args.file:
        names: list[str] = args.smart_name
        return names
    colls = []
    for name in args.smart_name:
        colls += lrdb.select_collections(lrdb.SMART_COLL, name)
    return [name for _, name, _ in colls]


def load_smart(lrdb: LRCatDB, smart_name: str, *, from_file: bool) -> LuaTable | None:
    """Return the definition of a smart collection from a file or the catalog, None if not found."""
    if from_file:
        return load_smart_file(smart_name)
    smart = lrdb.get_smartcoll_data(smart_name)
    if not smart:
        print("  ==> FAILED : Not found")
        return None
    return smart


def main() -> None:
    """Run lrsmart from the command line."""
    config = LRToolConfig()
    args = build_parser(config).parse_args()
    # --max_lines option implies --results
    if args.max_lines > 0:
        args.results = True

    setup_logging(args.log)
    count_smart = load_validation_file(args.validation_file)

    # open catalog
    if not args.lrcat.endswith("lrcat"):
        # specify LR catalog or INI file
        config.load(args.lrcat)
        args.lrcat = config.default_lrcat
    lrdb = LRCatDB(config, args.lrcat)

    for smart_name in smart_names(lrdb, args):
        if not args.file:
            print(f'Smart Collection "{smart_name}"')
        if args.raw:
            raw = print_raw(lrdb, smart_name, from_file=args.file)
            if raw == "stop":
                return
            if raw == "skip":
                continue
        smart = load_smart(lrdb, smart_name, from_file=args.file)
        if smart is None:
            continue
        sql = smart_sql(config, lrdb, smart, args)
        if sql is not None:
            execute_smart(lrdb, sql, smart_name, args, count_smart)

    log.info("lrsmart end")


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


if __name__ == "__main__":
    run()
