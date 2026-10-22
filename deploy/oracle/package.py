import runpy
from pathlib import Path

PACKAGE_SCRIPT = Path(__file__).resolve().parents[1] / "package.py"
runpy.run_path(str(PACKAGE_SCRIPT), run_name="__main__")
