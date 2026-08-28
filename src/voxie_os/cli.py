from __future__ import annotations

import argparse
import json
import sys

from .benchmark import summarize
from .core import SCHEMA_FILES, load_data, save_json, validate
from .qc import run_manifest_qc
from .timeline import to_neutral_timeline


def main() -> int:
    p = argparse.ArgumentParser(prog="voxie-os")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate")
    v.add_argument("kind", choices=sorted(SCHEMA_FILES))
    v.add_argument("path")

    q = sub.add_parser("qc")
    q.add_argument("canon")
    q.add_argument("manifest")
    q.add_argument("--out")

    t = sub.add_parser("timeline")
    t.add_argument("manifest")
    t.add_argument("--out", required=True)

    b = sub.add_parser("benchmark-summary")
    b.add_argument("run")

    args = p.parse_args()
    if args.cmd == "validate":
        errors = validate(args.kind, load_data(args.path))
        if errors:
            print("FAIL")
            print("\n".join(f"- {e}" for e in errors))
            return 1
        print("PASS")
        return 0

    if args.cmd == "qc":
        report = run_manifest_qc(load_data(args.canon), load_data(args.manifest))
        if args.out:
            save_json(args.out, report)
        print(json.dumps(report, indent=2))
        return 1 if report["status"] == "FAIL" else 0

    if args.cmd == "timeline":
        result = to_neutral_timeline(load_data(args.manifest))
        save_json(args.out, result)
        print(args.out)
        return 0

    if args.cmd == "benchmark-summary":
        print(json.dumps(summarize(load_data(args.run)), indent=2))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
