# Benchmark suite completeness fix v01

Recorded: **2026-08-30**  
Issue: **#32 — Fail closed when benchmark scenarios or required metrics are incomplete**  
Repository action: **safety correction / zero credits / no model execution or promotion**

## Corrected defects

The benchmark evaluator previously received only `promotion_policy`, so it could not verify scenario coverage or scenario-specific required metrics. It also calculated `wing_count_error_rate` from the subset of samples that happened to contain the metric.

The corrected evaluator now receives the complete benchmark suite and fails closed when:

- the suite contract or scenario list is unavailable;
- any configured scenario is missing;
- a run contains an unknown scenario;
- a scenario sample lacks any metric declared by that scenario;
- a required metric is non-numeric or non-finite;
- any sample lacks a valid `wing_count_error` while the wing-rate gate is active;
- aggregate promotion thresholds fail; or
- output provenance is incomplete.

## Promotion boundary

Even a complete passing run returns only:

`ELIGIBLE_FOR_HUMAN_PROMOTION_REVIEW`

It always records `production_promoted: false`. No model, adapter, workflow, or provider is promoted by this change.

## CLI correction

`voxie-os benchmark-evaluate` now:

1. validates the benchmark run and full suite;
2. passes the full suite into the evaluator;
3. returns a nonzero status for incomplete or failing runs; and
4. preserves JSON evidence for review.

## Regression coverage

Tests cover:

- a complete five-scenario run;
- omitted required scenarios;
- unknown scenarios;
- missing scenario-required metrics;
- partially missing wing metrics;
- policy-only calls without a suite contract;
- CLI passing of the complete suite; and
- CLI rejection of the intentionally incomplete example run.

## Safety

- provider execution: **none**
- benchmark generation: **none**
- paid credits: **0**
- model or adapter promotion: **none**
- canon or production authority changed: **no**
- publication: **none**

The successor PR must remain open until protected-branch CI, a non-author approval, resolved conversations, and an explicit named-PR merge instruction are present.
