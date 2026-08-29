from copy import deepcopy
from pathlib import Path
import sys
import zoneinfo

from jsonschema import Draft202012Validator

from voxie_os.cli import main
from voxie_os.core import SCHEMA_FILES, load_data, schema_for, validate


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests/productions/rainbow-colors/production-state-v01.yaml"


def _manifest():
    return deepcopy(load_data(MANIFEST))


def test_production_state_schema_is_registered_and_valid():
    assert SCHEMA_FILES["production_state"] == "production_state.schema.json"
    Draft202012Validator.check_schema(schema_for("production_state"))


def test_rainbow_colors_production_state_validates():
    assert validate("production_state", _manifest()) == []


def test_timezone_validation_has_packaged_iana_fallback():
    original_tzpath = zoneinfo.TZPATH
    zoneinfo.reset_tzpath(())
    zoneinfo.ZoneInfo.clear_cache()
    try:
        assert validate("production_state", _manifest()) == []
    finally:
        zoneinfo.reset_tzpath(original_tzpath)
        zoneinfo.ZoneInfo.clear_cache()


def test_cli_validates_rainbow_colors_production_state(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["voxie-os", "validate", "production_state", str(MANIFEST)],
    )
    assert main() == 0
    assert capsys.readouterr().out == "PASS\n"


def test_pending_lineage_cannot_authorize_media_execution():
    manifest = _manifest()
    manifest["authority_scope"]["execution_authority"] = "AUTHORIZED"
    manifest["authority_scope"]["execution_blockers"] = []

    errors = validate("production_state", manifest)

    assert any(
        error.startswith("authority_scope.execution_authority:")
        for error in errors
    )
    assert sum(
        error.startswith("authority_scope.execution_blockers:")
        for error in errors
    ) >= 2


def test_pending_lineage_requires_both_missing_lineage_blockers():
    manifest = _manifest()
    manifest["authority_scope"]["execution_blockers"].remove(
        "MISSING_SHA256_CHECKSUMS"
    )

    errors = validate("production_state", manifest)

    assert any(
        error.startswith("authority_scope.execution_blockers:")
        for error in errors
    )


def test_pending_lineage_rejects_invented_identifiers_or_checksums():
    manifest = _manifest()
    lineage = manifest["external_media"]["stable_asset_ids_and_checksums"]
    lineage["stable_asset_ids"] = ["invented-id"]
    lineage["sha256_checksums"] = {"invented-id": "a" * 64}

    errors = validate("production_state", manifest)

    assert any(
        error.startswith(
            "external_media.stable_asset_ids_and_checksums.stable_asset_ids:"
        )
        for error in errors
    )
    assert any(
        error.startswith(
            "external_media.stable_asset_ids_and_checksums.sha256_checksums:"
        )
        for error in errors
    )


def test_verified_lineage_requires_exact_asset_checksum_mapping():
    manifest = _manifest()
    lineage = manifest["external_media"]["stable_asset_ids_and_checksums"]
    lineage["status"] = "VERIFIED"
    lineage["stable_asset_ids"] = ["asset-a"]
    lineage["sha256_checksums"] = {"asset-b": "b" * 64}

    assert validate("production_state", manifest) == [
        "external_media.stable_asset_ids_and_checksums: VERIFIED "
        "asset IDs must exactly match SHA-256 checksum keys"
    ]


def test_audit_timestamp_must_resolve_to_local_production_date():
    manifest = _manifest()
    manifest["production_date_local"] = "2026-08-29"

    assert validate("production_state", manifest) == [
        "production_date_local: expected 2026-08-28 from recorded_at_utc "
        "in America/Chicago, got 2026-08-29"
    ]


def test_audit_timestamp_must_be_a_real_utc_instant():
    manifest = _manifest()
    manifest["recorded_at_utc"] = "2026-13-40T25:61:61Z"

    assert validate("production_state", manifest) == [
        "recorded_at_utc: must be a real RFC 3339 UTC timestamp "
        "in YYYY-MM-DDTHH:MM:SSZ form"
    ]


