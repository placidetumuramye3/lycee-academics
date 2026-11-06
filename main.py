"""Compatibility entrypoint for the legacy backend database helper."""

import runpy
from pathlib import Path

if __name__ == "__main__":
   
 backend_main = Path(__file__).resolve().parent / "backend-app" / "main.py"
 runpy.run_path(str(backend_main), run_name="__main__")
