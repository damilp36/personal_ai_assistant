from assistant.config import LOCAL_OLLAMA_URL, load_app_config


def test_local_mode_defaults() -> None:
    config = load_app_config(secrets={}, environ={})

    assert config.cloud_mode is False
    assert config.ollama_base_url == LOCAL_OLLAMA_URL
    assert config.errors == ()


def test_cloud_mode_requires_safe_settings() -> None:
    config = load_app_config(
        secrets={"NOTE_TAKER_CLOUD_MODE": True},
        environ={},
    )

    assert config.cloud_mode is True
    assert len(config.errors) == 4


def test_cloud_mode_accepts_valid_settings() -> None:
    config = load_app_config(
        secrets={
            "NOTE_TAKER_CLOUD_MODE": True,
            "OLLAMA_BASE_URL": "https://ollama.com",
            "OLLAMA_API_KEY": "secret-key",
            "OLLAMA_ALLOWED_MODELS": ["model-one", "model-two"],
            "NOTE_TAKER_ACCESS_PASSWORD": "long-password",
            "NOTE_TAKER_REQUESTS_PER_MINUTE": 5,
        },
        environ={},
    )

    assert config.errors == ()
    assert config.allowed_models == ("model-one", "model-two")
    assert config.requests_per_minute == 5
