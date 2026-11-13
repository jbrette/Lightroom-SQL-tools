# smart-collections Specification

## Purpose

Run a Lightroom Classic smart collection outside Lightroom: load its rule definition from the catalog or from an exported `.lrsmcol` file, translate each Lightroom criterion into a photo selection, and return the photos it matches.

## Requirements

### Requirement: Load a definition by name from the catalog
The system SHALL find a smart collection in the catalog by name, matching case-insensitively, with `%` as a wildcard, and use the first match. A name made only of digits SHALL be looked up as the collection's numeric id instead. Only collections of the smart type SHALL be considered.

#### Scenario: Exact name
- **WHEN** the smart collection "Five Stars" is requested
- **THEN** its definition is loaded: one criterion `rating >= 5`, combined with `intersect`

#### Scenario: Wildcard name
- **WHEN** the name `five%` is requested
- **THEN** the "Five Stars" definition is loaded

### Requirement: Unknown smart collection
The system SHALL fail with the error `smart collection "<name>" not found` when no smart collection matches the requested name or id, or when its stored definition does not decode to a table.

#### Scenario: Name not in the catalog
- **WHEN** the smart collection "Nope" is requested
- **THEN** the selection fails with `smart collection "Nope" not found`

### Requirement: Load a definition from an exported file
The system SHALL read an exported smart collection file as UTF-8, decode the Lua table that starts at the first `{`, and use its `value` table as the definition. The `title` entry is optional. A file whose table has no `value` entry, or whose `value` is not a table, SHALL be rejected.

#### Scenario: Exported video collection
- **WHEN** an exported file whose `value` holds one criterion `fileFormat == "VIDEO"` combined with `intersect` is run
- **THEN** only the video photo is selected

#### Scenario: File without a value table
- **WHEN** an exported file decodes to a table without a `value` entry
- **THEN** the file is rejected and nothing is selected

### Requirement: Lua definition decoding
The system SHALL decode these Lua values: tables, double-quoted strings, integers, decimals, negative numbers, `true`/`false` in any letter case, and bare words (decoded as strings). Text from `---` to the end of a line SHALL be ignored. A table with only positional entries SHALL decode to a list; a table with named entries SHALL keep its positional entries under keys 0, 1, 2…

#### Scenario: Stored catalog definition
- **WHEN** the definition `{ { criteria = "rating", operation = ">=", value = 5, }, combine = "intersect", }` is decoded
- **THEN** the result is criterion 0 with `criteria` "rating", `operation` ">=", the integer `value` 5, and `combine` "intersect"

#### Scenario: Positional table
- **WHEN** `{1,2,{x="y"}}` is decoded
- **THEN** the result is the list `1, 2, {x: "y"}`

### Requirement: Undecodable definitions
The system SHALL produce no definition for empty text, an empty table `{}`, an unterminated string or an unterminated table. Escape sequences inside strings and single-quoted strings SHALL NOT be supported.

#### Scenario: Unterminated string
- **WHEN** `{ x = "unterminated` is decoded
- **THEN** no definition is produced

#### Scenario: Escaped quote
- **WHEN** `{ x = "a\"b" }` is decoded
- **THEN** no definition is produced

### Requirement: Criteria order
The system SHALL read the criteria of a definition from positional entries 0, 1, 2… and stop at the first missing position. A definition with no criterion at position 0 SHALL produce an empty query.

#### Scenario: No criteria
- **WHEN** a definition holds only `combine = "intersect"`
- **THEN** the generated query is empty

### Requirement: Combine modes
The system SHALL combine the results of several criteria with the definition's `combine` entry: `intersect` keeps photos matching every criterion (Lightroom "match all"), `union` keeps photos matching at least one (Lightroom "match any"). The `combine` entry SHALL only be read when there are at least two criteria.

#### Scenario: Intersect
- **WHEN** `camera any "canon"` and `rating >= 4` are combined with `intersect`
- **THEN** only Canon photos rated 4 or more are selected

#### Scenario: Union
- **WHEN** `rating == 5` and `fileFormat == "VIDEO"` are combined with `union`
- **THEN** the 5-star photo and the video are selected

