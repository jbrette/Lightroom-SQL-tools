"""
Shared fixtures: a small synthetic Lightroom catalog built from the real schema
(tests/data/schema.sql, Lightroom Classic 13) and filled with known photos.

Photos (Adobe_images.id_local):
    1  /photos/2018/IMG_0001.JPG  2018-05-10  rating 5, flagged, Red, Canon, F8 1/1000, Paris GPS,
                                              keywords Places|beach + family, collection Holidays,
                                              cropped 3000x2000, published, import 1
    2  /photos/2018/IMG_0002.CR2  2018-07-20  rating 3, Canon, F5.6 1/250, ISO 1600, 200mm, Lyon GPS,
                                              keyword family, collections Holidays + Best, import 1
    3  /photos/2019/DSC_0100.NEF  2019-01-05  rejected, Nikon, ISO 6400, monochrome, stack 1 top
    4  /photos/2019/DSC_0101.NEF  2019-01-05  rating 1, Nikon, stack 1 position 2
    5  virtual copy "Copy 1" of photo 1 (same file), rating 4
    6  /photos/2019/VID_0001.MP4  2019-06-01  video, 30 seconds
"""

import sqlite3
from pathlib import Path

import pytest

from lrtools.lrcat import LRCatDB
from lrtools.lrtoolconfig import LRToolConfig

DATA_DIR = Path(__file__).parent / "data"

# Lightroom stores aperture as 2*log2(F) and shutter speed as log2(1/seconds)
APERTURE_F8 = 6.0
APERTURE_F56 = 4.970854
SPEED_1000 = 9.965784
SPEED_250 = 7.965784

# seconds since 2001-01-01 UTC
TOUCH_2019_08_02 = 586396800.0
TOUCH_2020_01_15 = 600739200.0

SMART_FIVE_STARS = """s = {
	{
		criteria = "rating",
		operation = ">=",
		value = 5,
	},
	combine = "intersect",
}
"""

SMART_CANON_FAMILY = """s = {
	{
		criteria = "camera",
		operation = "any",
		value = "canon",
		value2 = "",
	},
	{
		criteria = "keywords",
		operation = "any",
		value = "family",
		value2 = "",
	},
	combine = "intersect",
}
"""

