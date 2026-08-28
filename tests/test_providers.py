from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
import yaml

from voxie_os.cli import main
from voxie_os.core import load_data, validate
from voxie_os.providers import build_provider_plan

ROOT = Path(__file__).resolve().parents[1]
CATALOG = load_data(ROOT / "config/providers.v1.yaml")


@pytest.fixture
def approved_job():
    job = load_data(ROOT / "examples/provider-job.higgsfield-animation.yaml")
    job["status"] = "APPROVED"
    job["approvals"] = [
        {
            "approval_id": f"HF-{gate}",
            "gate": gate,
            "status": "APPROVED",
            "scope": {"provider": "higgsfield", "operation": "animate_keyframes", "max_credits": 6},
        }
        for gate in ("ASSET_UPLOAD", "CREATE_MEDIA", "CREDIT_SPEND")
    ]
    return job


def assert_invalid_plan(plan):
    assert plan["status"] == "INVALID_REQUEST"
    assert plan["external_execution_authorized"] is False
    assert plan["execution_performed"] is False
    assert plan["validation_errors"]
    # Error results must not echo NaN/Infinity back into an adapter's JSON plan.
    json.dumps(plan, allow_nan=False)


def test_provider_catalog_and_jobs_validate():
    assert validate("provider_catalog", CATALOG) == []
    for path in sorted((ROOT / "examples").glob("provider-job.*.yaml")):
        assert validate("provider_job", load_data(path)) == []


def test_vidiq_read_only_audit_is_ready_without_approval():
    job = load_data(ROOT / "examples/provider-job.vidiq-audit.yaml")
    plan = build_provider_plan(CATALOG, job)
    assert plan["status"] == "READY_READ_ONLY"
    assert plan["external_execution_authorized"] is True
    assert plan["execution_performed"] is False


@pytest.mark.parametrize(
    "filename,expected_gates",
    [
        ("provider-job.magiclight-character-preview.yaml", {"ASSET_UPLOAD", "CREATE_MEDIA", "CREDIT_SPEND"}),
        ("provider-job.elevenlabs-voice-preview.yaml", {"CREATE_MEDIA", "CREDIT_SPEND"}),
        ("provider-job.higgsfield-animation.yaml", {"ASSET_UPLOAD", "CREATE_MEDIA", "CREDIT_SPEND"}),
    ],
)
def test_paid_creative_jobs_are_blocked_without_scoped_approval(filename, expected_gates):
    plan = build_provider_plan(CATALOG, load_data(ROOT / "examples" / filename))
    assert plan["status"] == "BLOCKED_APPROVAL"
    assert set(plan["missing_approvals"]) == expected_gates
    assert plan["external_execution_authorized"] is False


def test_credit_approval_must_cover_provider_operation_and_budget():
    job = load_data(ROOT / "examples/provider-job.higgsfield-animation.yaml")
    job["status"] = "APPROVED"
    job["approvals"] = [
        {
            "approval_id": f"HF-{gate}",
            "gate": gate,
            "status": "APPROVED",
            "scope": {"provider": "higgsfield", "operation": "animate_keyframes", "max_credits": 6},
        }
        for gate in ("ASSET_UPLOAD", "CREATE_MEDIA", "CREDIT_SPEND")
    ]
    plan = build_provider_plan(CATALOG, job)
    assert plan["status"] == "READY_FOR_PROVIDER_EXECUTION"
    assert plan["external_execution_authorized"] is True

    job["max_credits"] = 5
    assert build_provider_plan(CATALOG, job)["status"] == "BLOCKED_BUDGET"


def test_credit_approval_must_cover_maximum_exposure_not_estimate():
    job = load_data(ROOT / "examples/provider-job.higgsfield-animation.yaml")
    job["status"] = "APPROVED"
    job["estimated_credits"] = 5
    job["max_credits"] = 100
    job["approvals"] = [
        {
            "approval_id": f"HF-{gate}",
            "gate": gate,
            "status": "APPROVED",
            "scope": {
                "provider": "higgsfield",
                "operation": "animate_keyframes",
                "max_credits": 5,
            },
        }
        for gate in ("ASSET_UPLOAD", "CREATE_MEDIA", "CREDIT_SPEND")
    ]

    plan = build_provider_plan(CATALOG, job)
    assert plan["status"] == "BLOCKED_APPROVAL"
    assert plan["missing_approvals"] == ["CREDIT_SPEND"]
    assert plan["external_execution_authorized"] is False


