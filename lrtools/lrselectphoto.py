"""LRSelectPhoto class for building SQL select for table Adobe_images."""

import logging
import math
import re
from datetime import datetime
from typing import TYPE_CHECKING, Unpack, overload, override

from .gps import geocodage, square_around_location
from .lrselectgeneric import (
    CursorOptions,
    LRSelectException,
    LRSelectGeneric,
    PrintOptions,
    SelectOptions,
    SqlOptions,
)

if TYPE_CHECKING:
    import sqlite3

    from .lrcat import LRCatDB
    from .lrtoolconfig import LRToolConfig

# number of date parts for a month (YYYY-MM) or a day (YYYY-MM-DD)
_MONTH_PARTS = 2
_DAY_PARTS = 3


def criteria_to_dict(criteria: str) -> dict[str, list[str | None]]:
    """
    Return dict of criter/value from string.

    As some criteria can be repeated more than once,
        value for a criter is a list
    """
    dcriteria: dict[str, list[str | None]] = {}
    for raw_crit in criteria.split(","):
        crit = raw_crit.strip()
        val: str | None
        try:
            key, val = crit.split("=", 1)
            key = key.lower()
        except ValueError:
            key = crit.lower()
            val = None
        if key not in dcriteria:
            dcriteria[key] = [val]
        else:
            dcriteria[key].append(val)
    return dcriteria


def dict_to_criteria(criteria: dict[str, list[str | None]]) -> str:
    """Return criteria string from dict criter/value."""
    final_crit = []
    for key, lval in criteria.items():
        for val in lval:
            if val is None:
                final_crit.append(f"{key}")
            else:
                final_crit.append(f"{key}={val}")
    return ",".join(final_crit)


