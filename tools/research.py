"""Initialize research records, inspect declared progress or fingerprint explicit files."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reverse_cli import research


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("adapter")
    init.add_argument("--application", required=True)
    init.add_argument("--goal", required=True)
    init.add_argument("--operation", action="append", required=True)
    init.add_argument("--output", type=Path, required=True)
    status = commands.add_parser("status")
    status.add_argument("workspace", type=Path)
    identity = commands.add_parser("fingerprint")
    identity.add_argument("files", type=Path, nargs="+")
    identity.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = research.initialize(args.adapter, args.application, args.goal, args.operation, args.output)
        elif args.command == "status":
            result = research.inspect(args.workspace)
        else:
            result = {"ok": True, "result": research.fingerprint(args.files)}
            if args.output:
                research.save_new(args.output, result["result"])
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 2
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
