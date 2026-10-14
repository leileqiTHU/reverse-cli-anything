"""Render adapter command documentation from saved data without importing runtime hooks."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reverse_cli.delivery import generate_docs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New subdirectory inside the adapter root")
    args = parser.parse_args()
    try:
        result = generate_docs(args.manifest, args.output)
    except (ValueError, OSError, KeyError, TypeError) as error:
        result = {"ok": False, "error": str(error)}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
