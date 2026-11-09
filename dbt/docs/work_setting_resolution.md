# Work-setting resolution v2 (implementation, not deployed)

`analysis.jobs_detail` owns evidence construction and resolution inline. The
regex-only `work_setting_patterns()` macro returns the bounded pattern
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

V2 adds two transparent **low-confidence** fallbacks below all of those tiers:
`company_policy_inference` (**-1**) recognizes clear company-wide assertions such
as “we are a fully remote company” or “we operate a hybrid work model,” not menus,
offered options or benefits. `physical_duties_inference` (**-2**) infers Office
from current concrete patient procedures/bedside hospital care, aircraft work,
physical machinery or inmate-custody duties. Both preserve the original matched
excerpts with explicit `company_policy:` / `physical_duties:` sources. A neutral
false WFH flag (0) does not block fallback and never itself establishes Office.

Fallbacks cannot override affirmative role/title/tag/metadata evidence or a
strong Unknown conflict, alternative, temporal transition or remote prohibition.
Company assertions outrank physical-duty inference. No title-only nurse/pilot
inference is made. Duty fragments mentioning negation, prior experience, skills,
hypotheticals, training, software/simulations, telehealth or remote operation are
excluded. These are bounded first-version heuristics with known recall gaps and
possible false positives; low confidence is a provenance tier, not measured odds.
No missing-WFH/Unknown-to-Office default was introduced.

Explicit coverage also includes remote negation “not structured as a remote
position,” Hybrid title delimiters such as `(Hybrid - Seattle, WA)`, “Work
Location: In person,” office-based positions, role-context hybrid models and
remote opportunities. Numeric onsite schedules can pair with Friday WFH or a
numeric remote component, including across sentences; counts must remain
compatible and full/exclusive assertions do not get silently converted to Hybrid.

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
`li_tag_fallback`, `metadata_fallback`, `company_policy_inference`,
`physical_duties_inference`, `insufficient_evidence`, or
`conflicting_or_ambiguous_evidence`). `work_setting_metadata.conflict` applies only to
winning-strength ambiguity/contradiction, not all weaker disagreement.
`work_setting_metadata.confidence` is ordinal: high explicit, medium tag/metadata,
low company/duty inference or Unknown.
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

As validated for v2: 196 literal fixture cases passed, singular
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
The earlier JSON-output migration was checked against a pre-change read-only snapshot of
all 105 labels and complete rule/evidence/confidence/conflict values, including
evidence order, numbers, nulls and booleans. The harness accepts that snapshot via
`--previous-audit-snapshot <path>` for exact deep comparison. Native unit YAML
also has representative complete object expectations; the harness compares JSON
objects in Python because adapter-native JSON equality can be unsupported.

## V2 staged tuning diagnostics (not holdout accuracy)

The **same frozen 300 typed dimension rows** and untouched provisional annotations
from `52515fb` were scored using each actual compiled stage. All 300 are now
**tuning diagnostics**, not a holdout or human validation. Existing baseline
reports/labels/predictions were not changed. The source distribution and reference
policy caveats in the separate evaluation report still apply.

|Stage|Representative agreement|Representative Unknown|Challenge agreement|Challenge Unknown|
|---|---:|---:|---:|---:|
|Frozen baseline|99/200|153/200|57/100|54/100|
|Explicit coverage|107/200|150/200|62/100|53/100|
|+ Company inference|107/200|150/200|62/100|53/100|
|+ Physical inference|121/200|136/200|62/100|53/100|

Explicit changes moved 4 representative / 2 challenge Unknown rows to known;
all six agreed with provisional references, and corrected four / three previous
known predictions. Company inference activated on no rows in this cohort
(its behavior is exercised by fixtures). Physical inference added 14 low-confidence
representative Office assignments, all matching provisional references, with no
known-prediction changes; none activated on challenge rows. No previously correct
known prediction regressed in these diagnostics. Decisive errors remain 8/64
representative and 8/47 challenge, so coverage gain does **not** establish broad
precision or correctness. Per-tier confidence/disagreements and complete stage
snapshots are stored in the temporary `work-setting-expansion-bxk` artifacts.
The final candidate compiled SHA256 is `1815bf72...`.

An initial broader in-person match surfaced generic “if this position is listed
as remote ... occasions ... work in person” boilerplate in tuning diagnostics;
the final explicit stage excludes that non-role assignment and includes a
regression fixture. This is another reason these 300 cannot be reported as an
untouched holdout. Future blind pilot labels must be frozen before any further
tuning; do not reuse a revealed pilot as holdout accuracy.
A fresh 80-row blind pilot excluding all 300 tuning surrogate IDs was downloaded
read-only with full source context, but not labeled or scored by the builder.
The parent can independently freeze annotations before evaluating the recorded
final candidate. Exact-ID disjointness does not guarantee distinct underlying
vacancies or absence of reposts.

An independently supplied challenge-enriched snippet file included **10** judged
examples across five via labels (its metadata mentions a larger source sampling
pool). Qualitative SELECT checks agreed on nine; a BeBee team schedule described
as `hybrid model (3 days a week in our San Jose HQ)` remained Unknown. This is a
documented conservative recall gap, not an accuracy estimate. Snippets are not
full postings. The separate ~300 human-labelled review remains issue
`jobs-data-platform-3oi`.

Known v2 boundaries after adversarial QA:

- Non-weekly remote or onsite cadence is treated as ambiguous, not Remote/Hybrid/
  Office: monthly, quarterly or yearly day statements stay Unknown in both
  “work onsite 2 days per month” and lead “4 days onsite per month” forms.
  Weekly lead order (“4 days onsite per week”) remains Hybrid.
- Space-form alternatives such as “In person or remote”, “In person, or remote”,
  “In person; remote possible” and “In person (or remote)” stay Unknown.
  Semicolons between two setting words are normalized to “or” before fragmenting;
  all other semicolons split fragments like periods, so an unqualified onsite
  statement plus separate weekly home days stays Unknown.
- Office evidence ignores interview, application, recruiting, training,
  orientation/onboarding, conference and event logistics unless the same fragment
  also contains substantive or quantified office wording. Physical-duty inference
  also ignores employer/facility/third-party subjects such as “our hospital”,
  “our client hospitals”, “partner clinics” and “teams that …”. This is precision-
  first: duties stated only at a facility (“Administer injections at our clinic”)
  remain Unknown.
- Hybrid titles recognize delimiters such as “(Hybrid - Seattle, WA)”,
  “(Hybrid, Seattle, WA)”, “(Hybrid: Seattle)” and leading “Hybrid - …”, while
  technical titles such as “Hybrid Cloud Engineer” and “Hybrid, Electric Vehicle
  Systems Engineer” remain excluded. A mid-title “Data Engineer - Hybrid -
  Seattle” is not recognized.
- “4 days onsite and 1 day remotely” is recognized without the word “work”.
- A quantified office component is still required for the cross-sentence
  compatibility mix. “This role is onsite. Work from home on Fridays.” remains
  Unknown rather than inferred Hybrid.
- Company assertions remain narrow: “we are a fully remote company” and
  “we operate/use a hybrid work model”. “Remote-first company” and
  “we have a hybrid work model” remain Unknown (recall gaps, not mislabels).
- Deliberate limitation: “We operate a hybrid work model. #LI-Remote” resolves
  Remote from the LI tag; weaker company evidence does not create a conflict.

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
