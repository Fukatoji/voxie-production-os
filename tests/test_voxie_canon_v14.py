from pathlib import Path

from voxie_os.authority_lock import build_authority_lock, verify_authority_lock
from voxie_os.core import load_data, sha256_file, validate


ROOT = Path(__file__).resolve().parents[1]
ASSET_PATH = ROOT / "manifests/assets/voxie-canon-v14.yaml"
V13_ASSET_PATH = ROOT / "manifests/assets/voxie-canon-v2-v13.yaml"
STATUS_PATH = ROOT / "manifests/characters/status-register-v03.yaml"
INDEX_PATH = ROOT / "manifests/control/authority-index-v03.yaml"
LOCK_PATH = ROOT / "manifests/control/authority-content-lock-v03.json"

EXPECTED_PACKAGE_SHA256 = (
    "b9ce2b414dc3bb25ec064646c4d45a70557683fb885d64f7c1583955d6c2f061"
)
EXPECTED_PRIMARY_SHEET_SHA256 = (
    "d9dc1779104b3bc8cc0a4ca950cd874eaa4499898d5075a866352f98936ecff1"
)
EXPECTED_VIEW_HASHES = {
    "FRONT_000": "6cbaed736eabc5323a50fea5d4abb554cac9042fb44da1e644db432a5c3c9194",
    "FRONT_3Q_RIGHT_045": "1afe2b3d5dda607534485385a124c2322b739b234a266fccee5ae820018220f0",
    "RIGHT_PROFILE_090": "b89b2a4e48c458b8b010a95e15fcffb349a8f1ceb82cd63624cfd2511d228983",
    "REAR_3Q_RIGHT_135": "f83b884e1d63d5a0a7bdca53aeb3d535d16bdcbe7b611f7f8f0897eaf692d760",
    "BACK_180": "d30025aa17db0b742db853ede7c4aa34cd7671058a310c666c49c10b1edb8f2d",
    "REAR_3Q_LEFT_225": "bb906bd69615790aca1d83399f099c8c5744b711c8b97ef36dc99aba138f68f5",
    "LEFT_PROFILE_270": "d10b30e8a964f55946538fb1f6796279901807b5cc52cc9c5981594575e3e64f",
    "FRONT_3Q_LEFT_315": "05da660b912015290e8506d2361542b10b5cbe6eb3bdc7f52e07e16cd408b6c3",
}


def _voxie(register):
    return next(
        character
        for character in register["characters"]
        if character["character_id"] == "VOXIE"
    )


def test_v14_asset_is_exact_approved_locked_package_authority():
    asset = load_data(ASSET_PATH)

    assert validate("asset", asset) == []
    assert asset["asset_id"] == "VOXIE_CANON_V14"
    assert asset["status"] == "locked"
    assert asset["approval_state"] == "APPROVED / LOCKED CANON"
    assert asset["qc_status"] == "PASS"
    assert asset["sha256"] == EXPECTED_PACKAGE_SHA256
    assert asset["provenance"]["source_package"] == {
        "library_file_id": "libfile_2158d521dfe88191aeddffdaa73d5aef",
        "file_id": "file_00000000d27481f596ad115084332396",
        "filename": "VOXIE_V14_APPROVED_LOCKED_v01.zip",
        "library_path": "/Voxie's Wonder World/01 Canon/Characters/Voxie/V14/Approved Locked/VOXIE_V14_APPROVED_LOCKED_v01.zip",
        "byte_size": 11604796,
        "sha256": EXPECTED_PACKAGE_SHA256,
        "preservation_state": "preserved_unchanged",
    }
    assert asset["primary_sheet"]["sha256"] == EXPECTED_PRIMARY_SHEET_SHA256
    assert {view["view_id"]: view["sha256"] for view in asset["views"]} == (
        EXPECTED_VIEW_HASHES
    )
    assert asset["media_committed_to_repository"] is False


def test_v14_gate_records_observable_design_and_evidence_limits():
    asset = load_data(ASSET_PATH)
    invariants = set(asset["qc"]["locked_invariants"])

    assert asset["canon_change_gate"]["status"] == "COMPLETE"
    assert asset["canon_change_gate"]["decision"] == "APPROVED_AND_LOCKED"
    assert asset["canon_change_gate"]["authority_effect"] == "CURRENT_FOR_NEW_WORK"
    assert "exactly four visible digits per hand, comprising three fingers and one thumb" in invariants
    assert "exactly four translucent wings with the upper pair larger than the lower pair" in invariants
    assert "navy-purple helmet crown wrap with white rear-side shell areas" in invariants
    assert "solid cyan rear V" in invariants
    assert asset["qc"]["visible_reference_limits"]["hidden_anatomy_certified"] is False
    assert asset["qc"]["visible_reference_limits"]["model_or_rig_certified"] is False


def test_v3_status_routes_new_work_to_v14_and_preserves_predecessors():
    register = load_data(STATUS_PATH)
    assert validate("character_status", register) == []

    voxie = _voxie(register)
    assert voxie["reference_assets"] == ["manifests/assets/voxie-canon-v14.yaml"]
    assert "pending_change_proposals" not in voxie
    assert voxie["next_gate"] == "USE_CANON_V14_LOCKED_AUTHORITY_ONLY"
    assert [item["path"] for item in voxie["historical_assets"]] == [
        "manifests/assets/voxie-canon-v2-v13.yaml",
        "manifests/assets/voxie-canon-v1.0.magiclight.yaml",
    ]
    assert sha256_file(V13_ASSET_PATH) == (
        "1e35abe6832f4ba2582ef0c448573c61175afdc0f039bd0fd30a222217426ccd"
    )


def test_v3_authority_index_and_lock_make_v14_current():
    index = load_data(INDEX_PATH)
    lock = load_data(LOCK_PATH)

    assert validate("authority_index", index) == []
    entries = {entry["authority_id"]: entry for entry in index["entries"]}
    assert "VOXIE_CANON_V14" in entries
    assert "VOXIE_CANON_V2_V13" not in entries
    assert entries["VOXIE_CANON_V14"]["path"] == (
        "manifests/assets/voxie-canon-v14.yaml"
    )
    assert entries["VOXIE_CANON_V14"]["predecessors"] == [
        "manifests/assets/voxie-canon-v2-v13.yaml",
        "manifests/assets/voxie-canon-v1.0.magiclight.yaml",
    ]
    assert entries["VWW_CHARACTER_STATUS_V03"]["predecessors"] == [
        "manifests/characters/status-register-v02.yaml",
        "manifests/characters/status-register-v01.yaml",
    ]
    assert build_authority_lock(index, index_path=INDEX_PATH) == lock
    assert verify_authority_lock(index, lock, index_path=INDEX_PATH)["status"] == "PASS"
