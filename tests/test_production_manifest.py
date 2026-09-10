from copy import deepcopy
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

from voxie_os.cli import main
from voxie_os.core import SCHEMA_FILES, load_data, schema_for, validate


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/production_manifest.json"


def _manifest():
    return deepcopy(load_data(MANIFEST))


def test_production_manifest_schema_is_registered_and_valid():
    assert SCHEMA_FILES["production_manifest"] == "production_manifest.schema.json"
    Draft202012Validator.check_schema(schema_for("production_manifest"))


def test_current_production_manifest_validates():
    assert validate("production_manifest", _manifest()) == []


def test_cli_validates_current_production_manifest(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["voxie-os", "validate", "production_manifest", str(MANIFEST)],
    )
    assert main() == 0
    assert capsys.readouterr().out == "PASS\n"


def test_missing_production_id_fails_closed():
    candidate = _manifest()
    del candidate["production_id"]

    assert any(
        error.startswith("<root>:") and "production_id" in error
        for error in validate("production_manifest", candidate)
    )


def test_invalid_state_fails_closed():
    candidate = _manifest()
    candidate["state"] = "READY_TO_POST"

    assert any(
        error.startswith("state:")
        for error in validate("production_manifest", candidate)
    )


def test_nonpositive_audio_duration_fails_closed():
    candidate = _manifest()
    candidate["audio"]["duration_ms"] = 0

    assert any(
        error.startswith("audio.duration_ms:")
        for error in validate("production_manifest", candidate)
    )


def test_unique_keyframes_cannot_exceed_shot_count():
    candidate = _manifest()
    candidate["timeline"]["unique_keyframes"] = 24

    assert validate("production_manifest", candidate) == [
        "timeline.unique_keyframes: cannot exceed timeline.shot_count"
    ]


def test_hold_or_continue_shots_cannot_exceed_shot_count():
    candidate = _manifest()
    candidate["timeline"]["hold_or_continue_shots"] = 24

    assert validate("production_manifest", candidate) == [
        "timeline.hold_or_continue_shots: cannot exceed timeline.shot_count"
    ]
