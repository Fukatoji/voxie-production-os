# Manifests

Versioned machine-readable production state belongs here.

Recommended groups:
- `assets/` — asset identity, checksum, status, and storage references.
- `productions/` — episode/song/short shot and production manifests.
- `distribution/` — approved platform packaging records; publishing remains a separate authorized action.

Rules:
- Never overwrite an approved historical manifest.
- Prefer semantic production IDs over UUID-only names.
- Reference large media externally rather than committing binaries.
