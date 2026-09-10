from copy import deepcopy
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

from voxie_os.cli import main
from voxie_os.core import SCHEMA_FILES, load_data, schema_for, validate


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "manifests/productions/ready-set-play/production-manifest-v01.json"
)


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


def test_missing_audio_identity_fails_closed():
    candidate = _manifest()
    del candidate["audio"]["asset_id"]

    errors = validate("production_manifest", candidate)

    assert any(
        error.startswith("audio:") and "asset_id" in error
        for error in errors
    )


def test_pending_audio_checksum_blocks_execution():
    candidate = _manifest()
    candidate["execution_authority"] = "AUTHORIZED"

    assert any(
        error.startswith("execution_authority:")
        for error in validate("production_manifest", candidate)
    )


def test_pending_audio_checksum_requires_matching_blocker():
    candidate = _manifest()
    candidate["blockers"].remove("AUDIO_SHA256_PENDING")

    assert validate("production_manifest", candidate) == [
        "blockers: missing required blockers: AUDIO_SHA256_PENDING"
    ]


def test_external_artifacts_use_stable_library_id_and_checksum():
    manifest = _manifest()

    for key in ("beatmap", "timeline"):
        assert manifest[key]["asset_id"] == manifest[key]["storage"]["library_file_id"]
        assert len(manifest[key]["sha256"]) == 64


def test_missing_source_is_not_treated_as_resolved():
    candidate = _manifest()
    candidate["beatmap"]["authoritative_sources"][0]["status"] = "AVAILABLE"
    candidate["blockers"].remove("SOURCE_MARKER_NOT_AVAILABLE")

    assert validate("production_manifest", candidate) == []


def test_v01_requires_null_predecessor():
    candidate = _manifest()
    candidate["supersedes"] = {
        "record_version": 1,
        "path": "manifests/productions/ready-set-play/production-manifest-v01.json",
        "sha256": "a" * 64,
    }

    assert validate("production_manifest", candidate) == [
        "supersedes: record_version 1 must not name a predecessor"
    ]


def test_future_version_requires_immediate_predecessor():
    candidate = _manifest()
    candidate["record_version"] = 2
    candidate["record_id"] = "VWW-RSP-001-PRODUCTION-MANIFEST-v02"
    candidate["supersedes"] = None

    assert validate("production_manifest", candidate) == [
        "supersedes: record_version 2 requires the immediate predecessor"
    ]


def test_record_id_matches_version():
    candidate = _manifest()
    candidate["record_id"] = "VWW-RSP-001-PRODUCTION-MANIFEST-v02"

    assert validate("production_manifest", candidate) == [
        "record_id: expected VWW-RSP-001-PRODUCTION-MANIFEST-v01"
    ]


def test_referenced_repository_schema_must_exist():
    candidate = _manifest()
    candidate["beatmap"]["schema"] = "schemas/missing.schema.json"

    errors = validate("production_manifest", candidate)

    assert any(
        error.startswith("beatmap.schema: referenced repository file does not exist:")
        for error in errors
    )


def test_timing_durations_must_match_audio():
    candidate = _manifest()
    candidate["timeline"]["duration_ms"] += 1

    assert validate("production_manifest", candidate) == [
        "timeline.duration_ms: expected 174693 to match audio.duration_ms, got 174694"
    ]


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
