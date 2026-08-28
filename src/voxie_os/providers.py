from __future__ import annotations

from copy import deepcopy
from typing import Any


def _approved_gate(
    approvals: list[dict[str, Any]],
    gate: str,
    provider: str,
    operation: str,
    estimated_credits: float | None,
) -> bool:
    for approval in approvals:
        if approval.get("gate") != gate or approval.get("status") != "APPROVED":
            continue
        scope = approval.get("scope", {})
        if scope.get("provider") not in {provider, "*"}:
            continue
        if scope.get("operation") not in {operation, "*"}:
            continue
        if gate == "CREDIT_SPEND" and estimated_credits is not None:
            if scope.get("max_credits", -1) < estimated_credits:
                continue
        return True
    return False


def build_provider_plan(catalog: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a provider job without contacting or mutating an external service."""
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

    validation_errors: list[str] = []
    invariant_gates = {
        "creates_asset": "CREATE_MEDIA",
        "publishing": "PUBLISH_CONTENT",
        "canon_mutation": "CANON_LOCK",
        "destructive": "DESTRUCTIVE_ACTION",
    }
    invariant_gate = invariant_gates.get(capability.get("risk_class"))
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
        if not _approved_gate(approvals, gate, provider_id, operation_id, estimated)
    ]

    if validation_errors:
        status = "INVALID_REQUEST"
    elif budget_status == "EXCEEDS_LIMIT":
        status = "BLOCKED_BUDGET"
    elif missing:
        status = "BLOCKED_APPROVAL"
    elif provider.get("connection_state") == "UNAVAILABLE":
        status = "BLOCKED_PROVIDER_UNAVAILABLE"
    elif capability.get("execution_status") != "AVAILABLE":
        status = "BLOCKED_PROVIDER_UNAVAILABLE"
    elif capability.get("risk_class") == "read_only":
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
        "risk_class": capability["risk_class"],
        "chargeable": chargeable,
        "budget": {
            "estimated_credits": estimated,
            "max_credits": maximum,
            "status": budget_status,
        },
        "required_approvals": required,
        "missing_approvals": missing,
        "validation_errors": validation_errors,
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
