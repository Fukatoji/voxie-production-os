# Voxie’s Wonder Freeze Dance — V3 Selective Animation Prep

Status: **PREPARED FOR SELECTIVE-MOTION PILOT**
Base authority: **V2.1 hard-freeze/audio master**
Publishing: **NOT AUTHORIZED**
Generation spend in this prep step: **0 credits**

## Strategy

The compositor remains responsible for exact song timing and literal freeze holds. Generative video is used only in short movement windows immediately before selected round freezes. Each generated motion clip must end on the exact V2.1 freeze still so the edit can cut seamlessly into a deterministic hard hold.

Do not ask a video model to hold still. Do not generate audio. Do not use lip-sync or open-mouth singing.

## Prepared 6-second motion slots

| Round | Motion window | Start frame | Required end frame |
|---|---:|---|---|
| Tap | 61.83–67.83 | `TAP_START_61.83s.jpg` | `TAP_END_FREEZE_67.83s.jpg` |
| March | 83.15–89.15 | `MARCH_START_83.15s.jpg` | `MARCH_END_FREEZE_89.15s.jpg` |
| Reach | 105.24–111.24 | `REACH_START_105.24s.jpg` | `REACH_END_FREEZE_111.24s.jpg` |
| Wiggle | 127.18–133.18 | `WIGGLE_START_127.18s.jpg` | `WIGGLE_END_FREEZE_133.18s.jpg` |
| Sway | 149.00–155.00 | `SWAY_START_149.00s.jpg` | `SWAY_END_FREEZE_155.00s.jpg` |

## Connected storage

Picsart Drive folder: `Voxie’s Wonder World / Freeze Dance — V3 Animation Inputs`
Folder UID: `eea0e447-1805-4c9d-be87-1b543f60cd8b`

Uploaded pairs:

- Tap start UID `4da52d67-86ac-486a-8da9-65a8a2f5c012`; end UID `e7b55568-d151-41b2-893c-212d1b5e5c86`
- March start UID `fa334c3d-b1ee-4ae7-be60-c7ad2481a236`; end UID `b7baf9f3-7424-46db-88b9-35871047a14e`
- Reach start UID `6b4ea773-31c4-44cc-ba93-eaee48f467be`; end UID `dbb7ac10-e50e-444d-9352-70114aa10dfd`
- Wiggle start UID `cd1990d4-1064-4524-92db-3a4bb0d4bd6d`; end UID `cb55c384-2fdd-46f4-bebc-27bc2a96a30f`
- Sway start UID `6a28916c-f1cd-47a3-bb37-d612f85e930a`; end UID `9a79f944-437c-4754-9469-b4cb81858ea7`

## Hard canon gate

Every generated motion clip must preserve one canonical Voxie, exact visor/eyes/catchlights/brows/small mouth/V emblem/ear modules/chest diamond, white/dark-indigo armor, toddler proportions, and exactly four translucent lavender-blue-cyan wings. No open mouth, teeth, antennae, heart belly light, duplicate Voxie, redesign, or playground drift.

## Pilot order

Generate **Tap only first**, using start/end frame conditioning where supported. Target gentle knee taps and a controlled settle into the supplied freeze pose. QA identity, anatomy, four-wing topology, environment continuity, camera stability, and end-frame match before spending on March. Then proceed one at a time: March → Reach → Wiggle → Sway.

## Assembly rule

Replace only the approved 6-second motion interval in V2.1. Preserve all existing hard-freeze intervals and original song bytes/timing. If a motion candidate fails canon or endpoint continuity, reject it and retain the V2.1 still-motion section rather than forcing a bad generation into the master.
