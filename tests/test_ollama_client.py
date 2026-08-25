from assistant.ollama_client import normalize_base_url


def test_normalize_base_url() -> None:
    assert normalize_base_url("localhost:11434/") == "http://localhost:11434"
    assert normalize_base_url("http://localhost:11434/api") == "http://localhost:11434"