FIXTURE_SQL = f"""
INSERT INTO Adobe_variablesTable (id_local, id_global, name, value)
    VALUES (1, 'var-1', 'Adobe_DBVersion', '1303001');

INSERT INTO AgLibraryRootFolder (id_local, id_global, absolutePath, name)
    VALUES (1, 'root-1', '/photos/', 'photos');
INSERT INTO AgLibraryFolder (id_local, id_global, pathFromRoot, rootFolder) VALUES
    (1, 'folder-1', '2018/', 1),
    (2, 'folder-2', '2019/', 1);
INSERT INTO AgLibraryFile (id_local, id_global, baseName, extension, folder, modTime, sidecarExtensions) VALUES
    (1, 'file-1', 'IMG_0001', 'JPG', 1, 100.0, 'xmp'),
    (2, 'file-2', 'IMG_0002', 'CR2', 1, 200.0, 'xmp'),
    (3, 'file-3', 'DSC_0100', 'NEF', 2, 300.0, ''),
    (4, 'file-4', 'DSC_0101', 'NEF', 2, 400.0, ''),
    (6, 'file-6', 'VID_0001', 'MP4', 2, 600.0, '');

INSERT INTO Adobe_images (id_local, id_global, rootFile, captureTime, rating, pick, colorLabels,
        fileFormat, fileWidth, fileHeight, orientation, aspectRatioCache, touchTime, touchCount,
        masterImage, copyName, sidecarStatus) VALUES
    (1, 'UUID-1', 1, '2018-05-10T10:00:00', 5, 1, 'Red', 'JPG', 6000, 4000, 'AB', 1.5, {TOUCH_2019_08_02}, 3, NULL, NULL, 0.0),
    (2, 'UUID-2', 2, '2018-07-20T15:30:00', 3, 0, '', 'RAW', 6000, 4000, 'BC', 0.6667, {TOUCH_2020_01_15}, 1, NULL, NULL, 1.0),
    (3, 'UUID-3', 3, '2019-01-05T08:00:00', NULL, -1, '', 'RAW', 6016, 4016, 'AB', 1.498, 0, 0, NULL, NULL, 0.0),
    (4, 'UUID-4', 4, '2019-01-05T08:00:05', 1, 0, '', 'RAW', 6016, 4016, 'AB', 1.498, 0, 0, NULL, NULL, 0.0),
    (5, 'UUID-5', 1, '2018-05-10T10:00:00', 4, 0, '', 'JPG', 6000, 4000, 'AB', 1.5, 0, 0, 1, 'Copy 1', 0.0),
    (6, 'UUID-6', 6, '2019-06-01T12:00:00', NULL, 0, '', 'VIDEO', 1920, 1080, 'AB', 1.7778, 0, 0, NULL, NULL, 0.0);

INSERT INTO AgInternedExifCameraModel (id_local, value, searchIndex) VALUES
    (1, 'Canon EOS 5D', '/tcanon/teos/t5d/t'),
    (2, 'NIKON D750', '/tnikon/td750/t');
INSERT INTO AgInternedExifCameraSN (id_local, value) VALUES (1, 'SN1234');
INSERT INTO AgInternedExifLens (id_local, value, searchIndex) VALUES
    (1, 'EF24-70mm f/2.8L', '/tef24-70mm/tf/2.8l/t'),
    (2, 'EF70-200mm f/4L', '/tef70-200mm/tf/4l/t');
INSERT INTO AgHarvestedExifMetadata (id_local, image, aperture, cameraModelRef, cameraSNRef, flashFired,
        focalLength, gpsLatitude, gpsLongitude, hasGPS, isoSpeedRating, lensRef, shutterSpeed) VALUES
    (1, 1, {APERTURE_F8}, 1, 1, 0, 50, 48.8566, 2.3522, 1, 100, 1, {SPEED_1000}),
    (2, 2, {APERTURE_F56}, 1, 1, 1, 200, 45.7640, 4.8357, 1, 1600, 2, {SPEED_250}),
    (3, 3, NULL, 2, NULL, 0, 35, NULL, NULL, 0, 6400, NULL, NULL),
    (4, 4, NULL, 2, NULL, 0, 35, NULL, NULL, 0, 6400, NULL, NULL),
    (5, 5, {APERTURE_F8}, 1, 1, 0, 50, 48.8566, 2.3522, 1, 100, 1, {SPEED_1000}),
    (6, 6, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, NULL, NULL, NULL);

INSERT INTO AgInternedIptcCreator (id_local, value) VALUES (1, 'Alice');
INSERT INTO AgInternedIptcCity (id_local, value) VALUES (1, 'Paris'), (2, 'Lyon');
INSERT INTO AgInternedIptcCountry (id_local, value) VALUES (1, 'France');
INSERT INTO AgInternedIptcState (id_local, value) VALUES (1, 'Ile-de-France');
INSERT INTO AgInternedIptcLocation (id_local, value) VALUES (1, 'Tour Eiffel');
INSERT INTO AgHarvestedIptcMetadata (id_local, image, cityRef, countryRef, creatorRef, locationRef, stateRef) VALUES
    (1, 1, 1, 1, 1, 1, 1),
    (2, 2, 2, 1, NULL, NULL, NULL);
INSERT INTO AgLibraryIPTC (id_local, image, caption, copyright) VALUES
    (1, 1, 'sunset at the beach', 'Alice 2018'),
    (2, 2, NULL, NULL);

INSERT INTO Adobe_imageDevelopSettings (id_local, image, croppedWidth, croppedHeight, digest, grayscale,
        hasDevelopAdjustments) VALUES
    (1, 1, 3000, 2000, 'digest-1', 0, 1),
    (2, 2, 'uncropped', 'uncropped', 'digest-2', 0, 0),
    (3, 3, 'uncropped', 'uncropped', 'digest-3', 1, 1),
    (4, 4, 'uncropped', 'uncropped', 'digest-4', 0, 0),
    (5, 5, 'uncropped', 'uncropped', 'digest-5', 0, 0),
    (6, 6, 'uncropped', 'uncropped', 'digest-6', 0, 0);
INSERT INTO Adobe_AdditionalMetadata (id_local, id_global, image, monochrome, externalXmpIsDirty, xmp) VALUES
    (1, 'am-1', 1, 0, 0, '<x:xmpmeta/>'),
    (2, 'am-2', 2, 0, 0, ''),
    (3, 'am-3', 3, 1, 0, ''),
    (4, 'am-4', 4, 0, 0, ''),
    (5, 'am-5', 5, 0, 0, ''),
    (6, 'am-6', 6, 0, 0, '');
INSERT INTO Adobe_libraryImageDevelopHistoryStep (id_local, id_global, image, dateCreated, name) VALUES
    (1, 'hist-1', 1, {TOUCH_2019_08_02}, 'Crop'),
    (2, 'hist-2', 1, {TOUCH_2020_01_15}, 'Export');

INSERT INTO AgLibraryFolderStackImage (id_local, image, stack, position) VALUES
    (1, 3, 1, 1.0),
    (2, 4, 1, 2.0);

INSERT INTO AgVideoInfo (id_local, image, duration) VALUES (1, 6, '000000000000012c/000000000000000a');

INSERT INTO AgLibraryKeyword (id_local, id_global, name, lc_name, parent, keywordType, genealogy) VALUES
    (1, 'kw-root', NULL, NULL, NULL, NULL, ''),
    (2, 'kw-places', 'Places', 'places', 1, NULL, '/22'),
    (3, 'kw-beach', 'beach', 'beach', 2, NULL, '/22/33'),
    (4, 'kw-family', 'family', 'family', 1, NULL, '/24'),
    (5, 'kw-alice', 'Alice', 'alice', 1, 'person', '/25');
INSERT INTO AgLibraryKeywordImage (id_local, image, tag) VALUES
    (1, 1, 3),
    (2, 1, 4),
    (3, 2, 4);

INSERT INTO AgLibraryCollection (id_local, creationId, genealogy, name, parent, systemOnly) VALUES
    (10, 'com.adobe.ag.library.collection', '/210', 'Holidays', NULL, 0),
    (11, 'com.adobe.ag.library.collection', '/211', 'Best', NULL, 0),
    (12, 'com.adobe.ag.library.smart_collection', '/212', 'Five Stars', NULL, 0),
    (13, 'com.adobe.ag.library.smart_collection', '/213', 'Canon Family', NULL, 0);
INSERT INTO AgLibraryCollectionImage (id_local, collection, image) VALUES
    (1, 10, 1),
    (2, 10, 2),
    (3, 11, 2);
INSERT INTO AgLibraryCollectionContent (id_local, collection, owningModule, content) VALUES
    (1, 12, 'ag.library.smart_collection', :five_stars),
    (2, 13, 'ag.library.smart_collection', :canon_family);

INSERT INTO AgLibraryPublishedCollection (id_local, name, creationId) VALUES (20, 'Flickr', 'com.adobe.ag.publish');
INSERT INTO AgLibraryPublishedCollectionImage (id_local, collection, image, positionInCollection) VALUES (1, 20, 1, 'a');
INSERT INTO AgRemotePhoto (id_local, id_global, collection, photo, remoteId, url) VALUES
    (1, 'rp-1', 20, 1, 'remote-1', 'flickr/600739200');

INSERT INTO AgLibraryImport (id_local, importDate, name) VALUES (1, '2018-08-01T10:00:00', 'import 1');
INSERT INTO AgLibraryImportImage (id_local, image, import) VALUES (1, 1, 1), (2, 2, 1);

INSERT INTO AgMetadataSearchIndex (id_local, image, exifSearchIndex, otherSearchIndex) VALUES
    (1, 1, '/tcanon/teos/t5d/t', '/tsunset/t'),
    (2, 3, '/tnikon/td750/t', '');
"""


