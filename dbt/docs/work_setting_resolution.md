# Work-setting resolution v1 (implementation, not deployed)

`analysis.jobs_detail` owns evidence construction and resolution inline. The
regex-only `work_setting_patterns()` macro returns the ten unchanged pattern
strings; it does not classify rows or resolve evidence. Existing
normalization/extraction macros only prepare text/arrays. Dimension passthrough is lossless and explicitly typed across
SerpApi and LinkedIn. The fact table and Evidence dashboards are unchanged.

## Contract and precedence

- **Office**: explicit role onsite/in-office attendance, without recurring remote.
- **Hybrid**: explicit role hybrid arrangement or a bounded recurring onsite/remote
  schedule. A technical hybrid-cloud mention is not an arrangement.
- **Remote**: ordinarily remote. Residency restrictions and occasional client travel,
  annual retreats or brief onboarding do not alone create Hybrid.
- **Unknown**: absent evidence, unresolved alternatives, substantive temporal or
  conditional arrangements, or contradictory evidence at the winning strength.

Strengths are role-specific description/eligible highlight **4**, clear title
**3**, LI tag **2**, exact metadata **1**. Role evidence wins over title and WFH.
Within a strength, contradictory proposed settings or explicit ambiguity yield
Unknown. A remote prohibition never proves Office; `work_from_home=false` is
retained as neutral strength **0** evidence and never proves Office. `No 100%
remote` does not veto an explicitly hybrid schedule. Negated remote experience
requirements are not attendance prohibitions.

Compatibility is deliberately narrow. An explicitly hybrid role and a partial
weekly onsite component are compatible; an unqualified or fully onsite assertion
still conflicts with Hybrid. Two separate sentences can establish a recurring
mix only when they quantify 1–4 onsite and 1–4 remote/home work days per week,
sum to at most five, have the same role-text source and strength, and are not
ambiguous, exclusive or prohibited. A synthetic `:weekly_mix` evidence item
preserves both originals. Arbitrary onsite/remote co-occurrence, impossible day
counts and contradictory full-remote assertions are not merged. Negated onsite
requirements are stripped before positive matching; substantive first-period /
thereafter transitions remain Unknown. Technical hybrid titles require clear
setting-label placement, rather than interpreting any `Hybrid <specialty>` as
an arrangement.

Negation handling covers bounded active requirements (including `require you to
work onsite`) and passive attendance/availability clauses (`onsite attendance is
not required`, `remote work is not available`). A remote prohibition is retained
at its source strength, so role text can veto a weaker title or WFH flag without
inventing Office. The same recognized negative metadata cannot become a positive
setting through an exact-label fallback. Positive evidence in a separate
sentence remains independently evaluable. Quantified remote cadence recognizes
imperative `work from home N days per week`, not only `you can/will` grammar.
Negated obligations (`not required/necessary to work from home`, including
passive WFH forms) are neutral: they are removed before positive signals **and**
weekly day extraction, and are not permission prohibitions. A separate explicit
onsite or remote sentence therefore remains usable. Actual `not available`,
`not allowed` and `not permitted` remote clauses still veto weaker Remote evidence.

The onboarding exemption is directional and narrow: a 1–5-day onsite introduction
with clear ongoing remote work. Remote-first transitions to onsite, month/week
periods and other substantive transitions remain Unknown even if the text says
`onboarding`; the presence of that word never globally exempts temporal text.

SerpApi extensions must match exact normalized setting labels. Its boolean flag
is independent metadata, not a role requirement. LinkedIn's **raw**
`fit_level_preferences` is split on its native `·` delimiter and exact labels
resolved here; the existing upstream inferred `work_location` is not used.
Highlights are restricted to named role/schedule/responsibility sections, not
benefits. Original title and description remain unchanged. The dimension keeps
its original earliest-observation surrogate-key grain; no raw join was added.

## Public work-setting output

Exactly two work-setting fields are public: `work_setting STRING` and
`work_setting_metadata JSON`. Metadata is a native JSON **object**, produced by
`TO_JSON(STRUCT(...))`, not a JSON-formatted string. Its four keys are `rule`,
`evidence`, `confidence`, and `conflict` (a JSON boolean). The previous separate
public audit columns are internal only and excluded from final output.
The private raw LinkedIn passthrough is named `work_setting_source_metadata`
(STRING), avoiding collision with public JSON metadata; it is excluded too.

