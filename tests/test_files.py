from __future__ import annotations

from io import BytesIO

from assistant.files import make_model_content, prepare_uploads


class Upload(BytesIO):
    def __init__(self, name: str, content: bytes) -> None:
        super().__init__(content)
        self.name = name

    def getvalue(self) -> bytes:
        return super().getvalue()


def test_prepares_text_file() -> None:
    result = prepare_uploads([Upload("notes.txt", b"A small note")])

    assert "A small note" in result.context
    assert result.attachments[0]["name"] == "notes.txt"
    assert result.images == []


def test_prepares_image_as_base64() -> None:
    result = prepare_uploads([Upload("photo.png", b"fake-image")])

    assert result.images[0]["name"] == "photo.png"
    assert result.images[0]["data"] == "ZmFrZS1pbWFnZQ=="


def test_model_content_keeps_request_and_file_context() -> None:
    content = make_model_content("Make this short", "FILE TEXT")

    assert "Make this short" in content
    assert "FILE TEXT" in content
