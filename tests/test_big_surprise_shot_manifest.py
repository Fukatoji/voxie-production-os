from pathlib import Path

import pytest

from voxie_os.core import load_data, validate
from voxie_os.timeline import to_neutral_timeline


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "productions"
    / "big-surprise"
    / "shot-manifest-v01.yaml"
)
BEATMAP_PATH = (
    ROOT
    / "manifests"
    / "productions"
    / "big-surprise"
    / "beatmap-001.final.json"
)


def _manifest():
    return load_data(MANIFEST_PATH)


def _beatmap():
    return load_data(BEATMAP_PATH)


def test_big_surprise_shot_manifest_validates():
    assert validate("shot_manifest", _manifest()) == []


def test_big_surprise_shot_manifest_has_27_contiguous_units():
    manifest = _manifest()
    shots = manifest["shots"]

    assert manifest["boundary_policy"] == {
        "unit_count": 27,
        "lyric_lines_consumed": 26,
        "coverage_start_s": 0.0,
        "coverage_end_s": 150.0,
        "contiguous": True,
        "rule": (
            "S001 covers 0.000 seconds to L01 vocal start. "
            "S002-S027 begin at L01-L26 vocal starts "
            "and end at the next lyric start or 150.000 seconds."
        ),
    }
    assert len(shots) == 27

    cursor = 0.0
    for index, shot in enumerate(shots, start=1):
        assert shot["shot_id"] == f"S{index:03d}"
        assert shot["source_window"]["start_s"] == pytest.approx(cursor, abs=1e-6)
        assert shot["duration_s"] == pytest.approx(
            shot["source_window"]["end_s"] - shot["source_window"]["start_s"],
            abs=1e-6,
        )
        cursor = shot["source_window"]["end_s"]

    assert cursor == pytest.approx(150.0, abs=1e-6)
    assert sum(shot["duration_s"] for shot in shots) == pytest.approx(150.0, abs=1e-6)


def test_big_surprise_lyric_markers_match_final_beatmap():
    manifest = _manifest()
    beatmap = _beatmap()

    assert manifest["source_beatmap"]["beatmap_id"] == beatmap["beatmap_id"]
    assert manifest["source_beatmap"]["status"] == beatmap["status"]
    assert manifest["source_audio"] == {
        "controlled_filename": beatmap["source_audio"]["controlled_filename"],
        "sha256": beatmap["source_audio"]["sha256"],
        "byte_identity_verified": True,
        "preserve_unchanged": True,
    }

    intro = manifest["shots"][0]
    assert intro["markers"] == [
        {"type": "structure", "label": "INTRO_PRELUDE", "at_s": 0.0}
    ]

    for shot, lyric in zip(manifest["shots"][1:], beatmap["lyrics"], strict=True):
        marker = shot["markers"][0]
        assert marker["type"] == "lyric"
        assert marker["line_id"] == lyric["line_id"]
        assert marker["at_s"] == 0.0
        assert marker["source_vocal_start_s"] == lyric["vocal_start_s"]
        assert marker["source_vocal_end_s"] == lyric["vocal_end_s"]
        assert marker["confidence"] == lyric["confidence"]
        assert shot["source_window"]["start_s"] == lyric["vocal_start_s"]


def test_big_surprise_manifest_does_not_invent_visual_authority():
    manifest = _manifest()

    assert manifest["visual_authority"]["status"] == "UNASSIGNED_REQUIRES_APPROVAL"
    assert manifest["visual_authority"]["execution_authorized"] is False
    assert manifest["publication_authorized"] is False

    for shot in manifest["shots"]:
        assert shot.get("asset_id") is None
        assert shot["characters"] == []
        assert shot["execution_authorized"] is False
        assert shot["motion"] == {
            "mode": "hold",
            "planning_placeholder": True,
            "execution_authorized": False,
        }


def test_big_surprise_manifest_builds_complete_unlinked_timeline():
    timeline = to_neutral_timeline(_manifest())

    assert timeline["duration_s"] == pytest.approx(150.0, abs=1e-6)
    assert len(timeline["clips"]) == 27
    assert timeline["clips"][0]["start_s"] == 0.0
    assert timeline["clips"][-1]["end_s"] == pytest.approx(150.0, abs=1e-6)
    assert all(clip["asset_id"] is None for clip in timeline["clips"])
