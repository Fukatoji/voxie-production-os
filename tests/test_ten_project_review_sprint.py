from datetime import datetime, timezone
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SPRINT_DIR = ROOT / "docs/reviews/ten-project-sprint-v01"
INDEX_PATH = SPRINT_DIR / "index.yaml"
SCHEMA_PATH = ROOT / "schemas/operational_review.schema.json"


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _index():
    return _load(INDEX_PATH)


def _projects():
    index = _index()
    return [_load(ROOT / path) for path in index["project_files"]]


def _by_number():
    return {project["project_number"]: project for project in _projects()}


def test_operational_review_schema_is_valid_and_all_ten_projects_validate():
    schema = _load(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    projects = _projects()
    assert len(projects) == 10
    for project in projects:
        assert list(validator.iter_errors(project)) == []


def test_sprint_index_references_exactly_ten_existing_unique_projects():
    index = _index()
    paths = index["project_files"]
    projects = _projects()

    assert index["project_count"] == 10
    assert len(paths) == len(set(paths)) == 10
    assert all((ROOT / path).is_file() for path in paths)
    assert [project["project_number"] for project in projects] == list(range(1, 11))
    assert len({project["project_id"] for project in projects}) == 10


def test_review_scope_is_explicit_and_fail_closed():
    index = _index()
    assert index["authorization"] == {
        "user_authorized": True,
        "merge_authorized": False,
        "publication_authorized": False,
        "spend_permission_provided": True,
        "credits_spent": 0,
    }
    assert index["merge_decision"] == "HOLD_FOR_EXPLICIT_INSTRUCTION"

    for project in _projects():
        authorization = project["authorization"]
        review = project["review"]

        assert authorization["user_authorized"] is True
        assert authorization["merge_authorized"] is False
        assert authorization["publication_authorized"] is False
        assert authorization["spend_permission_provided"] is True
        assert authorization["spend_exercised"] is False
        assert authorization["credits_spent"] == 0
        assert review["reviewer_context"] == "OWNER_CONTEXT"
        assert review["independent_review"] in {"NOT_CLAIMED", "PENDING_EXTERNAL"}
        assert review["process_complete"] is True


def test_recorded_timestamp_and_local_date_are_consistent():
    for project in _projects():
        recorded = datetime.strptime(
            project["recorded_at_utc"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        assert recorded.date().isoformat() == project["local_date"]
        assert project["timezone"] == "America/Chicago"


def test_repository_evidence_paths_exist():
    for project in _projects():
        for relative_path in project["evidence"]["repository_paths"]:
            assert (ROOT / relative_path).is_file(), (
                project["project_id"],
                relative_path,
            )


def test_process_deviations_are_processed_without_claiming_independence():
    project = _by_number()[1]
    rules = {
        finding["rule_id"]: finding["disposition"]
        for finding in project["evidence"]["findings"]
    }

    assert rules["OWNER_CONTEXT_REVIEW_NOT_INDEPENDENT"] == (
        "REMEDIATED_BY_EXPLICIT_CLASSIFICATION"
    )
    assert rules["MAIN_BRANCH_UNPROTECTED"] == "EXTERNAL_ADMIN_ACTION_PENDING"
    assert rules["CURRENT_REQUEST_NO_MERGE_AUTHORIZATION"] == "PR_MUST_REMAIN_OPEN"
    assert project["review"]["independent_review"] == "PENDING_EXTERNAL"


def test_merge_and_spend_ledgers_preserve_current_gates():
    projects = _by_number()
    merge = projects[3]
    spend = projects[4]

    assert merge["metrics"] == {
        "baseline_main_sha": "a77d3f176f9d0e6d65d1ba84d58fad1df0cfba55",
        "open_prs_at_start": 0,
    }
    assert merge["authorization"]["merge_authorized"] is False

    assert spend["metrics"]["credits_spent"] == 0
    assert spend["metrics"]["money_spent_usd"] == 0
    assert spend["metrics"]["magiclight_live_balance"] == "UNVERIFIED"
    assert spend["authorization"]["spend_exercised"] is False


def test_branch_protection_project_is_ready_but_not_claimed_applied():
    project = _by_number()[5]

    assert project["status"] == "READY_EXTERNAL_ADMIN_APPLY"
    assert project["metrics"]["branch"] == "main"
    assert project["metrics"]["protected"] is False
    assert project["metrics"]["recommended_approving_reviews"] == 1
    assert any(
        finding["rule_id"] == "NO_ADMIN_WRITE_PERFORMED"
        and finding["disposition"] == "EXTERNAL_ADMIN_ACTION_PENDING"
        for finding in project["evidence"]["findings"]
    )


def test_image_inventory_matches_observed_drive_evidence():
    project = _by_number()[6]
    items = project["evidence"]["drive_items"]

    assert project["metrics"] == {
        "observed_image_files": 3,
        "observed_image_bytes": 6355979,
        "modified_images": 0,
    }
    assert {item["id"] for item in items} == {
        "1YzS2HLj43I_UjNM1iUJfx5PIoVEmyLFR",
        "1Lqii-NrJrSH0nimV7U6xeRFFn_Ly0Uof",
        "1uohnYE4A7dWzDLsCMkDkRqiD58BG6M4H",
    }
    assert all(item["mime_type"] == "image/png" for item in items)
    assert all(item["state"] == "LOCKED" for item in items)


def test_video_audio_inventory_does_not_confuse_control_records_with_binaries():
    project = _by_number()[7]
    metrics = project["metrics"]

    assert metrics["observed_video_binaries"] == 0
    assert metrics["observed_audio_binaries"] == 1
    assert metrics["observed_audio_bytes"] == 50311674
    assert metrics["repository_video_authority_records"] == 4
    assert project["evidence"]["drive_items"][0]["mime_type"] == "audio/wav"
    assert any(
        finding["rule_id"] == "CONTROL_RECORD_NOT_BINARY"
        and finding["disposition"] == "FAIL_CLOSED"
        for finding in project["evidence"]["findings"]
    )


def test_document_inventory_is_explicitly_scoped():
    project = _by_number()[8]
    assert project["metrics"] == {
        "observed_google_docs": 25,
        "observed_spreadsheets": 1,
        "observed_presentations": 1,
        "empty_audited_publishing_folders": 1,
    }
    assert any(
        finding["rule_id"] == "DOCUMENT_COUNT_IS_AUDIT_SCOPE_COUNT"
        and finding["disposition"] == "SCOPE_DISCLOSED"
        for finding in project["evidence"]["findings"]
    )


def test_on_hold_register_routes_each_blocker_to_the_correct_workspace():
    project = _by_number()[9]
    dispositions = {
        finding["rule_id"]: finding["disposition"]
        for finding in project["evidence"]["findings"]
    }

    assert dispositions["RAINBOW_BINARY_AND_MAGICLIGHT_BLOCK"] == (
        "ROUTE_TO_90_UNTIL_EXTERNAL_PREREQUISITES"
    )
    assert dispositions["LUMI_PREVIEW_LOCK_PENDING"] == "ROUTE_TO_01_CANON"
    assert dispositions["NAVI_HUMPTY_RECONCILIATION_PENDING"] == (
        "ROUTE_TO_01_CANON"
    )
    assert dispositions["RELEASE_PACKAGES_PENDING"] == "ROUTE_TO_04_PUBLISHING"
    assert dispositions["RSP_AUDIO_BINARY_AVAILABLE"] == (
        "ROUTE_TO_02_ACTIVE_PRODUCTION_FOR_VISUAL_COMPLETION"
    )


def test_command_center_project_contains_exactly_ten_actionable_ideas():
    project = _by_number()[10]

    assert len(project["ideas"]) == 10
    assert len(set(project["ideas"])) == 10
    assert project["metrics"]["projects_completed"] == 10
    assert project["metrics"]["credits_spent"] == 0
    assert project["authorization"]["merge_authorized"] is False


def test_index_media_summary_matches_project_inventories():
    summary = _index()["media_summary"]
    projects = _by_number()

    assert summary["images_observed"] == projects[6]["metrics"]["observed_image_files"]
    assert summary["image_bytes_observed"] == projects[6]["metrics"][
        "observed_image_bytes"
    ]
    assert summary["video_binaries_observed"] == projects[7]["metrics"][
        "observed_video_binaries"
    ]
    assert summary["audio_binaries_observed"] == projects[7]["metrics"][
        "observed_audio_binaries"
    ]
    assert summary["audio_bytes_observed"] == projects[7]["metrics"][
        "observed_audio_bytes"
    ]
    assert summary["google_docs_observed"] == projects[8]["metrics"][
        "observed_google_docs"
    ]
    assert summary["spreadsheets_observed"] == projects[8]["metrics"][
        "observed_spreadsheets"
    ]
    assert summary["presentations_observed"] == projects[8]["metrics"][
        "observed_presentations"
    ]
