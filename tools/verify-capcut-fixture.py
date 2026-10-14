"""Compatibility entry point for an optional, historical showcase script."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parents[1]/"examples/tools/verify-capcut-fixture.py"),run_name="__main__")