#### Scenario: Single criterion
- **WHEN** a definition has one criterion and `combine = "xor"`
- **THEN** the criterion runs and the unknown combine mode is ignored

### Requirement: Unsupported combine modes
The system SHALL fail with `"combine" operation unsupported: <combine>` for any other combine mode when there are at least two criteria. This includes Lightroom's "match none" (`exclude`).

#### Scenario: Match none
- **WHEN** two criteria are combined with `exclude`
- **THEN** the selection fails with `"combine" operation unsupported: exclude`

### Requirement: Malformed criterion entries
The system SHALL fail with `criteria <n> is not a table: <entry>` when the entry at position n is not a table. Nested rule groups SHALL NOT be supported: an entry with no `criteria` key fails without a smart-collection error message.

#### Scenario: Entry is a string
- **WHEN** position 0 of a definition holds a string
- **THEN** the selection fails with `criteria 0 is not a table: …`

### Requirement: Unsupported criteria
The system SHALL fail with `criteria unsupported: <criteria>` for a criterion name it does not implement. The criteria names are case-sensitive.

#### Scenario: Unknown criterion
- **WHEN** a definition uses criterion `unknownCriteria`
- **THEN** the selection fails with `criteria unsupported: unknownCriteria`

#### Scenario: Copy name spelled with a capital N
- **WHEN** a definition uses criterion `copyName`
- **THEN** the selection fails with `criteria unsupported: copyName`; only the lower-case `copyname` is implemented

### Requirement: Unsupported operations
The system SHALL fail with `operation unsupported: <operation> on criteria <criteria>` when a criterion that validates its operations receives one it does not implement. For `touchTime`, the operation and criterion SHALL be quoted in the message.

#### Scenario: Unknown rating operation
- **WHEN** a definition uses `rating between 1`
- **THEN** the selection fails with `operation unsupported: between on criteria rating`

#### Scenario: Unknown edit-date operation
- **WHEN** a definition uses `touchTime bogus`
- **THEN** the selection fails with `operation unsupported: "bogus" on criteria "touchTime"`

### Requirement: Result columns, order and SQL-only mode
The system SHALL return the requested photo columns for the selected photos. With a sort column, it SHALL order the rows by that column, descending when the name starts with `-`. When only the query is requested, it SHALL return the generated SQL without running it.

#### Scenario: Descending sort
- **WHEN** "Canon Family" is run with columns `id` and sort column `-id`
- **THEN** the rows are photo 2 then photo 1

#### Scenario: SQL only
- **WHEN** "Canon Family" is run in SQL-only mode
- **THEN** a `SELECT` statement containing `INTERSECT` is returned and nothing is executed

### Requirement: Literal criterion values
The system SHALL insert criterion values into the query as written. A value containing a double quote SHALL make the selection fail with a database error. The catalog SHALL never be modified.

#### Scenario: Quote in a value
- **WHEN** a definition uses `camera any 'ca"n'`
- **THEN** the selection fails with a database syntax error

### Requirement: Rating criterion
The system SHALL support `rating` with `==`, `!=`, `>`, `<`, `>=`, `<=` against the star rating. Operations starting with `<` SHALL also select unrated photos. Other operations SHALL fail as unsupported.

#### Scenario: At least five stars
- **WHEN** `rating >= 5` is run
- **THEN** only the 5-star photo is selected

#### Scenario: Below three stars includes unrated
- **WHEN** `rating < 3` is run
- **THEN** the 1-star photo and the unrated photos are selected

#### Scenario: Equal to zero
- **WHEN** `rating == 0` is run with the integer value 0, as decoded from a definition
- **THEN** no photo is selected, unrated photos included

#### Scenario: Not equal excludes unrated
- **WHEN** `rating != 5` is run
- **THEN** rated photos other than 5 stars are selected, and unrated photos are not

### Requirement: Capture date criterion
The system SHALL support `captureTime` on the date part of the capture time: `in` (from `value` to `value2`, both included), `==`, `!=`, `>`, `<` against a `YYYY-MM-DD` value, and `inLast` (within the last `value` units, from `_units`). Other operations, including `>=` and `<=`, SHALL fail as unsupported.

