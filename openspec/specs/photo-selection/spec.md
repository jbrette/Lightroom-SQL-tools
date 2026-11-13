# photo-selection Specification

## Purpose

Lets users select photos and videos of a Lightroom Classic catalog by file, date, rating, EXIF, IPTC, location, keyword, collection, publication and stack data, and return chosen photo attributes or catalog-wide statistics.

## Requirements

### Requirement: Default photo column
When the columns string is empty, photo selection SHALL return the file name with its extension (`name=basext`) as the only column.

#### Scenario: Empty columns
- **WHEN** photos are selected with an empty columns string and criteria `id=2`
- **THEN** the single row is `("IMG_0002.CR2",)`

### Requirement: Photo name column variants
The `name` column SHALL accept the variants `base` (base name), `basext` (base name and extension, also the bare `name`), `full` (folder path, base name and extension), and `base_vc`, `basext_vc`, `full_vc`, which append the virtual copy name to the base name.

#### Scenario: Name variants of one photo
- **WHEN** the photo at `/photos/2018/IMG_0001.JPG` is selected with `name=base`, `name=basext` and `name=full`
- **THEN** the values are `IMG_0001`, `IMG_0001.JPG` and `/photos/2018/IMG_0001.JPG`

#### Scenario: Virtual copy name appended
- **WHEN** virtual copy `Copy 1` of `IMG_0001.JPG` is selected with `name=basext_vc,vname`
- **THEN** the row is `("IMG_0001Copy 1.JPG", "Copy 1")`

### Requirement: Identity and file columns
Photo selection SHALL provide the columns `id`, `uuid`, `uuidfile`, `idfolder`, `folder` (folder path), `master` (master photo of a virtual copy), `vname` (virtual copy name), `extfile` (sidecar extensions), `digest` and `all` (every field of the photo record).

#### Scenario: Folder and identifiers
- **WHEN** photo 1 is selected with `folder`, `uuid` and `extfile`
- **THEN** the values are `/photos/2018/`, `UUID-1` and `xmp`

### Requirement: Rating, flag, label and edit columns
Photo selection SHALL provide `rating`, `colorlabel`, `flag` (1 flagged, 0 unflagged, -1 rejected), `datecapt` (capture time as `YYYY-MM-DDTHH:MM:SS`), `datemod` (last modification, Lightroom timestamp), `datehist` (last develop history step other than exports and publications), `modcount` and `xmp`.

#### Scenario: Photo metadata values
- **WHEN** photo 1 is selected with `rating`, `colorlabel`, `flag` and `datecapt`
- **THEN** the values are `5`, `Red`, `1` and `2018-05-10T10:00:00`

### Requirement: Keyword and collection list columns
The `keywords` and `collections` columns SHALL return, in one value per photo, the comma-separated names of the photo's keywords and of the collections it belongs to.

#### Scenario: Lists for one photo
- **WHEN** a photo with keywords beach and family in collection Holidays is selected with `keywords,collections`
- **THEN** the values are `beach,family` and `Holidays`

### Requirement: EXIF and image columns
Photo selection SHALL provide `camera`, `camerasn`, `lens`, `iso`, `focal`, `aperture`, `speed`, `flash`, `orientation`, `monochrome`, `grayscale`, `hasgps`, `latitude`, `longitude`, `width`, `height`, `cropwidth`, `cropheight`, `aspectratio`, `duration` (video length in seconds), and `exif=var:<field>` for any other EXIF field.

#### Scenario: EXIF values
- **WHEN** photo 1 is selected with `camera`, `lens`, `iso` and `focal`
- **THEN** the values are `Canon EOS 5D`, `EF24-70mm f/2.8L`, `100` and `50`

### Requirement: dims column reports oriented, cropped size
The `dims` column SHALL return `<width>x<height>` using the cropped size when the photo is cropped, the file size otherwise, and SHALL swap width and height for photos rotated a quarter turn.

#### Scenario: Cropped photo
- **WHEN** a photo cropped to 3000 by 2000 is selected with `dims`
- **THEN** the value is `3000x2000`

#### Scenario: Rotated photo
- **WHEN** a 6000x4000 file rotated a quarter turn is selected with `dims`
- **THEN** the value is `4000x6000`

### Requirement: IPTC and location columns
Photo selection SHALL provide `creator`, `copyright`, `caption`, `country`, `state`, `city` and `location`.

