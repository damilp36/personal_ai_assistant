from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from assistant.ollama_client import OllamaClient

CLOUD_SECRETS = {
    "NOTE_TAKER_CLOUD_MODE": True,
    "OLLAMA_BASE_URL": "https://ollama.com",
    "OLLAMA_API_KEY": "test-key",
    "OLLAMA_ALLOWED_MODELS": ["test-model"],
    "NOTE_TAKER_ACCESS_PASSWORD": "long-test-password",
}


def cloud_app() -> AppTest:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(app_path, default_timeout=15)
    app.secrets.update(CLOUD_SECRETS)
    return app


def test_cloud_mode_stops_at_password_gate() -> None:
    app = cloud_app()

    app.run()

    assert not app.exception
    assert app.title[0].value == "🧸 My Local Note Taker"
    assert app.text_input[0].label == "Password"
    assert all(item.label != "Ollama address" for item in app.text_input)


def test_cloud_mode_hides_sensitive_controls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        OllamaClient,
        "list_models",
        lambda _client: [
            {"name": "test-model", "size": 100, "details": {"parameter_size": "1B"}}
        ],
    )
    monkeypatch.setattr(OllamaClient, "version", lambda _client: "test")
    app = cloud_app().run()

    app.text_input[0].input("long-test-password")
    app.button[0].click().run()

    button_labels = [button.label for button in app.button]
    assert not app.exception
    assert "Download model" not in button_labels
    assert "Save rules" not in button_labels
    assert "Sign out" in button_labels
    assert all(item.label != "Ollama address" for item in app.text_input)
    assert app.selectbox[0].options == ["test-model · 1B"]
