from pathlib import Path

from voxie_os.core import load_data, validate


ROOT = Path(__file__).resolve().parents[1]
ASSET_PATH = ROOT / "manifests/assets/voxie-canon-v2-v13.yaml"
STATUS_PATH = ROOT / "manifests/characters/status-register-v02.yaml"
INDEX_PATH = ROOT / "manifests/control/authority-index-v02.yaml"

EXPECTED_VIEW_HASHES = {
    "01_FRONT": "48ab231dca38a29fab31aa655f858d469044dd63b781372e8115e2293b06e974",
    "02_FRONT_3Q_RIGHT": "8cf5c1699c5a3fbc56bd9f11e2f84988d5c16307bad447e49ebf8d99bd6c0082",
    "03_TRUE_SIDE_RIGHT": "dd2b8a24ecfc03335bb187571947767f32eca4fa5147fdc6824e622b35b1fdfe",
    "04_REAR_3Q_RIGHT": "c9da5e873a24debb0867b01f8722d401ab9123ac15c7f7a52e87233677511cc3",
    "05_STRAIGHT_BACK": "f76b08f07f212ddffc1ba5340434da159fcae9932a1d6c4ca3884b81ab470038",
    "06_REAR_3Q_LEFT": "f8ec76486752d7f63e28fc158257ce4ea958f0637dff8ecdd020c3dfa240a32c",
    "07_TRUE_SIDE_LEFT": "7c19be37940de315acd892873c9555b05262e7cd970eb1676fae0d7e0dee11ad",
    "08_FRONT_3Q_LEFT": "7fd691ba3bf8146d3420643849ea0bd7b39f569dcebd7cb125da479e1fa9c218",
}


def test_v2_v13_asset_manifest_preserves_locked_identity():
    asset = load_data(ASSET_PATH)

    assert validate("asset", asset) == []
    assert asset["asset_id"] == "VOXIE_CANON_V2_V13"
    assert asset["status"] == "locked"
    assert asset["approval_state"] == "APPROVED / LOCKED CANON"
    assert asset["qc_status"] == "PASS"
    assert asset["sha256"] == (
        "bfbc8fe437662c7713c5c0044e851f8a7fabff98effcf10074ef748d565edb96"
    )
    assert asset["provenance"]["source_package"]["library_file_id"] == (
        "libfile_9597ccb65f4081919dba8385a253530b"
    )
    assert asset["provenance"]["approval_lock_record"]["library_file_id"] == (
        "libfile_732559e7ae308191baf8432be55720f2"
    )
    assert {
        view["view_id"]: view["sha256"] for view in asset["views"]
    } == EXPECTED_VIEW_HASHES
    assert asset["media_committed_to_repository"] is False


def test_v2_status_register_routes_new_work_to_v13_and_keeps_v14_pending():
    register = load_data(STATUS_PATH)
    assert validate("character_status", register) == []

    voxie = next(
        character
        for character in register["characters"]
        if character["character_id"] == "VOXIE"
    )
    assert voxie["reference_assets"] == [
        "manifests/assets/voxie-canon-v2-v13.yaml"
    ]
    assert voxie["historical_assets"] == [
        {
            "path": "manifests/assets/voxie-canon-v1.0.magiclight.yaml",
            "state": "HISTORICAL_LOCKED",
            "permitted_use": "EXISTING_APPROVED_V1_ERA_PRODUCTIONS_ONLY",
        }
    ]
    proposal = voxie["pending_change_proposals"][0]
    assert proposal["proposal_id"] == "VOXIE_CANON_V14"
    assert proposal["status"] == "PENDING_CANON_CHANGE_GATE"
    assert proposal["authority_effect"] == "NONE_UNTIL_SEPARATELY_APPROVED_AND_LOCKED"


def test_v2_authority_index_makes_v13_current_without_erasing_v1_history():
    index = load_data(INDEX_PATH)
    assert validate("authority_index", index) == []

    entries = {entry["authority_id"]: entry for entry in index["entries"]}
    assert "VOXIE_CANON_V2_V13" in entries
    assert "VOXIE_CANON_V1_0_MAGICLIGHT" not in entries
    assert entries["VOXIE_CANON_V2_V13"]["predecessors"] == [
        "manifests/assets/voxie-canon-v1.0.magiclight.yaml"
    ]
    assert entries["VWW_CHARACTER_STATUS_V02"]["predecessors"] == [
        "manifests/characters/status-register-v01.yaml"
    ]
    assert (ROOT / "manifests/assets/voxie-canon-v1.0.magiclight.yaml").is_file()
    assert (ROOT / "manifests/characters/status-register-v01.yaml").is_file()
