from copy import deepcopy
from pathlib import Path
import json
import sys

from voxie_os.authority import (
    AUTHORITY_DISCOVERY_PATTERNS,
    build_authority_coverage_report,
    discover_authority_records,
)
from voxie_os.cli import main
from voxie_os.core import load_data


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "manifests/control/authority-index-v01.yaml"


def _index():
    return deepcopy(load_data(INDEX_PATH))


def test_current_authority_index_covers_discovery_policy():
    report = build_authority_coverage_report(_index())

    assert report["status"] == "PASS"
    assert report["counts"]["current"] == 18
    assert report["counts"]["predecessors"] == 4
    assert report["counts"]["discovered"] == report["counts"]["covered"]
    assert report["missing_from_index"] == []
    assert report["outside_discovery_policy"] == []
    assert report["current_predecessor_overlap"] == []
    assert report["findings"] == []


def test_discovery_policy_is_explicit_and_control_plane_only():
    discovered = discover_authority_records()

    assert AUTHORITY_DISCOVERY_PATTERNS
    assert "manifests/control/authority-index-v01.yaml" not in discovered
    assert not any(path.startswith("examples/") for path in discovered)
    assert not any(path.startswith("handoff/") for path in discovered)
    assert not any(path.endswith((".mp4", ".wav", ".png")) for path in discovered)


def test_new_discovered_authority_fails_until_indexed():
    discovered = set(discover_authority_records())
    discovered.add("manifests/distribution/future/release-readiness-v01.yaml")

    report = build_authority_coverage_report(
        _index(), discovered_paths=discovered
    )

    assert report["status"] == "FAIL"
    assert report["missing_from_index"] == [
        "manifests/distribution/future/release-readiness-v01.yaml"
    ]
    assert report["findings"][-1]["rule_id"] == (
        "DISCOVERED_AUTHORITY_NOT_INDEXED"
    )


def test_indexed_path_outside_discovery_policy_fails():
    discovered = set(discover_authority_records())
    index = _index()
    unexpected = index["entries"][0]["path"]
    discovered.remove(unexpected)

    report = build_authority_coverage_report(
        index, discovered_paths=discovered
    )

    assert report["status"] == "FAIL"
    assert unexpected in report["outside_discovery_policy"]
    assert any(
        finding["rule_id"] == "INDEXED_PATH_OUTSIDE_DISCOVERY_POLICY"
        for finding in report["findings"]
    )


def test_missing_predecessor_coverage_is_detected():
    index = _index()
    index["entries"][0]["predecessors"] = []

    report = build_authority_coverage_report(index)

    assert report["status"] == "FAIL"
    assert "manifests/library-routing.v1.yaml" in report["missing_from_index"]


def test_authority_audit_cli_writes_machine_readable_report(
    monkeypatch, tmp_path, capsys
):
    out = tmp_path / "authority-audit.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "voxie-os",
            "authority-audit",
            str(INDEX_PATH),
            "--out",
            str(out),
        ],
    )

    assert main() == 0
    printed = json.loads(capsys.readouterr().out)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert printed == written
    assert written["status"] == "PASS"
