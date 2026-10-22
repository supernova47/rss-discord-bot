from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "feedflow-deploy.zip"
ROOT_FILES = ("Dockerfile", ".dockerignore", "pyproject.toml", "main.py", "deploy/package.py")
SOURCE_DIRS = ("rssbot", "deploy/oracle", "deploy/selectel", "deploy/ruvds", "deploy/newvps")
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    ".ruff_cache",
    "__pycache__",
    "build",
    "data",
    "dist",
}


def include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if path.name == ".env" or path.name == "tokens.txt":
        return False
    if path.suffix in {".pyc", ".sqlite", ".sqlite3", ".db"}:
        return False
    if path.name.endswith(".egg-info"):
        return False
    return path.is_file()


def main() -> None:
    paths = [ROOT / name for name in ROOT_FILES]
    for directory in SOURCE_DIRS:
        paths.extend((ROOT / directory).rglob("*"))

    files = sorted({path for path in paths if include(path)})
    if not files:
        raise SystemExit("No project files found to package.")

    with ZipFile(ARCHIVE, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())

    print(f"Created {ARCHIVE}")
    print(
        f"Included {len(files)} files; .env, database files, tokens.txt and local environments "
        "are excluded."
    )


if __name__ == "__main__":
    main()
