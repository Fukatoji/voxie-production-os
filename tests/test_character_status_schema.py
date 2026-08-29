from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from voxie_os.core import SCHEMA_FILES, load_data, schema_for, validate


ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "manifests/characters/status-register-v01.yaml"


def _register():
    return deepcopy(load_data(REGISTER_PATH))


def _characters(register):
    return {item["character_id"]: item for item in register["characters"]}


def test_character_status_schema_is_registered_and_valid():
    assert SCHEMA_FILES["character_status"] == "character_status.schema.json"
    Draft202012Validator.check_schema(schema_for("character_status"))
    assert validate("character_status", _register()) == []


def test_recorded_date_must_be_a_real_calendar_date():
    register = _register()
    register["recorded_date"] = "2026-02-31"

    assert validate("character_status", register) == [
        "recorded_date: must be a real calendar date"
    ]


def test_character_ids_must_be_unique():
    register = _register()
    register["characters"][1]["character_id"] = "VOXIE"

    assert validate("character_status", register) == [
        "characters: character IDs must be unique"
    ]


def test_locked_canon_requires_hard_lock_reference_and_allowed_use():
    register = _register()
    voxie = _characters(register)["VOXIE"]
    voxie["lock_level"] = "layered"
    voxie["production_use"] = "BLOCKED"
    voxie["reference_assets"] = []

    assert validate("character_status", register) == [
        "characters.0.lock_level: LOCKED_CANON requires hard lock level",
        "characters.0.production_use: LOCKED_CANON requires ALLOWED_WITH_LOCK",
        "characters.0.reference_assets: LOCKED_CANON requires at least one repository authority",
    ]


def test_locked_provider_authority_requires_qc_pass():
    register = _register()
    _characters(register)["VOXIE"]["provider_authority"]["qc_status"] = "REVIEW"

    assert validate("character_status", register) == [
        "characters.0.provider_authority.qc_status: locked provider authority must be PASS"
    ]


def test_non_locked_character_cannot_be_production_allowed():
    register = _register()
    _characters(register)["LUMI"]["production_use"] = "ALLOWED_WITH_LOCK"

    errors = validate("character_status", register)

    assert "characters.1.production_use: only LOCKED_CANON may use ALLOWED_WITH_LOCK" in errors
    assert (
        "characters.1.production_use: APPROVED_BUT_UNLOCKED requires "
        "BLOCKED_UNTIL_PREVIEW_LOCK"
    ) in errors


def test_reconciliation_branch_ids_must_be_unique():
    register = _register()
    navi = _characters(register)["NAVI"]
    navi["branches"][1]["branch_id"] = navi["branches"][0]["branch_id"]

    assert validate("character_status", register) == [
        "characters.2.branches: branch IDs must be unique"
    ]


def test_reconciliation_branches_remain_historical():
    register = _register()
    _characters(register)["HUMPTY"]["branches"][0]["status"] = "ACTIVE"

    assert validate("character_status", register) == [
        "characters.3.branches.0.status: reconciliation branches must remain "
        "HISTORICAL_PRODUCTION_BRANCH"
    ]


def test_reference_asset_must_exist_inside_repository():
    register = _register()
    _characters(register)["VOXIE"]["reference_assets"] = [
        "manifests/assets/missing-voxie.yaml"
    ]

    assert validate("character_status", register) == [
        "characters.0.reference_assets.0: referenced repository file does not exist: "
        "manifests/assets/missing-voxie.yaml"
    ]


def test_reference_asset_cannot_escape_repository():
    register = _register()
    _characters(register)["VOXIE"]["reference_assets"] = [
        "manifests/../../etc/passwd"
    ]

    assert validate("character_status", register) == [
        "characters.0.reference_assets.0: referenced path must stay within repository: "
        "manifests/../../etc/passwd"
    ]


def test_parked_alternative_cannot_replace_locked_canon():
    register = _register()
    _characters(register)["VOXIE"]["parked_alternatives"][0][
        "may_replace_locked_canon"
    ] = True

    assert validate("character_status", register) == [
        "characters.0.parked_alternatives.0.may_replace_locked_canon: must be false"
    ]
