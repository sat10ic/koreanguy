"""One-time migration of ChartsMaze history into manas_os/data.

Copies the existing dated-folder history (and root ``*-master.csv`` files) from
the legacy SwingEdge location into ``manas_os/data/chartsmaze``, leaving the
source untouched. After running this, the user must repoint the extractor — see
``manas_os/MIGRATION.md``.
"""
from __future__ import annotations

import shutil
from pathlib import Path

_LEGACY_SRC = "legacy/SwingEdge/data/chartsmaze"
_DEST = "data/chartsmaze"


def default_src() -> Path:
    return (Path(__file__).resolve().parents[2] / _LEGACY_SRC).resolve()


def default_dst() -> Path:
    return (Path(__file__).resolve().parents[1] / _DEST).resolve()


def migrate_history(src: str | Path | None = None,
                    dst: str | Path | None = None) -> list[str]:
    """Copy ChartsMaze history from ``src`` into ``dst`` (source is preserved).

    Copies every dated subfolder and every root ``*.csv`` (e.g. master files).
    Existing dated folders in ``dst`` are left as-is (skipped) so re-running is
    safe. Returns the list of top-level item names copied.
    """
    src_p = Path(src) if src is not None else default_src()
    dst_p = Path(dst) if dst is not None else default_dst()
    if not src_p.is_dir():
        raise FileNotFoundError(f"source not found: {src_p}")
    dst_p.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for item in sorted(src_p.iterdir()):
        target = dst_p / item.name
        if item.is_dir():
            if target.exists():
                continue  # don't clobber an already-migrated date folder
            shutil.copytree(item, target)
            copied.append(item.name)
        elif item.is_file() and item.suffix.lower() == ".csv":
            shutil.copy2(item, target)  # refresh root master CSVs
            copied.append(item.name)
    return copied
