#!/usr/bin/env python3
"""Prepare the live-editing (in-browser generator) web assets.

Bundles the minimal Python import chain for the cabinet generator
(sdk + specific_editing glue + generator snapshot) into
public/live/articraft-live.zip, and vendors the Pyodide runtime plus the
numpy/micropip/trimesh wheels into public/vendor/pyodide/ so the browser
can run the generator fully offline. Nothing here is loaded until the
reader explicitly opens Live mode.

    python3 scripts/prepare_live.py
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTI = Path("/home/lyuyuanbo.lyb/PVA/arti-template")
LIVE = ROOT / "public/live"
VENDOR = ROOT / "public/vendor/pyodide"
PYODIDE_PKG = ROOT / "node_modules/pyodide"

CDN = "https://cdn.jsdelivr.net/pyodide/v{version}/full/{name}"
PYPI_JSON = "https://pypi.org/pypi/trimesh/json"

RUNTIME_FILES = ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
LOCK_PACKAGES = ["numpy"]

ZIP_INCLUDE = [
    ("specific_editing/__init__.py", "specific_editing/__init__.py"),
    ("specific_editing/export.py", "specific_editing/export.py"),
    ("specific_editing/selectors.py", "specific_editing/selectors.py"),
    ("specific_editing/generators/__init__.py", "specific_editing/generators/__init__.py"),
    ("specific_editing/generators/catalog.py", "specific_editing/generators/catalog.py"),
    ("specific_editing/generators/source/cabinet_doors.py", "specific_editing/generators/source/cabinet_doors.py"),
]
ZIP_TREE = ("sdk", "sdk")
ZIP_EXCLUDE_DIRS = {"__pycache__", "_docs", "_examples"}


def fetch(url: str, dst: Path, sha256: str | None = None) -> None:
    if dst.exists() and sha256 and hashlib.sha256(dst.read_bytes()).hexdigest() == sha256:
        return
    print(f"fetch {url}")
    with urllib.request.urlopen(url, timeout=120) as resp:
        data = resp.read()
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        raise SystemExit(f"sha256 mismatch for {url}")
    dst.write_bytes(data)


def build_zip(extra_wheels: list[Path]) -> Path:
    LIVE.mkdir(parents=True, exist_ok=True)
    out = LIVE / "articraft-live.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for src_rel, arc in ZIP_INCLUDE:
            zf.write(ARTI / src_rel, arc)
        src_root, arc_root = ZIP_TREE
        for path in sorted((ARTI / src_root).rglob("*.py")):
            if ZIP_EXCLUDE_DIRS & set(path.relative_to(ARTI / src_root).parts):
                continue
            zf.write(path, str(Path(arc_root) / path.relative_to(ARTI / src_root)))
        for wheel in extra_wheels:
            with zipfile.ZipFile(wheel) as wf:
                for name in wf.namelist():
                    if name.endswith("/") or ".dist-info/" in name:
                        continue
                    zf.writestr(name, wf.read(name))
    out.write_bytes(buf.getvalue())
    return out


def main() -> int:
    if not PYODIDE_PKG.exists():
        sys.exit("pyodide package missing: npm i -D pyodide")
    pkg = json.loads((PYODIDE_PKG / "package.json").read_text())
    version = pkg["version"]
    lock = json.loads((PYODIDE_PKG / "pyodide-lock.json").read_text())

    VENDOR.mkdir(parents=True, exist_ok=True)
    for name in RUNTIME_FILES:
        shutil.copy2(PYODIDE_PKG / name, VENDOR / name)
    wheels = []
    for name in LOCK_PACKAGES:
        info = lock["packages"][name]
        file_name = info["file_name"]
        fetch(CDN.format(version=version, name=file_name), VENDOR / file_name, info.get("sha256"))
        wheels.append(file_name)

    meta = json.loads(urllib.request.urlopen(PYPI_JSON, timeout=60).read())
    wheel = next(f for f in meta["urls"] if f["filename"].endswith("py3-none-any.whl"))
    tri_name = wheel["filename"]
    fetch(wheel["url"], VENDOR / tri_name, wheel.get("digests", {}).get("sha256"))

    zip_path = build_zip([VENDOR / tri_name])
    (VENDOR / tri_name).unlink()  # trimesh ships inside the zip; only numpy is loaded by name

    cabinet_manifest = json.loads(
        (ARTI / "specific_editing/outputs/single_variable/cabinet_paper_showcase/manifest.json").read_text()
    )
    total = sum(p.stat().st_size for p in VENDOR.iterdir()) + zip_path.stat().st_size
    manifest = {
        "pyodideVersion": version,
        "zip": "live/articraft-live.zip",
        "vendorDir": "vendor/pyodide",
        "wheels": wheels,
        "objects": ["cabinet_paper_showcase"],
        "baseConfig": cabinet_manifest["base"]["config"],
    }
    (LIVE / "live.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"zip: {zip_path.stat().st_size/1e6:.2f} MB, vendor total: {total/1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
