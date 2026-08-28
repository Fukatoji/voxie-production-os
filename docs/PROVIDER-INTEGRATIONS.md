# Provider integrations v0.3

This layer gives MagicLight, ElevenLabs, Higgsfield, and vidIQ one deterministic job contract. It does not store credentials, balances, media binaries, or browser sessions.

## Control flow

`provider job -> schema validation -> capability lookup -> budget check -> scoped approval gates -> provider execution -> provenance/QC record`

`provider-plan` stops before provider execution. A result of `READY_FOR_PROVIDER_EXECUTION` means the requested action is within its declared approval and budget; it does not mean the external action occurred.

## Provider roles

| Provider | Production role | Read-only examples | Mutating examples |
| --- | --- | --- | --- |
| MagicLight | Character, visual, voice-emotion, and video workspace | Inspect account, list projects | Character preview, character lock, video generation |
| ElevenLabs | Voice and music generation | List voices | Voice preview, music generation, canonical voice registration |
| Higgsfield | Image and keyframe animation | Inspect account | Image generation, keyframe animation, conform |
| vidIQ | YouTube research and distribution assets | Channel audit, keyword research | Motion graphic, posting package |

## Safety model

- Creating media requires `CREATE_MEDIA`.
- Paid work additionally requires `CREDIT_SPEND` scoped to the exact provider, operation, and sufficient credit ceiling.
- Uploading character or shot references requires `ASSET_UPLOAD`.
- Canon changes require `CANON_LOCK`.
- Publishing and deletion gate types exist in the contract but no automatic publishing or destructive operation is enabled in the v1 catalog.
- Runtime connection state and balances are checked live and are never treated as repository truth.

## Commands

```bash
voxie-os validate provider_catalog config/providers.v1.yaml
voxie-os validate provider_job examples/provider-job.higgsfield-animation.yaml
voxie-os provider-plan config/providers.v1.yaml examples/provider-job.vidiq-audit.yaml
```

The next execution step is provider-specific. Browser- or connector-backed adapters must record the returned provider asset ID, actual credits, output checksum, and QC state before an output can enter the asset registry.
