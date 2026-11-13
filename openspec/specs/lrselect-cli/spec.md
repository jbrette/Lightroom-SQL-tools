# lrselect-cli Specification

## Purpose

The `lrselect` command selects photos or collections from a Lightroom Classic catalog with a columns string and a criteria string, and prints the SQL, the count or the rows. It is available both as the `lrselect.py` script and as the installed `lrselect` command, with identical behaviour.

## Requirements

### Requirement: Two invocation forms with identical behaviour
The system SHALL provide the command both as the `lrselect.py` script run with Python and as the installed `lrselect` console command, and both SHALL accept the same arguments and produce the same output.

#### Scenario: Script and installed command agree
- **WHEN** `lrselect.py -b test.lrcat "name,rating" "rating=>=3, sort=rating" -r -c` and `lrselect -b test.lrcat "name,rating" "rating=>=3, sort=rating" -r -c` are run on the same catalog
- **THEN** both exit with status 0 and print the same output

### Requirement: Positional columns and criteria
The command SHALL take two optional positional arguments: the columns to display and the criteria of selection, whose language is defined by the `selection-language` capability. When the columns argument is missing or empty, the columns SHALL default to `name,datecapt`. When the criteria argument is missing or empty, every row of the table SHALL be selected.

#### Scenario: Default columns
- **WHEN** `lrselect -b test.lrcat "" "" -c -s` is run
- **THEN** the printed SQL selects the `name` and `datecapt` columns
- **AND** ` * Count results: 6` is printed for the six-photo test catalog

### Requirement: Catalog or INI file option
The `-b`/`--lrcat` option SHALL name the catalog to open. A value ending in `lrcat` SHALL be opened as a catalog; any other value SHALL be read as an INI file in `lrtools.ini` form, whose catalog is then opened. Without `-b`, the catalog configured as described by the `catalog-access` capability SHALL be used; the help shows it as the default.

#### Scenario: Catalog named by an INI file
- **WHEN** `my.ini` contains `[Main]` with `LRCatalog = <path of test.lrcat>` and `lrselect -b my.ini id flag=rejected -r -N` is run
- **THEN** the command exits with status 0 and prints only `3`

#### Scenario: Unreadable INI file
- **WHEN** `lrselect -b x id "" -r` is run and `x` is not a readable INI file
- **THEN** ` ==> FAILED: Failed to read config file "x"` is printed on stderr

### Requirement: Output selection options
The command SHALL print the generated SQL with `-s`/`--sql`, the number of selected rows with `-c`/`--count` and the rows with `-r`/`--results`. When none of the three is given, it SHALL print `WARNING: option "--count" forced` and behave as if `-c` was given. The SQL line SHALL be printed first, as ` * SQL request =  <sql>`, then the count line, then the rows.

#### Scenario: SQL only
- **WHEN** `lrselect -b test.lrcat id rating=5 --sql` is run
- **THEN** the output contains ` * SQL request = ` followed by SQL containing `i.rating = 5`
- **AND** no count and no rows are printed

#### Scenario: Count forced
- **WHEN** `lrselect -b test.lrcat "name,rating" "rating=>=3"` is run
- **THEN** the output is `WARNING: option "--count" forced` followed by ` * Count results: 3`

#### Scenario: Count then results
- **WHEN** `lrselect -b test.lrcat "name,rating" "rating=>=3, sort=rating" -r -c` is run
- **THEN** the first line is ` * Count results: 3` and the second ` * Results (3 entries) :`

### Requirement: Maximum lines implies results
The `-n`/`--max-lines` option SHALL limit the number of rows displayed, `-1` (the default) meaning all rows. A value greater than 0 SHALL imply `-r`. The count printed by `-c` SHALL always be the total number of selected rows.

#### Scenario: Two lines out of six
- **WHEN** `lrselect -b test.lrcat "name,rating" "" -n 2` is run
- **THEN** ` * Results (first 2 entries of 6) :` is printed followed by the header and two rows
- **AND** no `--count` warning is printed

### Requirement: Display layout options
The command SHALL pass `-N`/`--no-header`, `-w`/`--widths`, `-S`/`--separator` (default ` | `), `-I`/`--indent` (default 4) and `--raw-print` to the result display, which formats them as defined by the `result-display` capability.

#### Scenario: Compact layout
- **WHEN** `lrselect -b test.lrcat "id,name" rating=5 -r -N -S ";" -I 0 -w "3,-15"` is run
- **THEN** the only output line is `  1;IMG_0001.JPG   `

### Requirement: Table selection
The `-t`/`--table` option SHALL choose the table to query: `photo` (the default) or `collection`. Any other value SHALL be rejected by the argument parser with exit status 2. The collection table's columns and criteria are defined by the `collection-selection` capability.

#### Scenario: Collections of type standard
- **WHEN** `lrselect -b test.lrcat -t collection name type=standard -r` is run
- **THEN** the output lists `Holidays` and `Best` and not `Five Stars`