#### Scenario: Location values
- **WHEN** photo 1 is selected with `city`, `country` and `location`
- **THEN** the values are `Paris`, `France` and `Tour Eiffel`

### Requirement: Publication and stack columns
Photo selection SHALL provide `pubcollection` (publish collection name), `pubname` (remote id of the published photo), `pubtime` (publish time in seconds since 2001-01-01), `pubposition`, `stack` (stack id) and `stackpos` (position in the stack).

#### Scenario: Published photo
- **WHEN** a photo published to the collection Flickr as `remote-1` is selected with `pubcollection,pubname`
- **THEN** the values are `Flickr` and `remote-1`

### Requirement: Every column executes
Every photo column SHALL execute on any catalog and return exactly one row per selected photo.

#### Scenario: One row per photo for every column
- **WHEN** each column is selected together with `id` and no criteria on a catalog of six photos
- **THEN** each selection returns six rows

### Requirement: Identity criteria
Photo selection SHALL accept the criteria `id`, `uuid`, `uuidfile` and `idfolder`, each selecting photos whose identifier equals the value.

#### Scenario: By id
- **WHEN** the criteria string is `id=4`
- **THEN** only photo 4 is selected

#### Scenario: By UUID
- **WHEN** the criteria string is `uuid=UUID-3`
- **THEN** only photo 3 is selected

### Requirement: File name and folder criteria
The criteria `name` (base name plus virtual copy name), `ext`, `folder` (full folder path) and `extfile` (sidecar extensions) SHALL match with `%` jokers; `exactname` and `exact_ext` SHALL match the upper-cased base name or extension exactly, so their values must be written in upper case.

#### Scenario: Name with joker
- **WHEN** the criteria string is `name=%Copy%`
- **THEN** only the virtual copy named `Copy 1` is selected

#### Scenario: exactname is compared upper case
- **WHEN** the criteria strings are `exactname=IMG_0001` and `exactname=img_0001`
- **THEN** the first selects the photo and its virtual copy, the second selects nothing

### Requirement: Rating criterion treats no rating as zero
The `rating` criterion SHALL compare the rating with the given operator, and SHALL treat an unrated photo as rating 0 for `=0`, `<n` and `>=0`.

#### Scenario: Unrated photos
- **WHEN** the criteria string is `rating=0`
- **THEN** only unrated photos are selected

#### Scenario: Less than includes unrated
- **WHEN** the criteria string is `rating=<3`
- **THEN** photos rated 1 or 2 and unrated photos are selected

### Requirement: Flag and color label criteria
The `flag` criterion SHALL accept `flagged`/`1`, `unflagged`/`0` and `rejected`/`-1`, and reject other values with `Incorrect flag value`. The `colorlabel` criterion SHALL match a label name exactly, or select photos with any label for `true` and without one for `false`.

#### Scenario: Rejected photos
- **WHEN** the criteria string is `flag=-1`
- **THEN** only rejected photos are selected

#### Scenario: Any color label
- **WHEN** the criteria string is `colorlabel=true`
- **THEN** only photos with a color label are selected

### Requirement: Capture date criterion compares at the precision given
The `datecapt` criterion SHALL require an operator before the date and compare at the precision written: a year alone, a month and year, or a full date compare by year, month or day; a date with a time compares the exact time. Day/month order SHALL follow the `DayFirst` setting. A date without operator SHALL fail with `None operator for date`.

#### Scenario: Whole year
- **WHEN** the criteria string is `datecapt==2018`
- **THEN** every photo captured in 2018 is selected

#### Scenario: Month
- **WHEN** the criteria string is `datecapt==7-2018`
- **THEN** only photos captured in July 2018 are selected

#### Scenario: Missing operator
- **WHEN** the criteria string is `datecapt=2018`
- **THEN** selection fails with `None operator for date`

### Requirement: Modification and publish time criteria
The `datemod` criterion SHALL compare the last modification time with a date read as local time, and `pubtime` SHALL compare the publish time with a date read as UTC. An unreadable date SHALL fail with `invalid date value on "datemod"`. The `modcount` criterion SHALL compare the modification count.

#### Scenario: Modified since a date
- **WHEN** the criteria string is `datemod=>=1-1-2020`
- **THEN** only photos modified on or after 1 January 2020 are selected

