# selection-language Specification

## Purpose

Defines the columns string and the criteria string that photo and collection selection share: how users name the values to return and combine the conditions rows must meet.

## Requirements

### Requirement: Columns string lists the values to return
The system SHALL accept a columns string of comma-separated entries, each either a bare column name or `name=value`, and SHALL return one result column per entry in the order given. Spaces around entries SHALL be ignored and empty entries (double commas) SHALL be skipped. A bare column name SHALL mean the column's default variant (value `True`).

#### Scenario: Columns in order
- **WHEN** the columns string is `name=full,id,rating`
- **THEN** each result row holds the full path, the id and the rating, in that order

#### Scenario: Bare name uses the default variant
- **WHEN** the columns string is `name` for a photo named `IMG_0001.JPG`
- **THEN** the value returned is `IMG_0001.JPG`

### Requirement: Unknown columns are rejected
The system SHALL reject a column name it does not know with the error `invalid column key "<name>"`, and a known column with an unknown variant with `Invalid value "<value>" on column "<name>"`. No query SHALL be executed in either case.

#### Scenario: Unknown column
- **WHEN** the columns string is `unknown`
- **THEN** selection fails with `invalid column key "unknown"`

#### Scenario: Unknown variant
- **WHEN** the columns string is `name=other`
- **THEN** selection fails with an invalid value error for column `name`

### Requirement: Free column expression with var:
For a column that accepts it (photo `exif`), the system SHALL accept `name=var:<expression>` and return the named catalog field as the result column; surrounding quotes around the expression SHALL be removed.

#### Scenario: EXIF field by name
- **WHEN** the columns string is `exif=var:em.isoSpeedRating` for a photo shot at ISO 1600
- **THEN** the value returned is `1600`

### Requirement: count and countby aggregate columns
The system SHALL accept `count(<column>)`, returning the number of non-null values of that column as a column named `count_<column>`, and `countby(<column>)`, which additionally groups the results by that column.

#### Scenario: Count photos per camera
- **WHEN** the columns string is `camera,countby(camera)` with criteria `camera=%` on a catalog of 3 Canon and 2 Nikon photos
- **THEN** the rows are `("Canon EOS 5D", 3)` and `("NIKON D750", 2)`

### Requirement: Criteria string is a sequence of key=value conditions
The system SHALL accept a criteria string of conditions `key=value`, or a bare `key` meaning value `True`. Keys SHALL be case-insensitive. Spaces around keys, `=` and operators SHALL be ignored, and trailing spaces SHALL not be part of a value. An empty criteria string SHALL select every row.

#### Scenario: Case and spaces ignored
- **WHEN** the criteria string is `RATING = 5`
- **THEN** it selects the same rows as `rating=5`

#### Scenario: Empty criteria
- **WHEN** the criteria string is empty
- **THEN** every photo of the catalog is returned

### Requirement: Quoted values keep reserved characters
The system SHALL accept a value in single or double quotes and use the text between the quotes verbatim, including commas, `|`, parentheses and spaces.

#### Scenario: Quoted value with an operator character
- **WHEN** the criteria string is `exifindex="canon|nikon"`
- **THEN** the whole text `canon|nikon` is the value of `exifindex`

#### Scenario: Quoted value with a comma
- **WHEN** the criteria string is `keyword='a, b'`
- **THEN** photos with the keyword `a, b` are selected

### Requirement: Comma is AND, bar is OR, parentheses group
The system SHALL combine conditions separated by `,` with AND and conditions separated by `|` with OR, and SHALL honour parentheses for grouping, with SQL precedence (AND before OR) where no parentheses are given.

#### Scenario: OR inside a group
- **WHEN** the criteria string is `(rating=5 | rating=3), camera=%canon%`
- **THEN** only Canon photos rated 5 or 3 are selected

#### Scenario: AND inside a group
- **WHEN** the criteria string is `rating=5 | (iso=6400, flag=rejected)`
- **THEN** photos rated 5 and rejected photos at ISO 6400 are selected

### Requirement: Criteria syntax errors are rejected
The system SHALL reject a criteria string whose tokens do not follow the grammar (an operator after an operator, a missing value after `=`, an unknown token, unbalanced parentheses) with an error starting `Criteria syntax error :` followed by the cause.

#### Scenario: Double comma
- **WHEN** the criteria string is `rating=5,,rating=4`
- **THEN** selection fails with `Criteria syntax error : "AND" not allowed after "AND"`

#### Scenario: Unbalanced parenthesis
- **WHEN** the criteria string is `(rating=5`
- **THEN** selection fails with an `unbalanced parenthesis` error

