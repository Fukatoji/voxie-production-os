from __future__ import annotations

from typing import Any


def to_neutral_timeline(manifest: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic neutral timeline JSON that can later map to OTIO/Remotion/Premiere."""
    cursor = 0.0
    clips = []
    for shot in manifest.get("shots", []):
        duration = float(shot["duration_s"])
        clips.append({
            "shot_id": shot["shot_id"],
            "start_s": round(cursor, 6),
            "duration_s": duration,
            "end_s": round(cursor + duration, 6),
            "asset_id": shot.get("asset_id"),
            "markers": shot.get("markers", []),
            "motion": shot.get("motion", {}),
        })
        cursor += duration
    return {"format": "voxie-neutral-timeline/v1", "duration_s": round(cursor, 6), "clips": clips}
