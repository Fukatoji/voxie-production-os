from pathlib import Path

from voxie_os.core import load_data, validate


ROOT = Path(__file__).resolve().parents[1]
ROUTING_PATH = ROOT / "manifests/library-routing.v2.yaml"
PREDECESSOR_PATH = ROOT / "manifests/library-routing.v1.yaml"


def test_existing_crlf_checkout_does_not_break_predecessor_checksum():
    original = PREDECESSOR_PATH.read_bytes()
    assert b"\r\n" not in original
    try:
        PREDECESSOR_PATH.write_bytes(original.replace(b"\n", b"\r\n"))
        assert b"\r\n" in PREDECESSOR_PATH.read_bytes()
        assert validate("library_routing", load_data(ROUTING_PATH)) == []
    finally:
        PREDECESSOR_PATH.write_bytes(original)


def test_predecessor_content_change_still_fails_after_line_ending_normalization():
    original = PREDECESSOR_PATH.read_bytes()
    try:
        PREDECESSOR_PATH.write_bytes(original + b"# unauthorized content change\r\n")
        errors = validate("library_routing", load_data(ROUTING_PATH))
        assert any(error.startswith("supersedes.sha256: expected ") for error in errors)
    finally:
        PREDECESSOR_PATH.write_bytes(original)
