# result-display Specification

## Purpose

Formats selected catalog rows as a fixed-width text table for `lrselect` and `lrsmart`: a results line, a column header, one line per row with per-column value formatting, and an optional file size total.

## Requirements

### Requirement: Empty result
When no row is selected, the display SHALL print ` * None data result` if the header is enabled, and nothing otherwise.

#### Scenario: No rows
- **WHEN** a selection returns no row and results are displayed with the header
- **THEN** the only results output is ` * None data result`

### Requirement: Results line
With the header enabled, the display SHALL first print ` * Results (<n> entries) :` when every row is displayed, or ` * Results (first <m> entries of <n>) :` when the maximum number of lines `<m>` is lower than the number of rows `<n>`. A negative maximum SHALL mean all rows.

#### Scenario: All rows
- **WHEN** three rows are displayed with the maximum `-1`
- **THEN** the results line is ` * Results (3 entries) :`

#### Scenario: Limited rows
- **WHEN** six rows are displayed with the maximum 2
- **THEN** the results line is ` * Results (first 2 entries of 6) :` and exactly two data lines follow the header

### Requirement: Column header
With the header enabled, the display SHALL print the column names, each padded or truncated to its column width and joined by the separator, then an underline of `=` as long as the sum of the widths plus the separators. With the header disabled, neither the results line nor the column header SHALL be printed.

#### Scenario: Names truncated to width
- **WHEN** rows are displayed for columns `name,aperture,flash` with separator `|` and indent 0
- **THEN** the header line is `name                |apert|fla`
- **AND** the next line is 30 `=` characters

### Requirement: Indentation and separator
Every header and data line SHALL be prefixed by the indentation (default 4 spaces) and its values joined by the separator (default ` | `).

#### Scenario: Default layout
- **WHEN** the row `("a", 6.0)` is displayed for columns `name,aperture` with raw print and no header
- **THEN** the line is `    a                    |   6.0`

### Requirement: Default column widths
Each known column SHALL have a default printf width: for example `name` `%-20s`, `name=full` `%-80s`, `name=basext` `%-25s`, `id` `%8s`, `uuid` `%38s`, `rating` `%1s`, `datecapt`/`datemod` `%19s`, `keywords` `%-30s`, `lens` `%-25s`, `iso` `%5s`, `aperture` `%5s`, `speed` `%6s`, `flash` `%3s`, `filesize` `%8s`. Any other column SHALL use `%6s`; a negative width left-aligns.

#### Scenario: Unknown column width
- **WHEN** the columns are `name,aperture,unknown` with no widths given
- **THEN** `unknown` is printed right-aligned in 6 characters

### Requirement: Width override
A comma separated widths list (for example `30,-50,10`) SHALL override the widths of the first columns in order, each value `<w>` becoming the printf width `%<w>s`. Columns beyond the list SHALL keep their default width.

#### Scenario: Override of the first column
- **WHEN** the columns are `name,aperture,unknown` and the widths `-10`
- **THEN** `name` is left-aligned in 10 characters and `aperture` keeps `%5s`

### Requirement: Extra row values
When a row holds more values than the displayed column names, the extra values SHALL be displayed as columns named `column<i>` (zero-based index) with width `%6s`.

#### Scenario: Unnamed value
- **WHEN** the row `("a", 6.0, 7)` is displayed for columns `name,aperture`
- **THEN** the header line is `    name                 | apert | column` (`column2` truncated to 6 characters)
- **AND** the data line is `    a                    |  F8.0 |      7`

### Requirement: Value formatting
Unless raw print is enabled, an empty value SHALL be printed as an empty field, and values SHALL be formatted per column: `aperture` as `F<f>` with one decimal (stored 6.0 → `F8.0`), `speed` as `1/<n>` above one second else seconds (9.965784 → `1/1000`, -1.0 → `2`), `iso` without decimals, `rating`/`modcount`/`stackpos` as integers, `flash`/`monochrome` as `no`/`yes`/`?`, `flag` as `unflagged`/`flagged`/`rejected`.

#### Scenario: Formatted row
- **WHEN** the rows `("IMG_1.JPG", 6.0, None)` and `("IMG_2.JPG", 4.970854, 1)` are displayed for `name,aperture,flash` with separator `|` and indent 0
- **THEN** the data lines are `IMG_1.JPG           | F8.0|   ` and `IMG_2.JPG           | F5.6|yes`

### Requirement: Date and duration formatting
Unless raw print is enabled, `datecapt` SHALL be cut to its first 19 characters (`2018-05-10T10:00:00.123` → `2018-05-10T10:00:00`); `datemod`, `datehist` and `pubtime`, stored as seconds since 2001-01-01 UTC, SHALL be printed in the local time zone as `YYYY-MM-DD HH:MM:SS`; `duration`, stored as a hexadecimal fraction, SHALL be printed as `[H:]MM:SS.f`.

#### Scenario: Lightroom timestamp zero
- **WHEN** a `datemod` value of 0 is displayed
- **THEN** it is printed as 2001-01-01 00:00:00 UTC converted to local time, in the form `YYYY-MM-DD HH:MM:SS`

#### Scenario: Video duration
- **WHEN** a `duration` value `000000000000012c/000000000000000a` is displayed
- **THEN** it is printed as `00:30.0`

### Requirement: Raw print
With raw print, values SHALL be printed as stored, without the per-column formatting and with an empty value printed as `None`.

#### Scenario: Raw aperture and speed
- **WHEN** photo 1 of the test catalog is displayed with columns `aperture,speed,datecapt` and raw print
- **THEN** the data line is `      6.0 | 9.965784 | 2018-05-10T10:00:00`

### Requirement: File size column and total
When file sizes are requested, the display SHALL read the size on disk of each row's full file name, insert it as a byte count at the position of the `filesize` column (0 when the file cannot be read), and after the rows print ` * Total filesize : <size> (<bytes> bytes)` over all rows, including rows beyond the maximum number of lines.

#### Scenario: Unreadable files
- **WHEN** file sizes are requested and no selected file exists on disk
- **THEN** each `filesize` value is `0` and the total line is ` * Total filesize : 0.00 B (0 bytes)`

### Requirement: Human readable size unit
The total size SHALL be printed with two decimals in the largest unit it exceeds, with factor 1000: `B`, `KB`, `MB`, `GB`, `TB` (999 → `999.00 B`, 1500 → `1.50 KB`, 2500000 → `2.50 MB`, 3000000000 → `3.00 GB`).

#### Scenario: Kilobytes
- **WHEN** the total is 1500 bytes
- **THEN** the total line is ` * Total filesize : 1.50 KB (1500 bytes)`
