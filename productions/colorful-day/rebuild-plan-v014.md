# Voxie’s Colorful Day — v01.4 Recovery Rebuild Plan

Status: **PREPARED — BINARY RECOVERY REQUIRED**
Publishing: **NOT AUTHORIZED**

## Reason for rebuild preparation

The locked v01.3 master is fully documented in Production OS and File Library records, but the exact MP4 binary is not currently surfaced/mounted in the active production runtime for direct user review. Do not pretend the binary is present and do not overwrite the locked v01.3 authority.

## Protected authorities

- Existing locked master record: `VWF_COLORFUL_DAY_1080P_MASTER_v01.3_APPROVED_LOCKED.mp4`
- Existing master SHA-256: `b23fd47f3ad1f1da03b1e98cb79183e74ad362bdb0c2f7ea46eb8ea172dd83ea`
- Locked audio: `VWF_COLORFUL_DAY_AUDIO_MASTER_v01.1_APPROVED_LOCKED.wav`
- Locked audio SHA-256: `99a65be90a9d40f8c96ca8d1f3c575f9863937f93117d8c64f3764bf098a1320`
- Locked timing: `VWF_COLORFUL_DAY_38SHOT_MAP_v01_APPROVED_LOCKED.md`
- Picture basis: 14 approved keyframes, 38-shot deterministic still-motion assembly
- Runtime target: 190.000 s
- Output target: 1920×1080, 24 fps, H.264/AAC

## Recovery-first rule

1. Recover/mount the exact v01.3 MP4 if possible. If its SHA-256 matches the locked authority, surface it for review and cancel unnecessary reconstruction.
2. If the exact master cannot be recovered, recover the 14 approved keyframe binaries and exact locked audio.
3. Rebuild from those authorities using the locked 38-shot map and the same deterministic camera/parallax/pose-swap method.
4. Only if an approved keyframe binary is genuinely unavailable after recovery may a replacement still be generated. Every replacement must use current hard Voxie canon and reproduce the original shot purpose/environment; it becomes new REVIEW material.

## Version boundary

Any reconstructed or materially changed artifact is **not** v01.3. Name the first rebuilt review master:

`VWF_COLORFUL_DAY_1080P_MASTER_v01.4_REBUILD_REVIEW.mp4`

Do not promote it to locked status until full decode, timing, canon/four-wing, child-safety, black-frame, audio-integrity, and user playback review pass.

## Spend policy

Prefer recovery and deterministic rebuild. Paid generation is contingency only. Generated/native video audio remains off; the locked v01.1 soundtrack is the sole audio authority.
