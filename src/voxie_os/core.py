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
    "character_status": "character_status.schema.json",
    "authority_index": "authority_index.schema.json",
    "asset": "asset.schema.json",
    "beatmap": "beatmap.schema.json",
    "shot_manifest": "shot_manifest.schema.json",
    "benchmark": "benchmark.schema.json",
    "qc_report": "qc_report.schema.json",
    "release_readiness": "release_readiness.schema.json",
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


def _append_repository_file_error(
    errors: list[str], field: str, relative_path: str
) -> None:
    """Require a repository-local reference to resolve to an existing file."""
    repository_root = ROOT.resolve()
    target = (ROOT / relative_path).resolve()
    try:
        target.relative_to(repository_root)
    except ValueError:
        errors.append(
            f"{field}: referenced path must stay within repository: {relative_path}"
        )
        return
    if not target.is_file():
        errors.append(
            f"{field}: referenced repository file does not exist: {relative_path}"
        )


def _validate_library_routing_state(data: Any) -> list[str]:
    """Check intake counts and verify exact predecessor lineage."""
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
        expected_manifest = f"manifests/library-routing.v{previous}.yaml"
        if lineage["version"] != previous:
            errors.append(f"supersedes.version: expected {previous}")
        if lineage["manifest"] != expected_manifest:
            errors.append("supersedes.manifest: must reference the preceding manifest version")

        before_reference_errors = len(errors)
        _append_repository_file_error(
            errors,
            "supersedes.manifest",
            lineage["manifest"],
        )
        if len(errors) == before_reference_errors:
            predecessor = ROOT / lineage["manifest"]
            # Hash canonical LF text so existing Windows checkouts cannot fail
            # solely because the working tree was written with CRLF before the
            # repository added its YAML eol=lf attribute.
            predecessor_bytes = predecessor.read_bytes().replace(b"\r\n", b"\n")
            actual_sha256 = hashlib.sha256(predecessor_bytes).hexdigest()
            if lineage["sha256"].lower() != actual_sha256:
                errors.append(
                    "supersedes.sha256: expected "
                    f"{actual_sha256} for {lineage['manifest']}, "
                    f"got {lineage['sha256']}"
                )
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


def _validate_release_readiness(data: Any) -> list[str]:
    """Keep release records fail-closed and verify their repository references."""
    errors = []
    gate = data["release_gate"]
    platforms = data["platforms"]

    platform_names = [platform["platform"] for platform in platforms]
    if len(platform_names) != len(set(platform_names)):
        errors.append("platforms: platform names must be unique")

    unresolved = bool(gate["required_approvals"] or gate["blockers"])
    if unresolved:
        if gate["execution_authority"] != "BLOCKED":
            errors.append(
                "release_gate.execution_authority: must be BLOCKED while "
                "approvals or blockers remain"
            )
        for field in (
            "publication_authorized",
            "scheduling_authorized",
            "account_write_authorized",
        ):
            if gate[field]:
                errors.append(
                    f"release_gate.{field}: must be false while approvals or blockers remain"
                )
        for index, platform in enumerate(platforms):
            if platform["upload_authorized"]:
                errors.append(
                    f"platforms.{index}.upload_authorized: must be false while "
                    "approvals or blockers remain"
                )
            if platform["publish_authorized"]:
                errors.append(
                    f"platforms.{index}.publish_authorized: must be false while "
                    "approvals or blockers remain"
                )

    if not gate["account_write_authorized"]:
        for index, platform in enumerate(platforms):
            if platform["upload_authorized"]:
                errors.append(
                    f"platforms.{index}.upload_authorized: cannot be true while "
                    "account writes are unauthorized"
                )

    if not gate["publication_authorized"]:
        for index, platform in enumerate(platforms):
            if platform["publish_authorized"]:
                errors.append(
                    f"platforms.{index}.publish_authorized: cannot be true while "
                    "publication is unauthorized"
                )

    finding_rules = {
        finding["rule_id"]
        for finding in data["findings"]
        if finding["severity"] in {"warning", "error"}
    }
    missing_findings = sorted(set(gate["blockers"]) - finding_rules)
    if missing_findings:
        errors.append(
            "release_gate.blockers: every blocker requires a warning or error finding; "
            f"missing {', '.join(missing_findings)}"
        )

    referenced_paths = [("master.manifest", data["master"]["manifest"])]
    if "final_review_record" in data["master"]:
        referenced_paths.append(
            ("master.final_review_record", data["master"]["final_review_record"])
        )
    timing = data.get("timing_authority", {})
    for field in ("beatmap", "shot_manifest"):
        if field in timing:
            referenced_paths.append((f"timing_authority.{field}", timing[field]))
    distribution = data.get("distribution_package", {})
    if "authority_source" in distribution:
        referenced_paths.append(
            ("distribution_package.authority_source", distribution["authority_source"])
        )

    for field, relative_path in referenced_paths:
        _append_repository_file_error(errors, field, relative_path)

    if data["status"] == "RELEASED":
        if not gate["publication_authorized"]:
            errors.append(
                "release_gate.publication_authorized: must be true when status is RELEASED"
            )
        if not any(platform["publish_authorized"] for platform in platforms):
            errors.append(
                "platforms: at least one platform must be publish-authorized when status is RELEASED"
            )

    return errors


