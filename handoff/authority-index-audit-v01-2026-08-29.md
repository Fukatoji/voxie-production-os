# Authority-index coverage audit v01

Recorded: **2026-08-29**  
Repository action: **control-plane drift detection / zero credits / no production or publication action**

## Completed project

The canonical authority index now has a deterministic completeness audit rather than validating only the entries already present in the index.

New CLI command:

```text
voxie-os authority-audit manifests/control/authority-index-v01.yaml
```

## Discovery policy

The audit discovers canonical control records through explicit repository patterns covering:

- library-routing versions
- asset manifests
- character-status registers
- distribution release-readiness records
- final BeatMaps
- shot manifests
- review masters and final-review records
- locked master-status records
- production-state versions
- provider catalogs
- executable workflow specifications

Examples, handoffs, documentation, tests, and media binaries are excluded.

## Coverage model

A discovered authority must be represented as either:

1. a current authority-index entry, or
2. explicit predecessor evidence on a current entry.

The audit fails when:

- a discovered authority is absent from both current and predecessor coverage
- an indexed current or predecessor path falls outside the declared discovery policy
- a path is simultaneously current and predecessor evidence
- the authority index itself is invalid

## First-run findings and correction

The first CI run found two genuine control records that the original index had missed:

- `manifests/productions/humpty-rolling-short-film/review-master-v01.json`
- `workflows/lyric-alignment-benchmark-v01.yaml`

Both were added as current, publication-blocked authorities. Discovery was not weakened and neither record was promoted beyond its existing review or blocked execution state.

## Current expected state

The v01 index now contains 18 current authorities and four predecessor records. Together they cover all 22 discovered control-authority paths.

## CI and regression scope

Production OS CI now runs the coverage audit after schema and nested authority-index validation. Regression tests cover current completeness, explicit control-plane-only discovery, newly discovered unindexed records, indexed paths outside policy, missing predecessor coverage, and machine-readable CLI output.

## Safety

- authority state changed beyond indexing existing evidence: **no**
- media generated or modified: **none**
- provider execution: **none**
- publication or scheduling: **none**
- credits spent: **0**

The project detects index drift only; it does not auto-promote newly discovered records.
