# Introduced-history media safeguard v01

Recorded: **2026-08-30**  
Issue: **#33 — Inspect introduced Git history for tracked media blobs**  
Repository action: **Git safety correction / zero credits / no history rewrite**

## Corrected defect

The fixture safeguard previously inspected only the current Git index. A pull request could therefore add a prohibited or oversized media blob in one commit, delete it in a later commit, and leave the binary reachable in the proposed history while the final index appeared clean.

## New validation boundary

`voxie-os fixtures-check` now accepts `--base` and `--head` and performs two independent checks:

1. the existing staged-index and staged-policy validation; and
2. inspection of every blob introduced by `base..head`, including blobs no longer present in the final tree.

For every introduced media blob, the validator enforces:

- an exact approved fixture path;
- a regular-file mode for approved fixture content; and
- the configured maximum fixture size.

Unapproved media introduced and later deleted is still rejected. Existing Git history is never rewritten.

## CI correction

Production OS CI now resolves the pull-request base SHA or push `before` SHA and runs:

`voxie-os fixtures-check --base "$BASE" --head HEAD`

The checkout remains full-history with `fetch-depth: 0`.

## Regression coverage

Tests cover:

- unapproved media added and later deleted;
- a small approved fixture added and later deleted;
- an oversized approved fixture added and later deleted;
- simultaneous current-index and history validation;
- invalid revision ranges; and
- CLI range handling and fail-closed exit status.

## Safety

- Git history rewritten: **no**
- media added to Production OS: **no**
- provider execution: **none**
- credits spent: **0**
- canon, production, or publication state changed: **no**

The successor PR must remain open until protected-branch CI, a non-author approval, resolved conversations, and an explicit named-PR merge instruction are present.