### Requirement: EXIF numeric criteria
The criteria `iso`, `focal` and `aspectratio` SHALL compare the stored value with an optional operator. `aperture` SHALL accept an f-number with optional `F` prefix and `speed` seconds or a fraction such as `1/500`; both SHALL be converted to Lightroom's logarithmic storage so the operator applies to the f-number or exposure time.

#### Scenario: Aperture with F prefix
- **WHEN** the criteria string is `aperture=F5.6`
- **THEN** only photos shot at f/5.6 are selected

#### Scenario: Faster than a speed
- **WHEN** the criteria string is `speed=>=1/500`
- **THEN** photos with an exposure value at or above that of 1/500 s are selected, here 1/1000 s photos

### Requirement: EXIF text and flag criteria
The criteria `camera`, `camerasn` and `lens` SHALL match with `%` jokers; `orientation` SHALL match the orientation code exactly; `flash` SHALL accept `0`, `1`, `null`/`false` (unknown) or `!null`/`true`; `monochrome`, `grayscale` and `hasgps` SHALL accept `0`/`false` or `1`/`true` and reject other values.

#### Scenario: Camera joker
- **WHEN** the criteria string is `camera=%canon%`
- **THEN** every Canon photo is selected

#### Scenario: Invalid hasgps value
- **WHEN** the criteria string is `hasgps=maybe`
- **THEN** selection fails with `invalid hasgps criterion value`

### Requirement: Image size criteria need the dims column
The `width` and `height` criteria SHALL compare the oriented, cropped size reported by the `dims` column, and SHALL only work when `dims` is among the selected columns.

#### Scenario: Width with dims
- **WHEN** the columns string is `id,dims` and the criteria string is `width=>=5000`
- **THEN** photos whose oriented width is at least 5000 are selected

### Requirement: Video and virtual copy criteria
The `videos` criterion SHALL select videos for a true value and exclude them for a false one. The `vcopies` criterion SHALL select master photos for `null`, virtual copies for `!null`, and the virtual copies of photo `<n>` for a number.

#### Scenario: Exclude videos
- **WHEN** the criteria string is `videos=0`
- **THEN** every photo except videos is selected

#### Scenario: Copies of one master
- **WHEN** the criteria string is `vcopies=1`
- **THEN** the virtual copies of photo 1 are selected

### Requirement: IPTC text criteria
The criteria `caption`, `copyright`, `country`, `state`, `city` and `location` SHALL match with `%` jokers, select photos without a value for `null`/`false` and with a value for `!null`/`true`. `creator` SHALL match with jokers.

#### Scenario: Caption joker
- **WHEN** the criteria string is `caption=%sunset%`
- **THEN** photos whose caption contains `sunset` are selected

#### Scenario: No caption
- **WHEN** the criteria string is `caption=null`
- **THEN** only photos without a caption are selected

### Requirement: Search index criteria
The `exifindex` and `title` criteria SHALL search whole words in Lightroom's EXIF and title search indexes; words joined by `&` SHALL all be required and words joined by `|` (quoted) SHALL be alternatives.

#### Scenario: Either word
- **WHEN** the criteria string is `exifindex="canon|nikon"`
- **THEN** both Canon and Nikon photos are selected

#### Scenario: Both words
- **WHEN** the criteria string is `exifindex=canon&nikon`
- **THEN** no photo is selected

### Requirement: GPS rectangle criterion
The `gps` criterion SHALL select geotagged photos inside a rectangle given as `<lat>;<lon>+<km>` (square of half-side km), `<lat>;<lon>/<lat>;<lon>` (two corners), `<town>+<km>`, `<town>/<town>`, or `photo:<name>+<km>` around a geotagged catalog photo. Any other form SHALL fail with `GPS coordinates malformed`.

#### Scenario: Around coordinates
- **WHEN** the criteria string is `gps=48.8566;2.3522+10`
- **THEN** photos taken within about 10 km of central Paris are selected

#### Scenario: Between two corners
- **WHEN** the criteria string is `gps=45;4/46;5`
- **THEN** photos inside that latitude/longitude rectangle are selected

#### Scenario: Around another photo
- **WHEN** the criteria string is `gps=photo:IMG_0002+5`
- **THEN** photos within 5 km of photo IMG_0002 are selected

### Requirement: Town names are geocoded online
For town forms of `gps`, the system SHALL look the town up with the geocoder named by the `GeoCoder` setting (`Nominatim` or `BanFrance`), which needs network access. A town not found, or a lookup timeout, SHALL fail with `Town coordinates not found`; an unsupported geocoder name SHALL fail with `None Geocoder`.

