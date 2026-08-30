# Routing lineage and alignment-source integrity v01

Recorded: **2026-08-30**  
Issue: **#34 — Verify routing predecessor checksums and distinct alignment sources**  
Repository action: **lineage and evidence correction / zero credits / no BeatMap promotion**

## Library-routing correction

Versioned library-routing validation now resolves the declared predecessor inside the repository, verifies that it exists, hashes its exact bytes, and compares that digest with `supersedes.sha256`.

The existing predecessor version and filename checks remain active. A structurally valid but incorrect 64-character digest no longer passes validation.

## Alignment correction

The consensus builder now:

- requires unique `source_id` values across input documents;
- rejects duplicate `line_id` values within one source;
- counts distinct source documents for the minimum-source gate;
- reports `only N distinct source(s)` when evidence is insufficient; and
- preserves source-by-source evidence and review gates.

The CLI catches malformed alignment input and emits a controlled `FAIL` result rather than an uncaught traceback.

## Authority boundary

This change does not modify final BeatMap 001, any locked lyric timing, or any production audio. A clean consensus remains `PROVISIONAL`; human approval is still required before `HUMAN_REVIEWED` or `LOCKED` status.

## Regression coverage

Tests cover:

- exact current predecessor checksum validation;
- wrong predecessor checksum rejection;
- duplicate source IDs;
- duplicate line IDs within one source;
- one-source evidence failing a two-source gate;
- clean two-source provisional consensus; and
- controlled CLI failure for malformed duplicate input.

## Safety

- final BeatMap changed: **no**
- alignment promoted automatically: **no**
- library routing content changed: **no**
- provider execution: **none**
- credits spent: **0**
- media or publication state changed: **none**

The successor PR must remain open until protected-branch CI, a non-author approval, resolved conversations, and an explicit named-PR merge instruction are present.
