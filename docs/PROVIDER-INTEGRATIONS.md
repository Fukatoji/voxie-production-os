# Provider integrations v0.3

This layer gives MagicLight, ElevenLabs, Higgsfield, and vidIQ one deterministic job contract. It does not store credentials, balances, media binaries, or browser sessions.

## Control flow

`provider job + catalog -> schema validation -> capability lookup -> asset-lineage validation -> budget check -> scoped approval gates -> provider execution -> provenance/QC record`

`provider-plan` stops before provider execution. A result of `READY_FOR_PROVIDER_EXECUTION` means the requested action is within its declared approval and budget; it does not mean the external action occurred.

Schema validation also runs inside the exported planner, so adapters cannot bypass the job and catalog contracts by calling the Python function directly.

Both schemas are checked before the planner reads job identities, looks up capabilities, validates lineage, or evaluates budgets and approvals. Schema-invalid inputs return an `INVALID_REQUEST` plan with `external_execution_authorized: false` and `execution_performed: false`. The plan retains its normal keys but leaves unvalidated metadata and lineage null, transport and approval lists empty, and the budget `NOT_EVALUATED`. Empty approval lists on this error result mean evaluation did not run; they never authorize work. Schema-valid requests with an unknown provider or unsupported operation continue to raise `ValueError`.

## Provider roles

| Provider | Production role | Read-only examples | Mutating examples |
| --- | --- | --- | --- |
| MagicLight | Character, visual, voice-emotion, and video workspace | Inspect account, list projects | Character preview, character lock, video generation |
| ElevenLabs | Voice and music generation | List voices | Voice preview, music generation, canonical voice registration |
| Higgsfield | Image and keyframe animation | Inspect account | Image generation, keyframe animation, conform |
| vidIQ | YouTube research and distribution assets | Channel audit, keyword research | Motion graphic, posting package |

## Safety model

- Creating media requires `CREATE_MEDIA`.
- Paid work additionally requires `CREDIT_SPEND` scoped to the exact provider and operation. Wildcards never authorize execution.
- A credit approval must cover `max_credits`, not merely the lower estimate. The maximum is the actual exposure boundary passed to a provider adapter.
- Shared schema validation rejects non-finite values in fields declared as numbers, including YAML `.nan`/`.inf` and Python NaN or infinity. Estimates, job maxima, and approval ceilings must be finite before any budget comparison; finite integers (including large Python integers) remain supported.
- Uploading character or shot references requires `ASSET_UPLOAD`.
- Canon changes require `CANON_LOCK`.
- Publishing and deletion gate types exist in the contract but no automatic publishing or destructive operation is enabled in the v1 catalog.
- Runtime connection state and balances are checked live and are never treated as repository truth.
- Only an `ACTIVE` catalog may authorize work. `EXECUTED`, `FAILED`, and `CANCELLED` jobs are terminal, and mutating jobs must be explicitly `APPROVED`.

## Asset lineage

Every provider job carries an `asset_lineage` block. Each input asset referenced by the job must appear exactly once with its stable asset ID, approved or locked status, version, and SHA-256 checksum. Extra or missing lineage entries fail closed. Asset-producing and canon-mutation operations must also declare the output asset ID and version before execution; read-only operations must declare no output. This keeps a provider result tied to exact reviewed sources rather than a regenerated approximation.

## Commands

```bash
voxie-os validate provider_catalog config/providers.v1.yaml
voxie-os validate provider_job examples/provider-job.higgsfield-animation.yaml
voxie-os provider-plan config/providers.v1.yaml examples/provider-job.vidiq-audit.yaml
```

The next execution step is provider-specific. Browser- or connector-backed adapters must record the returned provider asset ID, actual credits, output checksum, and QC state before an output can enter the asset registry.
