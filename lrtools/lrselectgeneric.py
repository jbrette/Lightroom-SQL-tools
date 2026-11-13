"""Base class for building simple SQL select from a table."""

import logging
import re
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Required, TypedDict, Unpack, overload

from dateutil import parser

from .criterlexer import CriterLexer
from .lrdates import date_to_lrstamp

if TYPE_CHECKING:
    import sqlite3

    from .lrcat import LRCatDB
    from .lrtoolconfig import LRToolConfig

log = logging.getLogger(__name__)

# JOIN clause(s) of a column or criterion: one string, a list, or nothing
type Joins = str | list[str] | None
# column value -> (SQL select expression, JOIN clauses); expression is None for a "var:" column
type ColumnSpec = tuple[str | None, Joins]
# column name -> {column value -> ColumnSpec}
type ColumnTable = dict[str, dict[str, ColumnSpec]]
# value returned by a criterion converter, substituted in the WHERE template with %
type SqlValue = str | tuple[str | float, ...]
# converts the user value of a criterion into SqlValue
type Converter = Callable[[str], SqlValue]
# criterion -> (JOIN clauses, WHERE template[, converter])
type CriterionSpec = tuple[Joins, str] | tuple[Joins, str, Converter]
# criterion name -> CriterionSpec
type CriteriaTable = dict[str, CriterionSpec]


class LRSelectException(Exception):  # noqa: N818 public API name
    """LRSelect Exception."""


class _BaseOptions(TypedDict, total=False):
    distinct: bool  # request SELECT DISTINCT
    debug: bool  # print sql


class SqlOptions(_BaseOptions, total=False):
    """Options of select_generic returning the SQL string."""

    sql: Required[Literal[True]]


class PrintOptions(_BaseOptions, total=False):
    """Options of select_generic printing the SQL and returning None."""

    print: Required[Literal[True]]
    sql: bool


class CursorOptions(_BaseOptions, total=False):
    """Options of select_generic executing the SQL and returning the cursor."""

    print: Literal[False]
    sql: Literal[False]


class SelectOptions(_BaseOptions, total=False):
    """All options of select_generic."""

    print: bool  # print sql and return None
    sql: bool  # return SQL string only


# sqlite date modifiers accordigf parts of date string
STARTS_OF_DATE = {
    1: "start of year",
    2: "start of month",
    3: "start of day",
}


def parsedate(config: LRToolConfig, date: str | datetime) -> datetime:
    """Return datetime from string."""
    if isinstance(date, str):
        return parser.parse(
            date,
            # capture times are naive local times
            default=datetime(1900, 1, 1, 0, 0, 0),  # noqa: DTZ001
            dayfirst=config.dayfirst,
        )
    return date


def to_bool(value: str) -> bool:
    """Convert value to bool (true, false, 1, 0)."""
    if value.lower() == "true" or value in {"1", "yes"}:
        return True
    if value.lower() == "false" or value in {"0", "no"}:
        return False
    msg = "Invalid bool value"
    raise LRSelectException(msg)


