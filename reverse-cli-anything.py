"""Canonical entry point; reverse-cli.py remains a compatibility alias."""
from reverse_cli.cli import main
if __name__ == '__main__':
    raise SystemExit(main())
