from pathlib import Path
import shutil

import pytest

import voxie_os.core as core
from voxie_os.core import load_data, validate


ROOT = Path(__file__).resolve().parents[1]
ROUTING_PATH = ROOT / "manifests/library-routing.v2.yaml"
PREDECESSOR_PATH = ROOT / "manifests/library-routing.v1.yaml"


def _canonical_lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _isolated_routing_checkout(tmp_path):
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / PREDECESSOR_PATH.name).write_bytes(
        _canonical_lf(PREDECESSOR_PATH.read_bytes())
    )
    (manifests / ROUTING_PATH.name).write_bytes(
        _canonical_lf(ROUTING_PATH.read_bytes())
    )
    return manifests / ROUTING_PATH.name


@pytest.mark.parametrize("line_ending", [b"\n", b"\r\n"])
def test_existing_checkout_line_endings_do_not_break_predecessor_checksum(
    tmp_path,
    monkeypatch,
    line_ending,
):
    routing_path = _isolated_routing_checkout(tmp_path)
    predecessor_path = routing_path.parent / PREDECESSOR_PATH.name
    canonical = predecessor_path.read_bytes()
    materialized = (
        canonical
        if line_ending == b"\n"
        else canonical.replace(b"\n", b"\r\n")
    )
    predecessor_path.write_bytes(materialized)
    monkeypatch.setattr(core, "ROOT", tmp_path)

    assert validate("library_routing", load_data(routing_path)) == []


def test_predecessor_content_change_still_fails_after_line_ending_normalization(
    tmp_path,
    monkeypatch,
):
    routing_path = _isolated_routing_checkout(tmp_path)
    predecessor_path = routing_path.parent / PREDECESSOR_PATH.name
    canonical = predecessor_path.read_bytes()
    predecessor_path.write_bytes(
        canonical.replace(b"\n", b"\r\n")
        + b"# unauthorized content change\r\n"
    )
    monkeypatch.setattr(core, "ROOT", tmp_path)

    errors = validate("library_routing", load_data(routing_path))

    assert any(error.startswith("supersedes.sha256: expected ") for error in errors)
