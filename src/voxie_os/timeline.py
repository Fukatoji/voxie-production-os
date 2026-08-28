from __future__ import annotations

import uuid
from pathlib import Path
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


def to_remotion_manifest(
    manifest: dict[str, Any], *, fps: int = 30, width: int = 1920, height: int = 1080
) -> dict[str, Any]:
    """Convert a shot manifest into deterministic frame-domain render input."""
    cursor = 0
    clips = []
    for shot in manifest.get("shots", []):
        duration_frames = round(float(shot["duration_s"]) * fps)
        markers = []
        for marker in shot.get("markers", []):
            relative_frame = round(float(marker.get("at_s", 0)) * fps)
            markers.append({**marker, "relative_frame": relative_frame, "absolute_frame": cursor + relative_frame})
        clips.append({
            "shot_id": shot["shot_id"],
            "from": cursor,
            "duration_in_frames": duration_frames,
            "asset_id": shot.get("asset_id"),
            "motion": shot.get("motion", {}),
            "markers": markers,
        })
        cursor += duration_frames
    return {
        "format": "voxie-remotion-manifest/v1",
        "composition_id": manifest.get("project_id", "VOXIE-PREVIEW"),
        "fps": fps,
        "width": width,
        "height": height,
        "duration_in_frames": cursor,
        "clips": clips,
    }


def to_premiere_plan(manifest: dict[str, Any], *, fps: int = 30, preset_path: str = "") -> dict[str, Any]:
    """Create a transaction plan for an official Premiere UXP 26.3 controller.

    The plan is data, not an unofficial MCP bridge. A UXP plugin can execute it
    inside ``project.lockedAccess()`` and stop before export if approval is absent.
    """
    timeline = to_remotion_manifest(manifest, fps=fps)
    operations: list[dict[str, Any]] = [
        {"op": "create_sequence", "name": manifest.get("project_id", "Voxie Sequence"), "preset_path": preset_path},
        {"op": "rename_tracks", "video": ["V1_PICTURE", "V2_OVERLAYS"], "audio": ["A1_MASTER", "A2_VOICE", "A3_MUSIC"]},
    ]
    for clip in timeline["clips"]:
        operations.append({
            "op": "insert_clip",
            "shot_id": clip["shot_id"],
            "asset_id": clip["asset_id"],
            "start_frame": clip["from"],
            "duration_frames": clip["duration_in_frames"],
            "track": "V1_PICTURE",
        })
        for marker in clip["markers"]:
            stable_key = f"{manifest.get('project_id')}:{clip['shot_id']}:{marker['absolute_frame']}:{marker.get('type')}"
            operations.append({
                "op": "create_marker",
                "marker_guid": str(uuid.uuid5(uuid.NAMESPACE_URL, stable_key)),
                "at_frame": marker["absolute_frame"],
                "name": marker.get("label") or marker.get("type", "marker"),
                "metadata": marker,
            })
    operations.append({
        "op": "queue_batch_export",
        "enabled": False,
        "approval_gate": "EXPORT_REQUIRES_EXPLICIT_APPROVAL",
    })
    return {
        "format": "voxie-premiere-uxp-plan/v1",
        "minimum_premiere_version": "26.3",
        "fps": fps,
        "duration_frames": timeline["duration_in_frames"],
        "transaction": "project.lockedAccess",
        "operations": operations,
    }


def write_otio(manifest: dict[str, Any], path: str | Path, *, fps: int = 30) -> None:
    """Write a real OpenTimelineIO file using the optional pinned dependency."""
    try:
        import opentimelineio as otio
    except ImportError as exc:  # pragma: no cover - exercised in installations without the extra
        raise RuntimeError("Install the timeline extra: pip install -e '.[timeline]'") from exc

    timeline = otio.schema.Timeline(name=manifest.get("project_id", "Voxie Timeline"))
    track = otio.schema.Track(name="V1_PICTURE", kind=otio.schema.TrackKind.Video)
    for shot in manifest.get("shots", []):
        duration_frames = round(float(shot["duration_s"]) * fps)
        duration = otio.opentime.RationalTime(duration_frames, fps)
        clip = otio.schema.Clip(
            name=shot["shot_id"],
            media_reference=otio.schema.MissingReference(
                metadata={"asset_id": shot.get("asset_id"), "requires_media_link": True}
            ),
            source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0, fps), duration),
            metadata={
                "voxie": {
                    "shot_id": shot["shot_id"],
                    "asset_id": shot.get("asset_id"),
                    "motion": shot.get("motion", {}),
                }
            },
        )
        for marker in shot.get("markers", []):
            marker_frame = round(float(marker.get("at_s", 0)) * fps)
            clip.markers.append(otio.schema.Marker(
                name=marker.get("label") or marker.get("type", "marker"),
                marked_range=otio.opentime.TimeRange(
                    otio.opentime.RationalTime(marker_frame, fps),
                    otio.opentime.RationalTime(1, fps),
                ),
                metadata={"voxie": marker},
            ))
        track.append(clip)
    timeline.tracks.append(track)
    otio.adapters.write_to_file(timeline, str(path))
