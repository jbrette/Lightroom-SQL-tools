# catalog-access Specification

## Purpose

Defines how a Lightroom Classic catalog is opened safely while Lightroom may be running, and the fixed catalog queries the library offers alongside the generic column and criteria selection.

## Requirements

### Requirement: Catalog or INI file argument
The catalog argument (`-b`) SHALL be treated as a catalog when its path ends with `lrcat`. Any other path SHALL be loaded as a configuration file, and its `LRCatalog` value SHALL be used as the catalog.

#### Scenario: Catalog path
- **WHEN** a script is run with `-b /photos/main.lrcat`
- **THEN** that catalog is opened

#### Scenario: INI path
- **WHEN** a script is run with `-b family.ini` and that file sets `LRCatalog = /photos/family.lrcat`
- **THEN** `/photos/family.lrcat` is opened

#### Scenario: No argument
- **WHEN** a script is run without `-b`
- **THEN** the catalog named by the configuration's `LRCatalog` is opened

### Requirement: Read-only immutable access
The catalog SHALL be opened by default in read-only, private-cache and immutable mode, so the tools can run while Lightroom has the catalog open. The library SHALL never modify a catalog; any write attempt through the connection SHALL fail.

#### Scenario: Write attempt
- **WHEN** a delete statement is executed on an opened catalog
- **THEN** it fails with a read-only database error
- **AND** the catalog file is unchanged

### Requirement: Custom open options
A library caller SHALL be able to replace the default open mode with its own SQLite URI options; an empty option string SHALL open the file with no URI options.

#### Scenario: Caller-supplied options
- **WHEN** a caller opens a catalog with options `mode=ro`
- **THEN** the catalog is opened read-only without the immutable flag

### Requirement: Missing catalog
Opening a catalog path that does not exist SHALL fail with the error `LR catalog doesn't exist: <path>`.

#### Scenario: Nonexistent file
- **WHEN** a caller opens `/tmp/missing.lrcat`
- **THEN** the error message is `LR catalog doesn't exist: /tmp/missing.lrcat`

### Requirement: Not a Lightroom catalog
Opening a file that is not an SQLite database, or an SQLite database without the Lightroom version variable, SHALL fail with the error `Unable to open LR catalog`.

#### Scenario: Other SQLite database
- **WHEN** a caller opens an SQLite file containing only an unrelated table
- **THEN** the error message is `Unable to open LR catalog`

### Requirement: Catalog version
Opening a catalog SHALL read and expose the catalog's database version string.

#### Scenario: Lightroom Classic 13 catalog
- **WHEN** a Lightroom Classic 13 catalog is opened
- **THEN** the reported version is `1303001`

### Requirement: Base name lookup
The library SHALL tell whether a photo file base name (without extension) exists in the catalog, compared case-insensitively.

#### Scenario: Existing and missing names
- **WHEN** the catalog holds `IMG_0001.CR2`
- **THEN** `IMG_0001` and `img_0001` are reported as existing
- **AND** `IMG_9999` is reported as missing

### Requirement: Master and virtual copies
The library SHALL return a master photo and all its virtual copies, ordered by photo id, with the requested columns.

#### Scenario: Photo with one copy
- **WHEN** master photo 1 has virtual copy 5 named `Copy 1` and columns `id,vname` are requested
- **THEN** the rows are `(1, none)` and `(5, "Copy 1")`

### Requirement: Duplicate names by base name
The duplicate query in format `1` (the default) SHALL list, for every base name shared by several master photos (excluding virtual copies and videos, base names compared case-insensitively), one full file path and the number of photos sharing it.

#### Scenario: Two files with the same base name
- **WHEN** two folders each hold a master photo `IMG_0042` and duplicates are requested without options
- **THEN** one row gives a full path of `IMG_0042` and the count 2

### Requirement: Duplicate names with copy name
The duplicate query in format `2` SHALL list the UUID and name (base name, copy name and extension) of every photo whose name appears more than once, ordered by name; `2,novideos` SHALL exclude videos from the duplicate count. Any other format SHALL fail with `Invalid format`.

#### Scenario: Unknown format
- **WHEN** duplicates are requested with format `3`
- **THEN** the error message is `Invalid format`

#### Scenario: Excluding videos
- **WHEN** duplicates are requested with format `2,novideos`
- **THEN** the query ignores video files when counting duplicates

### Requirement: Imports
The library SHALL list catalog imports as (import id, import date, number of photos imported), ordered by import date, or only the import with a given id.

