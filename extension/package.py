#!/usr/bin/env python3
"""Create a clean, loadable ZIP package for the VANTIQ Chrome extension."""
from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
DIST = REPO_ROOT / "dist"
REQUIRED_FILES = (
    "manifest.json",
    "content.js",
    "service-worker.js",
    "sidepanel.html",
    "sidepanel.css",
    "sidepanel.js",
    "transcript.mjs",
)


def main() -> None:
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != 3:
        raise SystemExit("Only Manifest V3 extensions are supported.")

    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit(f"Missing required extension files: {', '.join(missing)}")

    DIST.mkdir(exist_ok=True)
    version = manifest["version"]
    output = DIST / f"VANTIQ-Chrome-Extension-{version}.zip"
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name in REQUIRED_FILES:
            archive.write(ROOT / name, arcname=name)

    print(f"Packaged {len(REQUIRED_FILES)} files: {output.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