def build_catalog(path):
    """create a synthetic catalog file at path"""
    conn = sqlite3.connect(path)
    conn.executescript((DATA_DIR / "schema.sql").read_text())
    # executescript doesn't support parameters: run inserts one by one
    params = {"five_stars": SMART_FIVE_STARS, "canon_family": SMART_CANON_FAMILY}
    for statement in FIXTURE_SQL.split(";\n"):
        if statement.strip():
            conn.execute(statement, params if ":" in statement else ())
    conn.commit()
    conn.close()
    return path


@pytest.fixture(scope="session")
def catalog_path(tmp_path_factory):
    """path of the synthetic catalog"""
    return build_catalog(tmp_path_factory.mktemp("catalog") / "test.lrcat")


@pytest.fixture
def config():
    """default config, independent of any lrtools.ini"""
    cfg = LRToolConfig(None)
    cfg.dayfirst = True
    return cfg


@pytest.fixture
def lrdb(config, catalog_path):
    """catalog opened read-only, as scripts do"""
    db = LRCatDB(config, str(catalog_path))
    yield db
    db.conn.close()


@pytest.fixture
def select_ids(lrdb):
    """run a photo select on criteria and return sorted distinct photo ids"""

    def _select(criteria, columns="id"):
        rows = lrdb.lrphoto.select_generic(columns, criteria).fetchall()
        return sorted({row[0] for row in rows})

    return _select