#### Scenario: Date range
- **WHEN** `captureTime in "2018-01-01" "2018-06-30"` is run
- **THEN** photos captured in the first half of 2018 are selected

#### Scenario: After a date
- **WHEN** `captureTime > "2018-12-31"` is run
- **THEN** photos captured from 2019 on are selected

#### Scenario: In the last weeks
- **WHEN** `captureTime inLast 30` with `_units = "weeks"` is run
- **THEN** no photo is selected, because the unit `weeks` is not understood

### Requirement: Edit date criterion
The system SHALL support `touchTime` on the date of the last edit: `in`, `==`, `!=`, `>`, `inLast`, `<` (never-edited photos excluded), `today`, `yesterday`, `thisWeek` (the last 7 days), `thisMonth` (since the same day last month) and `thisYear` (the current calendar year).

#### Scenario: Edited in August 2019
- **WHEN** `touchTime in "2019-08-01" "2019-08-31"` is run
- **THEN** only the photo edited on 2019-08-02 is selected

#### Scenario: Edited before a date
- **WHEN** `touchTime < "2020-01-01"` is run
- **THEN** the photo edited in 2019 is selected and never-edited photos are not

### Requirement: Numeric EXIF criteria
The system SHALL support `isoSpeedRating`, `focalLength` and `aperture` with `in` (from `value` to `value2`, both included) or any comparison operator, which is passed to the database as written. `aperture` SHALL use Lightroom's stored value, 2·log2(f-number), so f/8 is 6. An operator the database does not understand SHALL fail with a database error.

#### Scenario: High ISO
- **WHEN** `isoSpeedRating >= 1600` is run
- **THEN** the photos shot at ISO 1600 and 6400 are selected

#### Scenario: Focal range
- **WHEN** `focalLength in 40 100` is run
- **THEN** the photos shot at 50 mm are selected

#### Scenario: Aperture f/8
- **WHEN** `aperture == 6` is run
- **THEN** the photos shot at f/8 are selected

### Requirement: Shutter speed criterion
The system SHALL support `shutterSpeed` like the numeric EXIF criteria, on Lightroom's stored value log2(1/exposure time), with `>` and `<` swapped in the operation so the comparison follows exposure time.

#### Scenario: Slower than about 1/500 s
- **WHEN** `shutterSpeed >= 9` is run
- **THEN** the photo at 1/250 s is selected and the photo at 1/1000 s is not

### Requirement: Boolean EXIF criteria
The system SHALL support `hasGPSData` and `flashFired`, selecting photos whose flag equals the criterion's `value` (true or false), whatever the operation.

#### Scenario: Has GPS
- **WHEN** `hasGPSData == true` is run
- **THEN** the photos with GPS coordinates are selected

#### Scenario: Flash fired
- **WHEN** `flashFired == true` is run
- **THEN** only the photo taken with flash is selected

### Requirement: Text criteria operations
The system SHALL match text criteria case-insensitively with `any` (contains at least one word), `all` (contains every word), `noneOf` (contains none of the words), `==`/`!=` (whole value), and `notEmpty`. Values SHALL be split into words. A word prefixed with `+` SHALL always be required; a word prefixed with `!` SHALL be negated. Other operations SHALL fail as unsupported.

#### Scenario: Any word
- **WHEN** `camera any "canon"` is run
- **THEN** the Canon photos are selected

#### Scenario: Forced word
- **WHEN** `camera any "canon +eos"` is run
- **THEN** only photos whose camera contains both "canon" and "eos" are selected

### Requirement: Word-position text operations
The system SHALL support `beginsWith`, `endsWith` and `words` on text criteria by matching word boundaries of Lightroom's search index. On criteria that compare plain text (`filename`, `folder`, `copyname`, `creator`), these operations SHALL select nothing.

#### Scenario: Camera word prefix
- **WHEN** `camera beginsWith "can"` is run
- **THEN** the Canon photos are selected

#### Scenario: Folder prefix
- **WHEN** `folder beginsWith "/photos"` is run
- **THEN** no photo is selected

### Requirement: Camera and lens criteria
The system SHALL support `camera` and `lens` with the text operations. `==` and `!=` SHALL compare the full model or lens name; `!=` SHALL also select photos with no camera or lens recorded.

