# lrsmart-cli Specification

## Purpose

The `lrsmart` command runs Lightroom smart collections, read from the catalog by name or from exported smart collection files, and prints their definition, SQL, count or photos. It is available both as the `lrsmart.py` script and as the installed `lrsmart` command, with identical behaviour.

## Requirements

### Requirement: Two invocation forms with identical behaviour
The system SHALL provide the command both as the `lrsmart.py` script run with Python and as the installed `lrsmart` console command, and both SHALL accept the same arguments and produce the same output.

#### Scenario: Script and installed command agree
- **WHEN** `lrsmart.py -b test.lrcat "Five Stars" -c` and `lrsmart -b test.lrcat "Five Stars" -c` are run on the same catalog
- **THEN** both exit with status 0 and print `Smart Collection "Five Stars"` and ` * Count results: 1`

### Requirement: Smart collections selected by name
The positional arguments SHALL be smart collection names, matched case-insensitively against the catalog's smart collections. A name containing `%` SHALL be a LIKE pattern. Matching collections SHALL be processed in ascending name order, each introduced by the line `Smart Collection "<name>"`. A name matching no smart collection SHALL be silently ignored.

#### Scenario: Joker runs every smart collection
- **WHEN** `lrsmart -b test.lrcat % -C id,name -r -N` is run
- **THEN** the output contains `Smart Collection "Canon Family"` before `Smart Collection "Five Stars"`

#### Scenario: Unknown name
- **WHEN** `lrsmart -b test.lrcat Nope -c` is run and no smart collection is named `Nope`
- **THEN** nothing is printed and the exit status is 0

### Requirement: Smart collections from exported files
With `-f`/`--file`, the positional arguments SHALL be paths of exported smart collection files (`.lrsmcol`), processed in the given order, each introduced by `Smart Collection filename "<path>"`. The definition SHALL be read from the first `{` of the file; its `title` is printed as ` * Collection name : "<title>"` (the path when absent) and its `value` table is run. The command does not expand `*` itself; the shell does.

#### Scenario: Exported file counted
- **WHEN** `videos.lrsmcol` defines `title = "Videos"` with one criterion `fileFormat == "VIDEO"` and `lrsmart -b test.lrcat --file videos.lrsmcol -c` is run
- **THEN** the output contains ` * Collection name : "Videos"` and ` * Count results: 1`

#### Scenario: Missing file
- **WHEN** `lrsmart -b test.lrcat --file missing.lrsmcol -c` is run and the file does not exist
- **THEN** `Smart Collection filename "missing.lrsmcol"` then `  ==> FAILED : Not found` are printed and the next file, if any, is processed

#### Scenario: Invalid file content
- **WHEN** the file decodes to a table with no `value` table, for example `s = { title = 1 }`
- **THEN** `  ==> FAILED : Invalid syntax` is printed and the next file, if any, is processed

### Requirement: List smart collections
`-l`/`--list` SHALL print the line `Smart Collection "<name>"` for each smart collection matching the positional names, or for every smart collection when no name is given.

#### Scenario: List all
- **WHEN** `lrsmart -b test.lrcat -l` is run
- **THEN** the output is `Smart Collection "Canon Family"` then `Smart Collection "Five Stars"`

### Requirement: Definition display
`--raw` SHALL print the definition as stored: from the catalog under ` * Raw definition as stored :`, each line prefixed by a tab, or with `--file` the file content verbatim. `-d`/`--dict` SHALL print the decoded definition under ` * Definition as python dictionary :`, one `<key> = <value>` line per entry, each prefixed by a tab.

#### Scenario: Raw definition from the catalog
- **WHEN** `lrsmart -b test.lrcat "Five Stars" --raw` is run
- **THEN** ` * Raw definition as stored :` is printed followed by the stored Lua text `s = { ... }`, one tab-prefixed line per line

#### Scenario: Decoded definition
- **WHEN** `lrsmart -b test.lrcat "Five Stars" -d` is run
- **THEN** the output contains `0 = {'criteria': 'rating', 'operation': '>=', 'value': 5}` and `combine = intersect`

#### Scenario: Raw definition of a missing file
- **WHEN** `lrsmart -b test.lrcat --file missing.lrsmcol --raw -c` is run
- **THEN** `  ==> FAILED : Not found` is printed and the file is skipped

### Requirement: SQL, count and results
`-s`/`--sql` SHALL print ` * SQL Request:  <sql>`, `-c`/`--count` SHALL print ` * Count results: <n>` and `-r`/`--results` SHALL print the rows as defined by the `result-display` capability. The SQL is the translation defined by the `smart-collections` capability. `-n`/`--max-lines` greater than 0 SHALL imply `-r`.

#### Scenario: SQL of a smart collection
- **WHEN** `lrsmart -b test.lrcat "Five Stars" -s` is run
- **THEN** ` * SQL Request:  SELECT ... WHERE i.rating >= 5 ORDER BY 1 ASC` is printed and no query is executed

