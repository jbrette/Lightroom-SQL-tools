"""Main class LRCatDB for Lightroom database manipulations."""

import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, overload

# date helpers, also exported from here for compatibility
from .lrdates import LIGHTROOM_EPOCH, TIMESTAMP_LR_EPOCH, date_to_lrstamp, lr_strptime
from .lrselectphoto import LRSelectPhoto
from .slpp import SLPP, LuaTable

if TYPE_CHECKING:
    from .lrtoolconfig import LRToolConfig

__all__ = [
    "LIGHTROOM_EPOCH",
    "TIMESTAMP_LR_EPOCH",
    "LRCatDB",
    "LRCatException",
    "date_to_lrstamp",
    "lr_strptime",
]

log = logging.getLogger(__name__)

# (hierarchical name, collection id_local, collection creationId)
type HierarchicalCollection = tuple[list[str], int, str]

SELECT_DUPLICATES_COUNT = """
SELECT * FROM (
  SELECT rf.absolutePath || fo.pathFromRoot || fi.baseName || "." || fi.extension as name, count( fi.baseName) AS duplicates
  FROM Adobe_images i
  JOIN AgLibraryFile fi on i.rootFile = fi.id_local
  JOIN AgLibraryFolder fo on fi.folder = fo.id_local
  JOIN AgLibraryRootFolder rf on fo.rootFolder = rf.id_local
  WHERE i.MasterImage IS NULL
  AND i.fileFormat != "VIDEO"
  GROUP BY UPPER(fi.baseName))
WHERE duplicates >1
"""
SELECT_DUPLICATES_UUID = """
SELECT  i.id_global AS uuid, fi.baseName || COALESCE(i.copyName, "") || "." || fi.extension AS name FROM Adobe_images i LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local WHERE UPPER(fi.baseName || COALESCE(i.copyName, "") || "." || fi.extension)
IN
  (
  SELECT fi.baseName || COALESCE(i.copyName, "") || "." || fi.extension AS name
  FROM Adobe_images i
  LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local %s
  GROUP BY name HAVING count(fi.baseName||COALESCE(i.copyName,"")||"."||fi.extension)>1
  )
ORDER BY name
"""


class LRCatException(Exception):  # noqa: N818 - public name, caught by the scripts and callers
    """LRCatDB Exception."""


