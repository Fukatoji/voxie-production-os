from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from jsonschema import Draft202012Validator, validators


def _is_finite_number(_checker: Any, value: Any) -> bool:
    """Keep JSON numbers finite, including values loaded from YAML or Python."""
    if not Draft202012Validator.TYPE_CHECKER.is_type(value, "number"):
        return False
    # Python integers are finite without conversion to a possibly overflowing float.
    if isinstance(value, int):
        return True
    try:
        return math.isfinite(value)
    except (TypeError, ValueError, OverflowError):
        return False


FiniteNumberValidator = validators.extend(
    Draft202012Validator,
    type_checker=Draft202012Validator.TYPE_CHECKER.redefine("number", _is_finite_number),
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"

SCHEMA_FILES = {
    "canon": "canon.schema.json",
    "asset": "asset.schema.json",
    "beatmap": "beatmap.schema.json",
    "shot_manifest": "shot_manifest.schema.json",
    "benchmark": "benchmark.schema.json",
    "qc_report": "qc_report.schema.json",
    "library_routing": "library_routing.schema.json",
    "alignment": "alignment.schema.json",
    "benchmark_suite": "benchmark_suite.schema.json",
    "provider_catalog": "provider_catalog.schema.json",
    "provider_job": "provider_job.schema.json",
    "production_state": "production_state.schema.json",
}


def load_data(path: str | Path) -> Any:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def save_json(path: str | Path, data: Any) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def schema_for(kind: str) -> dict[str, Any]:
    if kind not in SCHEMA_FILES:
        raise KeyError(f"Unknown schema kind: {kind}")
    return json.loads((SCHEMAS / SCHEMA_FILES[kind]).read_text(encoding="utf-8"))


def _validate_library_routing_state(data: Any) -> list[str]:
    """Check relationships only after the manifest schema has passed."""
    status = data["current_intake_status"]
    unresolved = status["unresolved"]
    unresolved_count = status["unresolved_count"]
    errors = []
    # JSON Schema also accepts integer-valued floats such as 2.0.
    if unresolved_count != len(unresolved):
        errors.append(
            "current_intake_status.unresolved_count: "
            f"expected {len(unresolved)} to match unresolved items, got {unresolved_count}"
        )
    if data["version"] > 1:
        previous = int(data["version"]) - 1
        lineage = data["supersedes"]
        if lineage["version"] != previous:
            errors.append(f"supersedes.version: expected {previous}")
        if lineage["manifest"] != f"manifests/library-routing.v{previous}.yaml":
            errors.append("supersedes.manifest: must reference the preceding manifest version")
    return errors


def _validate_production_state(data: Any) -> list[str]:
    """Validate cross-field audit, balance, spend, and lineage relationships."""
    errors = []

    try:
        recorded_at = datetime.strptime(
            data["recorded_at_utc"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        errors.append(
            "recorded_at_utc: must be a real RFC 3339 UTC timestamp "
            "in YYYY-MM-DDTHH:MM:SSZ form"
        )
        recorded_at = None

    try:
        local_date = datetime.strptime(
            data["production_date_local"], "%Y-%m-%d"
        ).date()
    except ValueError:
        errors.append("production_date_local: must be a real calendar date")
        local_date = None

    try:
        production_zone = ZoneInfo(data["production_timezone"])
    except ZoneInfoNotFoundError:
        errors.append("production_timezone: must be a recognized IANA timezone")
        production_zone = None

    if recorded_at is not None and local_date is not None and production_zone is not None:
        expected_local_date = recorded_at.astimezone(production_zone).date()
        if local_date != expected_local_date:
            errors.append(
                "production_date_local: expected "
                f"{expected_local_date.isoformat()} from recorded_at_utc in "
                f"{data['production_timezone']}, got {local_date.isoformat()}"
            )

    balance = data["spend_and_balance_gate"]
    expected_discrepancy = abs(
        balance["separately_displayed_balance"]
        - balance["recorded_post_generation_balance"]
    )
    if balance["discrepancy_credits"] != expected_discrepancy:
        errors.append(
            "spend_and_balance_gate.discrepancy_credits: expected "
            f"{expected_discrepancy}, got {balance['discrepancy_credits']}"
        )

    if expected_discrepancy > 0 and not balance["reconcile_before_any_future_spend"]:
        errors.append(
            "spend_and_balance_gate.reconcile_before_any_future_spend: "
            "must be true while account balances differ"
        )

    spend_blocked = (
        expected_discrepancy > 0
        or balance["reconcile_before_any_future_spend"]
        or data["continuation"]["zero_cost_only"]
    )
    if balance["spend_authorized"] and spend_blocked:
        errors.append(
            "spend_and_balance_gate.spend_authorized: must be false while "
            "balance reconciliation is required or continuation is zero-cost-only"
        )

    lineage = data["external_media"]["stable_asset_ids_and_checksums"]
    if lineage["status"] == "VERIFIED":
        asset_ids = set(lineage["stable_asset_ids"])
        checksum_ids = set(lineage["sha256_checksums"])
        if asset_ids != checksum_ids:
            errors.append(
                "external_media.stable_asset_ids_and_checksums: VERIFIED "
                "asset IDs must exactly match SHA-256 checksum keys"
            )

    return errors


def validate(kind: str, data: Any) -> list[str]:
    validator = FiniteNumberValidator(schema_for(kind))
    errors = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        where = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{where}: {err.message}")
    if kind == "library_routing" and not errors:
        errors.extend(_validate_library_routing_state(data))
    if kind == "production_state" and not errors:
        errors.extend(_validate_production_state(data))
    return errors


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
