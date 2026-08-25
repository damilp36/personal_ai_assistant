from pathlib import Path
from typing import Self

import pytest

import desktop_launcher


def test_source_bundle_root_is_project_root() -> None:
    assert desktop_launcher.bundle_root() == Path(desktop_launcher.__file__).parent


def test_available_port_is_local_port(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSocket:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def bind(self, address: tuple[str, int]) -> None:
            assert address == ("127.0.0.1", 0)

        def getsockname(self) -> tuple[str, int]:
            return ("127.0.0.1", 18_501)

    monkeypatch.setattr(
        desktop_launcher.socket,
        "socket",
        lambda *_args: FakeSocket(),
    )

    assert desktop_launcher.available_port(0) == 18_501