### Requirement: Unknown criteria are rejected
The system SHALL reject a criterion key it does not know with the error `No existent criterion "<key>"`.

#### Scenario: Unknown criterion
- **WHEN** the criteria string is `unknown=1`
- **THEN** selection fails with `No existent criterion "unknown"`

### Requirement: Comparison operators prefix the value
For criteria that compare numbers or dates, the system SHALL read an optional operator (`=`, `==`, `!=`, `<>`, `<`, `<=`, `>`, `>=`) written before the value, so that `rating=>=3` means rating greater than or equal to 3. Where the operator is optional and omitted, equality SHALL be used.

#### Scenario: Greater or equal
- **WHEN** the criteria string is `iso=>=1600`
- **THEN** photos with ISO 1600 and above are selected

#### Scenario: Operator omitted
- **WHEN** the criteria string is `rating=5`
- **THEN** only photos rated exactly 5 are selected

### Requirement: Percent jokers in text criteria
Text criteria documented as accepting jokers SHALL match with SQL LIKE semantics: `%` matches any sequence of characters, and matching SHALL be case-insensitive for ASCII letters.

#### Scenario: Joker on a folder
- **WHEN** the criteria string is `folder=%2019%`
- **THEN** photos whose folder path contains `2019` are selected

#### Scenario: Case-insensitive joker
- **WHEN** the criteria string is `camera=%canon%` and the camera is `Canon EOS 5D`
- **THEN** the photo is selected

### Requirement: Repeated criteria are independent conditions
The system SHALL allow the same criterion key several times in one criteria string, each occurrence being its own condition.

#### Scenario: Two keywords required
- **WHEN** the criteria string is `keyword=family, keyword=beach`
- **THEN** only photos that have both keywords are selected

### Requirement: Multi-valued criteria return each row once
Criteria on data that holds several entries per photo (keywords, collections, imports) SHALL select each matching photo once, however many of its entries match.

#### Scenario: OR over keywords
- **WHEN** the criteria string is `keyword=beach|keyword=family` and a photo has both keywords
- **THEN** that photo appears once in the results

#### Scenario: Joker over collections
- **WHEN** the criteria string is `collection=%` and a photo is in two collections
- **THEN** that photo appears once in the results

### Requirement: sort criterion orders results
The pseudo-criterion `sort=<column>` SHALL order results by that result column name or one-based column index, descending; `sort=-<column>` SHALL order ascending.

#### Scenario: Default descending
- **WHEN** the criteria string is `rating=>=1, sort=rating` on photos rated 5, 4, 3 and 1
- **THEN** the photos come in rating order 5, 4, 3, 1

#### Scenario: Minus sign for ascending
- **WHEN** the criteria string is `rating=>=1, sort=-rating`
- **THEN** the photos come in rating order 1, 3, 4, 5

### Requirement: distinct removes duplicate rows
The pseudo-criterion `distinct`, or the distinct option of the programmatic interface, SHALL remove identical result rows.

#### Scenario: Distinct cameras
- **WHEN** the columns string is `camera` and the criteria string is `camera=%, distinct` on 5 photos from 2 cameras
- **THEN** 2 rows are returned

### Requirement: count criterion filters aggregated counts
The pseudo-criterion `count=<column><operator><number>` SHALL keep only the groups produced by a `countby(<column>)` column whose count satisfies the comparison.

#### Scenario: Cameras with more than 100 photos
- **WHEN** the columns string is `camera,countby(camera)` and the criteria string is `camera=%,count=camera>100`
- **THEN** only cameras with more than 100 photos are returned

### Requirement: groupby criterion
The system SHALL accept the pseudo-criterion `groupby=<column>`. In current behaviour it is placed among the conditions, so the resulting query is invalid and fails when executed.

#### Scenario: groupby produces an invalid query
- **WHEN** the criteria string is `groupby=camera`
- **THEN** the generated SQL contains `WHERE GROUP BY camera` and executing it fails

### Requirement: SQL can be returned instead of executed
The system SHALL be able to return the SQL text it generated instead of executing it, or print it and return nothing, so users can inspect or reuse the query.

#### Scenario: SQL only
- **WHEN** a selection with columns `id` and criteria `rating=5` is requested as SQL only
- **THEN** the result is a string starting with `SELECT` that contains `i.rating = 5`

#### Scenario: Print SQL
- **WHEN** the same selection is requested with print
- **THEN** a line starting `SQL =` is printed and no rows are returned
