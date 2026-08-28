# Voxie Production OS

Version 0.3 adds approval-gated provider planning to the executable evaluation and interchange layer for Voxie's Wonder World production.

## What exists now

- Versioned canon schema
- Asset registry record schema
- Forced lyric/beat timing schema (BeatMap)
- Shot manifest schema with hold/keyframe/generated/hybrid motion modes
- Benchmark schema and benchmark summary logic
- Deterministic neutral timeline exporter
- Initial manifest QC rules
- CLI
- Multi-aligner lyric consensus with explicit disagreement gates
- Reproducible Voxie model benchmark suite and promotion scoring
- Real OpenTimelineIO export
- Deterministic Remotion manifests and Premiere UXP 26.3 transaction plans
- Read-only GitHub change-impact reporting and CI
- Approval-gated provider contracts for MagicLight, ElevenLabs, Higgsfield, and vidIQ

## Install locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e .
```

## Validate examples

```bash
voxie-os validate canon examples/canon.voxie.v1.yaml
voxie-os validate beatmap examples/beatmap.example.json
voxie-os validate shot_manifest examples/shot_manifest.example.yaml
voxie-os validate benchmark examples/benchmark.example.json
voxie-os validate library_routing manifests/library-routing.v2.yaml
```

## Library routing and media fixtures

The `library_routing` validator checks the routing structure, version lineage, and that `current_intake_status.unresolved_count` equals the length of `unresolved`. The CLI takes its schema choices from the shared schema registry; new validators are registered in one place (`SCHEMA_FILES`).

`manifests/library-routing.v2.yaml` quotes the snapshot date so PyYAML returns a string. It preserves the v1 routes and intake snapshot, with a `supersedes` reference containing the original manifest's version, path, and SHA-256. Historical `library-routing.v1.yaml` is unchanged; use v2 for schema validation. This representation change does not constitute a new asset audit or canon approval.

Production media remains ignored, including inside fixture directories. Only the exact `tests/fixtures/tone.wav` and `examples/fixtures/tone.wav` paths are allowed as optional small fixture files by `config/media-fixtures.v1.json` and `.gitignore`; no binary fixtures are included by this change. New exceptions require a deliberate update to both files. Subtree and wildcard exceptions are prohibited.

After staging changes, run:

```bash
voxie-os fixtures-check
```

This read-only check uses the Git index and staged policy: listed fixtures must be regular files no larger than **65,536 bytes (64 KiB)**, and unlisted tracked media is rejected even if force-added. CI runs this check along with routing validation. Git ignore patterns cannot enforce file size, so an oversized file at an allowed path may be staged, but the checker and CI reject it. Resizing the working copy or editing an unstaged policy does not bypass the check. Large media belongs in external storage and should be referenced by manifest.

## Run QC

```bash
voxie-os qc examples/canon.voxie.v1.yaml examples/shot_manifest.example.yaml --out qc-report.json
```

## Build a neutral timeline

```bash
voxie-os timeline examples/shot_manifest.example.yaml --out timeline.json
```

Build real OTIO, Remotion, and Premiere-controller artifacts from the same shot manifest:

```bash
pip install -e '.[timeline]'
voxie-os timeline examples/shot_manifest.example.yaml --format otio --fps 30 --out timeline.otio
voxie-os timeline examples/shot_manifest.example.yaml --format remotion --fps 30 --out remotion.json
voxie-os timeline examples/shot_manifest.example.yaml --format premiere --fps 30 --out premiere-plan.json
```

## Merge lyric-alignment evidence

Normalize each aligner result to the source contract, then merge without hiding conflicts:

```bash
voxie-os alignment-consensus whisperx.json lyric-align.json \
  --id VWF-SONG-ALIGN-001 --out alignment-consensus.json
```

The consensus result is provisional by construction. Audio hash mismatches fail; timing and text disagreement create review gates.

## Benchmark summary

```bash
voxie-os benchmark-summary examples/benchmark.example.json
voxie-os benchmark-evaluate examples/benchmark.example.json workflows/voxie-model-benchmark-v01.yaml
```

## Current execution boundary

The code and contracts are runnable here. LTX, ComfyUI, Diffusers, WhisperX/Yass, and Premiere execution still require their own isolated GPU/desktop environments. The repository records those results; it does not promote a model, export a master, spend credits, or publish automatically.

Provider jobs are evaluated the same way:

```bash
voxie-os provider-plan config/providers.v1.yaml examples/provider-job.vidiq-audit.yaml
```

See `docs/PROVIDER-INTEGRATIONS.md` for the four-service capability matrix and approval model.

## Repository layout

See [`docs/REPOSITORY-STRUCTURE.md`](docs/REPOSITORY-STRUCTURE.md) for the authoritative placement, naming, versioning, and media-boundary rules.

- `config/` — provider configuration, policies, and spend gates
- `schemas/` — machine-readable contracts
- `src/` — executable Production OS implementation
- `tests/` — automated validation and regression tests
- `examples/` — small runnable examples and fixtures
- `manifests/` — versioned asset, production, and distribution state
- `workflows/` — declarative workflows and orchestration notes
- `handoff/` — compact ChatGPT, Codex, and operator handoffs
- `docs/` — architecture, decisions, runbooks, and conventions

Large media remains outside Git and is referenced from manifests by stable identity and storage metadata.
