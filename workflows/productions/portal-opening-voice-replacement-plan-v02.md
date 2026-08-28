# Voxie Portal Opening / Episode 1 — Voice Replacement Plan v02

Status: **PREPARED — VOICE AUDITION REQUIRED**
Picture authority: `Voxie_Portal_Opening_HQ_MASTER.mp4`
Publishing: **NOT AUTHORIZED**

## Objective

Correct Voxie’s dialogue voice without rebuilding or degrading the 99-second HQ picture master.

## Core method

Do **not** use AI vocal isolation on the mixed master unless no clean components exist. The connected Portal workspace already contains scene-by-scene dialogue stems, instrumental music, and scene SFX. Use those assets to reconstruct the soundtrack with the old dialogue omitted, then insert newly rendered Voxie dialogue at the original line timings.

This preserves picture quality and avoids vocal-removal artifacts.

## Existing timing/reference assets

Workspace: `Marc - AI Agent / Voxie Portal Opening Script Summary`

- `Dialogue_Scene01.wav` … `Dialogue_Scene10.wav` plus available v2 variants: timing/reference only for voice replacement
- `Instrumental_extended_124s.mp3`
- `Instrumental_underscore_-_full_opening-generate_audio.mp3`
- scene SFX S1–S10 and later simplified SFX references
- HQ picture master: `Voxie_Portal_Opening_HQ_MASTER.mp4`

The existing dialogue stems must not be treated as the new voice authority; they are alignment evidence for line placement, duration, pauses, and mix interaction.

## Voice authority boundary

No Portal replacement voice is globally locked by this plan. The next voice must first be an audition/review asset. Do not silently promote Leda, Kore, Sulafat, Aoede, any generic connected voice, or any other historical candidate as canonical.

The current leading finalist from the prior voice audition may be tested as a **review candidate only**. Do not clone a licensed preset voice. Generate it through its licensed provider/preset where available.

## Safe execution sequence

1. Recover the exact spoken wording and line timing for Scene 1 from existing script/dialogue evidence.
2. Render **one Scene 1 replacement line** in the chosen review voice.
3. Build a Scene 1 A/B review over the real Portal picture and reconstructed music/SFX bed.
4. QA: perceived age, warmth, energy, intelligibility, preschool pacing, fit with Voxie, line duration, and mix headroom.
5. Only after user voice approval, generate the remaining scene dialogue using the same exact voice/preset/version.
6. Reconstruct the complete 99-second soundtrack from instrumental + SFX + approved replacement dialogue.
7. Mux with the untouched HQ picture master.
8. Output first full replacement review as `VWF_PORTAL_OPENING_EP1_HQ_VOICE-REPLACEMENT_v02_REVIEW.mp4`.
9. Full decode/listening/QC and user playback approval are required before any lock promotion.

## Important non-substitution rule

If the selected finalist voice is not exposed through the currently connected voice-generation tool, stop at the audition-prep gate rather than substitute another voice. Obtain/export the line from the licensed provider and continue deterministic assembly from that exact file.

## Picture lock

No visual regeneration, resize, reframe, timing change, or new character animation is required for this voice correction. Keep the HQ picture bytes/timing as the visual authority throughout the review path.
