# Big Surprise Multi-Aligner Evaluation v01

Date: **2026-08-29**  
Workspace: **05 — Research & Pipeline Development**  
Repository action: **executable evaluation specification / zero credits / no audio processing**

## Completed project

A provider-neutral comparison workflow now exists at:

`workflows/big-surprise-multi-aligner-evaluation-v01.yaml`

It formalizes the next timing experiment without changing final BeatMap 001.

## Comparison design

The evaluation compares four evidence paths:

1. Final BeatMap 001 as the locked timing baseline
2. AccurateScribe as the recorded transcription baseline
3. WhisperX as the local forced-alignment candidate
4. Yass Reloaded as the vocal pitch/energy-aware candidate

The ordered pipeline is:

`verify locked WAV → local vocal separation → WhisperX → Yass Reloaded → normalize adapters → compare baselines → build review-only confidence candidate → human-review exceptions`

## Historical focus

The plan explicitly targets the historical generic-transcription weakness from `59.690002` to `81.110000` seconds, a duration of `21.419998` seconds. The workflow states that this historical gap motivates the benchmark; it does not claim the final BeatMap lacks timing evidence there.

## Metrics

The workflow records targets for:

- lyric-line coverage
- unresolved historical-gap seconds
- median and p95 line-start error
- median line-end error
- human-review exception count

## Promotion boundary

The experiment cannot auto-promote an alignment result.

- BeatMap 001 remains authoritative.
- Lyric text changes are forbidden.
- Nonverbal cues require human review.
- Any successor requires explicit approval.
- Output is `REVIEW_ONLY` and may not replace BeatMap 001 directly.

## Current execution state

The specification is ready, but execution is blocked until the exact locked audio binary is mounted and its SHA-256 is verified.

- provider calls: **0**
- credits spent: **0**
- audio changed: **no**
- output artifact: **none**

## Validation

Regression tests verify:

- alignment-schema compatibility
- exact locked-audio lineage against final BeatMap 001
- explicit BeatMap, AccurateScribe, WhisperX, and Yass adapters
- existence of baseline artifacts
- blocked state for unexecuted candidate adapters
- historical-gap arithmetic and wording
- exact pipeline order and metric set
- fail-closed execution and no auto-promotion

CI directly validates the evaluation workflow.

## Next gate

Mount and verify the locked Big Surprise WAV in a controlled local environment, review local tool licenses and versions, then run the comparison. The resulting candidate must return through Production OS review before any timing authority changes.