class LRSelectGeneric:
    """Build select SQL requests for a specific table from columns and criteria strings.

    This a base class not intended to be used directly.

    Exemple:
        lrdb = LRCatDB('holidays.lrcat')
        lrphoto = LRSelecPhoto(lrdb)
        results = lrphoto.select_generic("name=full, uuid," "rating=2, datecapt<2012-05-18")

    """

    # specific key for column specification
    _VAR_FIELD = "var:"

    def __init__(
        self,
        config: LRToolConfig,
        lrdb: LRCatDB,
        main_table: str,
        columns: ColumnTable,
        criteria: CriteriaTable,
    ) -> None:
        """Store the table descriptions.

        * param lrdb : LRCatDB instance
        * param main_table: string,
        * param columns: dictionnary for convert to SQL.
          structure :
            column_name (the key) :  {
                value1 : ( SQL_COLUMNS,  [SQL_FROM_TABLE_LIST] ),
                value2 : ( SQL_COLUMNS,  [SQL_FROM_TABLE_LIST] ),
                ...
                }
            example :
                'name' : {
                    'full':
                        (   'rf.absolutePath || fo.pathFromRoot || fi.baseName || "." || fi.extension AS name',
                            [
                                ' JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local',
                                'JOIN AgLibraryFolder fo ON fi.folder = fo.id_local', 'JOIN AgLibraryFile fi ON i.rootFile = fi.id_local'
                            ],
                        ),
                    'True':  ( 'fi.baseName || "." || fi.extension AS name', [ 'JOIN AgLibraryFile fi ON i.rootFile = fi.id_local' ] ),
                }

        * params criteria :  dictionnary where :
          structure :
            criter_name : ( SQL_JOIN_TABLES, SQL_WHERES, parser_value_function )
            ...
            example :
            'collection' : (
                'JOIN AgLibraryCollection col ON col.id_local = ci.Collection JOIN  AgLibraryCollectionimage ci ON ci.image = i.id_local',
                'col.name = "%s"' )
        """
        self.config = config
        self.lrdb = lrdb
        self.from_table = f"FROM {main_table}"
        self.froms: list[str] = []
        self.column_description = columns
        self.criteria_description = criteria
        self.groupby = ""
        self.having_criters: list[str] = []
        self.sql_column_names: list[str] = []
        self.raw_column_names: list[str] = []

    def selected_column_names(self) -> list[str]:
        """Column names from SQL statement executed."""
        return self.raw_column_names

    #
    # Some general functions called for convert value key in value sql
    #

    def func_oper_parsedate(self, value: str) -> str:
        """Parse operation and date value."""
        oper = ""
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                value = value[index:]
                break
        if not oper:
            msg = "None operator for date"
            raise LRSelectException(msg)
        date = parsedate(self.config, value)
        # value is it year, month/year or day/month/year ?
        nparts = len(re.findall(r"\d+", value))
        if nparts in STARTS_OF_DATE:
            sql = f'DATE(i.captureTime, "{STARTS_OF_DATE[nparts]}") {oper} DATE("{date}", "{STARTS_OF_DATE[nparts]}")'
        else:
            sql = f'i.captureTime {oper} "{date.strftime("""%Y-%m-%dT%H:%M:%S""")}"'
        return sql

    def func_oper_dateloc_to_lrstamp(self, value: str) -> tuple[str, float]:
        """Value is a lightroom timestamp."""
        oper = ""
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                value = value[index:]
                break
        dtmod = date_to_lrstamp(self.config, value)
        if dtmod is None:
            msg = 'invalid date value on "datemod"'
            raise LRSelectException(msg)
        return oper, dtmod

    def func_oper_dateutc_to_lrstamp(self, value: str) -> tuple[str, float]:
        """Value is a lightroom timestamp."""
        oper = ""
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                value = value[index:]
                break
        dtmod = date_to_lrstamp(self.config, value, localtz=False)
        if not dtmod:
            msg = 'invalid date value on "datemod"'
            raise LRSelectException(msg)
        return oper, dtmod

    def func_oper_value(self, value: str) -> tuple[str, str]:
        """Split the optional operator (default "=") from the value."""
        oper = None
        for index, char in enumerate(value):
            if char.isalnum():
                oper = value[:index] or "="
                value = value[index:]
                break
        if oper is None:
            msg = "operator without value"
            raise LRSelectException(msg)
        return oper, value

    def func_bool_to_equal(self, value: str) -> str:
        """Value is boolean."""
        return "=" if to_bool(value) else "!="

    def func_0_1(self, value: str) -> str:
        """Value is a null condition."""
        value = value.lower()
        if value in {"0", "false"}:
            return "0"
        if value in {"1", "true"}:
            return "1"
        msg = "invalid hasgps criterion value"
        raise LRSelectException(msg)

    def func_value_or_null(self, value: str) -> str:
        """Value is a null condition."""
        value = value.lower()
        if value in {"null", "false"}:
            return "IS NULL"
        if value in {"!null", "true"}:
            return "NOT NULL"
        return f'= "{value}"'

    def func_like_value_or_null(self, value: str) -> str:
        """Value is a null condition."""
        value = value.lower()
        if value in {"null", "false"}:
            return "IS NULL"
        if value in {"!null", "true"}:
            return "NOT NULL"
        return f'LIKE "{value}"'

    def func_value_or_not_equal(self, value: str) -> tuple[str, str]:
        """Value is parameter or comparaison."""
        try:
            is_true = to_bool(value)
        except LRSelectException:
            return ("=", f'"{value}"')
        if is_true:
            return ("<>", '""')
        return ("==", '""')

    def _keyval_to_keys(self, strlist: str) -> list[dict[str, str]]:
        """Convert string of key=value in list of dict."""
        pairs: list[dict[str, str]] = []
        if not strlist:
            return pairs
        for raw_keyval in strlist.split(","):
            if not raw_keyval:
                continue  # skip double commas
            keyval = raw_keyval.strip()
            if keyval.startswith(("count(", "countby(")):
                pairs.append({keyval: "True"})
                continue
            # support key without value => value is True
            _k, _, _v = keyval.partition("=")
            pairs.append({_k: _v if "=" in keyval else "True"})
        return pairs

    def _add_from(self, sql: str | list[str], froms: list[str]) -> None:
        """Add from to final FROM statement (internal function)."""
        if isinstance(sql, str):
            sql = [sql]
        for raw_sqlfrom in sql:
            sqlfrom = raw_sqlfrom.strip()
            if sqlfrom in froms:
                continue
            froms.append(sqlfrom)

    def remove_quotes(self, value: str) -> str:
        """Remove quotes from string."""
        if not value:
            return ""
        if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
            value = value[1:-1]
        return value

    def _column_to_sql(
        self, column: dict[str, str], sqlcols: list[str], sqlfroms: list[str], case: str = ""
    ) -> None:
        """Add the SQL of one column to sqlcols and its JOINs to sqlfroms."""
        key, value = next(iter(column.items()))
        if key not in self.column_description:
            msg = f'invalid column key "{key}"'
            raise LRSelectException(msg)
        dvalues = self.column_description[key]
        col_sql: str | None
        if self._VAR_FIELD in dvalues and value.startswith(self._VAR_FIELD):
            # _VAR_FIELD introduces process for columns name specification
            _, from_sql = dvalues[self._VAR_FIELD]
            col_sql = self.remove_quotes(value[len(self._VAR_FIELD) :])
        else:
            if value not in dvalues:
                msg = f'Invalid value "{value}" on column "{key}"'
                raise LRSelectException(msg)
            col_sql, from_sql = dvalues[value]
        if col_sql is None:
            msg = f'invalid column key "{key}"'
            raise LRSelectException(msg)
        if case in {"count", "countby"}:
            parts = col_sql.split(" ")
            if len(parts) < 2 or parts[-2].upper() != "AS":  # noqa: PLR2004 "<expr> AS <name>"
                msg = "Error in count definition"
                raise LRSelectException(msg)
            sqlcols.append(f"count({''.join(parts[:-2])}) AS count_{parts[-1]}")
            if case == "countby":
                self.groupby = f"GROUP BY {parts[-1]}"
        else:
            sqlcols.append(col_sql)
        if from_sql:
            self._add_from(from_sql, sqlfroms)

    def columns_to_sql(self, columns: str, sqlcols: list[str], sqlfroms: list[str]) -> None:
        """Convert string of column names comma separated to sql string."""
        self.raw_column_names = []
        for keyval in self._keyval_to_keys(columns):
            key, value = next(iter(keyval.items()))
            if key == "name":
                self.raw_column_names.append(f"{key}={value}")
            else:
                self.raw_column_names.append(f"{key}")
            match = re.match(r"(count|countby)\(([\w=]+)\)", key)
            if match:
                if match.group(1) == "count":
                    self._column_to_sql({match.group(2): value}, sqlcols, sqlfroms, "count")
                    continue
                # countby :
                lkv = self._keyval_to_keys(match.group(2))
                self._column_to_sql(lkv[0], sqlcols, sqlfroms, "countby")
                continue
            self._column_to_sql(keyval, sqlcols, sqlfroms)

    def select_predefined(self, _columns: str, _criters: str) -> str | None:
        """Return SQL statement if columns or criters is a supported keyword (a function).

        To be redefined in derived class; returns None when nothing is predefined.
        """
        return None

    @overload
    def select_generic(
        self, columns: str, criters: str = "", **kwargs: Unpack[PrintOptions]
    ) -> None: ...
    @overload
    def select_generic(
        self, columns: str, criters: str = "", **kwargs: Unpack[SqlOptions]
    ) -> str: ...
    @overload
    def select_generic(
        self, columns: str, criters: str = "", **kwargs: Unpack[CursorOptions]
    ) -> sqlite3.Cursor: ...
    @overload
    def select_generic(
        self, columns: str, criters: str = "", **kwargs: Unpack[SelectOptions]
    ) -> sqlite3.Cursor | str | None: ...
    def select_generic(  # noqa: C901, PLR0912, PLR0915 single pass over the criteria tokens
        self, columns: str, criters: str = "", **kwargs: Unpack[SelectOptions]
    ) -> sqlite3.Cursor | str | None:
        """Build SQL request from key/value pairs.

        columns :
            - 'NAME1'='VALUE1'
            - ...
        criteria :
            - 'CRITERION' = 'OPERATION+VALUE'
            - ....
        kwargs :
            - distinct : request SELECT DISTINCT
            - debug : print sql
            - print : print sql and return None
            - sql : return SQL string only
        """

        def _finalize(sql: str) -> sqlite3.Cursor | str | None:
            if kwargs.get("debug") or kwargs.get("print"):
                print("SQL =", sql)  # noqa: T201 the "debug"/"print" options print the SQL
            if kwargs.get("print"):
                return None
            if kwargs.get("sql"):
                return sql
            log.info("SQL = %s", sql)
            self.lrdb.cursor.execute(sql)
            # retrieve columns names as detected by sqlite
            self.sql_column_names = [d[0] for d in self.lrdb.cursor.description]
            return self.lrdb.cursor

        log.info('select_generic("%s" "%s")', columns, criters)

        # init
        fields: list[str] = []
        self.froms = [self.from_table]
        wheres: list[str] = []
        sort = ""
        nb_wheres: dict[str, int] = {}
        select_type: str | None = None
        self.groupby = ""
        self.having_criters = []
        self.sql_column_names = []
        self.raw_column_names = []

        #
        # process predefined sql functions
        #
        sql = self.select_predefined(columns, criters)
        if sql:
            return _finalize(sql)

        #
        # process criteria :
        #

        lex = CriterLexer(criters)
        if criters and not lex.parse():
            msg = f"Criteria syntax error : {lex.last_error}"
            raise LRSelectException(msg)
        token2sql = {"LPAR": "(", "RPAR": ")", "AND": "AND", "OR": "OR"}

        # process tokens
        prev_optoken: str | None = None
        has_where = False
        for kind, data in lex.tokens:
            if kind in token2sql:
                # add previous token if any
                if prev_optoken:
                    wheres.append(token2sql[prev_optoken])
                prev_optoken = kind
                continue

            if kind != "KEYVAL" or data is None:
                msg = f'Invalid Token : "{kind}"'
                raise LRSelectException(msg)
            key, raw_value = data
            stripped = self.remove_quotes(raw_value)
            value: SqlValue = stripped
            if key not in nb_wheres:
                nb_wheres[key] = 1
            else:
                nb_wheres[key] += 1
            if key not in self.criteria_description:
                msg = f'No existent criterion "{key}"'
                raise LRSelectException(msg)
            criter_desc = self.criteria_description[key]
            _from, _where = criter_desc[0], criter_desc[1]
            if len(criter_desc) == 3:  # noqa: PLR2004 (joins, where, converter)
                try:
                    value = criter_desc[2](stripped)
                except TypeError as _e:
                    msg = f'Syntax error on criterion "{key}"'
                    raise LRSelectException(msg) from _e
            # some specific keywords for SQL
            if key == "sort":  # specific key for sql 'ORDER BY'
                way = "DESC"
                sort_col = str(value)
                if sort_col[0] == "-":
                    way = "ASC"
                    sort_col = sort_col[1:]
                sort = f"ORDER BY {sort_col} {way}"
                prev_optoken = None
                continue
            if key == "distinct":  # specific key for sql 'SELECT DISTINCT'
                select_type = _where
                prev_optoken = None
                continue
            if key == "count":  # key for sql 'COUNT (*) ... HAVING'
                self.having_criters.append(f"count_{value}")
                prev_optoken = None
                continue

            if _from:
                if isinstance(_from, str):
                    _from = [_from]
                self._add_from(
                    [_f.replace("<NUM>", f"{nb_wheres[key]}") for _f in _from], self.froms
                )
            _where = _where.replace("<NUM>", f"{nb_wheres[key]}")
            if "%s" in _where:
                _where = _where % value

            # append the operation token if any
            if prev_optoken:
                if prev_optoken == "LPAR" or has_where:
                    wheres.append(token2sql[prev_optoken])
                prev_optoken = None
            # and the "where" string
            wheres.append(_where)
            has_where = True

        # finally: last operation token (a parenthesis)
        if prev_optoken:
            wheres.append(token2sql[prev_optoken])

        #
        # process columns :
        #
        self.columns_to_sql(columns, fields, self.froms)

        #
        # finalize request
        #
        sql_fields = (
            ", ".join(fields)
            if fields
            else 'rf.absolutePath || fo.pathFromRoot || fi.baseName || "." || fi.extension '
        )
        sql_froms = " ".join(self.froms)
        sql_wheres = f"WHERE {' '.join(wheres)}" if wheres else ""

        if kwargs.get("distinct"):
            select_type = "SELECT DISTINCT"
        elif not select_type:
            select_type = "SELECT"

        having = f"HAVING {' AND '.join(self.having_criters)}" if self.having_criters else ""

        sql = f"{select_type}  {sql_fields} {sql_froms} {sql_wheres} {self.groupby} {having} {sort}"
        return _finalize(sql)
