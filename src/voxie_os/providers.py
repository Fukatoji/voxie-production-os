from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .core import validate


TERMINAL_JOB_STATUSES = {"EXECUTED", "FAILED", "CANCELLED"}
MUTATING_RISK_CLASSES = {"creates_asset", "publishing", "canon_mutation", "destructive"}
OUTPUT_PRODUCING_RISK_CLASSES = {"creates_asset", "canon_mutation"}
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _approved_gate(
    approvals: list[dict[str, Any]],
    gate: str,
    provider: str,
    operation: str,
    maximum_credits: float | None,
) -> bool:
    for approval in approvals:
        if approval.get("gate") != gate or approval.get("status") != "APPROVED":
            continue
        scope = approval.get("scope", {})
        if scope.get("provider") != provider:
            continue
        if scope.get("operation") != operation:
            continue
        if gate == "CREDIT_SPEND" and maximum_credits is not None:
            if scope.get("max_credits", -1) < maximum_credits:
                continue
        return True
    return False


def _referenced_asset_ids(value: Any) -> set[str]:
    """Collect stable asset IDs from provider inputs without treating prose as lineage."""
    references: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "asset_id" or key.endswith("_asset_id"):
                if isinstance(child, str) and child:
                    references.add(child)
            elif key == "asset_ids" or key.endswith("_asset_ids"):
                if isinstance(child, list):
                    references.update(item for item in child if isinstance(item, str) and item)
            else:
                references.update(_referenced_asset_ids(child))
    elif isinstance(value, list):
        for child in value:
            references.update(_referenced_asset_ids(child))
    return references


def _validate_asset_lineage(job: dict[str, Any], risk_class: str) -> list[str]:
    lineage = job.get("asset_lineage")
    if not isinstance(lineage, dict):
        return ["asset_lineage is required"]

    errors: list[str] = []
    lineage_inputs = lineage.get("inputs", [])
    if not isinstance(lineage_inputs, list):
        return ["asset_lineage.inputs must be an array"]
    for index, item in enumerate(lineage_inputs):
        if not isinstance(item, dict):
            errors.append(f"asset_lineage input {index} must be an object")
            continue
        if not isinstance(item.get("asset_id"), str) or not item["asset_id"]:
            errors.append(f"asset_lineage input {index} requires an asset_id")
        if item.get("status") not in {"approved", "locked"}:
            errors.append("asset_lineage inputs must have approved or locked status")
        if not isinstance(item.get("version"), str) or not item["version"]:
            errors.append(f"asset_lineage input {index} requires a version")
        if not isinstance(item.get("sha256"), str) or not SHA256_PATTERN.fullmatch(item["sha256"]):
            errors.append(f"asset_lineage input {index} requires a lowercase SHA-256 checksum")
    lineage_ids = [item.get("asset_id") for item in lineage_inputs if isinstance(item, dict)]
    if len(lineage_ids) != len(set(lineage_ids)):
        errors.append("asset_lineage input asset IDs must be unique")

    referenced_ids = _referenced_asset_ids(job.get("inputs", {}))
    declared_ids = {asset_id for asset_id in lineage_ids if isinstance(asset_id, str)}
    missing = sorted(referenced_ids - declared_ids)
    undeclared = sorted(declared_ids - referenced_ids)
    if missing:
        errors.append(f"asset_lineage is missing referenced inputs: {', '.join(missing)}")
    if undeclared:
        errors.append(f"asset_lineage contains inputs not used by the job: {', '.join(undeclared)}")

    output_asset_id = lineage.get("output_asset_id")
    output_asset_version = lineage.get("output_asset_version")
    if risk_class in OUTPUT_PRODUCING_RISK_CLASSES and not output_asset_id:
        errors.append("asset_lineage.output_asset_id is required for mutating operations")
    if risk_class in OUTPUT_PRODUCING_RISK_CLASSES and not output_asset_version:
        errors.append("asset_lineage.output_asset_version is required for mutating operations")
    if risk_class == "read_only" and (output_asset_id is not None or output_asset_version is not None):
        errors.append("read-only operations cannot declare an output asset or version")
    return errors


def _invalid_provider_plan(validation_errors: list[str]) -> dict[str, Any]:
    """Return the plan envelope without interpreting or copying invalid inputs."""
    return {
        "plan_version": "1.0",
        "job_id": None,
        "project_id": None,
        "provider": None,
        "provider_display_name": None,
        "operation": None,
        "transport_preference": [],
        "runtime_connection_check_required": True,
        "risk_class": None,
        "chargeable": None,
        "budget": {
            "estimated_credits": None,
            "max_credits": None,
            "status": "NOT_EVALUATED",
        },
        "required_approvals": [],
        "missing_approvals": [],
        "validation_errors": validation_errors,
        "asset_lineage": None,
        "status": "INVALID_REQUEST",
        "external_execution_authorized": False,
        "execution_performed": False,
        "safety": {
            "credentials_stored_in_repository": False,
            "runtime_balance_stored_in_repository": False,
            "automatic_publish": False,
            "automatic_canon_promotion": False,
        },
    }


