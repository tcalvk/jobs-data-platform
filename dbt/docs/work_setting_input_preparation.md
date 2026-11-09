# SerpApi work-setting input preparation

`int_jobs_scraping__serpapi_jobs` adds eight evidence/preparation columns only.
It does not classify work setting, infer missing flags, resolve conflicts, or
change marts or dashboards. Existing title, description, location and JSON evidence
columns remain unchanged. Extraction is correlated per job, so it adds no rows.

See `models/int/schema.yml` for field types. String extension values and individual
highlight items retain their original strings, order, duplicates and empty strings.
Missing/null/non-array inputs produce typed empty arrays; null, object, array,
numeric and boolean entries are ignored rather than coerced to evidence strings.
Highlight section titles use `JSON_VALUE`: missing/non-scalar titles become NULL.
Sections without valid string items emit no entries. `work_from_home` is a nullable
safe cast of the detected extension, not a classification or default-false flag.

`normalize_work_setting_text` applies NFKC then lowercase, maps curly single/double
quotes and common Unicode dashes/minus signs to ASCII, maps NBSP to space, collapses
whitespace (including Unicode separator characters), and trims. NULL remains NULL;
empty/whitespace-only text becomes `''`. Normalized arrays retain positional
alignment with raw arrays. No word removal, inference, or title fallback is applied.
The existing pay-text extraction now consumes the safe string-only extension array,
selecting the first matching source-order entry, so malformed extensions cannot
cause the former `JSON_VALUE_ARRAY` null-element failure.

## Deployment / historical data

The model deliberately retains `on_schema_change='fail'` and its existing
`insert_overwrite` partition window. An existing table will reject these additive
columns until an operator approves a schema migration. Do not casually run the
normal daily job expecting automatic schema synchronization.

Choose an operator-controlled full refresh of this model (after confirming source
history/availability and cost), or explicitly add the eight columns with the types
documented in schema.yml and plan a controlled historical partition backfill.
An additive schema migration alone leaves older partitions NULL/unpopulated;
normal incremental runs only populate the configured recent partition window.
No migration, materialization, refresh or cloud writes are performed by this change.

## Fixture checks

`assert_serpapi_work_setting_input_fixtures` and
`assert_normalize_work_setting_text_fixtures` are singular tests containing only
literal fixtures, with no warehouse-table dependencies. They share extraction and
normalization macros with the model and assert ordered values, malformed inputs,
nullable booleans, Unicode normalization and positional alignment. Running their
compiled SELECTs is read-only; dbt parse/render can also be checked offline.
