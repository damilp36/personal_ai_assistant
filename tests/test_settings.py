from __future__ import annotations

from pathlib import Path

from assistant.settings import load_extra_rules, save_extra_rules


def test_saved_rules_can_be_loaded(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"

    save_extra_rules("Use a small table.", settings_path)

    assert load_extra_rules(settings_path) == "Use a small table."


def test_missing_settings_returns_empty_rules(tmp_path: Path) -> None:
    assert load_extra_rules(tmp_path / "missing.json") == ""
