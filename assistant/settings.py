"""Persistent settings stored only on the local machine."""

from __future__ import annotations

import json
from pathlib import Path

SETTINGS_PATH = Path(__file__).resolve().parents[1] / ".local" / "settings.json"


class SettingsError(RuntimeError):
    """Raised when local settings cannot be read or written."""


def load_extra_rules(path: Path = SETTINGS_PATH) -> str:
    """Load saved extra rules, or return an empty string when none exist."""

    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SettingsError("I could not read the saved rules.") from error

    rules = data.get("extra_rules", "") if isinstance(data, dict) else ""
    return rules if isinstance(rules, str) else ""


def save_extra_rules(rules: str, path: Path = SETTINGS_PATH) -> None:
    """Save extra rules with an atomic local file replacement."""

    temporary_path = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_text(
            json.dumps({"extra_rules": rules}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except OSError as error:
        raise SettingsError("I could not save the rules.") from error
