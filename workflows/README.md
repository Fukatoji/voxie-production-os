# Workflows

Declarative production workflow specifications and orchestration notes belong here.

Suggested groups:
- `productions/` — production-specific recovery, revision, and execution plans
- `image-generation/`
- `video-generation/`
- `audio/`
- `editing/`
- `publishing/`

A workflow should declare inputs, outputs, provider/tool assumptions, approval gates, spend limits when applicable, validation checks, and failure behavior. Publishing workflows must remain gated behind explicit authorization.