#### Scenario: Exact camera
- **WHEN** `camera == "NIKON D750"` is run
- **THEN** the Nikon photos are selected

#### Scenario: Not this camera
- **WHEN** `camera != "NIKON D750"` is run
- **THEN** the Canon photos and the video without a camera are selected

#### Scenario: Lens
- **WHEN** `lens any "70-200mm"` is run
- **THEN** the photo shot with the 70-200 mm lens is selected

### Requirement: File name criterion
The system SHALL support `filename` with the text operations, matched against the result column `name`. The selection SHALL fail with a database error when `name` is not among the requested columns.

#### Scenario: Name column requested
- **WHEN** `filename any "img"` is run with columns `id,name`
- **THEN** the photos whose file name contains "img" are selected

#### Scenario: Name column missing
- **WHEN** `filename any "img"` is run with columns `id`
- **THEN** the selection fails with `no such column: name`

### Requirement: Folder, copy name, creator, EXIF and IPTC criteria
The system SHALL support these text criteria: `folder` (the full folder path), `copyname` (the virtual copy name), `creator` (the IPTC creator), `exif` (Lightroom's EXIF search index) and `iptc` (Lightroom's IPTC search index).

#### Scenario: Folder
- **WHEN** `folder any "2019"` is run
- **THEN** the photos in the 2019 folder are selected

#### Scenario: Copy name
- **WHEN** `copyname any "copy"` is run
- **THEN** only the virtual copy is selected

#### Scenario: Creator
- **WHEN** `creator any "alice"` is run
- **THEN** the photo whose creator is Alice is selected

### Requirement: File type criterion
The system SHALL support `fileFormat`, comparing Lightroom's file format (for example `VIDEO`, `RAW`, `JPG`) with the operation as written.

#### Scenario: Videos
- **WHEN** `fileFormat == "VIDEO"` is run
- **THEN** only the video is selected

#### Scenario: Not videos
- **WHEN** `fileFormat != "VIDEO"` is run
- **THEN** every photo except the video is selected

### Requirement: Aspect ratio criterion
The system SHALL support `aspectRatio` with value `square`, `portrait` or `landscape` and operation `==` or `!=`. Another value SHALL fail with `value unsupported: <value>`, which is checked before the operation; another operation SHALL fail as unsupported.

#### Scenario: Portrait
- **WHEN** `aspectRatio == "portrait"` is run
- **THEN** only the portrait photo is selected

#### Scenario: Unknown shape
- **WHEN** `aspectRatio == "round"` is run
- **THEN** the selection fails with `value unsupported: round`

### Requirement: Cropped size criteria
The system SHALL support `widthCropped` and `heightCropped` on the displayed width or height after crop and orientation, with `in` (both bounds included) or a comparison operator. Videos SHALL be excluded. Without `dims` among the requested columns, the selection SHALL fail with `This smart collection needs "dims" columns`.

#### Scenario: Wide photos
- **WHEN** `widthCropped >= 5000` is run with columns `id,dims`
- **THEN** the uncropped landscape photos at least 5000 px wide are selected

#### Scenario: Missing dims column
- **WHEN** `widthCropped >= 5000` is run with columns `id`
- **THEN** the selection fails with a message naming the "dims" columns

### Requirement: Keyword matching criteria
The system SHALL support `keywords` with `any`, `all`, `words`, `beginsWith` and `endsWith`. A word SHALL match keywords whose lower-case name contains it (`any`, `all`), contains it as a whole word (`words`), or has a word starting or ending with it. A matching keyword SHALL also match every keyword below it in the hierarchy.

#### Scenario: Any keyword
- **WHEN** `keywords any "family"` is run
- **THEN** the photos tagged "family" are selected

#### Scenario: Parent keyword
- **WHEN** `keywords any "places"` is run
- **THEN** the photo tagged with the child keyword "Places|beach" is selected

#### Scenario: All keywords
- **WHEN** `keywords all "family beach"` is run
- **THEN** only the photo tagged with both is selected

### Requirement: Keyword exclusion and presence criteria
The system SHALL support `keywords noneOf` (photos with none of the matching keywords or their children), `empty` (photos with no keyword) and `notEmpty` (photos with at least one keyword).