def _validate_character_status(data: Any) -> list[str]:
    """Validate character lock, routing, branch, and reference relationships."""
    errors = []
    required_categories = {
        "LOCKED_CANON",
        "APPROVED_BUT_UNLOCKED",
        "PARKED_ALTERNATIVE",
        "NEEDS_RECONCILIATION",
    }
    categories = set(data["status_categories"])
    if categories != required_categories:
        missing = sorted(required_categories - categories)
        extra = sorted(categories - required_categories)
        details = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"unexpected {', '.join(extra)}")
        errors.append(
            "status_categories: must contain the four canonical categories"
            + (f"; {'; '.join(details)}" if details else "")
        )

    try:
        datetime.strptime(data["recorded_date"], "%Y-%m-%d")
    except ValueError:
        errors.append("recorded_date: must be a real calendar date")

    character_ids = [character["character_id"] for character in data["characters"]]
    if len(character_ids) != len(set(character_ids)):
        errors.append("characters: character IDs must be unique")

    for index, character in enumerate(data["characters"]):
        prefix = f"characters.{index}"
        status = character["status_category"]
        production_use = character["production_use"]

        for ref_index, relative_path in enumerate(character["reference_assets"]):
            _append_repository_file_error(
                errors, f"{prefix}.reference_assets.{ref_index}", relative_path
            )

        if status == "LOCKED_CANON":
            if character["lock_level"] != "hard":
                errors.append(
                    f"{prefix}.lock_level: LOCKED_CANON requires hard lock level"
                )
            if production_use != "ALLOWED_WITH_LOCK":
                errors.append(
                    f"{prefix}.production_use: LOCKED_CANON requires ALLOWED_WITH_LOCK"
                )
            if not character["reference_assets"]:
                errors.append(
                    f"{prefix}.reference_assets: LOCKED_CANON requires at least one repository authority"
                )
            provider = character.get("provider_authority")
            if provider is not None and provider["qc_status"] != "PASS":
                errors.append(
                    f"{prefix}.provider_authority.qc_status: locked provider authority must be PASS"
                )
        elif production_use == "ALLOWED_WITH_LOCK":
            errors.append(
                f"{prefix}.production_use: only LOCKED_CANON may use ALLOWED_WITH_LOCK"
            )

        blockers = character.get("blockers", [])
        if status == "APPROVED_BUT_UNLOCKED":
            if production_use != "BLOCKED_UNTIL_PREVIEW_LOCK":
                errors.append(
                    f"{prefix}.production_use: APPROVED_BUT_UNLOCKED requires BLOCKED_UNTIL_PREVIEW_LOCK"
                )
            if not blockers:
                errors.append(
                    f"{prefix}.blockers: APPROVED_BUT_UNLOCKED requires unresolved blockers"
                )

        if status == "NEEDS_RECONCILIATION":
            if production_use != "BLOCKED_UNTIL_RECONCILED":
                errors.append(
                    f"{prefix}.production_use: NEEDS_RECONCILIATION requires BLOCKED_UNTIL_RECONCILED"
                )
            branches = character.get("branches", [])
            if len(branches) < 2:
                errors.append(
                    f"{prefix}.branches: NEEDS_RECONCILIATION requires at least two branches"
                )
            branch_ids = [branch["branch_id"] for branch in branches]
            if len(branch_ids) != len(set(branch_ids)):
                errors.append(f"{prefix}.branches: branch IDs must be unique")
            for branch_index, branch in enumerate(branches):
                if branch["status"] != "HISTORICAL_PRODUCTION_BRANCH":
                    errors.append(
                        f"{prefix}.branches.{branch_index}.status: reconciliation branches must remain HISTORICAL_PRODUCTION_BRANCH"
                    )
            if not blockers:
                errors.append(
                    f"{prefix}.blockers: NEEDS_RECONCILIATION requires unresolved blockers"
                )

        if status == "PARKED_ALTERNATIVE" and production_use not in {"PARKED", "BLOCKED"}:
            errors.append(
                f"{prefix}.production_use: PARKED_ALTERNATIVE must remain PARKED or BLOCKED"
            )

        for alternative_index, alternative in enumerate(
            character.get("parked_alternatives", [])
        ):
            if alternative["may_replace_locked_canon"]:
                errors.append(
                    f"{prefix}.parked_alternatives.{alternative_index}.may_replace_locked_canon: must be false"
                )

    return errors


