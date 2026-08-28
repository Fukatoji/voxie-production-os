# Repository Structure

This document defines the canonical layout of the Voxie Production OS repository. Git stores the versioned control plane—code, contracts, policies, workflows, manifests, and audit records. Large creative media stays in approved external storage and is referenced by manifests.

## Canonical layout

```text
voxie-production-os/
├── config/       Provider configuration, policies, and spend gates
├── schemas/      Machine-readable contracts
├── src/          Executable Production OS implementation
├── tests/        Automated validation and regression tests
├── examples/     Small runnable examples and fixtures
├── manifests/    Versioned asset, production, and distribution state
├── workflows/    Declarative workflows and orchestration notes
├── handoff/      Compact operator and system handoff records
├── docs/         Architecture, decisions, runbooks, and conventions
├── AGENTS.md
├── README.md
├── pyproject.toml
└── .gitignore
```

Only repository-wide entry points and toolchain files belong at the root. A root-level `productions/` directory is not part of the canonical layout.

## Directory responsibilities

### `config/`

Environment-neutral provider configuration, approval policies, spend gates, QC rules, and safe defaults. Never commit credentials, API keys, account cookies, or machine-specific paths.

### `schemas/`

Authoritative reusable contracts. Schemas define valid structure; they do not record a particular production's state.

### `src/`

Executable planners, validators, QC logic, reporting, adapters, command-line code, and reusable domain utilities.

### `tests/`

Deterministic unit, integration, regression, safety, and repository-layout tests. Tests must not spend credits, publish content, or depend on private media.

### `examples/`

Small illustrative inputs and fixtures. Examples are not authoritative production state.

### `manifests/`

Versioned records describing identity, provenance, lineage, approval state, storage references, and allowed use.

```text
manifests/
├── assets/          Canonical asset identity and lineage
├── productions/     Episode, song, shot, BeatMap, and master state
└── distribution/    Platform packages and release state
```

Preserve explicit states such as `candidate`, `review`, `approved`, `locked`, `superseded`, and `non-canon`. Never overwrite an approved or locked historical record; create a successor with explicit lineage.

The read-only change reporter classifies asset, production, distribution, and repository-level manifest records separately. Every non-README manifest change requires human review; final, locked, and master production records receive the stricter lock-gate classification.

### `workflows/`

Declarative production, recovery, editing, QC, and publishing processes. A workflow may describe an action but cannot silently grant spend, approval, canon promotion, or publication authority.

### `handoff/`

Compact continuity records between ChatGPT, Codex, and operators. Each handoff should identify status, evidence date, authoritative inputs, approved outputs, blockers, the next permitted action, and any required approval or spend gate. Multi-production summaries belong under `handoff/completion-batches/`.

### `docs/`

Architecture, decisions, provider guides, runbooks, status reports, and repository conventions. Documentation does not replace machine-readable state when automation depends on it.

## Placement guide

| Artifact | Canonical location |
| --- | --- |
| Provider or spend policy | `config/` |
| Machine contract | `schemas/` |
| Planner or validator | `src/` |
| Regression or policy test | `tests/` |
| Sample job or fixture | `examples/` |
| Approved production state | `manifests/productions/` |
| Character or environment identity | `manifests/assets/` |
| Posting or release package | `manifests/distribution/` |
| Recovery or execution plan | `workflows/productions/` |
| Operator continuity summary | `handoff/` |
| Multi-production completion summary | `handoff/completion-batches/` |
| Architecture or runbook | `docs/` |
| WAV, MP4, source image, or ZIP | External media storage |

## Change checklist

1. Place files by function, not extension.
2. Update internal references after a move.
3. Validate changed manifests and version lineage.
4. Preserve approved and locked history.
5. Run the relevant tests and repository-layout check.
6. Confirm no secrets, large media, caches, or generated outputs entered Git.