#### Scenario: None of
- **WHEN** `keywords noneOf "family"` is run
- **THEN** every photo not tagged "family" is selected

#### Scenario: No keywords
- **WHEN** `keywords empty` is run
- **THEN** the untagged photos are selected

### Requirement: Collection criterion
The system SHALL support `collection` with `all` (for each word, belongs to a collection whose name contains it), `beginsWith`, `endsWith`, and `noneOf` (belongs to no collection whose name contains any of the words). Other operations, including `any`, SHALL fail as unsupported.

#### Scenario: In a collection
- **WHEN** `collection all "Holidays"` is run
- **THEN** the photos in the "Holidays" collection are selected

#### Scenario: Name prefix
- **WHEN** `collection beginsWith "Be"` is run
- **THEN** the photo in the "Best" collection is selected

#### Scenario: Not in a collection
- **WHEN** `collection noneOf "Best"` is run
- **THEN** every photo outside the "Best" collection is selected

### Requirement: Color label criteria
The system SHALL support `labelText` and `labelColor` when the value is text, comparing the photo's color label with the operation as written; the value `none` SHALL mean no label. A numeric label value SHALL fail with `labelColor unsupported : prefer using criteria labelText`.

#### Scenario: Red label
- **WHEN** `labelText == "Red"` is run
- **THEN** only the red-labelled photo is selected

#### Scenario: No label
- **WHEN** `labelText == "none"` is run
- **THEN** every photo without a label is selected

#### Scenario: Numeric color code
- **WHEN** `labelColor == 1` is run
- **THEN** the selection fails with `labelColor unsupported : prefer using criteria labelText`

### Requirement: Color mode and treatment criteria
The system SHALL support `colorMode`, comparing Lightroom's numeric color mode with the operation as written, and `treatment` with the value `grayscale` only, where `==` selects black-and-white photos and `!=` selects color ones. Any other treatment value SHALL fail as an unsupported operation.

#### Scenario: Black and white
- **WHEN** `treatment == "grayscale"` is run
- **THEN** only the monochrome photo is selected

#### Scenario: Other treatment value
- **WHEN** `treatment == "color"` is run
- **THEN** the selection fails with `operation unsupported: == on criteria treatment`

### Requirement: Develop adjustments criterion
The system SHALL support `hasAdjustments`: operation `isFalse` selects photos without develop adjustments, and any other operation selects photos with them.

#### Scenario: Not adjusted
- **WHEN** `hasAdjustments isFalse` is run
- **THEN** the photos without develop adjustments are selected

### Requirement: Metadata status criterion
The system SHALL support `metadataStatus` with value `upToDate`, `hasBeenChanged`, `changedOnDisk`, `conflict` or `unknown`, comparing the catalog and the XMP sidecar state; the operation is ignored. Another value SHALL fail with `value unsupported: <operation> on criteria <value>`.

#### Scenario: Up to date
- **WHEN** `metadataStatus is "upToDate"` is run
- **THEN** the photos whose metadata matches their files are selected

#### Scenario: Unknown status
- **WHEN** `metadataStatus is "bogus"` is run
- **THEN** the selection fails with `value unsupported: is on criteria bogus`

### Requirement: Any searchable text criterion
The system SHALL support `all` (Lightroom's "Any Searchable Text") with `any` or `all`. Each word SHALL be searched in the metadata search index, the file name, the folder and root paths, the creator, the caption, the copyright, the color profile name, the collection names and the keywords (with their children). Other operations SHALL fail as unsupported.

#### Scenario: Caption word
- **WHEN** `all any "beach"` is run
- **THEN** the photo whose caption and keywords mention the beach is selected

#### Scenario: Every word
- **WHEN** `all all "alice 2018"` is run
- **THEN** the photo by Alice with "2018" in its searchable text is selected

### Requirement: Searchable metadata criterion
The system SHALL support `metadata` (Lightroom's "Any Searchable Metadata") with `any` or `all`, searching each word in the metadata search index and the keywords (with their children). Other operations SHALL fail as unsupported.

#### Scenario: Keyword word
- **WHEN** `metadata any "family"` is run
- **THEN** the photos tagged "family" are selected
