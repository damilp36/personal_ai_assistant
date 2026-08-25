"""Small client for Ollama's local HTTP API."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import requests

MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:+-]{0,199}$")


class OllamaError(RuntimeError):
    """A friendly error raised for Ollama connection or API problems."""


@dataclass(frozen=True)
class PullUpdate:
    status: str
    completed: int = 0
    total: int = 0

    @property
    def progress(self) -> float | None:
        if self.total <= 0:
            return None
        return min(max(self.completed / self.total, 0.0), 1.0)


def normalize_base_url(base_url: str) -> str:
    """Normalize either an Ollama root URL or an /api URL."""

    cleaned = base_url.strip().rstrip("/")
    cleaned = cleaned.removesuffix("/api")
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"http://{cleaned}"
    return cleaned


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.session = session or requests.Session()

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/{path.lstrip('/')}"

    @staticmethod
    def _error_message(response: requests.Response) -> str:
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("error"):
                return str(body["error"])
        except ValueError:
            pass
        return response.text.strip() or f"HTTP {response.status_code}"

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        timeout: float | tuple[float, float] = 10,
        **kwargs: Any,
    ) -> dict[str, Any]:
        try:
            response = self.session.request(
                method, self._url(path), timeout=timeout, **kwargs
            )
        except requests.RequestException as error:
            raise OllamaError(
                f"I cannot reach Ollama at {self.base_url}. Make sure Ollama is running."
            ) from error
        if not response.ok:
            raise OllamaError(self._error_message(response))
        try:
            return response.json()
        except ValueError as error:
            raise OllamaError("Ollama sent a reply I could not read.") from error

    def version(self) -> str:
        data = self._request_json("GET", "version", timeout=3)
        return str(data.get("version", "unknown"))

    def list_models(self) -> list[dict[str, Any]]:
        data = self._request_json("GET", "tags", timeout=5)
        models = data.get("models", [])
        return sorted(models, key=lambda item: str(item.get("name", "")).lower())

    def model_capabilities(self, model: str) -> set[str]:
        data = self._request_json(
            "POST", "show", json={"model": model, "verbose": False}, timeout=10
        )
        return {str(item).lower() for item in data.get("capabilities", [])}

    def pull_model(self, model: str) -> Iterator[PullUpdate]:
        model = model.strip()
        if not MODEL_NAME_PATTERN.fullmatch(model):
            raise OllamaError("Use a valid Ollama model name, such as gemma3:4b.")
        try:
            response = self.session.post(
                self._url("pull"),
                json={"model": model, "stream": True},
                stream=True,
                timeout=(5, 3600),
            )
        except requests.RequestException as error:
            raise OllamaError(
                f"I cannot reach Ollama at {self.base_url}. Make sure Ollama is running."
            ) from error
        if not response.ok:
            raise OllamaError(self._error_message(response))

        try:
            try:
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise OllamaError(
                            "Ollama sent bad download progress data."
                        ) from error
                    if item.get("error"):
                        raise OllamaError(str(item["error"]))
                    yield PullUpdate(
                        status=str(item.get("status", "Working…")),
                        completed=int(item.get("completed", 0) or 0),
                        total=int(item.get("total", 0) or 0),
                    )
            except requests.RequestException as error:
                raise OllamaError("The model download connection stopped.") from error
        finally:
            response.close()

    def stream_chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        num_ctx: int = 8192,
        num_predict: int = 512,
    ) -> Iterator[str]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
                "num_predict": num_predict,
            },
        }
        try:
            response = self.session.post(
                self._url("chat"),
                json=payload,
                stream=True,
                timeout=(10, 600),
            )
        except requests.RequestException as error:
            raise OllamaError(
                f"I cannot reach Ollama at {self.base_url}. Make sure Ollama is running."
            ) from error
        if not response.ok:
            raise OllamaError(self._error_message(response))

        try:
            try:
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise OllamaError(
                            "Ollama sent a reply I could not read."
                        ) from error
                    if item.get("error"):
                        raise OllamaError(str(item["error"]))
                    content = item.get("message", {}).get("content", "")
                    if content:
                        yield str(content)
            except requests.RequestException as error:
                raise OllamaError("The Ollama chat connection stopped.") from error
        finally:
            response.close()
