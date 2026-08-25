from assistant.ollama_client import OllamaClient, normalize_base_url


def test_normalize_base_url() -> None:
    assert normalize_base_url("localhost:11434/") == "http://localhost:11434"
    assert normalize_base_url("http://localhost:11434/api") == "http://localhost:11434"


def test_api_key_creates_bearer_header() -> None:
    client = OllamaClient("https://ollama.com", api_key="private-key")

    assert client.headers == {"Authorization": "Bearer private-key"}