def test_wildcard_approvals_never_authorize_provider_work():
    job = load_data(ROOT / "examples/provider-job.higgsfield-animation.yaml")
    job["status"] = "APPROVED"
    job["approvals"] = [
        {
            "approval_id": f"WILDCARD-{gate}",
            "gate": gate,
            "status": "APPROVED",
            "scope": {"provider": "*", "operation": "*", "max_credits": 6},
        }
        for gate in ("ASSET_UPLOAD", "CREATE_MEDIA", "CREDIT_SPEND")
    ]

    assert validate("provider_job", job)
    plan = build_provider_plan(CATALOG, job)
    assert_invalid_plan(plan)
    assert plan["budget"]["status"] == "NOT_EVALUATED"
    assert plan["required_approvals"] == plan["missing_approvals"] == []
    assert any("provider job schema" in error for error in plan["validation_errors"])


@pytest.mark.parametrize("catalog_status", ["DRAFT", "SUPERSEDED"])
def test_inactive_catalog_never_authorizes_execution(catalog_status):
    catalog = load_data(ROOT / "config/providers.v1.yaml")
    catalog["status"] = catalog_status
    job = load_data(ROOT / "examples/provider-job.vidiq-audit.yaml")

    plan = build_provider_plan(catalog, job)
    assert plan["status"] == "BLOCKED_CATALOG_INACTIVE"
    assert plan["external_execution_authorized"] is False


@pytest.mark.parametrize("job_status", ["EXECUTED", "FAILED", "CANCELLED"])
def test_terminal_job_never_authorizes_execution(job_status):
    job = load_data(ROOT / "examples/provider-job.vidiq-audit.yaml")
    job["status"] = job_status

    plan = build_provider_plan(CATALOG, job)
    assert plan["status"] == "BLOCKED_JOB_TERMINAL"
    assert plan["external_execution_authorized"] is False


def test_mutating_job_requires_approved_status_even_with_approvals():
    job = load_data(ROOT / "examples/provider-job.higgsfield-animation.yaml")
    job["approvals"] = [
        {
            "approval_id": f"HF-{gate}",
            "gate": gate,
            "status": "APPROVED",
            "scope": {"provider": "higgsfield", "operation": "animate_keyframes", "max_credits": 6},
        }
        for gate in ("ASSET_UPLOAD", "CREATE_MEDIA", "CREDIT_SPEND")
    ]

    plan = build_provider_plan(CATALOG, job)
    assert plan["status"] == "BLOCKED_JOB_STATUS"
    assert plan["external_execution_authorized"] is False


def test_asset_lineage_must_exactly_cover_referenced_assets():
    job = load_data(ROOT / "examples/provider-job.higgsfield-animation.yaml")
    job["asset_lineage"]["inputs"] = job["asset_lineage"]["inputs"][:1]

    plan = build_provider_plan(CATALOG, job)
    assert plan["status"] == "INVALID_REQUEST"
    assert any("VOXIE-STAR-FREEZE-APPROVED" in error for error in plan["validation_errors"])
    assert plan["external_execution_authorized"] is False


def test_asset_lineage_rejects_unapproved_inputs():
    job = load_data(ROOT / "examples/provider-job.magiclight-character-preview.yaml")
    job["asset_lineage"]["inputs"][0]["status"] = "candidate"

    assert validate("provider_job", job)
    plan = build_provider_plan(CATALOG, job)
    assert_invalid_plan(plan)
    assert any("asset_lineage.inputs.0.status" in error for error in plan["validation_errors"])


def test_asset_lineage_requires_output_version():
    job = load_data(ROOT / "examples/provider-job.magiclight-character-preview.yaml")
    job["asset_lineage"]["output_asset_version"] = None

    assert validate("provider_job", job) == []
    plan = build_provider_plan(CATALOG, job)
    assert_invalid_plan(plan)
    assert "asset_lineage.output_asset_version is required for mutating operations" in plan["validation_errors"]


def test_direct_planner_call_enforces_job_schema():
    job = load_data(ROOT / "examples/provider-job.higgsfield-animation.yaml")
    job["max_credits"] = -1

    plan = build_provider_plan(CATALOG, job)
    assert plan["status"] == "INVALID_REQUEST"
    assert any("provider job schema" in error for error in plan["validation_errors"])
    assert plan["external_execution_authorized"] is False


def test_unknown_operation_fails_closed():
    job = load_data(ROOT / "examples/provider-job.vidiq-audit.yaml")
    job["operation"] = "publish_everywhere"
    with pytest.raises(ValueError, match="Unsupported operation"):
        build_provider_plan(CATALOG, job)


