# Voxie Production OS

Version 0.1 is the first executable control-plane scaffold for Voxie's Wonder World production.

## What exists now

- Versioned canon schema
- Asset registry record schema
- Forced lyric/beat timing schema (BeatMap)
- Shot manifest schema with hold/keyframe/generated/hybrid motion modes
- Benchmark schema and benchmark summary logic
- Deterministic neutral timeline exporter
- Initial manifest QC rules
- CLI

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

## Benchmark summary

```bash
voxie-os benchmark-summary examples/benchmark.example.json
```

## Next build target

The next layer should ingest a real completed Voxie song and produce a BeatMap with lyric timestamps, confidence flags, beats, downbeats, and manual-review markers. After that, the same manifest can drive ComfyUI/Diffusers benchmarks and later OTIO/Premiere.
