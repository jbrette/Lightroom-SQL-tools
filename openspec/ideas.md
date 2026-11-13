# Ideas

Backlog for lrtools. Entries in § Raw ideas are `- [ ]` (open) or `- [x]` (done
through an archived change). The suspected bugs below were found on 2026-11-13
while reverse-engineering the code into `openspec/specs/`; the specs describe the
current behaviour, so fixing one of these is a change that MODIFIES its spec.
"(verified)" means reproduced against the synthetic test catalog.

## Suggested next-up

## Raw ideas

- [ ] **cli-exit-status-on-failure** — Both CLIs exit 0 on most failures: missing catalog, bad INI, unknown column or criterion, missing UUID file, untranslatable smart collection. Only argparse errors (2) and a missing `lrsmart --validation-file` (1) differ. Scripts calling them cannot detect failure.
      _capability: lrselect-cli, lrsmart-cli_
- [ ] **lrsmart-results-default-max-lines** — `lrsmart -r` alone prints ` * Results (first 0 entries of N) :` and only the header, because `-n` defaults to 0; `lrselect` defaults to -1 (all rows).
      _capability: lrsmart-cli_
- [ ] **lrsmart-widths-ignored** — `lrsmart -w/--widths` is parsed but never passed to the display.
      _capability: lrsmart-cli_
- [ ] **lrsmart-unknown-name-silent** — A name (or `%` pattern) matching no smart collection prints nothing at all; no "not found" message.
      _capability: lrsmart-cli_
- [ ] **lrsmart-file-joker** — The help mentions a `*` joker for `--file`, but the script does not expand it; only the shell does (fails on Windows or when quoted).
      _capability: lrsmart-cli_
- [ ] **lrsmart-raw-file-order** — `lrsmart --raw --file` prints the file content before the `Smart Collection filename` line.
      _capability: lrsmart-cli_
- [ ] **lrsmart-missing-options** — `lrsmart` has no `-V/--version` and no `-I/--indent`, unlike `lrselect`.
      _capability: lrsmart-cli_
- [ ] **lrselect-sql-with-uuid-file** — `lrselect -s -f <uuids>` prints SQL built from the ignored criteria argument, not the UUID-file query actually run.
      _capability: lrselect-cli_
- [ ] **lrselect-collection-default-columns** — `lrselect -t collection` with no columns fails with `invalid column key "datecapt"`: the photo defaults `name,datecapt` are applied before the collection default `name`.
      _capability: lrselect-cli, collection-selection_

- [ ] **groupby-broken-sql** — `groupby=<col>` builds invalid SQL (`WHERE GROUP BY camera ...`).
      _capability: selection-language_
- [ ] **count-criterion-help-mismatch** — The help documents `count(NAME)` as a criterion, but the parser rejects it (`Invalid token "=>1"`); the working form is `count=camera>100`.
      _capability: selection-language_
- [ ] **sort-direction-inverted** — `sort=<col>` sorts descending by default and `-<col>` ascending, the reverse of the usual convention. Tests lock the current behaviour in; changing it breaks users.
      _capability: selection-language_
- [ ] **name-default-variant-help** — The help says `base` is the default `name` variant; a bare `name` (and empty columns) actually gives `basext` (`IMG_0001.JPG`).
      _capability: photo-selection_
- [ ] **exactname-case** — The help calls `exactname` case-insensitive, but it compares against the upper-cased base name, so a lowercase value matches nothing (`exactname=img_0001` → no rows).
      _capability: photo-selection_
- [ ] **orientation-column-typo** — The `orientation` column is returned under the name `orientaton`.
      _capability: photo-selection_
- [ ] **width-height-need-dims** — `width`/`height` criteria produce invalid SQL unless the `dims` column is selected (documented in help, but should add the join itself).
      _capability: photo-selection_
- [ ] **pubtime-timezone-and-zero** — `pubtime` treats its value as UTC while `datemod` uses local time; `pubtime` rejects a value converting to timestamp 0 and reports the error as `invalid date value on "datemod"`.
      _capability: photo-selection, date-handling_
- [ ] **datemod-without-operator** — `datemod=2020` (no operator) produces `i.touchtime  <ts>` and ends in a raw SQL error instead of a clear message.
      _capability: date-handling_
- [ ] **dead-func-pubtime** — `func_pubtime` in `lrselectphoto.py` is never used and its body copies `func_published`.
      _capability: photo-selection_
- [ ] **count-by-date-dayfirst-and-bounds** — `count_by_date(...)` parses dates year-first and ignores `DayFirst` (`5-1-2019` → year 5); its end date is inclusive by year (`<=`) but exclusive by month and day (`<`).
      _capability: photo-selection, date-handling_
- [ ] **duplicated-names-format2-case** — `duplicated_names(2)` compares the upper-cased name with non-upper-cased names from the inner query, so only all-upper-case duplicates match.
      _capability: catalog-access, photo-selection_

