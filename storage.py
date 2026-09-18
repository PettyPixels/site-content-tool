import json
import os
import shutil
import tempfile
from pathlib import Path

from config import PORTFOLIO_SITE, DATA_DIR


class JSONParseError(Exception):
    pass


def load_entries(json_file):
    path = DATA_DIR / json_file
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise JSONParseError(f"{json_file} could not be parsed: {e}") from e


def save_entries(json_file, entries):
    path = DATA_DIR / json_file
    DATA_DIR.mkdir(exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=DATA_DIR, prefix=f".{json_file}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _unique_image_path(images_dir, filename):
    dest = images_dir / filename
    if not dest.exists():
        return dest
    stem, suffix = os.path.splitext(filename)
    n = 2
    while True:
        candidate = images_dir / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def copy_image(source_path, images_dir):
    source_path = Path(source_path)
    try:
        if source_path.resolve().parent == images_dir.resolve():
            return str(source_path.relative_to(PORTFOLIO_SITE))
    except (OSError, ValueError):
        pass
    images_dir.mkdir(parents=True, exist_ok=True)
    dest = _unique_image_path(images_dir, source_path.name)
    shutil.copy2(source_path, dest)
    return str(dest.relative_to(PORTFOLIO_SITE))