#### Scenario: Results with max lines
- **WHEN** `lrsmart -b test.lrcat "Five Stars" -n 5 -C id,name,rating` is run
- **THEN** ` * Results (1 entries) :` is printed followed by the header and the row of photo 1

### Requirement: Results default to zero displayed rows
The `-n`/`--max-lines` default SHALL be 0. With `-r` and no `-n`, the results header SHALL be ` * Results (first 0 entries of <n>) :` followed by the column header and no rows.

#### Scenario: -r alone
- **WHEN** `lrsmart -b test.lrcat Five% -c -r` is run
- **THEN** ` * Count results: 1` then ` * Results (first 0 entries of 1) :` and the column header are printed, with no data row

### Requirement: Columns and sort
`-C`/`--columns` SHALL set the photo columns to select, in the columns syntax of the `selection-language` capability (default `uuid,name`). `-o`/`--sort-column` SHALL set the column name or one-based number to sort on (default `1`), ascending, or descending when prefixed by `-`.

#### Scenario: Descending sort by first column
- **WHEN** `lrsmart -b test.lrcat "Five Stars" -r -n 5 -C id,name,rating -o -1` is run
- **THEN** the printed SQL order, visible with `-s`, is `ORDER BY 1 DESC`

### Requirement: Display options
`-N`/`--no-header`, `-S`/`--separator` (default ` | `) and `--raw-print` SHALL be passed to the result display. `-w`/`--widths` SHALL be accepted but has no effect on the output. The indentation SHALL be the display default of 4 spaces.

#### Scenario: No header
- **WHEN** `lrsmart -b test.lrcat "Five Stars" -n 5 -N` is run
- **THEN** only the data row is printed after `Smart Collection "Five Stars"`

### Requirement: Validation against Lightroom counts
The hidden option `--validation-file <file>` SHALL read lines `<name> ==> <count>` (other lines ignored) and, for each smart collection with a known count, append to its count line `=> conform to LR` when equal or `=> NOT_CONFORM to LR : <count>` otherwise. A missing validation file SHALL stop the command with `Validation file not found` on stderr and exit status 1.

#### Scenario: Conform and not conform
- **WHEN** the file holds `Five Stars ==> 2`, `Canon Family ==> 2` and `garbage`, and `lrsmart -b test.lrcat % -c --validation-file val.txt` is run
- **THEN** the output contains ` * Count results: 2  => conform to LR` for `Canon Family` and ` * Count results: 1  => NOT_CONFORM to LR : 2` for `Five Stars`

#### Scenario: Missing validation file
- **WHEN** `lrsmart -b test.lrcat % -c --validation-file nope.txt` is run and the file does not exist
- **THEN** `Validation file not found` is printed and the exit status is 1

### Requirement: Catalog option
The `-b`/`--lrcat` option SHALL name the catalog; a value not ending in `lrcat` SHALL be read as an INI file in `lrtools.ini` form, as for `lrselect`. Without `-b`, the configured default catalog SHALL be used.

#### Scenario: Missing catalog
- **WHEN** `lrsmart -b nope.lrcat % -c` is run and `nope.lrcat` does not exist
- **THEN** ` ==> FAILED: LR catalog doesn't exist: nope.lrcat` is printed on stderr

### Requirement: Help lists supported criteria
`-h`/`--help` SHALL print the usage and a description that lists, comma separated after `Supported criteria are : `, every Lightroom smart collection criterion the translation supports.

#### Scenario: Help
- **WHEN** `lrsmart -h` is run
- **THEN** the description contains `Supported criteria are : all, aperture, aspectRatio, camera, captureTime,`

### Requirement: Error reporting
A smart collection that cannot be translated or whose SQL fails SHALL print ` ==> FAILED :  <message>` on stdout and the next collection SHALL be processed. Configuration, catalog and selection errors outside a collection SHALL print ` ==> FAILED: <message>` on stderr and stop. The exit status SHALL be 0 in all these cases.

#### Scenario: Unsupported criterion in a collection
- **WHEN** `b.lrsmcol` uses the criterion `nosuch` and `lrsmart -b test.lrcat --file b.lrsmcol v.lrsmcol -c` is run
- **THEN** ` ==> FAILED :  criteria unsupported: nosuch` is printed for `b.lrsmcol`
- **AND** `v.lrsmcol` is still run and its count printed, and the exit status is 0

### Requirement: Log file option
`--log <file>` SHALL append timestamped UTF-8 lines recording the start, the package version and, for each executed collection, `start smart "<name>"` and `end smart : <n> rows` (or `end smart : FAILED : <message>`), then `lrsmart end`.

#### Scenario: Log of one collection
- **WHEN** `lrsmart -b test.lrcat "Five Stars" -c --log run.log` is run
- **THEN** `run.log` contains `start smart "Five Stars"` and `end smart : 1 rows`

### Requirement: Closed output pipe is silent
When the reader of the command's output closes the pipe early, the command SHALL exit with status 0 and print nothing on stderr.

#### Scenario: Pipe closed before any output
- **WHEN** `lrsmart -b test.lrcat % -r` is run with its stdout pipe closed before it writes
- **THEN** the exit status is 0 and stderr is empty
