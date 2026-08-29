from pathlib import Path

from voxie_os.core import load_data, validate


ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = (
    ROOT
    / "manifests"
    / "distribution"
    / "colorful-day"
    / "release-readiness-v01.yaml"
)
MASTER_STATUS_PATH = (
    ROOT
    / "manifests"
    / "productions"
    / "colorful-day"
    / "master-status-v01.md"
)


def _readiness():
    return load_data(READINESS_PATH)


def test_colorful_day_release_readiness_validates():
    assert validate("qc_report", _readiness()) == []


def test_master_authority_matches_locked_status_record():
    readiness = _readiness()
    master = readiness["master"]
    source = MASTER_STATUS_PATH.read_text(encoding="utf-8")

    assert master["status"] == "COMPLETE_APPROVED_LOCKED"
    assert master["controlled_filename"] in source
    assert master["sha256"] in source
    assert "190.000000" in source
    assert master["duration_seconds"] == 190.0
    assert master["resolution"] == "1920x1080"
    assert master["aspect_ratio"] == "16:9"
    assert master["progressive"] is True
    assert master["pixel_format"] == "yuv420p"
    assert master["fps"] == 24
    assert master["frame_count"] == 4560
    assert master["video_codec"] == "H.264 High"
    assert master["audio_codec"] == "AAC-LC"
    assert master["audio_sample_rate_hz"] == 48000
    assert master["audio_channels"] == 2
    assert master["audio_bitrate_kbps"] == 320
    assert master["locked_soundtrack"] in source
    assert master["source_audio_preserved"] is True


def test_master_qc_and_caption_limitation_are_preserved():
    readiness = _readiness()
    qc = readiness["qc"]
    source = MASTER_STATUS_PATH.read_text(encoding="utf-8")

    assert qc["complete_decode"] == "PASS"
    assert qc["shot_timeline_coverage"] == "PASS"
    assert qc["canon_four_wing_topology"] == "PASS"
    assert qc["child_safety_pacing"] == "PASS"
    assert qc["black_frame_scan"] == "PASS"
    assert qc["captions_status"] == "OMITTED_INTENTIONALLY_LOW_CONFIDENCE"
    assert qc["captions_reason"] == "several sung words remain low-confidence"
    assert "Captions intentionally omitted" in source
    assert qc["paid_credits"] == 0


def test_distribution_authority_is_preserved_without_inventing_inventory():
    readiness = _readiness()
    distribution = readiness["distribution_package"]
    source = MASTER_STATUS_PATH.read_text(encoding="utf-8")

    assert "distribution package is also approved and locked" in source
    assert distribution["authority_status"] == "APPROVED_LOCKED"
    assert distribution["repository_inventory_status"] == "NOT_ENUMERATED"
    assert distribution["package_filenames_recorded"] is False
    assert distribution["package_sha256_recorded"] is False
    assert distribution["platform_metadata_recorded"] is False
    assert distribution["thumbnail_recorded"] is False
    assert distribution["platform_format_records_present"] is False


def test_release_gate_fails_closed_until_evidence_and_approvals_exist():
    readiness = _readiness()
    gate = readiness["release_gate"]

    assert readiness["status"] == "REVIEW"
    assert gate["execution_authority"] == "BLOCKED"
    assert gate["publication_authorized"] is False
    assert gate["scheduling_authorized"] is False
    assert gate["account_write_authorized"] is False
    assert gate["required_approvals"] == [
        "DISTRIBUTION_PACKAGE_INVENTORY_CAPTURE_OR_EXPLICIT_WAIVER",
        "PLATFORM_METADATA_CONFIRMATION",
        "THUMBNAIL_CONFIRMATION",
        "MADE_FOR_KIDS_CONFIGURATION",
        "CAPTION_OR_NO_CAPTION_ACCESSIBILITY_APPROVAL",
        "SCHEDULE_APPROVAL",
        "EXPLICIT_PUBLICATION_APPROVAL",
    ]
    assert "DISTRIBUTION_PACKAGE_DETAILS_NOT_ENUMERATED" in gate["blockers"]
    assert "CAPTION_ACCESSIBILITY_DECISION_PENDING" in gate["blockers"]
    assert "PUBLICATION_NOT_AUTHORIZED" in gate["blockers"]


def test_platform_state_preserves_approval_but_blocks_execution():
    platforms = _readiness()["platforms"]

    assert [platform["platform"] for platform in platforms] == [
        "youtube",
        "tiktok",
        "instagram",
    ]
    for platform in platforms:
        assert platform["format"] == "NOT_RECORDED"
        assert platform["package_status"] == (
            "AUTHORITY_APPROVED_DETAILS_UNRECORDED"
        )
        assert platform["upload_authorized"] is False
        assert platform["publish_authorized"] is False
