from pathlib import Path

from voxie_os.core import load_data, validate


ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = (
    ROOT
    / "manifests"
    / "distribution"
    / "big-surprise"
    / "release-readiness-v01.yaml"
)
REVIEW_MASTER_PATH = (
    ROOT
    / "manifests"
    / "productions"
    / "big-surprise"
    / "review-master-v01.json"
)
BEATMAP_PATH = (
    ROOT
    / "manifests"
    / "productions"
    / "big-surprise"
    / "beatmap-001.final.json"
)
SHOT_MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "productions"
    / "big-surprise"
    / "shot-manifest-v01.yaml"
)


def _readiness():
    return load_data(READINESS_PATH)


def test_big_surprise_release_readiness_validates_as_qc_report():
    assert validate("qc_report", _readiness()) == []


def test_release_readiness_matches_review_master_authority():
    readiness = _readiness()
    review_master = load_data(REVIEW_MASTER_PATH)
    master = readiness["master"]

    assert readiness["status"] == "REVIEW"
    assert master["status"] == review_master["status"]
    assert master["controlled_filename"] == review_master["controlled_filename"]
    assert master["sha256"] == review_master["sha256"]
    assert master["duration_seconds"] == review_master["technical"]["duration_seconds"]
    assert master["resolution"] == review_master["technical"]["resolution"]
    assert master["fps"] == review_master["technical"]["fps"]
    assert master["subtitle_track_present"] is True
    assert master["source_audio_preserved"] is True


def test_timing_authority_matches_beatmap_and_shot_manifest():
    readiness = _readiness()
    beatmap = load_data(BEATMAP_PATH)
    shot_manifest = load_data(SHOT_MANIFEST_PATH)
    timing = readiness["timing_authority"]

    assert timing["beatmap"] == "manifests/productions/big-surprise/beatmap-001.final.json"
    assert timing["shot_manifest"] == (
        "manifests/productions/big-surprise/shot-manifest-v01.yaml"
    )
    assert timing["duration_seconds"] == beatmap["duration_s"] == 150.0
    assert timing["shot_units"] == len(shot_manifest["shots"]) == 27
    assert timing["contiguous"] is True


def test_release_gate_is_fail_closed():
    readiness = _readiness()
    gate = readiness["release_gate"]

    assert gate["execution_authority"] == "BLOCKED"
    assert gate["publication_authorized"] is False
    assert gate["scheduling_authorized"] is False
    assert gate["account_write_authorized"] is False
    assert {
        "USER_FINALIZATION",
        "PLATFORM_METADATA_APPROVAL",
        "THUMBNAIL_APPROVAL",
        "MADE_FOR_KIDS_CONFIGURATION",
        "SCHEDULE_APPROVAL",
        "EXPLICIT_PUBLICATION_APPROVAL",
    } == set(gate["required_approvals"])

    for platform in readiness["platforms"]:
        assert platform["package_status"] == "NOT_PREPARED"
        assert platform["upload_authorized"] is False
        assert platform["publish_authorized"] is False


def test_every_release_blocker_has_a_warning_finding():
    readiness = _readiness()
    blockers = set(readiness["release_gate"]["blockers"])
    warning_rules = {
        finding["rule_id"]
        for finding in readiness["findings"]
        if finding["severity"] == "warning"
    }

    assert blockers == warning_rules
    assert "PUBLICATION_NOT_AUTHORIZED" in blockers
