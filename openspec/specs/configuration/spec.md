# configuration Specification

## Purpose

Defines how the tools find and read the optional `lrtools.ini` file, which keys it holds, and the defaults used when it is missing or unreadable.

## Requirements

### Requirement: Built-in defaults
The system SHALL start from built-in defaults: default catalog `C:\Users\Default\Documents\My Lightroom Catalog.lrcat`, day-first date parsing enabled, and the `nominatim` geocoder.

#### Scenario: No configuration requested
- **WHEN** the configuration is created without a file name
- **THEN** the default catalog path ends with `My Lightroom Catalog.lrcat`
- **AND** day-first parsing is enabled
- **AND** the geocoder is `nominatim`

### Requirement: Configuration file search order
When the configuration file name has no directory part, the system SHALL look for it in the current directory, then the directory of the running script, then `~/.config/lrtools/`, and use the first one that exists. A name with a directory part SHALL be used as given.

#### Scenario: File in the current directory
- **WHEN** `lrtools.ini` exists in the current directory
- **THEN** its `LRCatalog` value becomes the default catalog

#### Scenario: File in the user configuration directory
- **WHEN** `lrtools.ini` exists only in `~/.config/lrtools/`
- **THEN** that file is loaded

#### Scenario: Explicit path
- **WHEN** the configuration is created with a path such as `/tmp/custom.ini`
- **THEN** exactly that file is loaded, whatever its file name

### Requirement: Missing configuration file is silent
The system SHALL keep the built-in defaults and print nothing when no configuration file is found in any searched location.

#### Scenario: No lrtools.ini anywhere
- **WHEN** none of the searched locations holds `lrtools.ini`
- **THEN** the defaults are used
- **AND** nothing is written to standard error

### Requirement: Configuration keys
The system SHALL read the keys `LRCatalog` (default catalog path), `DayFirst` (boolean controlling date parsing order) and `GeoCoder` (geocoding service name) from the `[Main]` section. A key missing from `[Main]` SHALL keep its default value.

#### Scenario: Full file
- **WHEN** `[Main]` sets `LRCatalog = /x/cat.lrcat`, `DayFirst = False` and `GeoCoder = BanFrance`
- **THEN** the default catalog is `/x/cat.lrcat`
- **AND** day-first parsing is disabled
- **AND** the geocoder is `BanFrance`

#### Scenario: Partial section
- **WHEN** `[Main]` only sets `DayFirst = False`
- **THEN** the catalog and geocoder keep their defaults

### Requirement: Unreadable file found at start-up
When a configuration file found automatically cannot be parsed or has no `[Main]` section, the system SHALL write `WARNING: failed to read config file <name>` to standard error and continue with the defaults.

#### Scenario: Garbage in lrtools.ini
- **WHEN** `lrtools.ini` in the current directory contains text that is not INI
- **THEN** the warning is written to standard error
- **AND** day-first parsing stays enabled

### Requirement: Explicit load failure
Loading a configuration file explicitly (for example an INI file given to `-b`) SHALL fail with the error `Failed to read config file "<name>"` when the file has no `[Main]` section or cannot be read.

#### Scenario: INI without a Main section
- **WHEN** a file containing only `[Other]` is loaded explicitly
- **THEN** a configuration error with that message is raised

#### Scenario: Missing INI given to a script
- **WHEN** `lrselect.py -b x name ""` is run and `x` does not exist
- **THEN** the script prints ` ==> FAILED: Failed to read config file "x"`

### Requirement: Geocoder selection
The geocoder name SHALL be matched case-insensitively against `nominatim` and `banfrance`. Any other name SHALL make the town-based GPS criterion fail with the error `None Geocoder`; other features SHALL not be affected.

#### Scenario: Mixed-case name
- **WHEN** `GeoCoder = BanFrance` is configured and a town GPS criterion is used
- **THEN** the French BAN geocoding service is queried

#### Scenario: Unknown geocoder
- **WHEN** `GeoCoder = Google` is configured and a town GPS criterion is used
- **THEN** the selection fails with `None Geocoder`