#### Scenario: All imports
- **WHEN** the catalog has one import on `2018-08-01T10:00:00` with two photos
- **THEN** the imports list is `[(1, "2018-08-01T10:00:00", 2)]`

#### Scenario: One import by id
- **WHEN** import 1 is requested
- **THEN** the same single row is returned

### Requirement: Collections by type and name
The library SHALL list standard, smart or all (standard and smart) collections as (id, name, type), ordered by name. A name filter containing `%` SHALL match as a pattern; otherwise it SHALL match exactly; both comparisons SHALL ignore case.

#### Scenario: Standard collections
- **WHEN** the catalog has standard collections `Holidays` and `Best`
- **THEN** standard collections are listed as `Best`, `Holidays`

#### Scenario: Pattern and exact name
- **WHEN** all collections are filtered by `h%`, then by `best`
- **THEN** the first filter returns `Holidays`
- **AND** the second returns `Best`

### Requirement: Collection hierarchy
The library SHALL return every user collection set, standard collection and smart collection (system collections excluded) with its full name path from the top-level set, its id and its type, sorted by name path. The same SHALL be available for published collections and publish services.

#### Scenario: Flat collections
- **WHEN** the catalog has top-level collections `Best`, `Canon Family`, `Five Stars` and `Holidays`
- **THEN** the name paths are `[Best]`, `[Canon Family]`, `[Five Stars]`, `[Holidays]`

#### Scenario: Nested collection
- **WHEN** collection `Paris` is inside set `Trips`
- **THEN** its name path is `[Trips, Paris]`

### Requirement: Smart collection definition
The library SHALL return a smart collection's definition, looked up by numeric id or by name (case-insensitive, `%` allowed), either as stored text or decoded into a structure. A missing collection, or a definition that does not decode to a table, SHALL return nothing.

#### Scenario: Id and name give the same definition
- **WHEN** smart collection 12 is named `Five Stars`
- **THEN** looking it up by `12` and by `Five Stars` gives the same decoded definition

#### Scenario: Raw definition
- **WHEN** the raw definition of `Five Stars` is requested
- **THEN** the text starts with `s = {`

#### Scenario: Unknown collection
- **WHEN** the smart collection `Nope` is requested
- **THEN** nothing is returned

### Requirement: Count photos by date
The library SHALL count photos per year, month or day of capture between a start date and an end date (now when absent), returning (period, count) rows. Per-day and per-month counts SHALL exclude the end date; per-year counts SHALL include it.

#### Scenario: Per month
- **WHEN** photos are counted per month from 2018-01 to 2019-01 and two photos are from May 2018 and one from July 2018
- **THEN** the rows are `("2018-05", 2)` and `("2018-07", 1)`

### Requirement: XMP metadata
The library SHALL return the stored XMP metadata of a photo identified by numeric id or by file base name.

#### Scenario: By id and by name
- **WHEN** photo 1 has XMP `<x:xmpmeta/>` and photo `IMG_0002` has empty XMP
- **THEN** the XMP of `1` is `<x:xmpmeta/>`
- **AND** the XMP of `IMG_0002` is empty

### Requirement: EXIF metadata fields
The library SHALL return the requested harvested EXIF fields of a photo identified by numeric id or by file base name. A value that reads as an integer SHALL be taken as an id, so a photo named `1235` is looked up as photo id 1235.

#### Scenario: Numeric base name
- **WHEN** EXIF fields are requested for `1235`
- **THEN** the photo with id 1235 is used, not the file named `1235`

### Requirement: Production path from XMP
The library SHALL derive a photo's capture time from its XMP (`exif:DateTimeOriginal`, else `exif:DateTimeDigitized`, else `xmp:CreateDate`, else 1 January 1900) and return a production path made of a base directory and that time formatted with a caller date format.

#### Scenario: Original date present
- **WHEN** the XMP holds `exif:DateTimeOriginal="2019-08-13T19:47:33"`, the base is `/prod` and the format is `%Y/%m`
- **THEN** the path is `/prod/2019/08` and the capture time is 2019-08-13 19:47:33

#### Scenario: No date in XMP
- **WHEN** the XMP holds none of the three date keys
- **THEN** the capture time is 1900-01-01 00:00:00

### Requirement: Metadata to archive
The library SHALL list the full names of photos whose metadata status is in conflict with their file, sorted by capture time.

#### Scenario: Conflicting metadata
- **WHEN** one photo's metadata status is conflict
- **THEN** that photo's full name is returned
