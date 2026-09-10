# Rainbow Colors YouTube private native-review handoff v01

Recorded at (UTC): **2026-09-10T02:34:24Z**  
Repository action: **versioned control-plane sync / zero credits / no media binaries / no public publication**

## Outcome

The separately authorized private upload-only native review is complete on the authenticated **Voxie's Wonder World** channel.

- Channel: `@VoxiesWonderWorld` (`UCWku_aFjx61hePgosuzzyvg`)
- Video ID: `2hfGiF27iM8`
- Video URL: `https://youtu.be/2hfGiF27iM8`
- Visibility: **Private / owner-only**
- Schedule: **unset**
- Public publication: **not authorized and not performed**
- Credits spent: **0**

The existing upload was resumed after its exact filename and destination were verified. No duplicate upload was created.

## Locked authority

| Role | Library ID | SHA-256 |
| --- | --- | --- |
| Master `VWF_RAINBOW_COLORS_FULL_MASTER_v02_APPROVED_LOCKED.mov` | `libfile_64109527eacc8191aa0ec53196960cc9` | `d105f6b89aa6a924cd72a2b1d3be5df28fb2483064e31a9e5087b5e45cadaef7` |
| Audio `VWF_RAINBOW_COLORS_AUDIO_MASTER_v01.1_APPROVED_LOCKED.wav` | `libfile_b84a335eaa248191a7692a956b264862` | `6c5919525c0f8b465ed6625dfd9a1d59adfe38f0cd33147f3c4f453bc9650fb0` |
| English VTT v01 | `libfile_7c28fe90ac6c8191b9af69e82d230f36` | `883ad68b5b9ae3f71fa117e1ad7c8c728960863b3bbc45b0aeeab0bdfcdee264` |
| Thumbnail S33 | `libfile_2362d07fa7908191bf95741940755c11` | `53a262287231e50a4356158a79e1a2151c3865136e0fc85d3784672f2c3fb283` |
| YouTube package v02 | `libfile_2d82c14bed008191bcfb54d623f8047a` | `1600290980012b099bbf15705f05af8cd1648a7faf02d75aef6ec026556bb481` |

Full native-review audit: `libfile_10bf43fb13e4819181f19b54bfee8244`.

## Platform state and QA

- Exact approved title, description, five chapters, eleven tags, and custom thumbnail are saved.
- Made for Kids is selected.
- Category is Education.
- Video and title/description languages are English (United States).
- Standard YouTube License and No paid promotion are saved.
- YouTube reports SD and HD processing complete.
- The private player exposes and renders 1080p at 1920x1080.
- Continuous native playback reached 2:30 / 2:30 without a transport or decode error.
- Original audio is the published track and the player was unmuted. This is a machine-observable transport check; no subjective human listening claim is made.
- The recovered locked WAV was freshly rehashed, and its decoded 24-bit PCM payload matches the locked master audio payload exactly (`f748533b2bc882fb0c8cddf2ddcc312642cf7b126b785fbcacbb831ebc33fe65`).
- The approved 32-cue manual English track displayed across the opening, color, quiz, counting, and closing beats.
- YouTube's generated automatic English track was deleted, leaving one published manual caption authority.
- Copyright and Community Guidelines checks report no issues.
- Opening S02-to-S03 frames preserved the six-color-light to six-stepping-pool sequence without an observed playback discontinuity.

## Counting synchronization QC

Result: **PASS** against the exact locked v02 master, locked WAV, approved locked marker map, and approved locked caption authority.

- `00:33.700–00:37.800`: the setup lyric “Count the colors one through six with me” plays over six ordered color pools; this is an invitation beat, not the sequential numeral build.
- `01:52.791667`: `1` appears over the red orb; one object is numbered.
- `01:54.375000`: `2` appears over the orange orb; two objects are numbered.
- `01:55.958333`: `3` appears over the yellow orb; three objects are numbered.
- `01:57.791667`: `4` appears over the green orb; four objects are numbered.
- `01:59.208333`: `5` appears over the blue orb; five objects are numbered.
- `02:00.583333`: `6` appears over the purple orb; all six objects are numbered.
- The complete `1–6` labels remain visible through `02:02.166667`, then clear for the refrain at the next 24-fps frame boundary.

No wrong numeral, wrong color-object association, skipped count, duplicate count, or reverse ordering was observed. This QC binds the observed picture frames to the already approved/locked lyric and marker authorities; it does not make a new subjective human-listening claim.

## Versioned control records

- `manifests/productions/rainbow-colors/production-state-v05.yaml`
- `manifests/distribution/rainbow-colors/release-readiness-v01.yaml`
- `manifests/control/authority-index-v02.yaml`
- `manifests/control/authority-content-lock-v02.json`

Historical v01-v04 production manifests and authority-index/content-lock v01 remain unchanged.

## Next permitted action

Do not retry or duplicate video ID `2hfGiF27iM8`. Obtain explicit authorization for the exact public visibility and either immediate release or a specific schedule. Public, Unlisted, Premiere, Schedule, and public Publish remain blocked.
