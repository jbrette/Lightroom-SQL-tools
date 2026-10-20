# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`lrtools` is a Python library plus two CLI scripts (`lrselect.py`, `lrsmart.py`) that query an Adobe Lightroom Classic catalog (`.lrcat`, a SQLite database) directly. The catalog is opened read-only (`mode=ro&cache=private&immutable=1`), so scripts are safe to run while Lightroom is open. The code never writes to a catalog.

## Commands

There is no test suite, linter config, or build step. Verify changes by running the scripts against a real catalog.

```sh
uv sync                              # creates .venv (Python >=3.14, see .python-version) from uv.lock
uv add <pkg>                         # add a dependency (updates pyproject.toml and uv.lock)
uv build                             # sdist + wheel (hatchling; version read from lrtools/_version.py)

# lrselect: columns string, criteria string
uv run lrselect.py -b "Lightroom Famille BL-v13-4/Lightroom Famille BL-v13-4.lrcat" \
    "name,datecapt,keywords" "rating=>3,videos=0" --results --count
uv run lrselect.py -b <catalog> --sql "name,datecapt" "rating=>4"   # print generated SQL
uv run lrselect.py -h                                                # full column/criteria reference

# lrsmart: run smart collection(s) by name ("%" joker) or from exported files (--file, "*" joker)
uv run lrsmart.py -b <catalog> "<smart collection name>" --sql --count
uv run lrsmart.py -b <catalog> --file exported.lrsmcol --results
```

`-b` accepts either a `.lrcat` file or an INI file in `lrtools.ini` format. Without `-b`, `LRCatalog` from `lrtools.ini` is used (searched in the current directory, the script directory, then `~/.config/lrtools/`; defaults are used silently if none exists). `lrtools.ini` also sets `DayFirst` (date parsing order) and `GeoCoder` (`Nominatim` or `BanFrance`, used by the `gps=<town>+<km>` criterion, which requires network access).

`Lightroom Famille BL-v13-4/` is a local catalog for manual testing; it and all `*.lrcat*` files are git-ignored.

## Architecture

- `lrtools/lrcat.py` — `LRCatDB` opens the catalog and exposes `cursor`, plus hand-written queries (duplicates, imports, collections hierarchy, XMP/EXIF extraction, count-by-date). It instantiates `self.lrphoto = LRSelectPhoto(...)`. Also holds Lightroom timestamp conversion (`date_to_lrstamp`, `lr_strptime`); Lightroom stores dates as seconds since 2001-01-01.
- `lrtools/lrselectgeneric.py` — `LRSelectGeneric` is the table-driven SQL builder. Subclasses pass a main table plus two dicts:
  - **columns**: `name -> {value -> [SQL select expr, [JOIN clauses] | None]}`. The value is the part after `=` in the columns string (`name=full`); a bare column name means value `"True"`.
  - **criteria**: `name -> [JOIN clause(s), WHERE template with %s, optional value-conversion func]`. Conversion funcs (`func_oper_value`, `func_oper_parsedate`, `func_like_value_or_null`, …) turn user input like `>=2016-5-15` into SQL fragments.
  
  `select_generic()` first tries `select_predefined()` (special pseudo-columns like `count_by_date(...)`, `duplicated_names(...)`), then tokenizes criteria with `CriterLexer` (`,` = AND, `|` = OR, parentheses), accumulates deduplicated JOINs, and executes. Repeated criteria (e.g. two `keyword=`) get numbered table aliases. Pseudo-criteria `sort`, `distinct`, `groupby`, `count` map to ORDER BY / SELECT DISTINCT / GROUP BY / HAVING.
- `lrtools/lrselectphoto.py` — `LRSelectPhoto` (main table `Adobe_images i`) defines nearly all photo columns and criteria. **Adding a column or criterion means adding a dict entry here**, plus documenting it in the `select_generic` docstring.
- `lrtools/lrselectcollection.py` — same pattern for `AgLibraryCollection` (`lrselect.py -t collection`).
- `lrtools/lrsmartcoll.py` — `SQLSmartColl` translates a smart collection definition (Lua table, decoded by `slpp.py`) into SQL. Each Lightroom smart-collection criterion maps to a `criteria_<lrCriterionName>` method, dispatched by name.
- `lrtools/display.py` — `display_results()` formats rows. `DEFAULT_SPECS` maps column names to printf width and a formatter (`display_date`, `display_lrtimestamp`, `display_int`, …); new columns needing formatting get an entry here.
- `lrtools/lrkeyword.py` — hierarchical keyword tree (`AgLibraryKeyword`); `lrtools/gps.py` — geocoding and bounding boxes; `lrtools/lrtoolconfig.py` — INI loader.

## Conventions

- `lrselect.py -h` builds its help text by slicing the `select_generic` docstrings of `LRSelectPhoto` and `LRSelectCollection` between `columns :` and `kwargs :`. Keep those markers intact when editing the docstrings; they are the user-facing reference for columns and criteria.
- Errors surface as `LRCatException`, `LRSelectException`, `SmartException`, `LRConfigException`; scripts catch these and exit with a message.
- Version string lives in `lrtools/_version.py` (date-based, `YYYY.MM.DD`), read by hatchling via `[tool.hatch.version]`.
- `lrselect.py` and `lrsmart.py` are shipped as top-level modules in the wheel (`only-include` in `pyproject.toml`) and exposed as the `lrselect` / `lrsmart` console scripts via their `run()` functions, which wrap `main()` with the error handling. Keep both runnable directly as `.py` files too.
- This is a fork of `fdenivac/Lightroom-SQL-tools`; `origin` is `jbrette/Lightroom-SQL-tools`.
