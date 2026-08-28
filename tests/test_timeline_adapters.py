import json

import pytest

from voxie_os.core import load_data
from voxie_os.timeline import to_premiere_plan, to_remotion_manifest, write_otio


def test_remotion_manifest_is_frame_deterministic():
    manifest = load_data("examples/shot_manifest.example.yaml")
    result = to_remotion_manifest(manifest, fps=30, width=1080, height=1920)
    assert result["duration_in_frames"] == 150
    assert result["clips"][1]["from"] == 60
    assert result["clips"][1]["markers"][0]["absolute_frame"] == 105


def test_premiere_plan_has_stable_markers_and_closed_export_gate():
    manifest = load_data("examples/shot_manifest.example.yaml")
    first = to_premiere_plan(manifest, fps=30)
    second = to_premiere_plan(manifest, fps=30)
    first_markers = [op for op in first["operations"] if op["op"] == "create_marker"]
    second_markers = [op for op in second["operations"] if op["op"] == "create_marker"]
    assert [m["marker_guid"] for m in first_markers] == [m["marker_guid"] for m in second_markers]
    assert first["operations"][-1]["enabled"] is False


def test_real_otio_round_trip(tmp_path):
    otio = pytest.importorskip("opentimelineio")
    manifest = load_data("examples/shot_manifest.example.yaml")
    output = tmp_path / "timeline.otio"
    write_otio(manifest, output, fps=30)
    timeline = otio.adapters.read_from_file(str(output))
    assert len(list(timeline.find_clips())) == 2
    assert json.loads(output.read_text())["OTIO_SCHEMA"].startswith("Timeline")