def build_provider_plan(catalog: Any, job: Any) -> dict[str, Any]:
    """Evaluate a provider job without contacting or mutating an external service."""
    validation_errors = [
        *(f"provider catalog schema: {error}" for error in validate("provider_catalog", catalog)),
        *(f"provider job schema: {error}" for error in validate("provider_job", job)),
    ]
    if validation_errors:
        return _invalid_provider_plan(validation_errors)

    provider_id = job["provider"]
    operation_id = job["operation"]
    providers = catalog.get("providers", {})
    if provider_id not in providers:
        raise ValueError(f"Unknown provider: {provider_id}")

    provider = providers[provider_id]
    capabilities = provider.get("capabilities", {})
    if operation_id not in capabilities:
        raise ValueError(f"Unsupported operation for {provider_id}: {operation_id}")

    capability = capabilities[operation_id]
    required = list(capability.get("approval_gates", []))
    approvals = job.get("approvals", [])
    estimated = job.get("estimated_credits")
    maximum = job.get("max_credits")
    chargeable = bool(capability.get("chargeable", False))
    risk_class = capability.get("risk_class")
    job_status = job.get("status")

    validation_errors.extend(_validate_asset_lineage(job, risk_class))
    if "ASSET_UPLOAD" in required and not _referenced_asset_ids(job.get("inputs", {})):
        validation_errors.append("ASSET_UPLOAD operations require at least one referenced input asset")
    invariant_gates = {
        "creates_asset": "CREATE_MEDIA",
        "publishing": "PUBLISH_CONTENT",
        "canon_mutation": "CANON_LOCK",
        "destructive": "DESTRUCTIVE_ACTION",
    }
    invariant_gate = invariant_gates.get(risk_class)
    if invariant_gate and invariant_gate not in required:
        validation_errors.append(
            f"provider catalog must require {invariant_gate} for {capability['risk_class']} operations"
        )
    if chargeable and "CREDIT_SPEND" not in required:
        validation_errors.append("provider catalog must require CREDIT_SPEND for chargeable operations")
    if chargeable and estimated is None:
        validation_errors.append("estimated_credits is required for a chargeable operation")
    if chargeable and maximum is None:
        validation_errors.append("max_credits is required for a chargeable operation")

    budget_status = "NOT_APPLICABLE"
    if chargeable and estimated is not None and maximum is not None:
        budget_status = "WITHIN_LIMIT" if estimated <= maximum else "EXCEEDS_LIMIT"

    missing = [
        gate
        for gate in required
        if not _approved_gate(approvals, gate, provider_id, operation_id, maximum)
    ]

    if validation_errors:
        status = "INVALID_REQUEST"
    elif catalog.get("status") != "ACTIVE":
        status = "BLOCKED_CATALOG_INACTIVE"
    elif job_status in TERMINAL_JOB_STATUSES:
        status = "BLOCKED_JOB_TERMINAL"
    elif budget_status == "EXCEEDS_LIMIT":
        status = "BLOCKED_BUDGET"
    elif missing:
        status = "BLOCKED_APPROVAL"
    elif risk_class in MUTATING_RISK_CLASSES and job_status != "APPROVED":
        status = "BLOCKED_JOB_STATUS"
    elif provider.get("connection_state") == "UNAVAILABLE":
        status = "BLOCKED_PROVIDER_UNAVAILABLE"
    elif capability.get("execution_status") != "AVAILABLE":
        status = "BLOCKED_PROVIDER_UNAVAILABLE"
    elif risk_class == "read_only":
        status = "READY_READ_ONLY"
    else:
        status = "READY_FOR_PROVIDER_EXECUTION"

    return {
        "plan_version": "1.0",
        "job_id": job["job_id"],
        "project_id": job["project_id"],
        "provider": provider_id,
        "provider_display_name": provider["display_name"],
        "operation": operation_id,
        "transport_preference": deepcopy(provider["transports"]),
        "runtime_connection_check_required": provider.get("connection_state") == "RUNTIME_CHECK_REQUIRED",
        "risk_class": risk_class,
        "chargeable": chargeable,
        "budget": {
            "estimated_credits": estimated,
            "max_credits": maximum,
            "status": budget_status,
        },
        "required_approvals": required,
        "missing_approvals": missing,
        "validation_errors": validation_errors,
        "asset_lineage": deepcopy(job.get("asset_lineage")),
        "status": status,
        "external_execution_authorized": status in {"READY_READ_ONLY", "READY_FOR_PROVIDER_EXECUTION"},
        "execution_performed": False,
        "safety": {
            "credentials_stored_in_repository": False,
            "runtime_balance_stored_in_repository": False,
            "automatic_publish": False,
            "automatic_canon_promotion": False,
        },
    }
