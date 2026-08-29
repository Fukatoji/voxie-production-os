from copy import deepcopy
from pathlib import Path

from voxie_os.core import load_data, validate


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT
    / "manifests"
    / "productions"
    / "rainbow-colors"
    / "production-state-v04.yaml"
)


def _manifest():
    return deepcopy(load_data(MANIFEST_PATH))


def test_rainbow_colors_v04_validates():
    assert validate("production_state", _manifest()) == []


def test_v04_records_exhausted_transfer_routes_without_claiming_mounts():
    audit = _manifest()["recorded_progress"]["S00"]

    assert audit["search_completed"] is True
    assert audit["locked_stills_identified"] == 3
    assert audit["mounted_binary_count"] == 0
    assert audit["fresh_rehash_count"] == 0
    assert audit["google_drive_video_matches"] == 0
    assert audit["google_drive_audio_matches"] == 0
    assert audit["local_runtime_binary_matches"] == 0
    assert audit["completion_state"] == (
        "ALL_EXECUTABLE_RECOVERY_ROUTES_EXHAUSTED_EXTERNAL_INPUT_REQUIRED"
    )


def test_v04_preserves_latest_s03_stepping_pools_authority():
    shot = _manifest()["recorded_progress"]["S03"]
    source = shot["active_source"]

    assert source["status"] == "LOCKED"
    assert source["exact_filename"] == (
        "VWF_RAINBOW_COLORS_S03_SIX_STEPPING_POOLS_KF-A_"
        "v01_APPROVED_LOCKED.png"
    )
    assert source["stable_locator"] == (
        "file-library://file_000000007acc81f7896d61c56cfcb63f"
    )
    assert source["recorded_sha256"] == (
        "d29ee0c4cc2e4de5599cc64f12d982cf1ca778b5239ca805346ccb0a5651894f"
    )
    assert source["runtime_mount_state"] == "UNAVAILABLE"
    assert source["fresh_rehash_performed"] is False
    assert shot["six_light_image"]["status"] == "PARKED_ALTERNATE"
    assert shot["six_light_image"]["may_replace_active_source"] is False


def test_v04_s03_motion_gate_is_zero_credit_and_unexecuted():
    motion = _manifest()["recorded_progress"]["S03"]["motion_review"]

    assert motion["status"] == "PENDING"
    assert motion["execution_performed"] is False
    assert motion["output_binary_created"] is False
    assert motion["credits_spent"] == 0
    assert motion["blocker"] == "EXACT_LOCKED_SOURCE_BYTES_UNAVAILABLE"
    assert motion["transfer_attempts_exhausted"] is True
    assert motion["no_substitution"] is True


def test_v04_classifies_every_s04_s37_shot_once():
    manifest = _manifest()
    expected = {
        "READY_EXISTING_SOURCE": 11,
        "MISSING_APPROVED_SOURCE": 8,
        "NEW_PIXELS_REQUIRED": 15,
    }
    observed = {}

    for number in range(4, 38):
        shot = manifest["recorded_progress"][f"S{number:02d}"]
        observed[shot["classification"]] = observed.get(shot["classification"], 0) + 1
        assert shot["creative_decision_required"] is False
        assert shot["render_authorized"] is False

    assert observed == expected
    assert sum(observed.values()) == 34


def test_v04_missing_approved_sources_have_actionable_resolution():
    manifest = _manifest()
    missing = [
        manifest["recorded_progress"][f"S{number:02d}"]
        for number in range(4, 38)
        if manifest["recorded_progress"][f"S{number:02d}"]["classification"]
        == "MISSING_APPROVED_SOURCE"
    ]

    assert len(missing) == 8
    assert all(
        shot["resolution_state"]
        in {
            "REVIEW_CANDIDATE_READY_FOR_EXPLICIT_APPROVAL",
            "DEPENDENCY_READY_AFTER_S04_APPROVAL",
            "DEPENDENCY_READY_AFTER_S20_APPROVAL",
        }
        for shot in missing
    )


def test_v04_new_pixel_shots_remain_balance_and_review_gated():
    manifest = _manifest()
    new_pixel = [
        manifest["recorded_progress"][f"S{number:02d}"]
        for number in range(4, 38)
        if manifest["recorded_progress"][f"S{number:02d}"]["classification"]
        == "NEW_PIXELS_REQUIRED"
    ]

    assert len(new_pixel) == 15
    for shot in new_pixel:
        assert shot["resolution_state"] == (
            "GENERATION_PACKAGE_DEFINED_BALANCE_AND_REVIEW_GATED"
        )
        assert shot["credit_gate"]["required_before_generation"] is True
        assert shot["credit_gate"]["spend_authorized"] is False
        assert shot["credit_gate"]["magiclight_live_balance_state"] == (
            "UNVERIFIED_NO_AUTHENTICATED_SESSION"
        )


def test_v04_preserves_protected_timing():
    manifest = _manifest()
    protected = {
        "S07": (30.15, 33.70),
        "S08": (33.70, 37.80),
        "S27": (101.00, 104.85),
        "S28": (104.85, 108.40),
        "S29": (108.40, 112.80),
    }

    for shot_id, (start, end) in protected.items():
        shot = manifest["recorded_progress"][shot_id]
        assert shot["protected_timing"] is True
        assert shot["start_seconds"] == start
        assert shot["end_seconds"] == end


def test_v04_live_magiclight_balance_and_spend_fail_closed():
    manifest = _manifest()
    audit = manifest["recorded_progress"]["S00"]

    assert audit["magiclight_live_balance_state"] == (
        "UNVERIFIED_NO_AUTHENTICATED_SESSION"
    )
    assert audit["magiclight_connector_state"] == (
        "NO_CONNECTED_OR_INSTALLABLE_MAGICLIGHT_CONNECTOR_FOUND"
    )
    assert audit["historical_balance_math_state"] == (
        "RECONCILED_86395_MINUS_90_EQUALS_86305"
    )
    assert manifest["spend_and_balance_gate"]["spend_authorized"] is False
    assert manifest["spend_and_balance_gate"][
        "reconcile_before_any_future_spend"
    ] is True
    assert audit["credits_spent"] == 0
