# Dedicated release-readiness validation v01

Recorded: **2026-08-29**  
Repository action: **control-plane hardening / zero credits / no publication**

## Completed project

Release-readiness records no longer rely on the permissive generic QC-report schema. A dedicated `release_readiness` contract now validates the shared release-control invariants for:

- Voxie’s Big Surprise
- Voxie’s Wonder Freeze Dance
- Voxie’s Colorful Day

## New contract

`schemas/release_readiness.schema.json` requires:

- stable report and project identifiers
- explicit `record_type: release_readiness`
- master authority, controlled filename, SHA-256, runtime, format, codecs, and audio-preservation state
- root release status
- release-gate authorization flags, required approvals, and blockers
- platform package state and upload/publication flags
- structured findings
- a next permitted action

## Cross-field safeguards

The Production OS validator now rejects a release record when:

- approvals or blockers remain but execution, publication, scheduling, account writes, upload, or platform publication is authorized
- platform names are duplicated
- a platform is upload-authorized while account writes are unauthorized
- a platform is publish-authorized while root publication is unauthorized
- a blocker lacks a matching warning or error finding
- a referenced master, final-review, timing, or distribution-authority file does not exist in the repository
- a record claims `RELEASED` without root and platform publication authority

## Record normalization

Freeze Dance and Colorful Day retain their existing authority and blocker sets. Their findings were expanded so every blocker has an explicit warning record. No release gate was removed or weakened.

## CI and regression scope

CI now validates all three records directly as `release_readiness` artifacts. Regression tests cover schema registration, controlled-record validation, unresolved-gate authorization attempts, missing blocker findings, missing repository references, duplicate platforms, and invalid released-state claims.

## Safety

- media generated or modified: **none**
- metadata or thumbnails invented: **no**
- publication or scheduling: **none**
- account writes: **none**
- credits spent: **0**

The project changes validation strength only. Existing production and publication decisions remain unchanged.
