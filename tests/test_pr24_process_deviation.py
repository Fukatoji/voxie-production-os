from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/process_deviation.schema.json"
RECORD_PATH = (
    ROOT
    / "docs/reviews/process-deviations/pr24-merge-before-final-review-2026-08-29.yaml"
)


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_process_deviation_schema_and_record_validate():
    schema = _load(SCHEMA_PATH)
    record = _load(RECORD_PATH)

    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(record)) == []


def test_incident_timestamp_matches_chicago_local_date():
    record = _load(RECORD_PATH)
    occurred = datetime.strptime(
        record["pull_request"]["merged_at_utc"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)

    assert occurred.astimezone(ZoneInfo("America/Chicago")).date().isoformat() == (
        record["local_date"]
    )


def test_merge_occurred_despite_recorded_hold_state():
    record = _load(RECORD_PATH)

    assert record["pull_request"] == {
        "number": 24,
        "title": (
            "Complete process/media review and ten-project production-enablement "
            "program v01"
        ),
        "merged": True,
        "merged_at_utc": "2026-08-29T16:47:29Z",
        "merge_commit_sha": "c5f0fa78aa46f3610b9148e07765ef274377eb02",
        "merged_head_sha": "0e3a191f1521bf5e235d51ccbf79b6640e563736",
    }
    assert record["expected_control"] == {
        "merge_authorized": False,
        "publication_authorized": False,
        "independent_review_claimed": False,
        "required_disposition": "HOLD_FOR_EXPLICIT_INSTRUCTION",
    }
    assert record["observed_event"] == {
        "process_result": "MERGED_WITHOUT_RECORDED_AUTHORIZATION",
        "assistant_merge_call_performed": False,
        "repository_owner_context": True,
        "merged_before_final_correction_review": True,
    }


def test_incident_had_no_media_spend_publication_or_authority_impact():
    impact = _load(RECORD_PATH)["impact"]

    assert impact["media_generated_or_modified"] is False
    assert impact["provider_execution_performed"] is False
    assert impact["credits_spent"] == 0
    assert impact["publication_or_account_write"] is False
    assert impact["authority_promoted"] is False
    assert set(impact["post_merge_corrections_missing_from_main"]) == {
        "docs/reviews/ten-project-sprint-v02/02-vos-enablement-p02.json",
        "docs/reviews/ten-project-sprint-v02/04-vos-enablement-p04.json",
        "tests/test_ten_project_enablement_review.py",
        "handoff/ten-project-enablement-review-v01-2026-08-29.md",
    }


def test_remediation_is_forward_fix_and_remains_unmerged():
    record = _load(RECORD_PATH)
    remediation = record["remediation"]

    assert remediation["strategy"] == "FORWARD_FIX_WITH_AUDIT_RECORD"
    assert remediation["corrective_pull_request"] == 25
    assert remediation["historical_records_rewritten"] is False
    assert len(remediation["corrections"]) == 4
    assert remediation["branch_protection_required"] is True
    assert remediation["merge_authorized"] is False
    assert record["review"] == {
        "result": "PASS_WITH_REMEDIATION",
        "reviewer_context": "OWNER_CONTEXT",
        "independent_review": "PENDING_EXTERNAL",
        "approval_scope": "CORRECTIVE_PR_TECHNICAL_SCOPE_ONLY",
    }
