import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from voxie_os.alignment import build_consensus
from voxie_os.cli import main
from voxie_os.core import load_data, validate


ROOT = Path(__file__).resolve().parents[1]
ROUTING_PATH = ROOT / "manifests/library-routing.v2.yaml"
PREDECESSOR_PATH = ROOT / "manifests/library-routing.v1.yaml"
AUDIO = {"sha256": "a" * 64, "duration_s": 8.0}


def _source(source_id: str, *, line_id: str = "L001", start: float = 0.5):
    return {
        "source_id": source_id,
        "adapter": "whisperx" if source_id == "A" else "lyric-align",
        "weight": 1.0,
        "revision": "test",
        "audio": AUDIO,
        "lyrics": [
            {
                "line_id": line_id,
                "text": "Come explore with me!",
                "vocal_start_s": start,
                "vocal_end_s": start + 1.5,
                "confidence": 0.95,
                "manual_review": False,
            }
        ],
    }


def test_current_library_routing_predecessor_hash_matches_exact_bytes():
    manifest = load_data(ROUTING_PATH)
    expected = hashlib.sha256(PREDECESSOR_PATH.read_bytes()).hexdigest()

    assert manifest["supersedes"]["sha256"] == expected
    assert validate("library_routing", manifest) == []


def test_library_routing_rejects_wrong_predecessor_checksum():
    manifest = load_data(ROUTING_PATH)
    actual = hashlib.sha256(PREDECESSOR_PATH.read_bytes()).hexdigest()
    manifest["supersedes"]["sha256"] = "0" * 64

    assert validate("library_routing", manifest) == [
        "supersedes.sha256: expected "
        f"{actual} for manifests/library-routing.v1.yaml, got {'0' * 64}"
    ]


def test_alignment_rejects_duplicate_source_ids():
    first = _source("A")
    second = _source("A", start=0.55)

    with pytest.raises(ValueError, match="source_id values must be unique: A"):
        build_consensus([first, second], alignment_id="TEST")


def test_alignment_rejects_duplicate_line_ids_within_one_source():
    source = _source("A")
    source["lyrics"].append(deepcopy(source["lyrics"][0]))

    with pytest.raises(ValueError, match="A contains duplicate line_id values: L001"):
        build_consensus([source], alignment_id="TEST")


def test_single_distinct_source_cannot_satisfy_two_source_gate():
    result = build_consensus([_source("A")], alignment_id="TEST", min_sources=2)

    assert result["status"] == "REVIEW_REQUIRED"
    assert result["summary"]["source_count"] == 1
    assert result["lyrics"][0]["manual_review"] is True
    assert "only 1 distinct source(s)" in result["review_gates"][0]


def test_two_distinct_sources_produce_clean_provisional_consensus():
    result = build_consensus(
        [_source("A"), _source("B", start=0.55)],
        alignment_id="TEST",
        min_sources=2,
    )

    assert result["status"] == "PROVISIONAL"
    assert result["summary"]["source_count"] == 2
    assert result["review_gates"] == []
    assert validate("alignment", result) == []


def test_alignment_cli_returns_controlled_failure_for_duplicate_source_ids(
    monkeypatch,
    capsys,
    tmp_path,
):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    output = tmp_path / "consensus.json"
    first.write_text(json.dumps(_source("A")), encoding="utf-8")
    second.write_text(json.dumps(_source("A", start=0.55)), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "voxie-os",
            "alignment-consensus",
            str(first),
            str(second),
            "--id",
            "TEST",
            "--out",
            str(output),
        ],
    )

    assert main() == 1
    assert capsys.readouterr().out == (
        "FAIL\n- alignment-consensus: "
        "Alignment source_id values must be unique: A\n"
    )
    assert not output.exists()


def test_alignment_cli_returns_controlled_failure_for_duplicate_line_ids(
    monkeypatch,
    capsys,
    tmp_path,
):
    source = _source("A")
    source["lyrics"].append(deepcopy(source["lyrics"][0]))
    source_path = tmp_path / "source.json"
    output = tmp_path / "consensus.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "voxie-os",
            "alignment-consensus",
            str(source_path),
            "--id",
            "TEST",
            "--out",
            str(output),
        ],
    )

    assert main() == 1
    assert capsys.readouterr().out == (
        "FAIL\n- alignment-consensus: "
        "A contains duplicate line_id values: L001\n"
    )
    assert not output.exists()
