# My Local Note Taker

A Streamlit personal assistant powered by a local [Ollama](https://ollama.com/) model. It is built for online work and writes with short sentences and basic English.

## What it can do

- Chat with any Ollama model installed on your machine.
- Download any public Ollama model by name from the app.
- Read PDF, DOCX, XLSX, CSV, TSV, JSON, Markdown, plain text, and common code files.
- Send PNG, JPG, and WebP images to models that support vision.
- Stream answers as the model writes them.
- Switch between online work, writing, study, coding, and general modes.
- Save a chat as a Markdown file.
- Keep generation local. No API key is needed for a local Ollama server.

## Quick start

1. Install [Ollama](https://ollama.com/download).

2. Start Ollama. The desktop app normally starts it for you. You can also run:

   ```bash
   ollama serve
   ```

3. Create a Python environment and install the app:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

   On Windows PowerShell, activate it with:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

4. Start the app:

   ```bash
   streamlit run app.py
   ```

5. Open the local link shown by Streamlit. Use the left panel to download a model. For example, enter `gemma3:4b`. Model downloads can be large.

You may also install a model before opening the app:

```bash
ollama pull gemma3:4b
```

## Pick a model

The app accepts any valid Ollama model name. A smaller model is faster and uses less memory. A larger model may give better answers but needs more RAM. To ask about images, choose a model whose Ollama details list the `vision` capability.

The model name and size tag must exist in the [Ollama model library](https://ollama.com/search). Downloading a model is the one feature that needs internet access. Chat generation uses the configured Ollama server.

## Settings

The default Ollama address is `http://localhost:11434`. To use another address when the app starts:

```bash
OLLAMA_BASE_URL=http://192.168.1.20:11434 streamlit run app.py
```

The app reads at most 15 MB per upload. It also clips very long file text so one file cannot fill the whole model context. Scanned PDFs do not contain normal text and need OCR before this version can read them.

## Development checks

```bash
python -m pip install -r requirements-dev.txt
pytest -q
ruff check .
```

## Privacy notes

- Chat data is held in the Streamlit browser session and is not written to a database.
- Uploaded file data is kept in that active session so the model can remember recent turns.
- The app sends prompts and files only to the Ollama address shown in the sidebar.
- If that address points to another computer or a cloud service, the data is no longer only on this computer.

This first version does not browse the web, sign in to job sites, or submit work for you. It helps you read instructions and prepare answers; you stay in control of final submissions.