def _validate_authority_index(data: Any) -> list[str]:
    """Validate current authority uniqueness, lineage, references, and nested contracts."""
    errors = []

    try:
        datetime.strptime(data["recorded_date"], "%Y-%m-%d")
    except ValueError:
        errors.append("recorded_date: must be a real calendar date")

    authority_ids = [entry["authority_id"] for entry in data["entries"]]
    if len(authority_ids) != len(set(authority_ids)):
        errors.append("entries: authority IDs must be unique")

    paths = [entry["path"] for entry in data["entries"]]
    if len(paths) != len(set(paths)):
        errors.append("entries: authority paths must be unique")

    media_extensions = {
        ".aac",
        ".flac",
        ".jpeg",
        ".jpg",
        ".m4a",
        ".mov",
        ".mp3",
        ".mp4",
        ".png",
        ".wav",
        ".webm",
    }

    for index, entry in enumerate(data["entries"]):
        prefix = f"entries.{index}"
        path = entry["path"]

        if data["policy"]["current_entries_only"] and not entry["current"]:
            errors.append(
                f"{prefix}.current: must be true while policy.current_entries_only is true"
            )

        if Path(path).suffix.lower() in media_extensions:
            errors.append(
                f"{prefix}.path: authority index must reference control records, not media binaries"
            )

        before_reference_errors = len(errors)
        _append_repository_file_error(errors, f"{prefix}.path", path)
        target_is_valid = len(errors) == before_reference_errors

        predecessors = entry.get("predecessors", [])
        if path in predecessors:
            errors.append(f"{prefix}.predecessors: cannot include the current path")
        for predecessor_index, predecessor in enumerate(predecessors):
            _append_repository_file_error(
                errors,
                f"{prefix}.predecessors.{predecessor_index}",
                predecessor,
            )

        if entry["publication_authorized"] and entry["authority_state"] != "RELEASED":
            errors.append(
                f"{prefix}.publication_authorized: requires authority_state RELEASED"
            )

        validation_kind = entry.get("validation_kind")
        if validation_kind is not None and target_is_valid:
            nested_errors = validate(validation_kind, load_data(ROOT / path))
            for nested_error in nested_errors:
                errors.append(
                    f"{prefix}.validation_kind: {path} failed {validation_kind}: {nested_error}"
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
    if kind == "release_readiness" and not errors:
        errors.extend(_validate_release_readiness(data))
    if kind == "character_status" and not errors:
        errors.extend(_validate_character_status(data))
    if kind == "authority_index" and not errors:
        errors.extend(_validate_authority_index(data))
    return errors


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
