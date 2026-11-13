# collection-selection Specification

## Purpose

Selects Lightroom collections (standard and smart) from the catalog's collection table, with their own columns and criteria, through `lrselect -t collection`.

## Requirements

### Requirement: Collection columns
The collection table SHALL offer the columns `name` (collection name), `id` (collection id), `type` (the Lightroom creation id, such as `com.adobe.ag.library.collection` or `com.adobe.ag.library.smart_collection`), `parent` (id of the parent collection, empty at the top level) and `all` (every raw field of the collection row). Any other column SHALL fail with `invalid column key "<column>"`.

#### Scenario: Smart collections with id and type
- **WHEN** `lrselect -b test.lrcat -t collection "name,id,type,parent" type=smart -r` is run
- **THEN** two rows are printed, `Five Stars` with id 12 and `Canon Family` with id 13, both of type `com.adobe.ag.library.smart_collection` with an empty parent

#### Scenario: Photo column on collections
- **WHEN** `lrselect -b test.lrcat -t collection "" "" -r` is run
- **THEN** ` ==> FAILED: invalid column key "datecapt"` is printed, because the command's default columns `name,datecapt` are photo columns

### Requirement: Smart collection definition column
The column `smart` SHALL return the content entries stored for a collection, which for a smart collection is its definition as Lua text. Selecting it SHALL return one row per stored content entry: a collection without content is not returned, and a collection with several entries (filter, sort type, sort direction, ...) is returned once per entry unless `id4smart` or `name4smart` restricts it.

#### Scenario: Definition of one smart collection
- **WHEN** `lrselect -b test.lrcat -t collection "name,smart" "name4smart=Five Stars" -r` is run
- **THEN** one row is printed whose `smart` value starts with `s = {` and contains `criteria = "rating"`

#### Scenario: Standard collections without content
- **WHEN** `lrselect -b test.lrcat -t collection "name,smart" type=standard -c` is run on the test catalog, whose standard collections store no content
- **THEN** ` * Count results: 0` is printed

#### Scenario: Several content entries per collection
- **WHEN** a catalog has 3 standard collections each storing filter, sort type and sort direction entries, and `lrselect -t collection "name,smart" type=standard -c` is run
- **THEN** ` * Count results: 9` is printed

### Requirement: Name criterion
The criterion `name=<pattern>` SHALL select collections whose name matches the pattern with SQL LIKE semantics: `%` matches any sequence, `_` one character, and ASCII letters match case-insensitively.

#### Scenario: Pattern
- **WHEN** `lrselect -b test.lrcat -t collection "name,id" "name=%o%" -r` is run
- **THEN** `Holidays` (10) and `Canon Family` (13) are printed

#### Scenario: Case-insensitive name
- **WHEN** `lrselect -b test.lrcat -t collection "name,id" name=holidays -r` is run
- **THEN** `Holidays` (10) is printed

### Requirement: Id criterion
The criterion `id=<n>` SHALL select the collection whose id is `n`.

#### Scenario: Collection by id
- **WHEN** `lrselect -b test.lrcat -t collection "name,id" id=11 -r` is run
- **THEN** only `Best` (11) is printed

### Requirement: Type criterion
The criterion `type=<value>` SHALL select by creation id: `standard` for standard collections, `smart` for smart collections, `all` for both, or any other value taken as an explicit creation id (for example `com.adobe.ag.library.group`). The `all` value is not parenthesised, so combined with another criterion by `,` it still returns every smart collection.

#### Scenario: All collections
- **WHEN** `lrselect -b test.lrcat -t collection name type=all -r -c` is run
- **THEN** ` * Count results: 4` is printed followed by `Holidays`, `Best`, `Five Stars` and `Canon Family`

#### Scenario: Type all combined with a name
- **WHEN** `lrselect -b test.lrcat -t collection name "type=all,name=Best" -r` is run
- **THEN** `Best`, `Five Stars` and `Canon Family` are printed

#### Scenario: Explicit creation id
- **WHEN** `lrselect -b test.lrcat -t collection name type=com.adobe.ag.library.group -c` is run on a catalog without collection sets
- **THEN** ` * Count results: 0` is printed

### Requirement: Smart collection lookup criteria
The criteria `id4smart=<n>` and `name4smart=<pattern>` SHALL select smart collections only, by id or by name with LIKE semantics, and are meant to be combined with the `smart` column.

#### Scenario: Smart collection by id
- **WHEN** `lrselect -b test.lrcat -t collection name id4smart=12 -r -c` is run
- **THEN** ` * Count results: 1` is printed followed by `Five Stars`

### Requirement: Only collection criteria are accepted
The collection table SHALL accept only the criteria `name`, `id`, `type`, `id4smart` and `name4smart`; any other criterion, including photo criteria and `sort`, SHALL fail with `No existent criterion "<name>"`.

#### Scenario: Photo criterion
- **WHEN** `lrselect -b test.lrcat -t collection name rating=5 -c` is run
- **THEN** ` ==> FAILED: No existent criterion "rating"` is printed on stderr

#### Scenario: Sort criterion
- **WHEN** `lrselect -b test.lrcat -t collection "name,id" "type=standard,sort=-id" -r` is run
- **THEN** ` ==> FAILED: No existent criterion "sort"` is printed on stderr

### Requirement: No criteria selects every collection
An empty or missing criteria SHALL select every row of the collection table, including collection sets and other non-photo collections.

#### Scenario: Count all rows
- **WHEN** `lrselect -b test.lrcat -t collection name -c` is run
- **THEN** ` * Count results: 4` is printed for the test catalog