`work_setting_metadata.evidence` is an array of **matched** fragments/metadata, not a copy
of every source field. Each item carries `source`, original `text`, `normalized`,
`strength`, proposed `setting`, `conflict`, and `negative_remote`. LI tags get
separate entries at lower strength even when embedded in a strong role sentence.
Weaker disagreement remains visible but is not a winning-strength conflict.
Nullable `office_days` / `remote_days` identify narrowly recognized compatible
weekly components; they are not a complete extraction of all schedules.

`work_setting_metadata.rule` names the resolution path (`explicit_role_setting`,
`li_tag_fallback`, `metadata_fallback`, `insufficient_evidence`, or
`conflicting_or_ambiguous_evidence`). `work_setting_metadata.conflict` applies only to
winning-strength ambiguity/contradiction, not all weaker disagreement.
`work_setting_metadata.confidence` is ordinal: high explicit, medium fallback, low Unknown.
It is **not** calibrated probability or measured classifier accuracy. Private
helper and passthrough columns are excluded from final analysis output.

## Validation and limits

Native dbt unit-test YAML supplies SQL input mocks and expected results. The
read-only harness substitutes those mocks into **dbt-compiled actual model SQL**;
it does not copy the classifier. It executes BigQuery SELECTs, fixture output
invariants and existing-column/row-grain regression checks. It also dry-runs
hydrated nonincremental/incremental SELECT graphs with deployed staging inputs,
because production dimension/int tables do not yet contain the new columns.
The incremental branch is rendered from the original int SQL/macros with a local
three-day partition window; no incremental materialization is executed.

```sh
.venv/bin/dbt parse --project-dir dbt --profiles-dir dbt --no-partial-parse
.venv/bin/dbt compile --project-dir dbt --profiles-dir dbt --select +jobs_detail --no-introspect
.venv/bin/python scripts/validate_work_setting_readonly.py --graph-dry-run
git diff --check
```

As validated after QA fixes: 105 literal fixture cases passed, singular
output invariants passed, existing-column fixture regression passed. Both full
SELECT graph dry-runs passed (26 analysis columns / 22 dimension columns,
1,779,041,342 estimated bytes). No warehouse writes/materializations occurred.
Standard `dbt test` was deliberately not run because its unit-test adapter may
create temporary tables. Fixtures are not statistical validation.

Every harness execution first dry-runs and verifies `statement_type=SELECT`,
including baseline, invariant and optional sample queries; each has a 2 GB cap.
Optional snippet JSON is bound as a BigQuery parameter, never SQL interpolation.
Compiled model, normalization/pattern macros and dimension SQL staleness are checked.
Graph dry-runs compare exact nested data types against the dimension contract
and actual-model fixture output schema, not merely column names.
The JSON-output migration was checked against a pre-change read-only snapshot of
all 105 labels and complete rule/evidence/confidence/conflict values, including
evidence order, numbers, nulls and booleans. The harness accepts that snapshot via
`--previous-audit-snapshot <path>` for exact deep comparison. Native unit YAML
also has representative complete object expectations; the harness compares JSON
objects in Python because adapter-native JSON equality can be unsupported.

An independently supplied challenge-enriched snippet file included **10** judged
examples across five via labels (its metadata mentions a larger source sampling
pool). Qualitative SELECT checks agreed on nine; a BeBee team schedule described
as `hybrid model (3 days a week in our San Jose HQ)` remained Unknown. This is a
documented conservative recall gap, not an accuracy estimate. Snippets are not
full postings. The separate ~300 human-labelled review remains issue
`jobs-data-platform-3oi`.

This compact English ruleset is intentionally incomplete. Unfamiliar paraphrases,
unusual title meanings, punctuation/abbreviations, multi-sentence schedules,
unlisted highlight section names, and complex conditional/negated prose can be
missed or misread. A finite technical-title exclusion list is not semantic
understanding. Generic-policy avoidance is conservative, not a universal
boilerplate detector. Review Unknown/conflicting samples before expanding rules.

## Operator-approved rollout dependency

Nothing here deploys production. The int models use incremental insert-overwrite
with `on_schema_change='fail'`; the dimension has an enforced schema contract.
An operator must approve the prep-schema migration and historical hydration first
(including LinkedIn raw preferences and SerpApi typed passthrough). Adding columns
alone and processing only recent partitions leaves historical metadata absent;
the earliest-observation dimension makes that particularly important. Choose an
explicit reviewed backfill/rebuild plan, not an automatic full refresh. Then
rebuild the dimension and analysis/reporting dependents in dependency order and
run invariant/grain checks. Reporting's `jobs_detail.*` propagates final audit
fields on rebuild; Evidence explicit source lists remain unchanged intentionally.