def test_balance_discrepancy_must_reconcile():
    manifest = _manifest()
    manifest["spend_and_balance_gate"]["discrepancy_credits"] = 91

    assert validate("production_state", manifest) == [
        "spend_and_balance_gate.discrepancy_credits: expected 90, got 91"
    ]


def test_balance_difference_requires_reconciliation_gate():
    manifest = _manifest()
    manifest["spend_and_balance_gate"]["reconcile_before_any_future_spend"] = False

    assert validate("production_state", manifest) == [
        "spend_and_balance_gate.reconcile_before_any_future_spend: "
        "must be true while account balances differ"
    ]


def test_unresolved_balance_cannot_authorize_spend():
    manifest = _manifest()
    manifest["spend_and_balance_gate"]["spend_authorized"] = True

    assert validate("production_state", manifest) == [
        "spend_and_balance_gate.spend_authorized: must be false while "
        "balance reconciliation is required or continuation is zero-cost-only"
    ]


def test_zero_cost_continuation_cannot_authorize_spend():
    manifest = _manifest()
    balance = manifest["spend_and_balance_gate"]
    balance["recorded_post_generation_balance"] = 86395
    balance["discrepancy_credits"] = 0
    balance["reconcile_before_any_future_spend"] = False
    balance["spend_authorized"] = True

    assert validate("production_state", manifest) == [
        "spend_and_balance_gate.spend_authorized: must be false while "
        "balance reconciliation is required or continuation is zero-cost-only"
    ]


V03_MANIFEST = ROOT / "manifests/productions/rainbow-colors/production-state-v03.yaml"


def _v03_manifest():
    return deepcopy(load_data(V03_MANIFEST))


def test_rainbow_colors_v03_validates():
    assert validate("production_state", _v03_manifest()) == []


def test_v03_classifies_every_s04_s37_shot_once():
    manifest = _v03_manifest()
    expected = {
        "READY_EXISTING_SOURCE": 11,
        "MISSING_APPROVED_SOURCE": 8,
        "NEW_PIXELS_REQUIRED": 15,
    }
    observed = {}
    for number in range(4, 38):
        shot = manifest["recorded_progress"][f"S{number:02d}"]
        observed[shot["classification"]] = observed.get(shot["classification"], 0) + 1

    assert observed == expected
    assert sum(observed.values()) == 34


def test_v03_preserves_protected_timing_and_s03_review_gate():
    manifest = _v03_manifest()
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

    motion = manifest["recorded_progress"]["S03"]["motion_review"]
    assert motion["status"] == "PENDING"
    assert motion["execution_performed"] is False
    assert motion["credits_spent"] == 0
    assert motion["blocker"] == "LOCKED_SOURCE_BINARY_NOT_MOUNTED"
    assert motion["no_substitution"] is True


def test_v03_closes_creative_bucket_without_authorizing_generation():
    manifest = _v03_manifest()
    classifications = {
        manifest["recorded_progress"][f"S{number:02d}"]["classification"]
        for number in range(4, 38)
    }
    assert "CREATIVE_DECISION_REQUIRED" not in classifications
    assert manifest["recorded_progress"]["S05"]["dependency"] == (
        "S04 review candidate approval"
    )
    assert manifest["recorded_progress"]["S32"]["parked_assets_may_substitute"] is False
    assert manifest["recorded_progress"]["S33"]["classification"] == (
        "MISSING_APPROVED_SOURCE"
    )


def test_v03_magiclight_and_new_pixel_gates_fail_closed():
    manifest = _v03_manifest()
    assert manifest["spend_and_balance_gate"]["spend_authorized"] is False
    assert manifest["spend_and_balance_gate"]["reconcile_before_any_future_spend"] is True

    new_pixel_shots = [
        manifest["recorded_progress"][f"S{number:02d}"]
        for number in range(4, 38)
        if manifest["recorded_progress"][f"S{number:02d}"]["classification"]
        == "NEW_PIXELS_REQUIRED"
    ]
    assert len(new_pixel_shots) == 15
    for shot in new_pixel_shots:
        gate = shot["credit_gate"]
        assert gate["required_before_generation"] is True
        assert gate["spend_authorized"] is False
        assert gate["magiclight_live_balance_state"] == (
            "UNVERIFIED_NO_AUTHENTICATED_SESSION"
        )
