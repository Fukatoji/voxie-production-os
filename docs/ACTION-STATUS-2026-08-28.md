# Technology actions — 2026-08-28

This record converts the technology-watch recommendations into controlled Production OS work.

## Implemented now

| Development | Action taken | Current boundary |
|---|---|---|
| lyric-align / WhisperX / Yass | Added a normalized multi-source consensus engine, audio-hash gate, timing-spread gate, evidence preservation, CLI, schema, and isolated benchmark workflow. | Challenger tools still need isolated installation and execution against the locked WAV. |
| ComfyUI 0.34 / Diffusers 0.40 / LTX Desktop 1.2 | Added one five-scenario benchmark suite with fixed seeds and required identity, composition, keyframe, four-wing, face, runtime, memory, cost, and output-hash fields. | No GPU is exposed in this runtime; no generation result is claimed. |
| OTIO | Added a real `.otio` writer using pinned OpenTimelineIO 0.18.1 and a round-trip test. | Media linking remains asset-registry driven. |
| Remotion | Added deterministic 16:9 or 9:16 frame-manifest output from the neutral shot manifest. | The Remotion render UI is not yet a production dependency. |
| Premiere UXP 26.3 | Added a deterministic transaction plan with stable marker GUIDs, track naming, sequence operations, and a closed export gate. | Execution requires Premiere 26.3 on the production PC. |
| GitHub PR activity | Added CI, production-impact classification, lock-gate detection, and a pull-request checklist. | CI is read-only; the ChatGPT webhook automation is separate. |

## Explicitly held

- PixVerse and other paid cloud benchmark runs remain blocked until a run-specific spend approval exists.
- Photoshop API v2 remains a later asset-preparation adapter. It is not allowed to become the orchestration layer.
- OpenCut remains watch-only until its editor API, MCP server, and headless renderer are released and testable.
- Unofficial Premiere MCP bridges remain non-canonical.

## Next executor handoff

1. Run `workflows/lyric-alignment-benchmark-v01.yaml` in an isolated CPU/GPU environment.
2. Run `workflows/voxie-model-benchmark-v01.yaml` on a GPU executor with locked anchor assets resolved from connected media storage.
3. Execute the generated Premiere transaction plan on Premiere 26.3 only after the UXP extension and preset path are installed.