- [ ] **collection-type-all-or-precedence** — `type=all` emits an unparenthesised `OR`, so `type=all,name=Best` also returns every smart collection.
      _capability: collection-selection_
- [ ] **collection-smart-column-duplicates** — The `smart` collection column returns one row per stored content entry; on the real catalog 3 standard collections give 9 rows.
      _capability: collection-selection_
- [ ] **collection-help-criteria-names** — Collection help names `id4content`/`name4content`; the real criteria are `id4smart`/`name4smart`. The `all` column is not listed.
      _capability: collection-selection_
- [ ] **collection-sort-unsupported** — `sort` fails on the collection table with `No existent criterion "sort"`.
      _capability: collection-selection_

- [ ] **smart-copyname-unsupported** — Lightroom's `copyName` criterion fails with "criteria unsupported: copyName" because the method is `criteria_copyname` (verified). The class docstring lists `copyName` and has a `hadsGPSData` typo.
      _capability: smart-collections_
- [ ] **smart-rating-zero** — `rating == 0` selects nothing: the value is compared with the string `"0"` while the Lua decoder returns integer 0 (verified).
      _capability: smart-collections_
- [ ] **smart-rating-not-equal-unrated** — `rating != N` drops unrated (NULL) photos; probably differs from Lightroom (unverified).
      _capability: smart-collections_
- [ ] **smart-capturetime-inlast-units** — `captureTime inLast` with a unit SQLite does not know (e.g. `weeks`) silently selects nothing (verified).
      _capability: smart-collections_
- [ ] **smart-capturetime-operations** — `captureTime` lacks `>=`, `<=` and relative operations (`today`, `thisYear`, …), which fail as unsupported (`>=` verified), although `touchTime` supports the relative ones.
      _capability: smart-collections_
- [ ] **smart-touchtime-rolling-periods** — `touchTime` `thisMonth`/`thisWeek` are rolling windows (since this day last month, last 7 days), not calendar periods as in Lightroom.
      _capability: smart-collections_
- [ ] **smart-word-operations-plain-text** — `beginsWith`, `endsWith` and `words` use the search index's `/t` word markers, so on plain-text criteria (`filename`, `folder`, `copyname`, `creator`) they never match (verified for `folder`, `filename`).
      _capability: smart-collections_
- [ ] **smart-filename-needs-name-column** — The `filename` criterion filters on the result column `name` and fails with "no such column: name" unless `name` is among the requested columns (verified).
      _capability: smart-collections_
- [ ] **smart-operation-validation** — Numeric, `fileFormat`, `labelText` and `colorMode` criteria pass the operation into SQL unchecked; an unknown one gives a raw SQLite error instead of a SmartException (`isoSpeedRating between` → "incomplete input", verified).
      _capability: smart-collections_
- [ ] **smart-value-quoting** — Values are interpolated into SQL; a double quote in a value gives a syntax error (verified). Read-only catalog, so no write risk, but should use bound parameters.
      _capability: smart-collections_
- [ ] **smart-combine-errors** — `exclude` (match none) is unsupported (verified); with 2+ criteria a missing `combine` raises `KeyError` (verified); with one criterion any combine value, even invalid, is ignored (verified).
      _capability: smart-collections_
- [ ] **smart-nested-groups-crash** — An entry without a `criteria` key (a nested rule group) raises `KeyError` instead of a SmartException (verified).
      _capability: smart-collections_
- [ ] **smart-error-messages** — `metadataStatus` reports "value unsupported: <operation> on criteria <value>" with arguments swapped; `treatment` with a non-grayscale value reports "operation unsupported"; the `touchTime` message quotes its arguments while others don't (verified).
      _capability: smart-collections_
- [ ] **smart-empty-definition** — A definition with no criterion at position 0 produces an empty SQL string instead of an error (verified).
      _capability: smart-collections_
- [ ] **smart-digit-collection-name** — A collection whose name is all digits cannot be found by name: the lookup reads it as an id.
      _capability: smart-collections_
- [ ] **smart-collection-any-all** — `collection any` is unsupported (verified); `collection all` with several words matches when each word is in some collection, not necessarily the same one.
      _capability: smart-collections_
- [ ] **lua-decoder-gaps** — The Lua decoder does not handle escaped quotes or single-quoted strings; `{}` decodes to None; a trailing comma followed by spaces before `}` adds a stray `","` entry (all verified).
      _capability: smart-collections_

- [ ] **lr-strptime-offsets** — `lr_strptime` fails on fractional seconds followed by `Z`, and on any negative UTC offset (`-05:00`): it only checks for `+` or `Z`.
      _capability: date-handling_
- [ ] **date-to-lrstamp-naive-datetime** — `date_to_lrstamp` with a naive `datetime` subtracts the UTC-aware epoch and raises `TypeError`.
      _capability: date-handling_
- [ ] **lrcat-arg-ini-detection** — `-b` treats any path not ending in `lrcat` as an INI file; a partly read INI can leave settings changed before the error is raised.
      _capability: catalog-access, configuration_

## Archived ideas — by capability
