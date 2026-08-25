# My Local Note Taker

A private Streamlit assistant powered by Ollama on the same computer. It is built for online work and writes with short sentences and basic English.

Nothing is sent to a hosted model service. No model key or account is required.

## What it can do

- Chat with Ollama models installed on the computer.
- Download an Ollama model by name from inside the application.
- Read PDF, DOCX, XLSX, CSV, TSV, JSON, Markdown, text, and common code files.
- Send PNG, JPG, and WebP images to models that support vision.
- Stream answers as the model writes them.
- Switch between online work, writing, study, coding, and general modes.
- Save extra rules and export chats as Markdown.

## Download without cloning

Open the [latest GitHub release](https://github.com/damilp36/personal_ai_assistant/releases/latest) and download the file for your computer.

### macOS

1. Download `My-Local-Note-Taker-macOS-Apple-Silicon.zip` for an M-series Mac,
   or `My-Local-Note-Taker-macOS-Intel.zip` for an Intel Mac.
2. Unzip it and move **My Local Note Taker** to Applications.
3. Open it. If macOS blocks an unsigned download, right-click it and select **Open**.
4. If Ollama is missing, its official download page opens. Install Ollama and reopen the note taker.
5. Use the left panel to download a model, such as `gemma3:4b`.

### Windows

1. Download `My-Local-Note-Taker-Windows.zip`.
2. Unzip the whole folder.
3. Open `My Local Note Taker.exe` inside that folder.
4. If Windows SmartScreen appears, inspect the publisher warning before choosing **More info → Run anyway**.
5. If Ollama is missing, its official download page opens. Install Ollama and reopen the note taker.
6. Use the left panel to download a model, such as `gemma3:4b`.

The downloads are built by the GitHub workflow in `.github/workflows/build-desktop.yml`. They contain Python and the required packages, so users do not need Git, Python, or terminal commands.

## Start from the source ZIP

Users who do not want the packaged build can select **Code → Download ZIP** on GitHub. After extracting it:

- macOS: double-click `Start Note Taker.command`.
- Windows: double-click `Start Note Taker.bat`.
- Linux: run `./start-note-taker.sh`.

These launchers create a private `.venv`, install `requirements.txt`, start Ollama when it is installed, start Streamlit on `127.0.0.1`, and open the browser. Python 3 is required only for this source-ZIP method.

## Create downloadable releases

The repository owner can build the Windows download and both Mac downloads from
GitHub Actions:

1. Open **Actions → Build desktop downloads → Run workflow** to test a build.
2. Create and push a version tag to publish the downloads on a GitHub release:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

The builds are unsigned. Distributing without operating-system warnings requires Apple and Microsoft code-signing certificates.

## Manual development setup

1. Install [Ollama](https://ollama.com/download).
2. Start Ollama.
3. Create the Python environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

4. Start the local launcher:

   ```bash
   python desktop_launcher.py
   ```

The application binds to `127.0.0.1`. A Streamlit Community Cloud URL only shows a link to the local downloads; it never processes prompts or files.

## Pick a model

A smaller model is faster and uses less memory. A larger model may give better answers but needs more RAM. For images, choose a model whose Ollama details list the `vision` capability.

Model downloads need internet access. After a model is installed, chat generation runs through local Ollama.

## Files and settings

- Each upload is limited to 15 MB.
- Very long document text is clipped so it cannot fill the whole model context.
- Scanned PDFs need OCR before this version can read them.
- Saved rules use the normal per-user application-data folder on macOS, Windows, or Linux.

## Development checks

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
ruff check .
ruff format --check .
```

## Privacy notes

- Streamlit listens only on the local loopback address.
- Chats are held in the active browser session and are not written to a database.
- Uploaded file data stays in the local Streamlit process.
- Prompts, files, and answers go only between this application and local Ollama.

The note taker does not browse the web, sign in to job sites, or submit work. It helps read instructions and prepare answers; the user controls final submissions.
