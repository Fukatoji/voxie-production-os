# Dedicated character-status validation v01

Recorded: **2026-08-29**  
Repository action: **canon-control hardening / zero credits / no character generation**

## Completed project

The canonical character status register now has a dedicated `character_status` contract instead of relying on the broader generic canon schema.

Controlled register:

`manifests/characters/status-register-v01.yaml`

## New contract

`schemas/character_status.schema.json` requires:

- register identity, state, date, and authority scope
- exactly the four canonical status categories
- structured character identity, lock level, production-use state, references, forbidden assets, and next gate
- structured provider authority, parked alternatives, historical branches, and blockers where present

## Cross-field safeguards

The Production OS validator now enforces:

- a real register date
- unique character IDs
- repository-local, existing reference assets with path-traversal protection
- `LOCKED_CANON` requires hard lock, `ALLOWED_WITH_LOCK`, and at least one repository authority
- a recorded provider authority for locked canon must have QC `PASS`
- only locked canon may be production-allowed
- `APPROVED_BUT_UNLOCKED` remains blocked until preview lock and must retain blockers
- `NEEDS_RECONCILIATION` remains blocked, requires at least two uniquely identified historical branches, and must retain blockers
- parked alternatives may never replace locked canon

## Current controlled decisions remain unchanged

- Voxie remains locked canon and linked to the MagicLight asset authority.
- Lumi remains approved but unlocked and blocked from production use.
- Navi and Humpty remain unreconciled, with their two historical production branches preserved separately.
- Bubble Voxie remains parked and non-substitutable.

## CI and regression scope

CI now validates the status register directly as a `character_status` artifact. Regression tests cover schema registration, date validity, unique character IDs, locked-canon requirements, provider QC, nonlocked production use, branch uniqueness/status, repository-reference existence and containment, and parked-alternative substitution.

## Safety

- character media generated or modified: **none**
- locked traits changed: **no**
- parked alternatives promoted: **no**
- production use broadened: **no**
- credits spent: **0**

This project changes validation strength only. Existing character decisions remain authoritative.
