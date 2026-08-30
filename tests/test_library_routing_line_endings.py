from pathlib import Path
import shutil

import voxie_os.core as core
from voxie_os.core import load_data, validate


ROOT = Path(__file__).resolve().parents[1]
ROUTING_PATH = ROOT / "manifests/library-routing.v2.yaml"
PREDECESSOR_PATH = ROOT / "manifests/library-routing.v1.yaml"


def _isolated_routing_checkout(tmp_path):
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    shutil.copyfile(PREDECESSOR_PATH, manifests / PREDECESSOR_PATH.name)
    shutil.copyfile(ROUTING_PATH, manifests / ROUTING_PATH.name)
    return manifests / ROUTING_PATH.name


def test_existing_crlf_checkout_does_not_break_predecessor_checksum(tmp_path, monkeypatch):
    routing_path = _isolated_routing_checkout(tmp_path)
    predecessor_path = routing_path.parent / PREDECESSOR_PATH.name
    original = predecessor_path.read_bytes()
    assert b"\r\n" not in original
    monkeypatch.setattr(core, "ROOT", tmp_path)
    try:
        predecessor_path.write_bytes(original.replace(b"\n", b"\r\n"))
        assert b"\r\n" in predecessor_path.read_bytes()
        assert validate("library_routing", load_data(routing_path)) == []
    finally:
        predecessor_path.write_bytes(original)


def test_predecessor_content_change_still_fails_after_line_ending_normalization(tmp_path, monkeypatch):
    routing_path = _isolated_routing_checkout(tmp_path)
    predecessor_path = routing_path.parent / PREDECESSOR_PATH.name
    original = predecessor_path.read_bytes()
    monkeypatch.setattr(core, "ROOT", tmp_path)
    try:
        predecessor_path.write_bytes(original + b"# unauthorized content change\r\n")
        errors = validate("library_routing", load_data(routing_path))
        assert any(error.startswith("supersedes.sha256: expected ") for error in errors)
    finally:
        predecessor_path.write_bytes(original)
