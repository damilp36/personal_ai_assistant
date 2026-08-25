from __future__ import annotations

from pathlib import Path

from assistant.settings import load_extra_rules, save_extra_rules, settings_path


def test_saved_rules_can_be_loaded(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"

    save_extra_rules("Use a small table.", settings_path)

    assert load_extra_rules(settings_path) == "Use a small table."


def test_missing_settings_returns_empty_rules(tmp_path: Path) -> None:
    assert load_extra_rules(tmp_path / "missing.json") == ""


def test_macos_settings_use_application_support(tmp_path: Path) -> None:
    path = settings_path(environ={}, platform_name="darwin", home=tmp_path)

    assert (
        path
        == tmp_path / "Library/Application Support/My Local Note Taker/settings.json"
    )


def test_windows_settings_use_local_app_data(tmp_path: Path) -> None:
    path = settings_path(
        environ={"LOCALAPPDATA": str(tmp_path)},
        platform_name="win32",
        home=Path("unused"),
    )

    assert path == tmp_path / "My Local Note Taker/settings.json"
