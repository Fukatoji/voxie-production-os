import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SPRINT_DIR = ROOT / "docs/reviews/ten-project-sprint-v02"
INDEX_PATH = SPRINT_DIR / "index.json"
SCHEMA_PATH = ROOT / "schemas/production_enablement_review.schema.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _index():
    return _load(INDEX_PATH)


def _projects():
    index = _index()
    return [_load(ROOT / path) for path in index["project_files"]]


def _by_number():
    return {project["project_number"]: project for project in _projects()}


def _all_drive_items():
    return [
        item
        for project in _projects()
        for item in project["evidence"]["drive_items"]
    ]


def test_enablement_schema_is_valid_and_all_ten_packets_validate():
    schema = _load(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    projects = _projects()
    assert len(projects) == 10
    for project in projects:
        assert list(validator.iter_errors(project)) == []


def test_index_references_exactly_ten_unique_existing_packets():
    index = _index()
    paths = index["project_files"]
    projects = _projects()

    assert index["project_count"] == 10
    assert len(paths) == len(set(paths)) == 10
    assert all((ROOT / path).is_file() for path in paths)
    assert [project["project_number"] for project in projects] == list(range(1, 11))
    assert len({project["packet_id"] for project in projects}) == 10
    assert len({project["domain"] for project in projects}) == 10


def test_sprint_summary_matches_packet_statuses():
    observed = {}
    for project in _projects():
        observed[project["status"]] = observed.get(project["status"], 0) + 1

    assert observed == {
        "READY_FOR_REVIEW": 5,
        "BLOCKED_EXTERNAL": 4,
        "READY_FOR_EXTERNAL_APPLY": 1,
    }
    assert _index()["summary"] == {
        "ready_for_review": 5,
        "blocked_external": 4,
        "ready_for_external_apply": 1,
        "projects_completed": 10,
    }


def test_authority_spend_merge_and_publication_remain_fail_closed():
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
        authority = project["authority"]
        gates = project["gates"]
        review = project["review"]

        assert authority["decisions_preserved"] is True
        assert authority["execution_authorized"] is False
        assert authority["merge_authorized"] is False
        assert authority["publication_authorized"] is False
        assert gates["spend_permission_provided"] is True
        assert gates["spend_authorized"] is False
        assert gates["credits_spent"] == 0
        assert gates["provider_execution_performed"] is False
        assert review["reviewer_context"] == "OWNER_CONTEXT"
        assert review["independent_review"] in {"NOT_CLAIMED", "PENDING_EXTERNAL"}
        assert review["process_complete"] is True


def test_packet_timestamps_match_chicago_local_date():
    chicago = ZoneInfo("America/Chicago")
    for project in _projects():
        recorded = datetime.strptime(
            project["recorded_at_utc"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        assert recorded.astimezone(chicago).date().isoformat() == project["local_date"]
        assert project["timezone"] == "America/Chicago"


def test_all_repository_authority_source_paths_exist():
    for project in _projects():
        for relative_path in project["authority"]["source_paths"]:
            assert (ROOT / relative_path).is_file(), (
                project["packet_id"],
                relative_path,
            )


def test_rainbow_binary_intake_has_complete_seven_item_matrix():
    project = _by_number()[1]
    binaries = project["details"]["required_binaries"]

    assert project["status"] == "BLOCKED_EXTERNAL"
    assert project["details"]["required_count"] == len(binaries) == 7
    assert project["details"]["mounted_count"] == 0
    assert project["details"]["fresh_rehash_count"] == 0
    assert len({item["role"] for item in binaries}) == 7
    assert all(len(item["recorded_sha256"]) == 64 for item in binaries)
    assert {item["known_locator"] for item in binaries[:3]} == {
        "file-library://file_0000000038f881f7a40de0921d6a73dc",
        "file-library://file_000000003bb081f786c6b3f196941e13",
        "file-library://file_000000007acc81f7896d61c56cfcb63f",
    }


def test_rainbow_candidate_packet_has_six_sources_and_owns_its_review_deck():
    project = _by_number()[2]
    candidates = project["evidence"]["provider_items"]
    drive_items = project["evidence"]["drive_items"]

    assert project["status"] == "READY_FOR_REVIEW"
    assert project["details"]["candidate_count"] == len(candidates) == 6
    assert [candidate["shot_ids"][0] for candidate in candidates] == [
        "S04",
        "S15",
        "S18",
        "S20",
        "S33",
        "S35",
    ]
    assert len({candidate["task_id"] for candidate in candidates}) == 6
    assert len({candidate["sha256"] for candidate in candidates}) == 6
    assert all(candidate["state"] == "REVIEW_CANDIDATE" for candidate in candidates)
    assert project["details"]["dependent_shots"] == {"S05": "S04", "S19": "S20"}
    assert drive_items == [
        {
            "id": "17bQpup57kWQG3o8IzDoWJmdGVmyNsVDKIEZJ_HeSd7w",
            "title": "VWF_RAINBOW_COLORS_ACTION_ANCHOR_RECOVERY_QC_v01_REVIEW",
            "mime_type": "application/vnd.google-apps.presentation",
            "url": (
                "https://docs.google.com/presentation/d/"
                "17bQpup57kWQG3o8IzDoWJmdGVmyNsVDKIEZJ_HeSd7w/edit?usp=drivesdk"
            ),
            "role": "six-candidate visual review carrier",
            "state": "REVIEW",
        }
    ]


def test_rainbow_generation_packet_has_exact_fifteen_shot_queue_and_zero_budget():
    project = _by_number()[3]
    expected = [
        "S06",
        "S09",
        "S10",
        "S11",
        "S12",
        "S13",
        "S14",
        "S16",
        "S17",
        "S22",
        "S23",
        "S25",
        "S26",
        "S29",
        "S36",
    ]

    assert project["details"]["shot_ids"] == expected
    assert project["details"]["shot_count"] == len(expected) == 15
    assert project["details"]["current_live_balance"] == "UNVERIFIED"
    assert project["details"]["max_authorized_credits"] == 0
    assert project["gates"]["spend_authorized"] is False


def test_rsp_media_packet_matches_only_rsp_image_audio_and_document_evidence():
    project = _by_number()[4]
    items = project["evidence"]["drive_items"]
    details = project["details"]

    assert details == {
        "image_count": 3,
        "image_bytes": 6355979,
        "audio_count": 1,
        "audio_bytes": 50311674,
        "video_binary_count": 0,
        "document_count": 2,
        "spreadsheet_count": 1,
        "presentation_count": 0,
    }
    assert sum(
        item.get("bytes", 0)
        for item in items
        if item["mime_type"] == "image/png"
    ) == 6355979
    assert sum(
        item.get("bytes", 0)
        for item in items
        if item["mime_type"] == "audio/wav"
    ) == 50311674
    assert len([item for item in items if item["mime_type"] == "image/png"]) == 3
    assert len([item for item in items if item["mime_type"] == "audio/wav"]) == 1
    assert len(
        [
            item
            for item in items
            if item["mime_type"] == "application/vnd.google-apps.document"
        ]
    ) == 2
    assert len(
        [
            item
            for item in items
            if item["mime_type"] == "application/vnd.google-apps.spreadsheet"
        ]
    ) == 1
    assert not any(
        item["mime_type"] == "application/vnd.google-apps.presentation"
        for item in items
    )
    assert all("RAINBOW_COLORS" not in item["title"] for item in items)


def test_lumi_packet_is_preview_only_and_cannot_lock_or_substitute_voxie():
    project = _by_number()[5]
    details = project["details"]

    assert project["status"] == "BLOCKED_EXTERNAL"
    assert details["provider"] == "MagicLight"
    assert details["operation"] == "character_preview"
    assert details["output_count"] == 1
    assert details["preview_only"] is True
    assert "SEPARATE_FROM_VOXIE" in details["hard_constraints"]
    assert "NO_LOCK_BEFORE_APPROVAL" in details["hard_constraints"]
    assert "MAGICLIGHT_SESSION_UNAVAILABLE" in project["gates"]["blockers"]


def test_navi_and_humpty_packages_preserve_two_branches_and_five_options():
    projects = _by_number()
    for number, expected_ids in {
        6: {"NAVI_ROBOTIC_FAIRY", "NAVI_ORGANIC_LEAF_FAIRY"},
        7: {"HUMPTY_RAINBOW_PATCHWORK", "HUMPTY_CREAM_BLUE"},
    }.items():
        project = projects[number]
        branches = project["details"]["branches"]
        options = project["details"]["decision_options"]

        assert len(branches) == 2
        assert {branch["branch_id"] for branch in branches} == expected_ids
        assert all(
            branch["state"] == "HISTORICAL_PRODUCTION_BRANCH"
            for branch in branches
        )
        assert len(options) == 5
        assert "CONTINUE_HOLD" in options
        assert project["authority"]["execution_authorized"] is False


def test_publishing_matrix_has_three_projects_and_no_upload_or_publication():
    project = _by_number()[8]
    details = project["details"]

    assert [item["project_id"] for item in details["projects"]] == [
        "VWF-BIG-SURPRISE",
        "VWF-FREEZE-DANCE",
        "VWF-COLORFUL-DAY",
    ]
    assert details["platforms"] == ["youtube", "tiktok", "instagram"]
    assert details["upload_authorized"] is False
    assert details["publish_authorized"] is False
    assert "EXPLICIT_PUBLICATION_APPROVAL" in project["gates"]["required_approvals"]


def test_big_surprise_alignment_packet_matches_final_beatmap_audio_authority():
    project = _by_number()[9]
    beatmap = json.loads(
        (
            ROOT
            / "manifests/productions/big-surprise/beatmap-001.final.json"
        ).read_text(encoding="utf-8")
    )

    assert project["details"]["audio_filename"] == beatmap["source_audio"][
        "controlled_filename"
    ]
    assert project["details"]["audio_sha256"] == beatmap["source_audio"]["sha256"]
    assert project["details"]["duration_seconds"] == beatmap["duration_s"] == 150.0
    assert project["details"]["auto_promote"] is False
    assert "LOCKED_WAV_BINARY_NOT_MOUNTED" in project["gates"]["blockers"]


def test_branch_protection_packet_is_exact_but_not_claimed_applied():
    project = _by_number()[10]
    details = project["details"]

    assert project["status"] == "READY_FOR_EXTERNAL_APPLY"
    assert details == {
        "branch": "main",
        "current_protected": False,
        "required_status_checks": ["Production OS CI"],
        "required_approving_reviews": 1,
        "require_conversation_resolution": True,
        "dismiss_stale_reviews": True,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "allow_direct_pushes": False,
    }
    assert (
        "SAFE_BRANCH_RULESET_WRITE_UNAVAILABLE_IN_CURRENT_SESSION"
        in project["gates"]["blockers"]
    )


def test_index_media_summary_matches_all_enablement_packet_evidence():
    items = _all_drive_items()
    mime_counts = {
        "images_referenced": len(
            [item for item in items if item["mime_type"].startswith("image/")]
        ),
        "video_binaries_referenced": len(
            [item for item in items if item["mime_type"].startswith("video/")]
        ),
        "audio_binaries_referenced": len(
            [item for item in items if item["mime_type"].startswith("audio/")]
        ),
        "documents_referenced": len(
            [
                item
                for item in items
                if item["mime_type"] == "application/vnd.google-apps.document"
            ]
        ),
        "spreadsheets_referenced": len(
            [
                item
                for item in items
                if item["mime_type"] == "application/vnd.google-apps.spreadsheet"
            ]
        ),
        "presentations_referenced": len(
            [
                item
                for item in items
                if item["mime_type"] == "application/vnd.google-apps.presentation"
            ]
        ),
    }

    assert mime_counts == {
        "images_referenced": 3,
        "video_binaries_referenced": 0,
        "audio_binaries_referenced": 1,
        "documents_referenced": 2,
        "spreadsheets_referenced": 1,
        "presentations_referenced": 1,
    }
    assert _index()["media_summary"] == mime_counts
