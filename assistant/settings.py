"""Persistent settings stored only on the local machine."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path


def settings_path(
    environ: Mapping[str, str] | None = None,
    platform_name: str | None = None,
    home: Path | None = None,
) -> Path:
    """Return a writable per-user settings path for the current system."""

    environment = environ if environ is not None else os.environ
    system = platform_name or sys.platform
    user_home = home or Path.home()

    custom_directory = environment.get("NOTE_TAKER_DATA_DIR")
    if custom_directory:
        return Path(custom_directory).expanduser() / "settings.json"
    if system == "darwin":
        return (
            user_home
            / "Library"
            / "Application Support"
            / "My Local Note Taker"
            / "settings.json"
        )
    if system == "win32":
        local_data = environment.get("LOCALAPPDATA")
        root = Path(local_data) if local_data else user_home / "AppData" / "Local"
        return root / "My Local Note Taker" / "settings.json"
    config_root = Path(environment.get("XDG_CONFIG_HOME", user_home / ".config"))
    return config_root / "my-local-note-taker" / "settings.json"


SETTINGS_PATH = settings_path()


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
