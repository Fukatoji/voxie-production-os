from pathlib import Path

import pytest

from voxie_os.core import load_data, validate


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "workflows/big-surprise-multi-aligner-evaluation-v01.yaml"
BEATMAP_PATH = (
    ROOT
    / "manifests"
    / "productions"
    / "big-surprise"
    / "beatmap-001.final.json"
)


def _plan():
    return load_data(PLAN_PATH)


def test_multi_aligner_plan_validates_as_alignment_record():
    assert validate("alignment", _plan()) == []


def test_plan_uses_locked_big_surprise_audio_without_mutation():
    plan = _plan()
    beatmap = load_data(BEATMAP_PATH)

    assert plan["audio"]["controlled_filename"] == beatmap["source_audio"][
        "controlled_filename"
    ]
    assert plan["audio"]["sha256"] == beatmap["source_audio"]["sha256"]
    assert plan["audio"]["duration_s"] == beatmap["duration_s"] == 150.0
    assert plan["audio"]["immutable"] is True
    assert plan["summary"]["locked_audio_changed"] is False


def test_required_alignment_adapters_and_baseline_artifacts_are_explicit():
    sources = {source["source_id"]: source for source in _plan()["sources"]}

    assert {source["adapter"] for source in sources.values()} == {
        "beatmap",
        "accuratescribe",
        "whisperx",
        "yass-reloaded",
    }
    for source_id in ("BEATMAP_FINAL_BASELINE", "ACCURATESCRIBE_BASELINE"):
        source = sources[source_id]
        assert source["execution_status"] == "READY"
        assert source["artifact"] is not None
        assert (ROOT / source["artifact"]).exists()

    for source_id in ("WHISPERX_VOCAL_CANDIDATE", "YASS_RELOADED_VOCAL_CANDIDATE"):
        source = sources[source_id]
        assert source["artifact"] is None
        assert source["execution_status"] == "BLOCKED_LOCKED_AUDIO_BINARY_NOT_MOUNTED"


def test_historical_gap_arithmetic_is_exact_and_not_misrepresented():
    focus = _plan()["historical_focus"]

    assert focus["transcription_gap_duration_s"] == pytest.approx(
        focus["transcription_gap_end_s"] - focus["transcription_gap_start_s"],
        abs=1e-6,
    )
    assert "not a claim" in focus["note"]


def test_pipeline_order_and_metrics_are_complete():
    plan = _plan()
    assert [step["step_id"] for step in plan["pipeline"]] == [
        "MOUNT_LOCKED_AUDIO_READ_ONLY",
        "SEPARATE_LOCAL_VOCALS",
        "RUN_WHISPERX",
        "RUN_YASS_RELOADED",
        "NORMALIZE_ADAPTER_OUTPUTS",
        "COMPARE_TO_BASELINES",
        "BUILD_CONFIDENCE_MERGE_CANDIDATE",
        "HUMAN_REVIEW_EXCEPTIONS",
    ]
    assert all(step["changes_authority"] is False for step in plan["pipeline"])
    assert {metric["metric_id"] for metric in plan["metrics"]} == {
        "LYRIC_LINE_COVERAGE_RATE",
        "HISTORICAL_GAP_UNRESOLVED_SECONDS",
        "MEDIAN_ABSOLUTE_START_DELTA_SECONDS",
        "P95_ABSOLUTE_START_DELTA_SECONDS",
        "MEDIAN_ABSOLUTE_END_DELTA_SECONDS",
        "MANUAL_REVIEW_EXCEPTION_COUNT",
    }


def test_evaluation_fails_closed_and_cannot_auto_promote():
    plan = _plan()

    assert plan["status"] == "REVIEW_REQUIRED"
    assert plan["execution"] == {
        "performed": False,
        "provider_calls": 0,
        "credits_spent": 0,
        "spend_required_for_plan": False,
        "output_artifact": None,
        "blocker": "LOCKED_AUDIO_BINARY_NOT_MOUNTED",
    }
    assert plan["promotion_policy"]["auto_promote"] is False
    assert plan["promotion_policy"]["locked_beatmap_remains_authority"] is True
    assert plan["promotion_policy"]["lyric_text_changes_allowed"] is False
    assert plan["promotion_policy"]["successor_requires_explicit_approval"] is True
    assert plan["output_authority"]["candidate_status"] == "REVIEW_ONLY"
    assert plan["output_authority"]["may_replace_beatmap_001"] is False
    assert plan["lyrics"] == []