def test_chargeable_catalog_misconfiguration_fails_closed():
    catalog = load_data(ROOT / "config/providers.v1.yaml")
    catalog["providers"]["elevenlabs"]["capabilities"]["generate_music"]["approval_gates"] = ["CREATE_MEDIA"]
    job = load_data(ROOT / "examples/provider-job.elevenlabs-voice-preview.yaml")
    job["operation"] = "generate_music"
    plan = build_provider_plan(catalog, job)
    assert plan["status"] == "INVALID_REQUEST"
    assert "CREDIT_SPEND" in plan["validation_errors"][0]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")], ids=["nan", "inf", "negative-inf"])
@pytest.mark.parametrize("field", ["estimated_credits", "max_credits", "approval_ceiling"])
def test_nonfinite_credit_values_never_authorize_execution(approved_job, field, value):
    if field == "approval_ceiling":
        approved_job["approvals"][-1]["scope"]["max_credits"] = value
    else:
        approved_job[field] = value

    assert_invalid_plan(build_provider_plan(CATALOG, approved_job))
    assert validate("provider_job", approved_job)


@pytest.mark.parametrize("value", [0, 6, 6.5, 10**400], ids=["zero", "integer", "fraction", "large-integer"])
def test_finite_credit_values_preserve_valid_approval(approved_job, value):
    approved_job["estimated_credits"] = value
    approved_job["max_credits"] = value
    approved_job["approvals"][-1]["scope"]["max_credits"] = value

    plan = build_provider_plan(CATALOG, approved_job)
    assert plan["status"] == "READY_FOR_PROVIDER_EXECUTION"
    assert plan["budget"]["max_credits"] == value
    assert plan["execution_performed"] is False


@pytest.mark.parametrize("field", ["provider", "operation", "job_id", "project_id"])
def test_missing_required_identity_returns_invalid_plan(approved_job, field):
    del approved_job[field]
    assert_invalid_plan(build_provider_plan(CATALOG, approved_job))


@pytest.mark.parametrize("target", ["catalog", "job"])
@pytest.mark.parametrize("value", [None, [], "not an object", 42])
def test_malformed_root_returns_invalid_plan(approved_job, target, value):
    catalog, job = (value, approved_job) if target == "catalog" else (CATALOG, value)
    assert_invalid_plan(build_provider_plan(catalog, job))


@pytest.mark.parametrize(
    "target,path,value",
    [
        ("job", ("provider",), []),
        ("job", ("operation",), None),
        ("job", ("estimated_credits",), "6"),
        ("job", ("max_credits",), "6"),
        ("job", ("approvals",), ["not an object"]),
        ("job", ("approvals", 0, "scope"), "not an object"),
        ("job", ("inputs",), "not an object"),
        ("job", ("asset_lineage", "inputs"), None),
        ("job", ("asset_lineage", "inputs", 0, "asset_id"), []),
        ("catalog", ("providers",), []),
        ("catalog", ("providers", "higgsfield"), None),
        ("catalog", ("providers", "higgsfield", "capabilities"), None),
        ("catalog", ("providers", "higgsfield", "capabilities", "animate_keyframes"), []),
        ("catalog", ("providers", "higgsfield", "capabilities", "animate_keyframes", "approval_gates"), "CREATE_MEDIA"),
        ("catalog", ("providers", "higgsfield", "display_name"), None),
    ],
)
def test_malformed_nested_input_returns_invalid_plan(approved_job, target, path, value):
    catalog = deepcopy(CATALOG)
    container = approved_job if target == "job" else catalog
    for key in path[:-1]:
        container = container[key]
    container[path[-1]] = value

    plan = build_provider_plan(catalog, approved_job)
    assert_invalid_plan(plan)
    assert any(f"provider {target} schema" in error for error in plan["validation_errors"])


def test_both_invalid_inputs_report_both_schemas():
    plan = build_provider_plan({}, {})
    assert_invalid_plan(plan)
    assert any("provider catalog schema" in error for error in plan["validation_errors"])
    assert any("provider job schema" in error for error in plan["validation_errors"])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")], ids=["nan", "inf", "negative-inf"])
@pytest.mark.parametrize("command", ["validate", "provider-plan"])
def test_cli_rejects_nonfinite_yaml_approval(approved_job, tmp_path, monkeypatch, capsys, command, value):
    approved_job["approvals"][-1]["scope"]["max_credits"] = value
    job_path = tmp_path / "provider-job.invalid.yaml"
    job_path.write_text(yaml.safe_dump(approved_job), encoding="utf-8")
    arguments = ["validate", "provider_job"] if command == "validate" else ["provider-plan", str(ROOT / "config/providers.v1.yaml")]
    monkeypatch.setattr(sys, "argv", ["voxie-os", *arguments, str(job_path)])

    assert main() == 1
    output = capsys.readouterr().out
    assert "FAIL" in output
    assert "READY_FOR_PROVIDER_EXECUTION" not in output
