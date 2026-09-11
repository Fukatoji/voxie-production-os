from copy import deepcopy
import hashlib
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


def _verified_source_marker():
    return {
        "canonical_filename": "stage_d_verified_markers.tsv",
        "status": "AVAILABLE",
        "asset_id": "libfile_sourcemarker",
        "storage": {
            "provider": "CHATGPT_LIBRARY",
            "library_file_id": "libfile_sourcemarker",
            "path": "/Voxie's Wonder World/stage_d_verified_markers.tsv",
        },
        "checksum_status": "VERIFIED",
        "sha256": "c" * 64,
    }


def _verified_video_binaries():
    return {
        "status": "VERIFIED",
        "required_for_execution": True,
        "checksum_status": "VERIFIED",
        "assets": [
            {
                "asset_id": "libfile_rspvideo",
                "canonical_filename": "RSP_S01.mp4",
                "mime_type": "video/mp4",
                "storage": {
                    "provider": "CHATGPT_LIBRARY",
                    "library_file_id": "libfile_rspvideo",
                    "path": "/Voxie's Wonder World/RSP_S01.mp4",
                },
                "sha256": "d" * 64,
            }
        ],
    }


def _execution_ready_manifest():
    candidate = _manifest()
    candidate["state"] = "APPROVED"
    candidate["audio"]["checksum_status"] = "VERIFIED"
    candidate["audio"]["sha256"] = "a" * 64
    candidate["audio"]["content_status"] = "PASS"
    candidate["audio"]["known_defects"] = []
    candidate["beatmap"]["authoritative_sources"][0] = _verified_source_marker()
    candidate["video_binaries"] = _verified_video_binaries()
    candidate["registry"] = {
        "canonical_filename": "production_registry.sqlite3",
        "status": "VERIFIED",
        "storage": {
            "provider": "CHATGPT_LIBRARY",
            "library_file_id": "libfile_registry",
            "path": "/Voxie's Wonder World/production_registry.sqlite3",
        },
        "checksum_status": "VERIFIED",
        "sha256": "b" * 64,
    }
    candidate["blockers"] = []
    candidate["execution_authority"] = "AUTHORIZED"
    return candidate


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


def test_available_source_does_not_require_missing_source_blocker():
    candidate = _manifest()
    candidate["beatmap"]["authoritative_sources"][0] = _verified_source_marker()
    candidate["blockers"].remove("SOURCE_MARKER_NOT_AVAILABLE")

    assert validate("production_manifest", candidate) == []


def test_available_source_requires_stable_identity():
    candidate = _manifest()
    candidate["beatmap"]["authoritative_sources"][0]["status"] = "AVAILABLE"
    candidate["blockers"].remove("SOURCE_MARKER_NOT_AVAILABLE")

    errors = validate("production_manifest", candidate)

    assert any(
        error.startswith("beatmap.authoritative_sources.0.asset_id:")
        for error in errors
    )
    assert any(
        error.startswith("beatmap.authoritative_sources.0.storage:")
        for error in errors
    )
    assert any(
        error.startswith("beatmap.authoritative_sources.0.sha256:")
        for error in errors
    )


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


def test_any_declared_blocker_prevents_execution_authorization():
    candidate = _execution_ready_manifest()
    candidate["blockers"] = ["VISUAL_MASTER_MISSING"]

    assert validate("production_manifest", candidate) == [
        "execution_authority: must be BLOCKED while blockers remain"
    ]


def test_non_approved_states_prevent_execution_authorization():
    for state in ("DRAFT", "REVIEW", "CONDITIONAL", "BLOCKED", "ARCHIVED"):
        candidate = _execution_ready_manifest()
        candidate["state"] = state

        assert validate("production_manifest", candidate) == [
            "execution_authority: must be BLOCKED unless state is "
            "APPROVED or APPROVED_LOCKED"
        ]


def test_blocked_audio_without_known_defects_cannot_authorize_execution():
    candidate = _execution_ready_manifest()
    candidate["audio"]["content_status"] = "BLOCKED"

    assert validate("production_manifest", candidate) == [
        "blockers: missing required blockers: AUDIO_CONTENT_DEFECT_PRESENT"
    ]


def test_audio_asset_id_must_match_drive_file_id():
    candidate = _manifest()
    candidate["audio"]["storage"]["file_id"] = "different-drive-file"

    errors = validate("production_manifest", candidate)

    assert "audio.asset_id: must match audio.storage.file_id" in errors
    assert any(error.startswith("audio.storage.url:") for error in errors)


def test_audio_drive_url_must_encode_drive_file_id():
    candidate = _manifest()
    candidate["audio"]["storage"]["url"] = (
        "https://drive.google.com/file/d/different-drive-file/view"
    )

    assert validate("production_manifest", candidate) == [
        "audio.storage.url: must encode audio.storage.file_id "
        "in the Google Drive file path"
    ]


def test_predecessor_checksum_must_match_referenced_record():
    candidate = _manifest()
    candidate["record_version"] = 2
    candidate["record_id"] = "VWW-RSP-001-PRODUCTION-MANIFEST-v02"
    candidate["supersedes"] = {
        "record_version": 1,
        "path": "manifests/productions/ready-set-play/production-manifest-v01.json",
        "sha256": "a" * 64,
    }

    errors = validate("production_manifest", candidate)
    expected_sha256 = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()

    assert errors == [
        "supersedes.sha256: expected checksum "
        f"{expected_sha256} for "
        "manifests/productions/ready-set-play/production-manifest-v01.json"
    ]


def test_predecessor_record_must_exist():
    candidate = _manifest()
    candidate["record_version"] = 3
    candidate["record_id"] = "VWW-RSP-001-PRODUCTION-MANIFEST-v03"
    candidate["supersedes"] = {
        "record_version": 2,
        "path": "manifests/productions/ready-set-play/production-manifest-v02.json",
        "sha256": "a" * 64,
    }

    assert validate("production_manifest", candidate) == [
        "supersedes.path: referenced repository file does not exist: "
        "manifests/productions/ready-set-play/production-manifest-v02.json"
    ]


def test_recorded_timestamp_must_be_real_utc_time():
    candidate = _manifest()
    candidate["recorded_at_utc"] = "not-a-date"

    assert validate("production_manifest", candidate) == [
        "recorded_at_utc: must be a real RFC 3339 UTC timestamp "
        "in YYYY-MM-DDTHH:MM:SSZ form"
    ]


def test_missing_video_binaries_require_matching_blocker():
    candidate = _manifest()
    candidate["blockers"].remove("RSP_VIDEO_BINARIES_NOT_OBSERVED")

    assert validate("production_manifest", candidate) == [
        "blockers: missing required blockers: RSP_VIDEO_BINARIES_NOT_OBSERVED"
    ]


def test_verified_video_asset_id_must_match_storage_identity():
    candidate = _manifest()
    candidate["video_binaries"] = _verified_video_binaries()
    candidate["video_binaries"]["assets"][0]["asset_id"] = "libfile_wrongvideo"

    assert validate("production_manifest", candidate) == [
        "video_binaries.assets.0.asset_id: must match "
        "video_binaries.assets.0.storage.library_file_id"
    ]


def test_verified_video_requires_sha256():
    candidate = _manifest()
    candidate["video_binaries"] = _verified_video_binaries()
    candidate["video_binaries"]["assets"][0]["sha256"] = None

    errors = validate("production_manifest", candidate)

    assert any(
        error.startswith("video_binaries.assets.0.sha256:")
        for error in errors
    )