### Requirement: Selection from a file of photo UUIDs
With `-f`/`--file <file>`, the command SHALL read one photo UUID per line from the file and select those photos with the given columns, ignoring the criteria. UUIDs not found in the catalog SHALL be skipped and reported as `=> WARNING found uuids invalid (<bad>/<total>) : <uuid>, ...` on stdout before the results.

#### Scenario: One valid and one invalid UUID
- **WHEN** `uuids.txt` holds the UUID of photo 1 and the line `BADUUID`, and `lrselect -b test.lrcat "id,name" -f uuids.txt -r` is run
- **THEN** `=> WARNING found uuids invalid (1/2) : BADUUID` is printed
- **AND** the results show one row, photo 1 `IMG_0001.JPG`

#### Scenario: Missing UUID file
- **WHEN** `lrselect -b test.lrcat id -f missing.txt -r` is run and `missing.txt` does not exist
- **THEN** ` ==> Failed to open input file "missing.txt"` is printed on stderr and no results are printed

### Requirement: File size computation
With `-z`/`--filesize`, or when the columns contain the pseudo column `filesize`, the command SHALL read the size of each selected photo's file on disk and print the total. The full file name column `name=full` SHALL be added to the requested columns when absent. Without `-r`, only the count and the total line SHALL be printed.

#### Scenario: Total only
- **WHEN** `lrselect -b test.lrcat name "" -z` is run and the photo files do not exist on disk
- **THEN** the output is `WARNING: option "--count" forced`, ` * Count results: 6` and ` * Total filesize : 0.00 B (0 bytes)`

#### Scenario: Filesize column
- **WHEN** `lrselect -b test.lrcat "name,filesize" rating=5 -r` is run
- **THEN** the header shows the columns `name`, `filesize` and `name=full` in that order
- **AND** the last line is ` * Total filesize : 0.00 B (0 bytes)`

### Requirement: Version option
`-V`/`--version` SHALL print `lrselect version : <version> , using python <major>.<minor>.<micro>` and exit without opening a catalog.

#### Scenario: Version printed
- **WHEN** `lrselect --version` is run
- **THEN** stdout contains the package version string

### Requirement: Help text is the column and criteria reference
`-h`/`--help` SHALL print the usage, a description that contains the full reference of photo columns and criteria followed by the reference of collection columns and criteria (introduced by `For collection (use "-t collection")`), a note on the `filesize` pseudo column, three examples, then the option list.

#### Scenario: Help sections
- **WHEN** `lrselect -h` is run
- **THEN** the output contains `columns :`, `For collection (use "-t collection")`, `File sizes can be computed/displayed via the pseudo column "filesize"` and `Examples:`

### Requirement: Log file option
`--log <file>` SHALL append to the file, in UTF-8, timestamped lines recording the start, the package version, the command arguments, the catalog opened, each generated SQL request and the end of the run. Without `--log`, nothing SHALL be written to a log file.

#### Scenario: Log written
- **WHEN** `lrselect -b test.lrcat id "" -c --log run.log` is run
- **THEN** `run.log` starts with `lrselect start`, `lrtools version : <version>` and `arguments: -b test.lrcat id  -c --log run.log`, contains a line `SQL = SELECT ...`, and ends with `lrselect end`
- **AND** each line is prefixed by a timestamp and ` - `

### Requirement: Error reporting
Errors from the configuration, the catalog, the selection language or SQLite SHALL be printed on stderr as ` ==> FAILED: <message>` (` ==> FAILED SQL : <message>` for SQLite errors) and the command SHALL stop without a traceback. The exit status SHALL be 0 in these cases; only argument-parser errors exit with status 2.

#### Scenario: Unknown criterion
- **WHEN** `lrselect -b test.lrcat id unknown=1 -r` is run
- **THEN** ` ==> FAILED: No existent criterion "unknown"` is printed on stderr and the exit status is 0

#### Scenario: Unknown column
- **WHEN** `lrselect -b test.lrcat bogus "" -r` is run
- **THEN** ` ==> FAILED: invalid column key "bogus"` is printed on stderr

#### Scenario: Missing catalog
- **WHEN** `lrselect -b nope.lrcat id "" -r` is run and `nope.lrcat` does not exist
- **THEN** ` ==> FAILED: LR catalog doesn't exist: nope.lrcat` is printed on stderr

#### Scenario: Width or height criterion without dims column
- **WHEN** a selection fails with the message `no such column: dims`
- **THEN** the message printed is ` ==> FAILED: Try to add column "dims"`

### Requirement: Closed output pipe is silent
When the reader of the command's output closes the pipe early (for example `| head`), the command SHALL exit with status 0 and print nothing on stderr.

#### Scenario: Pipe closed before any output
- **WHEN** `lrselect -b test.lrcat name "" -r` is run with its stdout pipe closed before it writes
- **THEN** the exit status is 0 and stderr is empty
