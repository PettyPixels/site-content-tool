import tempfile
from pathlib import Path

import pytest

# config.py reads the saved portfolio-site location the moment it is imported, and raises
# if there isn't one. Point that lookup at a throwaway folder *before* any app module is
# imported, so (a) tests run on machines with no settings file (CI), and (b) a test can
# never reach the real site, even by accident.
import settings

_IMPORT_TIME_SITE = Path(tempfile.mkdtemp(prefix="sct-import-"))
settings.get_portfolio_site = lambda: _IMPORT_TIME_SITE

import blog_logic  # noqa: E402
import storage  # noqa: E402


@pytest.fixture
def site(tmp_path, monkeypatch):
    """A fresh, empty portfolio-site folder, wired into every module that captured a path.

    storage.py and blog_logic.py do `from config import X`, which copies the value at
    import time, so patching config alone wouldn't reach them. Patch each module's own name.
    """
    root = tmp_path / "site"
    (root / "data").mkdir(parents=True)
    (root / "blog").mkdir()
    monkeypatch.setattr(storage, "PORTFOLIO_SITE", root)
    monkeypatch.setattr(storage, "DATA_DIR", root / "data")
    monkeypatch.setattr(blog_logic, "BLOG_DIR", root / "blog")
    return root
