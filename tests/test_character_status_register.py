from pathlib import Path

from voxie_os.core import load_data, validate


ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "manifests/characters/status-register-v01.yaml"
VOXIE_ASSET_PATH = ROOT / "manifests/assets/voxie-canon-v1.0.magiclight.yaml"


def _register():
    return load_data(REGISTER_PATH)


def _by_id():
    return {item["character_id"]: item for item in _register()["characters"]}


def test_character_status_register_validates():
    assert validate("character_status", _register()) == []


def test_register_starts_with_four_required_characters():
    register = _register()
    assert register["register_status"] == "ACTIVE"
    assert [item["character_id"] for item in register["characters"]] == [
        "VOXIE",
        "LUMI",
        "NAVI",
        "HUMPTY",
    ]


def test_voxie_locked_authority_matches_asset_manifest():
    characters = _by_id()
    voxie = characters["VOXIE"]
    asset = load_data(VOXIE_ASSET_PATH)

    assert voxie["status_category"] == "LOCKED_CANON"
    assert voxie["lock_level"] == "hard"
    assert voxie["production_use"] == "ALLOWED_WITH_LOCK"
    assert voxie["provider_authority"]["provider"] == asset["provenance"]["provider"]
    assert voxie["provider_authority"]["reusable_asset_id"] == asset["provenance"][
        "reusable_asset_id"
    ]
    assert voxie["provider_authority"]["preview_task_id"] == asset["provenance"][
        "preview_task_id"
    ]
    assert voxie["provider_authority"]["qc_status"] == asset["qc_status"]
    assert voxie["reference_assets"] == [
        "manifests/assets/voxie-canon-v1.0.magiclight.yaml"
    ]
    assert all((ROOT / path).exists() for path in voxie["reference_assets"])
    assert voxie["parked_alternatives"][0]["may_replace_locked_canon"] is False


def test_approved_but_unlocked_character_fails_closed():
    lumi = _by_id()["LUMI"]

    assert lumi["status_category"] == "APPROVED_BUT_UNLOCKED"
    assert lumi["production_use"] == "BLOCKED_UNTIL_PREVIEW_LOCK"
    assert lumi["reference_assets"] == []
    assert {
        "NO_APPROVED_PROVIDER_PREVIEW",
        "NO_REUSABLE_ASSET_ID",
        "NO_LOCKED_REFERENCE_PACKAGE",
    }.issubset(lumi["blockers"])


def test_reconciliation_characters_preserve_branch_separation():
    characters = _by_id()

    for character_id in ("NAVI", "HUMPTY"):
        character = characters[character_id]
        assert character["status_category"] == "NEEDS_RECONCILIATION"
        assert character["production_use"] == "BLOCKED_UNTIL_RECONCILED"
        assert len(character["branches"]) == 2
        assert all(
            branch["status"] == "HISTORICAL_PRODUCTION_BRANCH"
            for branch in character["branches"]
        )
        assert "NO_SINGLE_GLOBAL_CANON_DECISION" in character["blockers"]


def test_no_unlocked_or_unreconciled_character_is_production_allowed():
    for character in _register()["characters"]:
        if character["status_category"] != "LOCKED_CANON":
            assert character["production_use"] != "ALLOWED_WITH_LOCK"
