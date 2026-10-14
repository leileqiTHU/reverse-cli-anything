"""Compatibility entry point; maintained implementation is in capcut-cli/."""
from pathlib import Path
import runpy
import sys

if __name__ == '__main__':
    adapter = Path(__file__).resolve().parent / 'capcut-cli'
    sys.path.insert(0, str(adapter))
    runpy.run_path(str(adapter / 'capcut_agent.py'), run_name='__main__')
