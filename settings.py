import json
from pathlib import Path

SETTINGS_DIR = Path.home() / ".site-content-tool"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


def load_settings() -> dict:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_settings(data: dict) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(SETTINGS_FILE)


def get_portfolio_site() -> Path | None:
    value = load_settings().get("portfolio_site")
    return Path(value) if value else None


def set_portfolio_site(path) -> None:
    data = load_settings()
    data["portfolio_site"] = str(path)
    _save_settings(data)
