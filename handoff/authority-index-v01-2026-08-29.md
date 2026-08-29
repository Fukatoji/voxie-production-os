# Canonical authority index v01

Recorded: **2026-08-29**  
Repository action: **control-plane consolidation / zero credits / no production or publication action**

## Completed project

The repository now has one machine-readable index of the current canonical control records across character canon, active productions, distribution, provider planning, library routing, and R&D workflows.

Canonical path:

`manifests/control/authority-index-v01.yaml`

The index deliberately references control records rather than media binaries and does not index itself, avoiding recursive self-authority.

## Indexed authority classes

The v01 index covers 16 current authorities:

- canonical library routing
- locked MagicLight Voxie asset
- priority-character status register
- Big Surprise final BeatMap, shot manifest, review master, and release-readiness gate
- Freeze Dance review master, final-review record, and release-readiness gate
- Colorful Day locked master status and release-readiness gate
- Rainbow Colors production-state v04 and its predecessor lineage
- provider catalog
- model benchmark workflow
- Big Surprise multi-aligner workflow

## New contract

`schemas/authority_index.schema.json` requires:

- stable index identity, state, date, repository, and default branch
- explicit control policy
- typed authority entries with project, path, state, current flag, execution scope, publication state, and source-of-truth purpose
- optional validation kind and predecessor lineage

## Cross-field safeguards

The Production OS validator now enforces:

- a real index date
- unique authority IDs and paths
- current-only entries when the index policy requires them
- repository-local, existing current and predecessor paths with path-traversal protection
- no media-binary paths
- no self-predecessor relationship
- publication authority only for `RELEASED` entries
- recursive validation of every referenced structured artifact that declares a validation kind

This means the index cannot remain green while an indexed BeatMap, shot manifest, production state, release-readiness record, character register, asset record, provider catalog, library-routing record, benchmark suite, or alignment workflow becomes invalid.

## Authority interpretation

The index does not change underlying decisions. It exposes them consistently:

- locked or final authority remains locked or final
- review and blocked records remain non-executable where recorded
- no entry is publication-authorized
- predecessor records remain evidence, not current authority
- media remains outside Git

## Safety

- media generated or modified: **none**
- authority promoted or replaced: **none**
- publication or scheduling: **none**
- provider execution: **none**
- credits spent: **0**

The project consolidates discovery and validation only.
