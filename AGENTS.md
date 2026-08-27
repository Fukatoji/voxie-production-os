# Codex Operating Rules — Voxie Production OS

## Purpose
This repository is the executable control plane for Voxie's Wonder World production. Codex should treat repository data as instructions, schemas, manifests, validation logic, and reproducible workflow state—not as the primary storage location for large media binaries.

## Source-of-truth split
- GitHub/Codex: code, schemas, configuration, policies, manifests, workflow definitions, tests, QC logic, decision records, and handoff documents.
- ChatGPT Library / connected media storage: approved images, audio, video masters, shorts, covers, keyframes, and other large creative assets.
- A manifest should reference external media by stable asset ID, canonical filename, checksum, status, and storage location when available.

## Canon discipline
- Never promote a draft or alternate asset to canon implicitly.
- Preserve explicit statuses such as candidate, review, approved, locked, superseded, and non-canon.
- Locked canon may evolve only through a deliberate versioned change.
- Do not overwrite historical manifests; create a new version.

## Production safety
- Do not publish, spend credits, overwrite masters, or delete authoritative assets unless the current task explicitly authorizes it.
- Prefer deterministic, reversible operations.
- Keep generated outputs out of source control unless they are small fixtures required by tests or documentation.

## Repository placement
- `config/`: provider configuration, policies, spend gates, and environment-neutral settings.
- `schemas/`: machine-readable contracts.
- `src/`: executable Production OS implementation.
- `tests/`: automated validation and regression tests.
- `examples/`: small runnable examples and fixtures.
- `manifests/`: versioned production, asset, and distribution manifests.
- `workflows/`: declarative workflow specifications and orchestration notes.
- `handoff/`: ChatGPT/Codex/operator handoff records; no large media.
- `docs/`: architecture, decisions, runbooks, and operating documentation.

## Naming
Use descriptive, stable names. For production records prefer identifiers such as `VSW-W01-E01`, followed by artifact role and version. Avoid UUID-only filenames when a semantic name is known.

## Validation before completion
When changing production state, verify schema validity, referenced asset status, version lineage, and that no large media was accidentally added to Git history.
