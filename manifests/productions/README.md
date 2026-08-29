# Production manifests

Store versioned episode, song, short, shot, BeatMap, assembly, and master state here. Historical approved or locked records are immutable; changes require a successor with explicit lineage.

## Audit timestamp convention

Production-state manifests use `recorded_at_utc` as an exact RFC 3339 UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ` form. When the local operating day matters, they also record `production_date_local` and an IANA `production_timezone`. Validation must confirm that converting `recorded_at_utc` into the stated timezone yields `production_date_local`.

A date-only field must not substitute for the exact audit timestamp.
