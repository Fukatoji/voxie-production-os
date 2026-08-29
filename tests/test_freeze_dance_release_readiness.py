from pathlib import Path

from voxie_os.core import load_data, validate


ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = (
    ROOT
    / "manifests"
    / "distribution"
    / "freeze-dance"
    / "release-readiness-v01.yaml"
)
MASTER_PATH = (
    ROOT
    / "manifests"
    / "productions"
    / "freeze-dance"
    / "review-master-v21.json"
)
FINAL_REVIEW_PATH = (
    ROOT
    / "manifests"
    / "productions"
    / "freeze-dance"
    / "final-review-v21.md"
)


def _readiness():
    return load_data(READINESS_PATH)


def _master():
    return load_data(MASTER_PATH)


def test_freeze_dance_release_readiness_validates():
    assert validate("release_readiness", _readiness()) == []


def test_release_record_matches_review_master_authority():
    readiness = _readiness()
    master = _master()
    recorded = readiness["master"]

    assert recorded["manifest"] == (
        "manifests/productions/freeze-dance/review-master-v21.json"
    )
    assert recorded["status"] == master["status"]
    assert recorded["controlled_filename"] == master["controlled_filename"]
    assert recorded["source_filename"] == master["source_filename"]
    assert recorded["sha256"] == master["sha256"]
    assert recorded["duration_seconds"] == master["technical"]["duration_seconds"]
    assert recorded["resolution"] == master["technical"]["resolution"]
    assert recorded["fps"] == master["technical"]["fps"]
    assert recorded["video_codec"] == master["technical"]["video_codec"]
    assert recorded["audio_codec"] == master["technical"]["audio_codec"]
    assert recorded["audio_sample_rate_hz"] == master["technical"][
        "audio_sample_rate_hz"
    ]
    assert recorded["audio_channels"] == master["technical"]["audio_channels"]
    assert recorded["source_audio_preserved"] is True


def test_freeze_reference_qc_matches_master_record():
    readiness = _readiness()
    master = _master()
    qc = readiness["qc"]

    assert qc["hard_freeze_count"] == master["qc"]["hard_freeze_count"] == 7
    assert qc["locked_freeze_references_present"] is True
    assert qc["verified_reference_match_times_seconds"] == master["qc"][
        "verified_reference_match_times_seconds"
    ]
    assert qc["character_consistency"] == master["qc"][
        "character_consistency"
    ]
    assert qc["frame_integrity"] == master["qc"]["frame_integrity"]
    assert master["qc"]["audio_master_preserved"] == "PASS"
    assert master["qc"]["publication_status"] == "NOT_PUBLISHED"


def test_final_review_hashes_and_audio_note_are_preserved():
    readiness = _readiness()
    final_review = FINAL_REVIEW_PATH.read_text(encoding="utf-8")

    assert readiness["master"]["final_review_lock_copy"] in final_review
    assert readiness["master"]["sha256"] in final_review
    assert readiness["review_delivery"]["controlled_filename"] in final_review
    assert readiness["review_delivery"]["sha256"] in final_review
    assert readiness["qc"]["integrated_loudness_lufs_approx"] == -12.4
    assert readiness["qc"]["peak_dbfs_approx"] == -0.1
    assert readiness["qc"]["gain_adjustment_performed"] is False
    assert readiness["qc"]["audio_review_note_required"] is True


def test_release_gate_fails_closed():
    readiness = _readiness()
    gate = readiness["release_gate"]

    assert readiness["status"] == "REVIEW"
    assert gate["execution_authority"] == "BLOCKED"
    assert gate["publication_authorized"] is False
    assert gate["scheduling_authorized"] is False
    assert gate["account_write_authorized"] is False
    assert gate["required_approvals"] == [
        "USER_FINALIZATION",
        "PLATFORM_METADATA_APPROVAL",
        "THUMBNAIL_APPROVAL",
        "MADE_FOR_KIDS_CONFIGURATION",
        "ACCESSIBILITY_AND_AUDIO_REVIEW",
        "SCHEDULE_APPROVAL",
        "EXPLICIT_PUBLICATION_APPROVAL",
    ]
    assert "AUDIO_PEAK_REVIEW_NOTE_NOT_ACCEPTED" in gate["blockers"]
    assert "PUBLICATION_NOT_AUTHORIZED" in gate["blockers"]


def test_every_release_blocker_has_a_warning_finding():
    readiness = _readiness()
    blockers = set(readiness["release_gate"]["blockers"])
    warning_rules = {
        finding["rule_id"]
        for finding in readiness["findings"]
        if finding["severity"] == "warning"
    }

    assert blockers == warning_rules


def test_all_platform_packages_are_unprepared_and_blocked():
    platforms = _readiness()["platforms"]

    assert [platform["platform"] for platform in platforms] == [
        "youtube",
        "tiktok",
        "instagram",
    ]
    assert all(platform["package_status"] == "NOT_PREPARED" for platform in platforms)
    assert all(platform["upload_authorized"] is False for platform in platforms)
    assert all(platform["publish_authorized"] is False for platform in platforms)
    assert platforms[1]["format"] == "VERTICAL_DERIVATIVE_REQUIRED"
    assert platforms[2]["format"] == "VERTICAL_DERIVATIVE_REQUIRED"
