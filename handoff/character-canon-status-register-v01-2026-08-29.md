# Character Canon Status Register v01

Date: **2026-08-29**  
Workspace: **01 — Character Canon & Brand**  
Repository action: **status-authority completion / zero credits / no media binaries**

## Completed project

The first canonical character status register now separates the four priority characters into explicit operating states:

- **Voxie — LOCKED_CANON**
- **Lumi — APPROVED_BUT_UNLOCKED**
- **Navi — NEEDS_RECONCILIATION**
- **Humpty — NEEDS_RECONCILIATION**

Canonical path:

`manifests/characters/status-register-v01.yaml`

## Authority boundaries

### Voxie

Voxie’s locked MagicLight reusable authority is linked directly to:

`manifests/assets/voxie-canon-v1.0.magiclight.yaml`

The register preserves reusable asset ID `7498224955395878912`, preview task ID `7499108870617059328`, hard-QC PASS, and the locked four-wing identity. Bubble Voxie remains a parked alternative and may not replace the locked authority.

### Lumi

Lumi’s approved name, role, personality, and design profile are recorded, but production use remains blocked until a provider preview is approved and locked. No asset ID, preview, or reference package is invented.

### Navi and Humpty

Both characters retain two established historical production branches. The register prevents silent cross-branch merging and blocks global production use until an explicit reconciliation or separate-character decision.

## Validation

Regression tests verify:

- schema compatibility with the canonical character contract
- the required four-character starting set
- exact Voxie provider lineage against the locked asset manifest
- fail-closed Lumi status
- two-branch preservation for Navi and Humpty
- no unlocked or unreconciled character is marked production-allowed

CI directly validates the register.

## Safety

- character pixels generated or modified: **none**
- credits spent: **0**
- locked traits changed: **no**
- parked alternatives promoted: **no**
- production assets substituted: **no**
- publication: **none**

## Next gates

- Lumi: create a preview, review it, then require explicit lock approval.
- Navi: reconcile branches or designate separate characters.
- Humpty: reconcile branches or designate separate characters.
- Voxie: continue using the locked authority only.