#### Scenario: Town found
- **WHEN** the criteria string is `gps=paris+10` and the geocoder places Paris at 48.85, 2.35
- **THEN** photos within 10 km of that point are selected

#### Scenario: Town not found
- **WHEN** the criteria string is `gps=nowhere+10` and the geocoder finds nothing
- **THEN** selection fails with `Town coordinates not found`

### Requirement: Keyword criteria
The `keyword` criterion SHALL select photos having a keyword whose name matches the value with `%` jokers, `idkeyword` photos having the keyword with that id, and `haskeywords` photos with (`1`/`True`) or without (`0`/`False`) any keyword.

#### Scenario: One keyword
- **WHEN** the criteria string is `keyword=family`
- **THEN** every photo tagged family is selected

#### Scenario: Photos without keywords
- **WHEN** the criteria string is `haskeywords=0`
- **THEN** only photos with no keyword are selected

### Requirement: Collection and import criteria
The `collection` criterion SHALL select photos in a collection whose name matches with `%` jokers, `idcollection` photos in the collection with that id, and `import` photos added by the import with that id.

#### Scenario: Two collections required
- **WHEN** the criteria string is `collection=Holidays, collection=Best`
- **THEN** only photos in both collections are selected

#### Scenario: By import
- **WHEN** the criteria string is `import=1`
- **THEN** the photos of import 1 are selected

### Requirement: Publish collection criteria
The `pubcollection` criterion SHALL select photos published in a publish collection whose name matches the value case-insensitively with jokers, or in any publish collection for `true`; `idpubcollection` SHALL select by publish collection id.

#### Scenario: Published to Flickr
- **WHEN** the criteria string is `pubcollection=Flickr`
- **THEN** the photos published in Flickr are selected

### Requirement: Stack criterion
The `stacks` criterion SHALL accept `yes`/`all`/`true` (in a stack), `no`/`none`/`false` (not in a stack), `top`/`first` (top of a stack), `no+top`/`one` (not in a stack or on top), or a stack id, and reject other values with `invalid "stacks" value`.

#### Scenario: Top of stacks
- **WHEN** the criteria string is `stacks=top`
- **THEN** only photos at the top of a stack are selected

#### Scenario: One per stack
- **WHEN** the criteria string is `stacks=no+top`
- **THEN** unstacked photos and stack tops are selected

### Requirement: Metadata status criterion
The `metastatus` criterion SHALL select photos by XMP synchronisation status: `uptodate`, `hasbeenchanged` (to be saved to disk), `changedondisk`, `conflict` or `unknown`, and reject other values with `invalid "metastatus" value`.

#### Scenario: Pending save
- **WHEN** the criteria string is `metastatus=hasbeenchanged`
- **THEN** only photos whose metadata must still be written to disk are selected

### Requirement: Photo count by date
The columns string `count_by_date(<from>[, <to>])` SHALL return the number of photos per period from `<from>` up to `<to>` (default now), the period being a year, month or day according to whether `<from>` is written `YYYY`, `YYYY-MM` or `YYYY-MM-DD`. Other forms SHALL fail with `Incorrect date`. The criteria string SHALL be ignored.

#### Scenario: By year
- **WHEN** the columns string is `count_by_date(2018)` on a catalog with 3 photos in 2018 and 3 in 2019
- **THEN** the rows are `("2018", 3)` and `("2019", 3)`

#### Scenario: By month in a range
- **WHEN** the columns string is `count_by_date(2018-1, 2019-1)`
- **THEN** the rows are `("2018-05", 2)` and `("2018-07", 1)`

#### Scenario: Invalid date
- **WHEN** the columns string is `count_by_date(year)`
- **THEN** selection fails with `Incorrect date`

### Requirement: Duplicated names
The columns string `duplicated_names()` or `duplicated_names(1)` SHALL return the full name and count of each base name shared by several master photos, videos excluded. `duplicated_names(2)` SHALL return UUID and name of each photo whose name with copy name and extension is shared, and `duplicated_names(2,novideos)` the same without videos.

#### Scenario: Virtual copies are not duplicates
- **WHEN** the only shared base name belongs to a photo and its virtual copy
- **THEN** every `duplicated_names` form returns no rows

#### Scenario: Excluding videos
- **WHEN** the SQL of `duplicated_names(2,novideos)` is requested
- **THEN** it excludes the video file format
