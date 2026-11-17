from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
OUTPUT = ROOT.parent / "dist" / "VANTIQ-WhatsApp-Dock-0.2.0.zip"

if not (DIST / "manifest.json").exists():
    raise SystemExit("Build the extension first: npm run build")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
    for path in sorted(DIST.rglob("*")):
        if path.is_file():
            archive.write(path, path.relative_to(DIST))
print(f"Packaged Chrome extension: {OUTPUT}")
