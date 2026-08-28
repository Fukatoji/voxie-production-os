# Voxie Production OS — Architecture v0.2

The Production OS is a control plane, not a single generator or NLE.

Flow:

`Canon + Asset Registry -> BeatMap -> Shot Manifest -> Generation Adapter -> QC -> Neutral Timeline -> NLE/Render Adapter -> Approval -> Publish`

The alignment and generation layers are evidence mergers, not authorities:

`AccurateScribe + lyric-align + WhisperX/Yass -> confidence consensus -> human exceptions -> BeatMap`

`ComfyUI + Diffusers + LTX + cloud challengers -> identical benchmark suite -> QC metrics -> human promotion review`

## Design rules

1. Canon is versioned and machine-readable.
2. Generators are replaceable adapters.
3. Timings are deterministic contracts, not prompt prose.
4. Every generated asset records provenance and QC state.
5. Timeline representation stays neutral until the finishing adapter.
6. Paid generation, destructive writes, publishing, and canon promotion remain approval-gated.
7. Model promotion is benchmark-driven against locked Voxie shots.

## Planned adapters

- lyric-align / WhisperX / Yass normalized evidence -> alignment consensus
- beat/downbeat detector -> BeatMap
- ComfyUI -> generation adapter
- Diffusers -> generation adapter
- LTX -> generation adapter
- Higgsfield/Picsart -> external generation adapters
- OpenTimelineIO -> interchange adapter (implemented)
- Premiere UXP -> deterministic transaction plan (implemented); desktop execution pending
- Remotion -> deterministic frame manifest (implemented); render project pending
- YouTube / TikTok / Instagram -> publishing package + approval adapter

## Promotion boundaries

- An alignment consensus may become `REVIEW_REQUIRED` or `PROVISIONAL`; only human approval may mark it reviewed or locked.
- A model benchmark may become `ELIGIBLE_FOR_HUMAN_PROMOTION_REVIEW`; it never promotes itself.
- Premiere batch export is disabled in generated plans until a separate approval is recorded.
- GitHub reports are read-only and never merge, publish, replace assets, or authorize spend.
