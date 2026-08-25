"""Start Ollama when possible, then open the local Streamlit application."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from streamlit.web import cli as streamlit_cli

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_DOWNLOAD_URL = "https://ollama.com/download"


def bundle_root() -> Path:
    """Return the source root in development or inside a packaged build."""

    frozen_root = getattr(sys, "_MEIPASS", None)
    return Path(frozen_root) if frozen_root else Path(__file__).resolve().parent


def find_ollama() -> Path | None:
    """Find Ollama in the command path or its normal application folder."""

    command = shutil.which("ollama")
    if command:
        return Path(command)

    candidates: list[Path] = []
    if sys.platform == "darwin":
        candidates.append(Path("/Applications/Ollama.app/Contents/Resources/ollama"))
    elif sys.platform == "win32":
        local_data = os.environ.get("LOCALAPPDATA")
        if local_data:
            candidates.append(Path(local_data) / "Programs" / "Ollama" / "ollama.exe")
    else:
        candidates.extend([Path("/usr/local/bin/ollama"), Path("/usr/bin/ollama")])

    return next((path for path in candidates if path.is_file()), None)


def ollama_is_ready(timeout: float = 0.5) -> bool:
    """Check whether the local Ollama HTTP service is responding."""

    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/version", timeout=timeout):
            return True
    except (OSError, urllib.error.URLError):
        return False


def start_ollama() -> None:
    """Start an installed Ollama service without opening a terminal window."""

    if ollama_is_ready():
        return

    executable = find_ollama()
    if executable is None:
        webbrowser.open(OLLAMA_DOWNLOAD_URL)
        return

    if sys.platform == "darwin":
        subprocess.Popen(
            ["open", "-a", "Ollama"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        subprocess.Popen(
            [str(executable), "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )

    for _attempt in range(20):
        if ollama_is_ready():
            return
        time.sleep(0.5)


def available_port(preferred: int = 8501) -> int:
    """Choose the normal Streamlit port, or another local free port."""

    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return int(probe.getsockname()[1])
    raise RuntimeError("No local port is available.")


def open_browser_when_ready(url: str) -> None:
    """Open the browser after Streamlit reports that it is healthy."""

    health_url = f"{url}/_stcore/health"
    for _attempt in range(120):
        try:
            with urllib.request.urlopen(health_url, timeout=0.5):
                webbrowser.open(url)
                return
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)


def main() -> int:
    """Launch all local services and hand control to Streamlit."""

    root = bundle_root()
    app_path = root / "app.py"
    if not app_path.is_file():
        raise FileNotFoundError(f"The application file is missing: {app_path}")

    os.chdir(root)
    start_ollama()
    port = available_port()
    local_url = f"http://127.0.0.1:{port}"
    threading.Thread(
        target=open_browser_when_ready,
        args=(local_url,),
        daemon=True,
    ).start()

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--global.developmentMode=false",
        "--server.headless=true",
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    return int(streamlit_cli.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
