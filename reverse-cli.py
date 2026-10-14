"""Shared reverse-cli entry point; adapter command syntax remains compatible."""
from reverse_cli.cli import main
if __name__ == '__main__':
    raise SystemExit(main())