class LRCatDB:
    """Build SQL requests for a Lightroom database.

    The database is opened by default in read-only, with cache local and as immutable (needed by Lightroom >= version 8).
    So Lightroom can be opened while running python scripts using this module.
    """

    ALL_COLL = 1
    STND_COLL = 2
    SMART_COLL = 3

    def __init__(
        self,
        config: LRToolConfig,
        lrcat_file: str,
        open_options: str = "mode=ro&cache=private&immutable=1",
    ) -> None:
        """Open the catalog `lrcat_file` with the sqlite URI options `open_options`."""
        self.config = config
        self.lrcat_file = lrcat_file
        if not Path(self.lrcat_file).exists():
            msg = f"LR catalog doesn't exist: {self.lrcat_file}"
            raise LRCatException(msg)
        log.info("sqlite3 version : %s", sqlite3.sqlite_version)
        self.conn, self.cursor, self.lrdb_version = self._open_db(open_options)
        self.lrphoto = LRSelectPhoto(config, self)

    def _open_db(self, open_options: str) -> tuple[sqlite3.Connection, sqlite3.Cursor, str]:
        """Connect to the catalog and read its Adobe_DBVersion."""
        uri = f"file:{self.lrcat_file}?{open_options or ''}"
        conn = None
        try:
            conn = sqlite3.connect(uri, uri="?" in uri)
            cursor = conn.cursor()
            (lrdb_version,) = cursor.execute(
                'SELECT value FROM Adobe_variablesTable WHERE name="Adobe_DBVersion"'
            ).fetchone()
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as _e:
            if conn is not None:
                conn.close()
            log.info('open "%s" failed : %s', self.lrcat_file, str(_e))
            log.info(
                'Failed to open "%s" with uri "%s"%s',
                self.lrcat_file,
                open_options,
                " reason: Not an Lightroom catalog",
            )
            msg = "Unable to open LR catalog"
            raise LRCatException(msg) from _e
        log.info('LR database "%s" opened with uri "%s"', self.lrcat_file, uri)
        log.info("Adobe_DBVersion : %s", lrdb_version)
        return conn, cursor, str(lrdb_version)

    def has_basename(self, name: str) -> bool:
        """Check if basename exists."""
        # COLLATE NOCASE for case insensitive
        self.cursor.execute(
            "SELECT baseName FROM AgLibraryFile WHERE baseName = ? COLLATE NOCASE",
            (name,),
        )
        return len(self.cursor.fetchall()) > 0

    def select_vcopies_master(self, master: int, columns: str) -> sqlite3.Cursor:
        """Select master image and the copies.

        Default return columns : name=basext , vname, stackpos, datemod, uuid, xmp, master, id
        """
        sqlcols: list[str] = []
        sqlfroms = ["Adobe_images i"]
        self.lrphoto.columns_to_sql(columns, sqlcols, sqlfroms)
        sql = f"SELECT {', '.join(sqlcols)} FROM {' '.join(sqlfroms)} WHERE i.masterImage={master} OR i.id_local={master} ORDER BY i.id_local"
        self.cursor.execute(sql)
        return self.cursor

    @overload
    def select_duplicates(self, options: str, *, sql: Literal[True]) -> str: ...
    @overload
    def select_duplicates(self, options: str, *, sql: Literal[False] = False) -> list[Any]: ...
    def select_duplicates(self, options: str, *, sql: bool = False) -> str | list[Any]:
        """Return duplicates photos name.

        - format 1 : same base name (without extension)
            ( (fullname, number_copies), ...)
        - format 2 :
            ( (uuid, UPPER(base name with extension)), ...)

        With `sql`, return the SQL request instead of executing it.
        """
        if not options or options == "1":
            request = SELECT_DUPLICATES_COUNT
        else:
            match = re.match(r"2 *,* *(.+)*", options)
            if not match:
                msg = "Invalid format"
                raise LRCatException(msg)
            options = match.group(1)
            if not options:
                request = SELECT_DUPLICATES_UUID % ""
            elif options == "novideos":
                request = SELECT_DUPLICATES_UUID % 'WHERE i.fileFormat != "VIDEO"'
            else:
                msg = "Invalid format"
                raise LRCatException(msg)
        if sql:
            return request
        self.cursor.execute(request)
        return self.cursor.fetchall()

    def select_imports(self, import_id: int | None = None) -> sqlite3.Cursor:
        """Select details on imports (date, count).

        Parameter:
            - import_id: import id or None for all imports
        """
        if import_id:
            sql = (
                "SELECT id_local, importDate,"
                " (SELECT COUNT(ii.import) FROM AgLibraryImport i JOIN AgLibraryImportImage ii ON i.id_local = ii.import"
                f" WHERE i.id_local = {import_id}) AS count"
                f" FROM AgLibraryImport WHERE id_local = {import_id}"
            )
        else:
            sql = (
                "SELECT id_local, importDate ,"
                " (SELECT COUNT(ii.import) FROM AgLibraryImport i "
                " JOIN AgLibraryImportImage ii ON i.id_local = ii.import WHERE i0.id_local = i.id_local) AS Count"
                " FROM AgLibraryImport i0 ORDER BY importDate ASC"
            )
        self.cursor.execute(sql)
        return self.cursor

    @overload
    def get_smartcoll_data(
        self, name_or_id: str | int, *, raw_value: Literal[True]
    ) -> str | None: ...
    @overload
    def get_smartcoll_data(
        self, name_or_id: str | int, *, raw_value: Literal[False] = False
    ) -> LuaTable | None: ...
    def get_smartcoll_data(
        self, name_or_id: str | int, *, raw_value: bool = False
    ) -> str | LuaTable | None:
        """Return smart collection lua request in a python structure.

        With `raw_value`, return the lua definition as stored.
        """
        try:
            pid = int(name_or_id)
            self.cursor.execute(
                'SELECT cont.content FROM AgLibraryCollectionContent cont \
                JOIN AgLibraryCollection  col on col.id_local = cont.collection\
                WHERE col.id_local=? AND cont.owningModule = "ag.library.smart_collection"',
                (pid,),
            )
        except ValueError:
            name = name_or_id
            self.cursor.execute(
                'SELECT cont.content FROM AgLibraryCollectionContent cont \
                JOIN AgLibraryCollection  col on col.id_local = cont.collection\
                WHERE  col.name LIKE ? AND cont.owningModule = "ag.library.smart_collection"',
                (name,),
            )
        row = self.cursor.fetchone()
        if row is None:
            return None
        smart: str = row[0]
        if raw_value:
            return smart
        data = SLPP().decode(smart[4:])
        return data if isinstance(data, dict) else None

    @overload
    def select_count_by_date(
        self,
        mode: str,
        date_start: datetime | str,
        date_end: datetime | str | None = None,
        *,
        sql: Literal[True],
    ) -> str: ...
    @overload
    def select_count_by_date(
        self,
        mode: str,
        date_start: datetime | str,
        date_end: datetime | str | None = None,
        *,
        sql: Literal[False] = False,
    ) -> list[Any]: ...
    def select_count_by_date(
        self,
        mode: str,
        date_start: datetime | str,
        date_end: datetime | str | None = None,
        *,
        sql: bool = False,
    ) -> str | list[Any]:
        """Return photos number by year, month or day.

        - mode : "by_year", "by_month" or "by_day"
        - date_start
        - date_end
        - sql : return the SQL request instead of executing it
        """
        # valid too : SELECT COUNT(captureTime),  DATE(captureTime, 'start of month') FROM Adobe_images  GROUP BY DATE(captureTime, 'start of month')
        if not date_end:
            # capture times are stored as naive local times
            date_end = datetime.now()  # noqa: DTZ005 - naive local, as captureTime
        if mode == "by_day":
            request = (
                'SELECT strftime("%Y-%m-%d", DATE(captureTime, "start of day")) as day, COUNT(captureTime) AS count'
                f' FROM Adobe_images WHERE captureTime >= "{date_start}" AND captureTime < "{date_end}" GROUP BY DATE(captureTime, "start of day")'
            )
        elif mode == "by_month":
            request = (
                'SELECT strftime("%Y-%m", DATE(captureTime, "start of month")) as month, COUNT(captureTime) AS count'
                f' FROM Adobe_images WHERE captureTime >= "{date_start}" AND captureTime < "{date_end}" GROUP BY DATE(captureTime, "start of month")'
            )
        elif mode == "by_year":
            request = (
                'SELECT strftime("%Y", DATE(captureTime, "start of year")) as year, COUNT(captureTime) AS count'
                f' FROM Adobe_images WHERE captureTime >= "{date_start}" AND captureTime <= "{date_end}" GROUP BY DATE(captureTime, "start of year")'
            )
        else:
            log.error("BUG select_count_by_date")
            request = ""
        if sql:
            return request
        self.cursor.execute(request)
        return self.cursor.fetchall()

    @staticmethod
    def _hierarchical(rows: list[Any]) -> list[HierarchicalCollection]:
        """Build hierarchical names from (id_local, creationId, genealogy, name, parent) rows."""
        id2coll: dict[str, tuple[int, str, str]] = {
            genealogy: (id_local, creation_id, name)
            for id_local, creation_id, genealogy, name, _parent in rows
        }
        hierachical_colls: list[HierarchicalCollection] = []
        for genealogy, (id_local, creation_id, _name) in id2coll.items():
            hname = []
            genkey = ""
            for part in genealogy.split("/")[1:]:
                genkey += f"/{part}"
                hname.append(id2coll[genkey][2])
            hierachical_colls.append((hname, id_local, creation_id))
        return sorted(hierachical_colls)

    def hierarchical_collections(self) -> list[HierarchicalCollection]:
        """Get hierarchical collections.

        return list( (hierachical_name, lr_id_local, lr_creation_id) )
        """
        return self._hierarchical(
            self.cursor.execute(
                "SELECT id_local,creationId,genealogy,name,parent FROM AgLibraryCollection WHERE "
                '(creationId="com.adobe.ag.library.group" OR '
                'creationId="com.adobe.ag.library.smart_collection" OR '
                'creationId="com.adobe.ag.library.collection") AND '
                "systemOnly=0"
            ).fetchall()
        )

    def select_collections(self, what: int, collname: str = "") -> list[tuple[int, str, str]]:
        """Select collections name for standard and dynamic type.

        what = [ALL_COLL, STND_COLL, SMART_COLL] : collections type to retrieve
        collname : partial (including a %) or complete name of collection, or empty for all collections
        """
        if what == self.STND_COLL:
            where = 'creationId="com.adobe.ag.library.collection"'
        elif what == self.SMART_COLL:
            where = 'creationId="com.adobe.ag.library.smart_collection"'
        else:
            where = '(creationId="com.adobe.ag.library.smart_collection" OR creationId="com.adobe.ag.library.collection")'
        if collname:
            oper = "LIKE" if "%" in collname else "="
            where += f' AND name {oper} "{collname}" COLLATE NOCASE'
        self.cursor.execute(
            f"SELECT id_local, name, creationId FROM AgLibraryCollection WHERE {where} ORDER BY name ASC"
        )
        return self.cursor.fetchall()

    def hierarchical_published_collections(self) -> list[HierarchicalCollection]:
        """Get hierarchical published collections.

        return list( (hierachical_name, lr_id_local, lr_creation_id) )
        """
        return self._hierarchical(
            self.cursor.execute(
                "SELECT id_local,creationId,genealogy,name,parent FROM AgLibraryPublishedCollection WHERE ("
                'creationId="com.adobe.ag.export.service.connection" OR '
                'creationId="com.adobe.ag.library.collection.published.built-in" OR '
                'creationId="com.adobe.ag.library.group.published" OR '
                'creationId="com.adobe.ag.library.collection.published") AND '
                "systemOnly=0"
            ).fetchall()
        )

    def select_metadatas_to_archive(self) -> sqlite3.Cursor:
        """Return photos as LR smart collection : métadatas "conflit détecté" OU "a été modifié"."""
        return self.lrphoto.select_generic("name=full", "metastatus=conflict, sort=capturetime")

    def get_xmp(self, name_or_id: str | int) -> list[Any]:
        """Return Adobe_AdditionalMetadata.xmp (list of tuple).

        name_or_id :  photo basename or id (Adobe_images.id_local)
        """
        try:
            self.lrphoto.select_generic("xmp", f'id="{int(name_or_id)}"')
        except ValueError:
            self.lrphoto.select_generic("xmp", f'name="{name_or_id}"')
        return self.cursor.fetchall()

    def get_exif_metadata(self, name_or_id: str | int, fields: str) -> list[Any]:
        """Return elements of table AgHarvestedExifMetadata for a photo basename.

        name_or_id : photo basename or id
        fields: (string) sql fields to retrieve (ex:'hasgps,focallength')
        NOTA: also possible: acces to GPS infos via self.get_xmp (field exif:GPS<KEY>)
        WARNING : a photo with a "numerical" name (1235.jpg) is searched by id.
        """
        try:
            self.cursor.execute(
                f"SELECT {fields} FROM AgHarvestedExifMetadata WHERE image = ? ",
                (int(name_or_id),),
            )
        except ValueError:
            self.cursor.execute(
                f"SELECT {fields}  FROM Adobe_images i JOIN AgHarvestedExifMetadata em on i.id_local = em.image "
                "JOIN AgLibraryFile fi on i.rootFile = fi.id_local WHERE fi.baseName = ? ",
                (name_or_id,),
            )
        return self.cursor.fetchall()

    def get_rowfield(self, field: int | None = None) -> Any:  # noqa: ANN401 - a row or one of its fields, any SQLite type
        """Get next row and return specific field."""
        row = self.cursor.fetchone()
        if not row:
            return None
        if field is None:
            return row
        return row[field]

    def prodpath_from_xmp(
        self, xmp: str, prod_basepath: str | os.PathLike[str], date_fmt: str
    ) -> tuple[str, datetime]:
        """Return production path and capture time from xmp.

        Parameters
            xmp  : XMP datas from LR
            prod_basepath : production directory base path
            date_fmt : date format for subdirectories in production dir

        Returns
            (str) production path, (datetime) capture_time
        """
        # image.captureTime always exists (with and without exif date) :
        #   so, we need to read xmp for exif:DateTimeOriginal ou exif:DateTimeDigitized
        # date capture is DateTimeOriginal or DateTimeDigitized else None
        datecapt = self.xtract_prop_key(xmp, "exif:DateTimeOriginal")
        if not datecapt:
            datecapt = self.xtract_prop_key(xmp, "exif:DateTimeDigitized")
        if not datecapt:  # last chance !
            datecapt = self.xtract_prop_key(xmp, "xmp:CreateDate")
        # XMP capture times are naive local times
        capturetime = lr_strptime(datecapt) if datecapt else datetime(1900, 1, 1)  # noqa: DTZ001 - naive local, as XMP dates
        prodpath = os.path.normpath(Path(prod_basepath) / capturetime.strftime(date_fmt))
        return prodpath, capturetime

    @staticmethod
    def xtract_prop_key(xmp: str, key: str) -> str | None:
        """Extract value for key in xmp string (exif:DateTimeOriginal='VALUE')."""
        i = xmp.find(key + '="')
        if i == -1:
            return None
        beg = i + len(key) + 2
        end = xmp.find('"', beg)
        if end == -1:
            return None
        return xmp[beg:end]
