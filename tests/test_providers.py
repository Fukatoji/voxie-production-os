from pathlib import Path

import pytest

from voxie_os.core import load_data, validate
from voxie_os.providers import build_provider_plan

ROOT = Path(__file__).resolve().parents[1]
CATALOG = load_data(ROOT / "config/providers.v1.yaml")


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
