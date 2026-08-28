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
```

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
