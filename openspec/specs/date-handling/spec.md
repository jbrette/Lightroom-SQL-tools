# date-handling Specification

## Purpose

Defines how dates typed by users are parsed and compared with the two date representations a Lightroom catalog stores: naive local capture times and modification timestamps counted from 2001-01-01 UTC.

## Requirements

### Requirement: Day-first parsing order
User date strings SHALL be parsed with day before month when the `DayFirst` setting is enabled (the default), and month before day when it is disabled. A leading four-digit year SHALL be read as the year in both modes.

#### Scenario: Day-first enabled
- **WHEN** `DayFirst` is enabled and the user enters `2-1-2001 00:00:00+00:00`
- **THEN** the date is 2 January 2001

#### Scenario: Day-first disabled with year first
- **WHEN** `DayFirst` is disabled and the user enters `2001-01-02 00:00:00+00:00`
- **THEN** the date is 2 January 2001

### Requirement: Capture date criterion requires an operator
The capture date criterion value SHALL start with a comparison operator (`=`, `<`, `<=`, `>`, `>=`, `!=`) before the first digit. A value without an operator SHALL fail with the error `None operator for date`.

#### Scenario: Missing operator
- **WHEN** the criteria string is `datecapt=2018`
- **THEN** the selection fails with `None operator for date`

#### Scenario: Equality operator
- **WHEN** the criteria string is `datecapt==2018`
- **THEN** the value is read as operator `=` and date `2018`

### Requirement: Capture date precision follows the number of date parts
A capture date with one, two or three numeric parts SHALL be compared at year, month or day precision respectively, using the start of that period on both sides. A value with more numeric parts SHALL be compared with the capture time to the second. Missing parts SHALL default to 1 January 1900, 00:00:00.

#### Scenario: Year precision
- **WHEN** the criterion is `datecapt==2018`
- **THEN** every photo captured during 2018 matches

#### Scenario: Month precision
- **WHEN** the criterion is `datecapt==7-2018`
- **THEN** only photos captured in July 2018 match

#### Scenario: Day precision with range operator
- **WHEN** the criterion is `datecapt=<=31-5-2018`
- **THEN** photos captured on or before 31 May 2018 match

### Requirement: Capture times are naive local times
Capture times SHALL be treated as local wall-clock times without a time zone, as Lightroom stores them; user capture dates SHALL be compared with them without any time zone conversion.

#### Scenario: No conversion
- **WHEN** a photo was captured at `2018-05-10T10:00:00` and the criterion is `datecapt=>=10-5-2018`
- **THEN** the photo matches regardless of the machine's time zone

### Requirement: Lightroom timestamps
Modification dates SHALL be expressed as seconds (fractional allowed) since 2001-01-01 00:00:00 UTC. Dates before that epoch SHALL convert to 0.

#### Scenario: One day after the epoch
- **WHEN** the date 2001-01-02 00:00:00 UTC is converted
- **THEN** the timestamp is 86400

#### Scenario: Date before the epoch
- **WHEN** the date 1990-01-01 UTC is converted
- **THEN** the timestamp is 0

### Requirement: Modification date criterion uses local time
The modification date criterion value SHALL be an optional operator followed by a date; a date without an explicit offset SHALL be interpreted in the machine's local time zone before conversion to a Lightroom timestamp. A value that cannot be converted SHALL fail with `invalid date value on "datemod"`.

#### Scenario: Modified after a date
- **WHEN** the criterion is `datemod=>=1-1-2020`
- **THEN** photos whose modification timestamp is at or after local midnight on 1 January 2020 match

### Requirement: Publication time criterion uses UTC
The publication time criterion value SHALL be an operator followed by a date interpreted in UTC and converted to a Lightroom timestamp. A date that converts to 0 or cannot be converted SHALL fail with `invalid date value on "datemod"`.

#### Scenario: Date at or before the epoch
- **WHEN** the publication time criterion is given a date on or before 1 January 2001
- **THEN** the selection fails with `invalid date value on "datemod"`

### Requirement: Unsupported date values
Converting a value that is neither a date string nor a date object SHALL return no timestamp rather than fail.

#### Scenario: Integer value
- **WHEN** the integer `12` is converted to a Lightroom timestamp
- **THEN** the result is empty (no timestamp)

### Requirement: Lightroom date string parsing
Lightroom date strings SHALL be parsed in the forms `YYYY-MM-DDTHH:MM`, `YYYY-MM-DDTHH:MM:SS`, either with fractional seconds, and either followed by `Z` or a `+HH:MM` offset. Strings without an offset SHALL give naive dates; strings with one SHALL keep it.

#### Scenario: Seconds without offset
- **WHEN** `2019-08-13T19:47:33` is parsed
- **THEN** the result is a naive 2019-08-13 19:47:33

#### Scenario: Minutes only
- **WHEN** `2019-08-13T19:47` is parsed
- **THEN** the result is a naive 2019-08-13 19:47:00

#### Scenario: Milliseconds
- **WHEN** `2019-08-13T19:47:33.269` is parsed
- **THEN** the result is a naive 2019-08-13 19:47:33.269

#### Scenario: UTC designator
- **WHEN** `2019-08-13T19:47:33Z` is parsed
- **THEN** the result is 2019-08-13 19:47:33 UTC

#### Scenario: Offset and milliseconds
- **WHEN** `2019-08-13T19:47:33.022+02:00` is parsed
- **THEN** the result keeps the +02:00 offset and 22 milliseconds

### Requirement: Count-by-date date arguments
Dates given to the count-by-date pseudo-column SHALL be read as year, year-month or year-month-day (in that order, regardless of `DayFirst`), and SHALL select per-year, per-month or per-day counting from the number of parts of the first date. Any other number of parts SHALL fail with `Incorrect date`.

#### Scenario: Year only
- **WHEN** the columns are `count_by_date(2018)`
- **THEN** photos are counted per year from 1 January 2018 until now

#### Scenario: Day range
- **WHEN** the columns are `count_by_date(2019-1-5, 2019-1-6)`
- **THEN** photos are counted per day from 5 January 2019 up to, but excluding, 6 January 2019

#### Scenario: Word instead of date
- **WHEN** the columns are `count_by_date(year)`
- **THEN** the selection fails with `Incorrect date`