class LRSelectPhoto(LRSelectGeneric):
    """Build select request for photo table Adobe_images."""

    def __init__(self, config: LRToolConfig, lrdb: LRCatDB) -> None:
        """Describe the columns and criteria of table Adobe_images."""
        super().__init__(
            config,
            lrdb,
            #
            # Table source
            #
            "Adobe_images i",
            #
            # Column description
            #
            #   This is dictionnary of column name.
            #       Each column name is a dictionnary of possible values :
            #           Each value describe :
            #               - the SQL column selection,
            #               - the list of SQL tables to join,
            #
            {
                "all": {"True": ("*", None)},
                "name": {
                    "full": (
                        'rf.absolutePath || fo.pathFromRoot || fi.baseName || "." || fi.extension AS name',
                        [
                            "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                            "LEFT JOIN AgLibraryFolder fo ON fi.folder = fo.id_local",
                            "LEFT JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local",
                        ],
                    ),
                    "full_vc": (
                        'rf.absolutePath || fo.pathFromRoot || fi.baseName || COALESCE(i.copyName, "") || "." || fi.extension AS name',
                        [
                            "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                            "LEFT JOIN AgLibraryFolder fo ON fi.folder = fo.id_local",
                            "LEFT JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local",
                        ],
                    ),
                    "base": (
                        "fi.baseName AS name",
                        ["LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local"],
                    ),
                    "base_vc": (
                        'fi.baseName || COALESCE(i.copyName, "") AS name',
                        ["LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local"],
                    ),
                    "True": (
                        'fi.baseName || "." || fi.extension AS name',
                        ["LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local"],
                    ),
                    "basext": (
                        'fi.baseName || "." || fi.extension AS name',
                        ["LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local"],
                    ),
                    "basext_vc": (
                        'fi.baseName || COALESCE(i.copyName, "") || "." || fi.extension AS name',
                        ["LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local"],
                    ),
                },
                "vname": {"True": ("i.copyName AS vname", None)},
                "uuidfile": {
                    "True": (
                        "fi.id_global",
                        [
                            "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                        ],
                    ),
                },
                "modtime": {
                    "True": (
                        "fi.modtime",
                        [
                            "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                        ],
                    ),
                },
                "idfolder": {
                    "True": (
                        "fo.id_local AS idfolder",
                        [
                            "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                            "LEFT JOIN AgLibraryFolder fo ON fi.folder = fo.id_local",
                            "LEFT JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local",
                        ],
                    )
                },
                "folder": {
                    "True": (
                        "rf.absolutePath || fo.pathFromRoot AS folder",
                        [
                            "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                            "LEFT JOIN AgLibraryFolder fo ON fi.folder = fo.id_local",
                            "LEFT JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local",
                        ],
                    ),
                },
                "uuid": {"True": ("i.id_global AS uuid", None)},
                "master": {"True": ("i.masterImage AS master", None)},
                "id": {"True": ("i.id_local AS id", None)},
                "rating": {"True": ("i.rating AS rating", None)},
                "colorlabel": {"True": ("i.colorlabels AS colorlabel", None)},
                "flag": {"True": ("i.pick AS flag", None)},
                "datemod": {
                    # modif date (including keywords changes)
                    "True": ("i.touchtime AS datemod", None),
                },
                "datehist": {
                    # modif date based on history developement steps, ignoring exportations and publications (TODO: strings need to be localized )
                    "True": (
                        (
                            "(SELECT max(ids2.datecreated) "
                            'FROM Adobe_libraryImageDevelopHistoryStep ids2 WHERE ids2.image =i.id_local AND substr(name,1,4) NOT IN ("Expo", "Publ")) AS datehist'
                        ),
                        None,
                    ),
                },
                "modcount": {"True": ("i.touchCount AS modcount", None)},
                "datecapt": {"True": ("i.captureTime AS datecapt", None)},
                "xmp": {
                    "True": (
                        "am.xmp AS xmp",
                        ["LEFT JOIN Adobe_AdditionalMetadata am ON i.id_local = am.image"],
                    )
                },
                "stack": {
                    "True": (
                        "fsi.stack AS stack",
                        ["LEFT JOIN AgLibraryFolderStackImage fsi ON i.id_local = fsi.image"],
                    )
                },
                "stackpos": {
                    "True": (
                        "fsi.position AS stackpos",
                        ["LEFT JOIN AgLibraryFolderStackImage fsi ON i.id_local = fsi.image"],
                    )
                },
                "keywords": {
                    "True": (
                        (
                            "(SELECT GROUP_CONCAT(kwdef.name) FROM AgLibraryKeywordImage kwimg JOIN AgLibraryKeyword kwdef ON kwdef.id_local = kwimg.tag"
                            " WHERE kwimg.image=i.id_local) AS keywords"
                        ),
                        None,
                    )
                },
                "collections": {
                    "True": (
                        (
                            "(SELECT GROUP_CONCAT(col.name) FROM AgLibraryCollection col JOIN AgLibraryCollectionimage ci ON ci.collection = col.id_local"
                            " WHERE ci.image = i.id_local) AS Collections"
                            ""
                        ),
                        None,
                    )
                },
                "camera": {
                    "True": (
                        "cm.value AS camera",
                        [
                            "LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image",
                            "LEFT JOIN AgInternedExifCameraModel cm ON cm.id_local = em.cameraModelRef",
                        ],
                    )
                },
                "camerasn": {
                    "True": (
                        "csn.value AS camerasn",
                        [
                            "LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image",
                            "LEFT JOIN AgInternedExifCameraSN csn ON csn.id_local = em.cameraSNRef",
                        ],
                    )
                },
                "lens": {
                    "True": (
                        "el.value AS lens",
                        [
                            "LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image",
                            "LEFT JOIN AgInternedExifLens el ON el.id_local = em.lensRef",
                        ],
                    )
                },
                "iso": {
                    "True": (
                        "em.isoSpeedRating AS iso",
                        ["LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image"],
                    )
                },
                "focal": {
                    "True": (
                        "em.focalLength AS focal",
                        ["LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image"],
                    )
                },
                "aperture": {
                    "True": (
                        "em.aperture AS aperture",
                        ["LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image"],
                    )
                },
                "speed": {
                    "True": (
                        "em.shutterSpeed AS speed",
                        ["LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image"],
                    )
                },
                "orientation": {"True": ("i.orientation AS orientaton", None)},
                "monochrome": {
                    "True": (
                        "am.monochrome AS monochrome",
                        ["LEFT JOIN Adobe_AdditionalMetadata am ON i.id_local = am.image"],
                    )
                },
                "grayscale": {
                    "True": (
                        "ids.grayscale AS grayscale",
                        ["LEFT JOIN Adobe_ImageDevelopSettings ids ON ids.image = i.id_local"],
                    )
                },
                "flash": {
                    "True": (
                        "em.flashFired AS flash",
                        ["LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image"],
                    )
                },
                "cropwidth": {
                    "True": (
                        "ids.croppedWidth AS cropwidth",
                        ["LEFT JOIN Adobe_ImageDevelopSettings ids ON ids.image = i.id_local"],
                    )
                },
                "cropheight": {
                    "True": (
                        "ids.croppedHeight AS cropheight",
                        ["LEFT JOIN Adobe_ImageDevelopSettings ids ON ids.image = i.id_local"],
                    )
                },
                "width": {"True": ("i.fileWidth AS width", None)},
                "height": {"True": ("i.fileHeight AS height", None)},
                "dims": {
                    "True": (
                        (
                            "(SELECT CASE "
                            'WHEN ids.croppedWidth <> "uncropped" AND i.orientation IN ("AB", "BA", "CD", "DC") THEN CAST(ids.croppedWidth AS int) || "x" || CAST(ids.croppedHeight AS int) '
                            'WHEN ids.croppedWidth <> "uncropped" AND i.orientation IN ("AD", "DA", "BC", "CB") THEN CAST(ids.croppedHeight AS int) || "x" || CAST(ids.croppedWidth AS int) '
                            'WHEN ids.croppedWidth = "uncropped" AND i.orientation IN ("AB", "BA", "CD", "DC") THEN CAST(i.filewidth AS int) || "x" || CAST(i.fileHeight AS int) '
                            'WHEN ids.croppedWidth = "uncropped" AND i.orientation IN ("AD", "DA", "BC", "CB") THEN CAST(i.fileHeight AS int) || "x" || CAST(i.filewidth AS int) '
                            'ELSE CAST(i.filewidth AS int) || "x" || CAST(i.fileHeight AS int) END) AS dims '
                        ),
                        ["LEFT JOIN Adobe_imageDevelopSettings ids ON ids.image = i.id_local"],
                    )
                },
                "aspectratio": {"True": ("i.aspectRatioCache AS aspectRatio", None)},
                "creator": {
                    "True": (
                        "iic.value AS creator",
                        [
                            "LEFT JOIN AgHarvestedIptcMetadata im ON i.id_local = im.image",
                            "LEFT JOIN AgInternedIptcCreator iic ON im.creatorRef = iic.id_local",
                        ],
                    )
                },
                "caption": {
                    "True": (
                        "iptc.caption AS caption",
                        ["LEFT JOIN AgLibraryIPTC iptc ON i.id_local = iptc.image"],
                    )
                },
                "copyright": {
                    "True": (
                        "iptc.copyright AS copyright",
                        ["LEFT JOIN AgLibraryIPTC iptc ON i.id_local = iptc.image"],
                    )
                },
                "hasgps": {
                    "True": (
                        "em.hasgps AS hasgps",
                        ["LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image"],
                    )
                },
                "latitude": {
                    "True": (
                        "em.GpsLatitude AS latitude",
                        ["LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image"],
                    )
                },
                "longitude": {
                    "True": (
                        "em.GpsLongitude AS longitude",
                        ["LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image"],
                    )
                },
                "exif": {
                    self._VAR_FIELD: (
                        None,
                        ["LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image"],
                    )
                },
                "pubcollection": {
                    "True": (
                        "pc.name AS pubcollection",
                        [
                            "LEFT JOIN AgLibraryPublishedCollectionImage pci ON pci.image = i.id_local",
                            "LEFT JOIN AgLibraryPublishedCollection pc ON pc.id_local = pci.collection",
                        ],
                    ),
                },
                "pubname": {
                    "True": (
                        "rm.remoteId AS pubname",
                        ["LEFT JOIN AgRemotePhoto rm ON i.id_local = rm.photo"],
                    )
                },
                "pubtime": {
                    "True": (
                        '(select substr(rm.url, pos+1) from (select instr(rm.url, "/") as pos)) AS pubtime',
                        ["LEFT JOIN AgRemotePhoto rm ON i.id_local = rm.photo"],
                    )
                },
                "pubposition": {
                    "True": (
                        "pci.positionInCollection AS pubposition",
                        [
                            "LEFT JOIN AgLibraryPublishedCollectionImage pci ON pci.image = i.id_local",
                            "LEFT JOIN AgLibraryPublishedCollection pc ON pc.id_local = pci.collection",
                        ],
                    ),
                },
                "extfile": {
                    "True": (
                        "fi.sidecarExtensions AS extfile",
                        ["LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local"],
                    )
                },
                "location": {
                    "True": (
                        "iptcloc.value AS location",
                        [
                            "LEFT JOIN AgHarvestedIptcMetadata iptcmeta ON iptcmeta.image = i.id_local",
                            "LEFT JOIN AgInternedIptcLocation iptcloc ON iptcloc.id_local = iptcmeta.locationRef",
                        ],
                    )
                },
                "city": {
                    "True": (
                        "iptccity.value AS city",
                        [
                            "LEFT JOIN AgHarvestedIptcMetadata iptcmeta ON iptcmeta.image = i.id_local",
                            "LEFT JOIN AgInternedIptcCity iptccity ON iptccity.id_local = iptcmeta.cityRef",
                        ],
                    )
                },
                "country": {
                    "True": (
                        "iptccountry.value AS country",
                        [
                            "LEFT JOIN AgHarvestedIptcMetadata iptcmeta ON iptcmeta.image = i.id_local",
                            "LEFT JOIN AgInternedIptcCountry iptccountry ON iptccountry.id_local = iptcmeta.countryRef",
                        ],
                    )
                },
                "state": {
                    "True": (
                        "iptcstate.value AS state",
                        [
                            "LEFT JOIN AgHarvestedIptcMetadata iptcmeta ON iptcmeta.image = i.id_local",
                            "LEFT JOIN AgInternedIptcState iptcstate ON iptcstate.id_local = iptcmeta.stateRef",
                        ],
                    )
                },
                "duration": {
                    "True": (
                        "vidinfo.duration AS duration",
                        [
                            "LEFT JOIN AgVideoInfo vidinfo ON vidinfo.image = i.id_local",
                        ],
                    )
                },
                "digest": {
                    "True": (
                        "ids.digest AS digest",
                        ["LEFT JOIN Adobe_ImageDevelopSettings ids ON ids.image = i.id_local"],
                    )
                },
            },
            #
            # Criteria description
            #
            #   dictionnary of criterion. Each criterion contains :
            #       - SQL tables to join
            #       - SQL where conditions
            #       - optional function for parsing value
            {
                "name": (
                    "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                    'UPPER(fi.baseName || COALESCE(i.copyName, "")) LIKE "%s"',
                ),
                "exactname": (
                    "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                    ' UPPER(fi.baseName) = "%s"',
                ),
                "ext": (
                    "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                    'UPPER(fi.extension) LIKE "%s"',
                ),
                "exact_ext": (
                    "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                    'UPPER(fi.extension) = "%s"',
                ),
                "idfolder": (
                    [
                        "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                        "LEFT JOIN AgLibraryFolder fo ON fi.folder = fo.id_local",
                        "LEFT JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local",
                    ],
                    "fo.id_local = %s",
                ),
                "folder": (
                    [
                        "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                        "LEFT JOIN AgLibraryFolder fo ON fi.folder = fo.id_local",
                        "LEFT JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local",
                    ],
                    'UPPER(rf.absolutePath || fo.pathFromRoot) LIKE "%s"',
                ),
                "id": (
                    "",
                    "i.id_local = %s",
                ),
                "uuid": (
                    "",
                    'i.id_global = "%s"',
                ),
                "uuidfile": (
                    [
                        "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                    ],
                    'fi.id_global = "%s"',
                ),
                "datecapt": (
                    "",
                    "%s",
                    self.func_oper_parsedate,
                ),
                "datemod": (
                    "",
                    "i.touchtime %s %s",
                    self.func_oper_dateloc_to_lrstamp,
                ),
                "modcount": (
                    "",
                    "i.touchcount %s %s",
                    self.func_oper_value,
                ),
                "videos": (
                    "",
                    'i.fileFormat %s "VIDEO"',
                    self.func_bool_to_equal,
                ),
                "vcopies": (
                    "",
                    "i.masterImage %s",
                    self.func_value_or_null,
                ),
                "rating": (
                    "",
                    "%s",
                    self.func_rating,
                ),
                "colorlabel": (
                    "",
                    "i.colorlabels %s %s",
                    self.func_value_or_not_equal,
                ),
                "flag": (
                    "",
                    "%s",
                    self.func_flag,
                ),
                "title": (
                    "LEFT JOIN AgMetadataSearchIndex msi ON i.id_local = msi.image",
                    "%s",
                    self.func_titleindex,
                ),
                "caption": (
                    "LEFT JOIN AgLibraryIPTC iptc ON i.id_local = iptc.image",
                    "iptc.caption %s",
                    self.func_like_value_or_null,
                ),
                "copyright": (
                    "LEFT JOIN AgLibraryIPTC iptc ON i.id_local = iptc.image",
                    "iptc.copyright %s",
                    self.func_like_value_or_null,
                ),
                "creator": (
                    [
                        "LEFT JOIN AgHarvestedIptcMetadata im ON i.id_local = im.image",
                        "LEFT JOIN AgInternedIptcCreator iic ON im.creatorRef = iic.id_local",
                    ],
                    'iic.value LIKE "%s"',
                ),
                "iso": (
                    "LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image",
                    "em.isoSpeedRating %s %s",
                    self.func_oper_value,
                ),
                "focal": (
                    "LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image",
                    "em.focalLength %s %s",
                    self.func_oper_value,
                ),
                "aperture": (
                    "LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image",
                    "em.aperture %s",
                    self.func_aperture,
                ),
                "speed": (
                    "LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image",
                    "em.shutterSpeed %s",
                    self.func_speed,
                ),
                "flash": (
                    "LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image",
                    "em.flashFired %s",
                    self.func_value_or_null,
                ),
                "camera": (
                    [
                        "LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image",
                        " LEFT JOIN AgInternedExifCameraModel cm ON cm.id_local = em.cameraModelRef",
                    ],
                    'cm.value LIKE "%s"',
                ),
                "camerasn": (
                    [
                        "LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image",
                        " LEFT JOIN AgInternedExifCameraSN csn ON csn.id_local = em.cameraSNRef",
                    ],
                    'csn.value LIKE "%s"',
                ),
                "lens": (
                    [
                        "LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image",
                        " LEFT JOIN AgInternedExifLens el ON el.id_local = em.lensRef",
                    ],
                    'el.value LIKE "%s"',
                ),
                "orientation": (
                    "",
                    'i.orientation = "%s"',
                ),
                # Limitation: width and height criteria work on the 'virtual' column dims,
                # so the 'dims' column MUST be included in the query
                "width": (
                    ["LEFT JOIN Adobe_imageDevelopSettings ids ON ids.image = i.id_local"],
                    'CAST(substr(dims, 1, instr(dims, "x")-1) AS int) %s %s',
                    self.func_oper_value,
                ),
                "height": (
                    ["LEFT JOIN Adobe_imageDevelopSettings ids ON ids.image = i.id_local"],
                    'CAST(substr(dims, instr(dims, "x")+1) AS int) %s %s',
                    self.func_oper_value,
                ),
                "aspectratio": (
                    "",
                    "i.aspectRatioCache %s %s",
                    self.func_oper_value,
                ),
                "monochrome": (
                    ["LEFT JOIN Adobe_AdditionalMetadata am ON i.id_local = am.image"],
                    "am.monochrome = %s",
                    self.func_0_1,
                ),
                "grayscale": (
                    ["LEFT JOIN Adobe_ImageDevelopSettings ids ON ids.image = i.id_local"],
                    "ids.grayscale = %s",
                    self.func_0_1,
                ),
                "hasgps": (
                    ["LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image"],
                    "em.hasGps = %s",
                    self.func_0_1,
                ),
                "gps": (
                    ["LEFT JOIN AgHarvestedExifMetadata em ON i.id_local = em.image"],
                    "%s",
                    self.func_gps,
                ),
                #
                # criteria on tables with several rows per photo (imports, collections, keywords)
                # are subqueries, not joins: joins would return one row per matching combination
                #
                "import": (
                    "",
                    "i.id_local IN (SELECT impim.image FROM AgLibraryImportImage impim WHERE impim.import = %s)",
                ),
                "idcollection": (
                    "",
                    "i.id_local IN (SELECT ci.image FROM AgLibraryCollectionImage ci WHERE ci.collection = %s)",
                ),
                "collection": (
                    "",
                    (
                        "i.id_local IN (SELECT ci.image FROM AgLibraryCollectionImage ci"
                        ' JOIN AgLibraryCollection col ON col.id_local = ci.collection WHERE col.name LIKE "%s")'
                    ),
                ),
                "idpubcollection": (
                    [
                        "LEFT JOIN AgLibraryPublishedCollectionImage pci ON pci.image = i.id_local",
                        " LEFT JOIN AgLibraryPublishedCollection pc ON pc.id_local = pci.collection",
                    ],
                    "pc.id_local = %s",
                ),
                "pubcollection": (
                    [
                        "LEFT JOIN AgLibraryPublishedCollectionImage pci ON pci.image = i.id_local",
                        "LEFT JOIN AgLibraryPublishedCollection pc ON pc.id_local = pci.collection",
                    ],
                    "%s",
                    self.func_published,
                ),
                "pubtime": (
                    ["LEFT JOIN AgRemotePhoto rm ON i.id_local = rm.photo"],
                    'CAST((select substr(rm.url, pos+1) from (select instr(rm.url, "/") as pos)) AS INTEGER) %s %s',
                    self.func_oper_dateutc_to_lrstamp,
                ),
                "metastatus": (
                    ["LEFT JOIN Adobe_AdditionalMetadata am ON i.id_local = am.image"],
                    "%s",
                    self.func_metastatus,
                ),
                "extfile": (
                    "LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local",
                    ' UPPER(fi.sidecarExtensions) LIKE "%s"',
                ),
                "stacks": (
                    "LEFT JOIN AgLibraryFolderStackImage fsi ON i.id_local = fsi.image",
                    "%s",
                    self.func_stacks,
                ),
                "idkeyword": (
                    "",
                    "i.id_local IN (SELECT kwi.image FROM AgLibraryKeywordImage kwi WHERE kwi.tag = %s)",
                ),
                "keyword": (
                    "",
                    (
                        "i.id_local IN (SELECT kwi.image FROM AgLibraryKeywordImage kwi"
                        ' JOIN AgLibraryKeyword kw ON kw.id_local = kwi.tag WHERE kw.name LIKE "%s")'
                    ),
                ),
                "haskeywords": (
                    "",
                    "%s",
                    self.func_haskeywords,
                ),
                "exifindex": (
                    "LEFT JOIN AgMetadataSearchIndex msi ON i.id_local = msi.image",
                    "%s",
                    self.func_exifindex,
                ),
                "country": (
                    [
                        "LEFT JOIN AgHarvestedIptcMetadata iptcmeta ON iptcmeta.image = i.id_local",
                        "LEFT JOIN AgInternedIptcCountry iptccountry ON iptccountry.id_local = iptcmeta.countryRef",
                    ],
                    "iptccountry.value %s",
                    self.func_like_value_or_null,
                ),
                "state": (
                    [
                        "LEFT JOIN AgHarvestedIptcMetadata iptcmeta ON iptcmeta.image = i.id_local",
                        "LEFT JOIN AgInternedIptcState iptcstate ON iptcstate.id_local = iptcmeta.stateRef",
                    ],
                    "iptcstate.value %s",
                    self.func_like_value_or_null,
                ),
                "city": (
                    [
                        "LEFT JOIN AgHarvestedIptcMetadata iptcmeta ON iptcmeta.image = i.id_local",
                        "LEFT JOIN AgInternedIptcCity iptccity ON iptccity.id_local = iptcmeta.cityRef",
                    ],
                    "iptccity.value %s",
                    self.func_like_value_or_null,
                ),
                "location": (
                    [
                        "LEFT JOIN AgHarvestedIptcMetadata iptcmeta ON iptcmeta.image = i.id_local",
                        "LEFT JOIN AgInternedIptcLocation iptcloc ON iptcloc.id_local = iptcmeta.locationRef",
                    ],
                    "iptcloc.value %s",
                    self.func_like_value_or_null,
                ),
                "sort": (
                    "",
                    "ORDER BY %s",
                ),
                "distinct": (
                    "",
                    "SELECT DISTINCT",
                ),
                "groupby": (
                    "",
                    "GROUP BY %s",
                ),
                "count": (
                    "",
                    "HAVING %s",
                ),
            },
        )

    def func_metastatus(self, value: str) -> str:
        """Specific value for metastatus."""
        if value == "unknown":
            return "am.externalXmpIsDirty = 0 AND i.sidecarStatus = 2.0"
        if value == "changedondisk":
            return "am.externalXmpIsDirty=1 and (i.sidecarStatus = 2.0 or i.sidecarStatus = 0.0)"
        if value == "hasbeenchanged":
            return "am.externalXmpIsDirty=0 and i.sidecarStatus = 1.0"
        if value == "conflict":
            return "am.externalXmpIsDirty=1 and i.sidecarStatus = 1.0"
        if value == "uptodate":
            return "am.externalXmpIsDirty=0 and i.sidecarStatus = 0.0"
        msg = f'invalid "metastatus" value "{value}"'
        raise LRSelectException(msg)

    def func_stacks(self, value: str) -> str:
        """Specific value for photos stack."""
        if value in ["top", "first"]:
            # photos at top of each stack
            return "fsi.position=1.0"
        if value in ["no", "none", "false"]:
            # photos not in a stack
            return "fsi.image is NULL"
        if value in ["no+top", "one"]:
            # photos not in stack, and photos at top of each stack
            return "(fsi.image is NULL OR fsi.position=1.0)"
        if value in ["yes", "all", "true"]:
            # photos in a stack
            return "fsi.image is NOT NULL"
        if value.isnumeric():
            return f"fsi.stack={value}"
        msg = f'invalid "stacks" value "{value}"'
        raise LRSelectException(msg)

    def func_exifindex(self, value: str) -> str:
        """Specific value for search exif."""
        if "&" in value:
            action = (" AND ", "&")
        elif "|" in value:
            action = (" OR ", "|")
        else:
            action = (" ", "__")
        return action[0].join(
            [f'msi.exifSearchIndex LIKE "%/t{val}/t%"' for val in value.split(action[1])]
        )

    def func_titleindex(self, value: str) -> str:
        """Specific value for title : in otherSearchIndex column."""
        if "&" in value:
            action = (" AND ", "&")
        elif "|" in value:
            action = (" OR ", "|")
        else:
            action = (" ", "__")
        return action[0].join(
            [f'msi.otherSearchIndex LIKE "%/t{val}/t%"' for val in value.split(action[1])]
        )

    def func_aperture(self, value: str) -> str:
        """
        Convert aperture value (as 5.6, F8) to LR value : 2 * ( log base 2 of F number).

        take care with operator '=' because it works on float
        """
        oper = None
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                if oper and oper[-1].upper() == "F":
                    oper = oper[:-1]
                value = value[index:]
                break
        if re.match(r"[F]*-?\d+(?:\.\d+)?", value) is None:
            msg = "invalid aperture value"
            raise LRSelectException(msg)
        if not oper:
            oper = "="
        return f"{oper} ROUND({2 * math.log2(float(value))}, 6)"

    def func_speed(self, value: str) -> str:
        """
        Convert speed value in seconds to LR value : log base 2 of Nth of speed.

        ex: ">=1/1000" for 1/1000s, "<5" for 5 seconds
        """
        oper = None
        for index, char in enumerate(value):
            if char.isnumeric():
                oper = value[:index]
                value = value[index:]
                break
        try:
            seconds: float
            if "/" in value:
                _n, _d = value.split("/")
                seconds = int(_n) / int(_d)
            else:
                seconds = int(value)
            # use 6 digits, as lightroom, for correct use with operator "="
            sql = f"{oper} {math.log2(float(1 / seconds)):.6f}"
        except ValueError as _e:
            raise LRSelectException(_e) from _e
        return sql

    def func_haskeywords(self, value: str) -> str:
        """Select photos with or without keywords."""
        if value in ["True", "1"]:
            return "i.id_local IN (SELECT DISTINCT kwi.image FROM AgLibraryKeywordImage kwi)"
        if value in ["False", "0"]:
            self._add_from(
                ["LEFT JOIN AgLibraryKeywordImage kwi1 ON i.id_local = kwi1.image"],
                self.froms,
            )
            return "kwi1.image IS NULL"
        msg = "invalid haskeywords value"
        raise LRSelectException(msg)

    def _photo_location(self, name_photo: str) -> tuple[float, float]:
        """Return coordinates of a geolocalized Lightroom photo."""
        lrphoto = LRSelectPhoto(self.config, self.lrdb)
        coords = lrphoto.select_generic("latitude, longitude", f"name={name_photo}").fetchone()
        if not coords:
            msg = f'Photo "{name_photo}" not in Lightroom'
            raise LRSelectException(msg)
        lat, lon = coords
        if not lat or not lon:
            msg = f'Photo "{name_photo}" is not geolocalized'
            raise LRSelectException(msg)
        return float(lat), float(lon)

    def _town_location(self, town: str) -> tuple[float, float]:
        """Return coordinates of a town, from the configured geocoder."""
        result = geocodage(self.config, town)
        if result is None:
            msg = "Town coordinates not found"
            raise LRSelectException(msg)
        (lat, lon), address = result
        logging.getLogger().info("Geocodage for %s : %s, %s (%s)", town, lat, lon, address)
        return lat, lon

    def _gps_bounds(self, value: str) -> tuple[float, float, float, float]:
        """Return (lat1, lon1, lat2, lon2) of the rectangle described by value."""
        re_gpsw = re.compile(r"([\d\-\.]+);([\d\-\.]+)\+([\d\.]+)")  # 45.78;-2.54+100
        re_2gps = re.compile(
            r"([\d\-\.]+);([\d\-\.]+)/([\d\-\.]+);([\d\-\.]+)"
        )  # 45.78;-2.51/46.01;1.05
        re_townw = re.compile(r"([\w\' -;]+)\+([\d\.]+)")  # paris+50
        re_2town = re.compile(r"([\w\' -]+)/([\w\' -]+)")  # paris/geneve
        re_photo = re.compile(r"photo:([\w\' _-]+)\+([\d\.]+)")  # photo_000151+2 (2km around photo)

        if match := re_photo.match(value):
            name_photo, width = match.groups()
            lat, lon = self._photo_location(name_photo)
        elif match := re_gpsw.match(value):
            str_lat, str_lon, width = match.groups()
            lat, lon = float(str_lat), float(str_lon)
        elif match := re_2gps.match(value):
            lat1, lon1, lat2, lon2 = match.groups()
            return float(lat1), float(lon1), float(lat2), float(lon2)
        elif match := re_townw.match(value):
            town, width = match.groups()
            lat, lon = self._town_location(town)
        elif match := re_2town.match(value):
            town1, town2 = match.groups()
            return *self._town_location(town1), *self._town_location(town2)
        else:
            msg = "GPS coordinates malformed"
            raise LRSelectException(msg)
        (lat1_, lon1_), (lat2_, lon2_) = square_around_location(lat, lon, float(width))
        return lat1_, lon1_, lat2_, lon2_

    def func_gps(self, value: str) -> str:
        """
        Select photos within gps values.

        ex: value=paris/lyon
        """
        lat1, lon1, lat2, lon2 = self._gps_bounds(value)
        lat1, lat2 = min(lat1, lat2), max(lat1, lat2)
        lon1, lon2 = min(lon1, lon2), max(lon1, lon2)
        return f"(em.hasGps = 1 AND em.gpsLatitude BETWEEN {lat1} AND {lat2} AND em.gpsLongitude BETWEEN {lon1} AND {lon2})"

    def func_published(self, value: str) -> str:
        """Select photos published."""
        if value.lower() in ["true", "0"]:
            return "i.id_local = pci.image"
        return f'(i.id_local = pci.image AND pc.name LIKE "{value}" COLLATE NOCASE)'

    def func_pubtime(self, value: str) -> str:
        """Select publish time."""
        if value == "True":
            return "i.id_local = pci.image"
        return f'(i.id_local = pci.image AND pc.name LIKE "{value}" COLLATE NOCASE)'

    def func_rating(self, value: str) -> str:
        """Select rating."""
        oper, value = self.func_oper_value(value)
        if oper == "<" or (oper == ">=" and value == "0"):
            return f"(i.rating IS NULL OR i.rating {oper} {value})"
        if oper == "=" and value == "0":
            return "i.rating IS NULL"
        return f"i.rating {oper} {value}"

    def func_flag(self, value: str) -> str:
        """Select flag : flagged (1), unflagged (0), rejected (-1)."""
        if value in ["1", "flagged"]:
            return "i.pick == 1"
        if value in ["0", "unflagged"]:
            return "i.pick == 0"
        if value in ["-1", "rejected"]:
            return "i.pick == -1"
        msg = "Incorrect flag value"
        raise LRSelectException(msg)

    @override
    def select_predefined(self, columns: str, _criters: str) -> str | None:
        """Return SQL of a predefined function (count_by_date, duplicated_names), else None."""

        def _todt(date: str) -> tuple[str, datetime]:
            parts = [int(part) for part in re.findall(r"\d+", date)]
            modes = {1: "by_year", _MONTH_PARTS: "by_month", _DAY_PARTS: "by_day"}
            if len(parts) not in modes:
                msg = "Incorrect date"
                raise LRSelectException(msg)
            year, month, day = (*parts, 1, 1)[:3]
            # capture times are stored as naive local times
            return modes[len(parts)], datetime(year, month, day)  # noqa: DTZ001

        match = re.match(r"count_by_date\((.+)\)", columns)
        if match:
            dt_to = None
            dates = match.group(1).split(",")
            mode, dt_from = _todt(dates[0])
            if len(dates) > 1:
                _, dt_to = _todt(dates[1])
            return self.lrdb.select_count_by_date(mode, dt_from, dt_to, sql=True)
        match = re.match(r"duplicated_names\((.*)\)", columns)
        if match:
            value = match.group(1)
            return self.lrdb.select_duplicates(value, sql=True)
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
    @override
    def select_generic(
        self, columns: str, criters: str = "", **kwargs: Unpack[SelectOptions]
    ) -> sqlite3.Cursor | str | None:
        r"""
        Build SQL request for photo table (Adobe_images) from key/value pair.

        columns :
            - 'name':
                'base' : base name (default), ex: "IMG_1101"
                'basext: base name + extension, ex: "IMG_1101.jpg"
                'full' : path + base name + extension, ex: "D:\Photos\IMG_1101.jpg"
                'base_vc' : base name + virtual copy name, ex: "IMG_1101 Copy 1"
                'basext_vc': base name + virtual copy name + extension, ex: "IMG_1101 Copy 1.jpg"
                'full_vc' :  path + base name + virtual copy name + extension, ex: "D:\Photos\IMG_1101 Copy 1.jpg"
            - 'idfolder'   : folder id
            - 'folder'     : folder name
            - 'id'         : id photo (Adobe_images.id_local)
            - 'uuid'       : UUID photo (Adobe_images.id_global)
            - 'rating'     : rating/note
            - 'colorlabel' : color and label
            - 'flag'       : flag (unflagged, flagged, rejected)
            - 'datemod'    : modificaton date
            - 'datecapt'   : capture date
            - 'modcount'   : number of modifications
            - 'master'     : master image of virtual copy
            - 'xmp'        : all xmp metadatas
            - 'vname'      : virtual copy name
            - 'stackpos'   : position in stack
            - 'stack'      : stack identifier
            - 'keywords'   : keywords list
            - 'collections': collections list
            - 'exif'       : 'var:SQLCOLUMN' : display column in table AgHarvestedExifMetadata. Ex: "exif=var:hasgps"
            - 'extfile'    : extension of an external/extension file (jpg,xmp,...)
            - 'dims'       : image dimensions in form <WIDTH>x<HEIGHT>
            - 'aspectratio': aspect ratio (width/height)
            - 'camera'     : camera name
            - 'lens'       : lens name
            - 'iso'        : ISO value
            - 'focal'      : focal lens
            - 'aperture'   : aperture lens
            - 'speed'      : speed shutter
            - 'monochrome' : monochrome image when = 1
            - 'flash'      : flash use ("0" = not used, "1" = used, "" = unknown)
            - 'latitude'   : GPS latitude
            - 'longitude'  : GPS longitude
            - 'creator'    : photo creator
            - 'copyright'  : copyright
            - 'caption'    : photo caption
            - 'pubname'    : remote path and name of published photo
            - 'pubcollection' : name of publish collection
            - 'pubtime'    : published datetime in seconds from 2001-1-1
            - 'pubposition': order number (float) in collection
            - 'country'    : location country name
            - 'state'      : location state name
            - 'city'       : location city name
            - 'location'   : location name
            - 'duration'   : video duration in seconds
            - 'count(NAME)' : count not NULL value for column NAME (ex: "count(master)")
            - 'countby(NAME)' : count aggregated not NULL value for column NAME
        criterias :
            - 'name'       : (str) filename without extension
            - 'exactname'  : (str) filename insensitive without extension
            - 'idfolder'   : (int) folder id
            - 'folder'     : (str) folder name, with optional jokers '%' (ex: folder=%family%)
            - 'ext'        : (str) file extension
            - 'id'         : (int) photo id (Adobe_images.id_local)
            - 'uuid'       : (string) photo UUID (Adobe_images.id_global)
            - 'rating'     : (str) [operator (<,<=,>,=, ...)] and rating/note (ex: "rating==5")
            - 'colorlabel' : (str) color and label. Color names are localized (Bleu, Rouge,...)
            - 'flag'       : (str) flag status : 'flagged', 'unflagged', 'rejected'. (ex: "flag=flagged")
            - 'creator'    : (str) photo creator, with optional jokers '%'
            - 'copyright"  : (str) photo copyright with optional jokers '%'
            - 'caption'    : (true/false/str) photo caption, with optional jokers '%'
            - 'datecapt'   : (str) operator (<,<=,>, >=) and capture date
            - 'datemod'    : (str) operator (<,<=,>, >=) and lightroom modification date
            - 'modcount'   : (int) number of modifications
            - 'iso'        : (int) ISO value with operators <,<=,>,>=,= (ex: "iso=>=1600")
            - 'focal'      : (int) focal lens with operators <,<=,>,>=,= (ex: "iso=>135")
            - 'aperture'   : (float) aperture lens with operators <,<=,>,>=,= (ex: "aperture=<=5.6")
            - 'speed'      : (float) speed shutter with operators <,<=,>,>=,= (ex: "speed=>=8")
            - 'flash'      : (0|1|null) flash use : 0=not used, 1=fired, null=unknown (ex: flash=1)
            - 'camera'     : (str) camera name, with optional jokers '%' (ex:"camera=canon%")
            - 'camerasn'   : (str) camera serial number
            - 'lens'       : (str) lens name, with optional jokers '%' (ex:"lens=%300%")
            - 'monochrome' : (bool) monochrome (ex="monochrome=1")
            - 'width'      : (int) cropped image width. Need to include column "dims"
            - 'height      : (int) cropped image height. Need to include column "dims"
            - 'aspectratio': (float) aspect ratio (width/height) (use ">1" for landscape and "<1" for portrait)
            - 'hasgps'     : (bool) has GPS datas
            - 'gps'        : (str) GPS rectangle defined by :
                                - town or coordinates, and bound in kilometer (ex:"paris+20", "45.7578;4.8320+10"),
                                - 2 towns or coordinates (ex: "grenoble/lyon", "44.84;-0.58/43.63;1.38")
                                - a geolocalized Lightroom photo name (ex:"photo:NIK_10312")
            - 'country'    : (str) country with optional jokers '%'
            - 'state'      : (str) state with optional jokers '%'
            - 'city'       : (str) city with optional jokers '%'
            - 'location'   : (str) location with optional jokers '%'
            - 'videos'     : (bool) type videos
            - 'exifindex'  : search words in exif (AgMetadataSearchIndex). Use '&' for AND words '|' for OR. ex: "exifindex=%Lowy%&%blanko%"
            - 'vcopies'    : 'NULL'|'!NULL'|'<NUM>' : all, none virtual copies or copies for a master image NUM
            - 'idkeyword'  : (int) keyword id
            - 'keyword'    : (str) keyword name.
            - 'haskeywords': (bool) photos with or without keywords
            - 'import'     : (int) import id
            - 'stacks'     : operation on stacks in :
                    'yes'    = photos in a stack
                    'no'     = excludes photos in a stack
                    'top'    = photos at the top of stacks
                    'no+top' = excludes photos in a stack not at first position
                    <NUM>    = photos in the stack identifier NUM
            - 'metastatus' :  metadatas status
                    'conflict' = metadatas different on disk from db
                    'changedondisk' = metadata changed externally on disk
                    'hasbeenchanged' = to be save on disk
                    'conflict' = metadatas different on disk from db
                    'uptodate' = uptodate, in error, or to write on disk
                    'unknown' = write error, phot missing ...
            - 'idcollection' : (int) collection id
            - 'collection' : (str) collection name
            - 'idpubcollection' : (int) publish collection id
            - 'pubcollection: (str) publish collection name
            - 'pubtime     : (str) publish time,  operator (<,<=,>, >=)
            - 'extfile'    : (str) has external file with <value> extension as jpg,xmp... (field AgLibraryFile.sidecarExtensions)

            - 'count(NAME) : (str) criter for column countby(NAME)
            - 'sort'       : (int|str) sort result: column index (one based) or column name
            - 'distinct'   : suppress similar lines of results
        kwargs :
            - distinct : request SELECT DISTINCT
            - debug : print sql
            - print : print sql and return None
            - sql : return SQL string only
        """
        if not columns:
            columns = "name=basext"
        return super().select_generic(columns, criters, **kwargs)
