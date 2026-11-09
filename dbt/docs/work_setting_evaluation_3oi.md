# Work-setting evaluation: frozen baseline 52515fb

## Status and restrictions

Evaluation only. No classifier fixes, tuning, deployment, or commits were performed.
Issue `jobs-data-platform-3oi` remains pending human adjudication. Do not interpret
the results below as validated accuracy or production approval.

Classifier commit: `52515fbf2977ee38f741f0ed2185bfcc839f7edd`.

## Sample and reference labels

- Population: 169,470 hydrated, earliest-observation dimension rows, preserving
  the current dimension grain. This is not a deduplicated count of real vacancies.
- Representative group: 200 deterministic uniform samples, not source-quota
  stratification. Source counts are available in the full report.
- Challenge group: 100 disjoint, deliberately enriched cases. Do not pool this
  group with the representative sample to estimate population performance.
- Six independent agent reviewers labelled 50 records each before seeing model
  predictions. Full original descriptions and source inputs were available.
- Labels are provisional agent judgments, NOT human-adjudicated ground truth.
  Original labels were frozen before comparison, with no post-reveal relabeling.
- 300 unique sample IDs aligned across inputs, labels, and predictions. All 470
  supporting quotations matched original source substrings.
- Native LinkedIn ingestion has zero representative samples and ten challenge
  samples; no representative native-LinkedIn precision estimate is supported.

## Results against provisional labels

| Measure | Representative (200) | Challenge (100) |
| --- | ---: | ---: |
| Agreement with provisional reference | 99/200 (49.5%) | 57/100 (57.0%) |
| Predicted Unknown | 153/200 (76.5%) | 54/100 (54.0%) |
| Model conflict flag | 6/200 (3.0%) | 12/100 (12.0%) |
| Non-Unknown disagreements / assigned non-Unknown | 12/47 (25.5%) | 11/46 (23.9%) |
| Non-Unknown disagreements / all sample rows | 12/200 (6.0%) | 11/100 (11.0%) |
| Unknown where reference assigned a setting | 89 | 32 |

Representative predicted-class precision against provisional references:
Office 6/11, Hybrid 5/6, Remote 24/30. These small denominators and unresolved
annotation differences do not support a validated accuracy claim.

## Findings to review before any fixes

1. **Recurring hybrid schedules classified as Office.**
   - `3oi-130` (representative): “Must work onsite in Boston 4 days a week,
     every week. Work from home on Fridays.” Predicted Office; reference Hybrid.
   - `3oi-290` (representative): “must work onsite for 4 days and 1 day remotely.”
     Predicted Office; reference Hybrid.
2. **Role-specific remote negation classified as Remote.**
   - `3oi-093` (challenge): the posting requires “consistent in-person presence”
     and “is not structured as a remote position.” Predicted Remote with high
     model confidence. This is a challenge finding, not a population error rate.
3. **Explicit arrangement labels missed.**
   - `3oi-127` (representative): “Work Location: In person” becomes Unknown.
   - `3oi-219` (representative): title includes “(Hybrid - Seattle, WA)”, but
     weaker WFH metadata yields Remote.
4. **Reference-label consistency needs human adjudication.** Some Office labels
   infer attendance from physical duties or location, while other reviewers
   require an explicit attendance statement. Do not count every Office→Unknown
   disagreement as a confirmed classifier defect. Reviewer confidence does not
   remove this problem.

Independent QA inspected 25 disagreements and 10 matches, reproduced all four
reported confusion matrices, and approved reporting the findings with these
caveats. QA did not approve deployment or validated-accuracy claims.

## Reproducibility and next decision

The evaluation executes the actual frozen compiled model SQL, not a duplicate
classifier. Successful sampling scanned 1,770,767,786 bytes; scoring scanned
6,318,900 bytes. Queries were SELECT-only with individual 2 GB caps. A failed
memory-exceeded sampling attempt is recorded separately in the artifacts.

Artifacts are local (not committed raw job data) at:

`/private/var/folders/2j/nf16mczs707fw1_p3d4qq0sr0000gn/T/opencode/work-setting-evaluation-3oi-52515fb/`

Key files: `evaluation_report.md`, `evaluation_report.json`, `review_sheet.csv`,
`candidate_disagreements.json`, `evaluation_inputs_lock.json`,
`qa_evaluation_note.md`, `design.json`, sampling/scoring SQL, and the repeatable
`evaluate.py` runner. Original blind inputs, label batches, and predictions are
retained separately. Temporary artifacts should be retained elsewhere by the
operator if long-term raw-sample retention is required.

Next: review confirmed errors and adjudicate the Office-label boundary with the
user. Do not fix or tune rules until the user has reviewed this report and
authorizes changes. No holdout-based improvement claim is made: no tuning has
occurred, and a future evaluation split must be fixed before tuning.
