# Authority content lock v01

Recorded: **2026-08-29**  
Repository action: **cryptographic control-plane integrity / zero credits / no production or publication action**

## Project purpose

The canonical authority index establishes which control records are current. This project adds a separate deterministic SHA-256 lock establishing the exact bytes of that current authority set.

## Lock model

The generated lock records:

- the authority-index ID, repository path, and SHA-256
- one entry for every current authority ID and path
- the SHA-256 of each referenced control record
- deterministic entry ordering by authority ID
- the exact entry count

The lock deliberately excludes itself and is not treated as a production authority, avoiding recursive self-hashing.

## Commands

```text
voxie-os authority-lock-build manifests/control/authority-index-v01.yaml --out authority-lock.json
voxie-os authority-lock-verify manifests/control/authority-index-v01.yaml authority-lock.json
```

## Fail-closed verification

Verification fails when:

- the lock does not satisfy its schema
- the authority index is invalid
- index identity, path, or SHA-256 differs
- lock entry count or deterministic ordering differs
- authority IDs or paths are missing, unexpected, duplicated, or remapped
- any current authority file is missing, outside the repository, or has changed bytes

## Operational effect

Once the committed lock is installed in CI, any change to an indexed authority or to the index itself must update the lock in the same reviewed pull request. Schema-valid but unreviewed byte drift will no longer pass.

## Safety

- authority status changed: **no**
- media generated or modified: **none**
- provider execution: **none**
- publication or scheduling: **none**
- credits spent: **0**

This is an integrity-control project only.
