# Voxie Production OS — Architecture v0.1

The Production OS is a control plane, not a single generator or NLE.

Flow:

`Canon + Asset Registry -> BeatMap -> Shot Manifest -> Generation Adapter -> QC -> Neutral Timeline -> NLE/Render Adapter -> Approval -> Publish`

## Design rules

1. Canon is versioned and machine-readable.
2. Generators are replaceable adapters.
3. Timings are deterministic contracts, not prompt prose.
4. Every generated asset records provenance and QC state.
5. Timeline representation stays neutral until the finishing adapter.
6. Paid generation, destructive writes, publishing, and canon promotion remain approval-gated.
7. Model promotion is benchmark-driven against locked Voxie shots.

## Planned adapters

- lyric-align / forced alignment -> BeatMap
- beat/downbeat detector -> BeatMap
- ComfyUI -> generation adapter
- Diffusers -> generation adapter
- LTX -> generation adapter
- Higgsfield/Picsart -> external generation adapters
- OpenTimelineIO -> interchange adapter
- Premiere UXP -> finishing adapter
- Remotion -> deterministic preview/render adapter
- YouTube / TikTok / Instagram -> publishing package + approval adapter
