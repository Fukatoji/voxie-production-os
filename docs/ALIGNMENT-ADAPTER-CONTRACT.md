# Alignment adapter contract

Every alignment adapter must emit one normalized JSON document before consensus. The source audio identity is mandatory; timing evidence from different audio hashes must never be merged.

```json
{
  "source_id": "WHISPERX-RUN-001",
  "adapter": "whisperx",
  "revision": "pinned-version-or-commit",
  "weight": 1.0,
  "audio": {
    "sha256": "64-hex-characters",
    "duration_s": 150.0
  },
  "lyrics": [
    {
      "line_id": "L001",
      "text": "Exact supplied lyric line",
      "vocal_start_s": 4.64,
      "vocal_end_s": 10.48,
      "confidence": 0.93,
      "manual_review": false
    }
  ]
}
```

Rules:

- `line_id` comes from the supplied exact lyric sheet, not from unconstrained transcription.
- Preserve the adapter's raw result outside Git when it is large; the normalized evidence belongs in the repository.
- Mark unresolved, invented, nonverbal, or low-confidence cues for review.
- Do not rewrite a locked BeatMap. Consensus produces a new provisional artifact for comparison.
- Record model and preprocessing revisions, including vocal separation, in `revision` or additional provenance fields.

Run:

```bash
voxie-os alignment-consensus examples/alignment-source.whisperx.example.json \
  examples/alignment-source.lyric-align.example.json \
  --id VOXIE-ALIGNMENT-DEMO --out alignment-consensus.json
voxie-os validate alignment alignment-consensus.json
```
