# Rainbow Colors S01–S03 production-state sync

Recorded at (UTC): **2026-08-29T02:05:56Z**  
Local production date: **2026-08-28**  
Production timezone: **America/Chicago**  
Production: **Voxie's Rainbow Colors**  
Repository action: **record-only / zero credits / no media binaries**

## Audit convention

Production-state records use an exact RFC 3339 UTC timestamp ending in `Z`. When an operating-day boundary matters, the record also carries the corresponding local production date and IANA timezone. The schema verifies that the UTC timestamp resolves to the stated local date.

## Durable production decisions recorded

- The active shot map is **v01.1**, locked, with 37 shots; locked v01 remains its predecessor.
- The 150.000-second audio remains locked and byte-preserved. Its canonical filename is not recorded here and must not be guessed.
- S01 opening keyframe v01 and Wonder Light glow-reveal v01 are locked.
- S02 is the locked six-color-lights shot with no character; motion v04 is locked and the legacy Voxie S02 is parked.
- S03 stepping-pools KF-A v01 is the active locked source.
- The newer six-light S03 image is a parked alternate and cannot replace the locked stepping-pools source.
- The S01–S02 transition v01 remains review-only because no later lock decision is recorded here.
- No full-length final master is recorded as complete.

## Authority boundary

This manifest is **valid production-decision authority** for the states listed above. It is **not executable media authority**.

Execution that reads, ingests, assembles, renders, transforms, or otherwise uses the S01–S03 media binaries remains **BLOCKED** until both of the following are captured from authoritative external storage and verified:

1. Stable external asset IDs for every required S01–S03 source.
2. Matching SHA-256 checksums keyed to those asset IDs.

A `LOCKED` production decision must not be interpreted as proof that the referenced media binary has been located or integrity-verified. Identifiers and checksums must not be invented. Zero-cost planning or record maintenance that does not consume those unverified binaries may continue.

## Standing continuation gate

Work after S03 may continue only through deterministic, zero-cost operations using approved or locked sources whose lineage is available and verified. Every applicable QC gate must pass. Work stops on any credit requirement, provider generation or new-pixel requirement, missing approved source, missing required lineage, canon or lock conflict, non-PASS result, audio alteration, publishing action, or new creative decision.

S07, S08, and S27–S29 timing must remain unchanged.

## Spend and balance boundary

The quoted 2,300-credit generation is not authorized. Before any later spend decision, reconcile the displayed 86,395 balance against the recorded 86,305 post-generation balance. The verified discrepancy is 90 credits. This record spends **0 credits** and grants no publishing, provider, or merge authority.

## Validation added in this PR

- `schemas/production_state.schema.json` defines the machine-readable contract.
- `production_state` is registered with the Production OS validator and CLI.
- CI validates the Rainbow Colors production-state manifest directly.
- Regression tests enforce timestamp/local-date consistency, balance reconciliation, pending-lineage execution blocking, and exact asset-ID/checksum mapping for verified lineage.

## Repository effect

This sync changes text-only control-plane records, schema validation, tests, and CI coverage. It does not generate or commit media, execute a provider, spend credits, modify locked audio or sources, change canon, publish content, or authorize merge.
