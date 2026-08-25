#!/bin/bash

set -e

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  open "https://www.python.org/downloads/"
  osascript -e 'display dialog "Python is needed. Install Python, then open Start Note Taker again." buttons {"OK"} default button "OK" with icon caution'
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

".venv/bin/python" -m pip install --disable-pip-version-check -r requirements.txt
exec ".venv/bin/python" desktop_launcher.py

