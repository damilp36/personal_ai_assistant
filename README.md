# My Local Note Taker

A Streamlit personal assistant powered by a local [Ollama](https://ollama.com/) model. It is built for online work and writes with short sentences and basic English.

## What it can do

- Chat with approved Ollama models.
- Download any public Ollama model by name when running locally.
- Read PDF, DOCX, XLSX, CSV, TSV, JSON, Markdown, plain text, and common code files.
- Send PNG, JPG, and WebP images to models that support vision.
- Stream answers as the model writes them.
- Switch between online work, writing, study, coding, and general modes.
- Save a chat as a Markdown file.
- Run locally without a key, or connect safely to a hosted model service.

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

## Deploy on Streamlit Community Cloud

Streamlit installs the Python packages in `requirements.txt` during deployment. Visitors only need the app URL. Do not add a terminal or package-install button.

The hosted app cannot use Ollama on a visitor's `localhost`. Use Ollama Cloud or an HTTPS Ollama server protected by a bearer token.

1. Push this project to a GitHub repository.

2. In Streamlit Community Cloud, create an app from that repository. Set the entrypoint to `app.py`.

3. Open **Advanced settings**, then paste the following into **Secrets**:

   ```toml
   NOTE_TAKER_CLOUD_MODE = true
   OLLAMA_BASE_URL = "https://ollama.com"
   OLLAMA_API_KEY = "replace-with-your-private-key"
   OLLAMA_ALLOWED_MODELS = ["gpt-oss:20b"]
   NOTE_TAKER_ACCESS_PASSWORD = "replace-with-a-long-private-password"
   NOTE_TAKER_REQUESTS_PER_MINUTE = 6
   ```

4. Replace the example values. The model names must be available from your configured service. Use a password with at least 12 characters.

5. Deploy the app and share its Streamlit URL.

Cloud mode makes these changes automatically:

- The Ollama address cannot be changed by visitors.
- The secret key stays on the server.
- Only models in `OLLAMA_ALLOWED_MODELS` appear.
- Model downloads are hidden.
- A password is required before the model service is contacted.
- Each signed-in session is limited to the configured number of messages per minute.
- Extra rules remain in that visitor's session and are not written to a shared file.

The same template is available at `.streamlit/secrets.toml.example`. Never rename it to `secrets.toml` and commit real secrets.

## Pick a model

The app accepts any valid Ollama model name. A smaller model is faster and uses less memory. A larger model may give better answers but needs more RAM. To ask about images, choose a model whose Ollama details list the `vision` capability.

The model name and size tag must exist in the [Ollama model library](https://ollama.com/search). Downloading a model is the one feature that needs internet access. Chat generation uses the configured Ollama server.

## Settings

The default Ollama address is `http://localhost:11434`. To use another address when the app starts:

```bash
OLLAMA_BASE_URL=http://192.168.1.20:11434 streamlit run app.py
```

Local mode keeps the address and model-download controls available. It also lets the Save rules button write to `.local/settings.json`.

The app reads at most 15 MB per upload. It also clips very long file text so one file cannot fill the whole model context. Scanned PDFs do not contain normal text and need OCR before this version can read them.

## Development checks

```bash
python -m pip install -r requirements-dev.txt
pytest -q
ruff check .
```

## Privacy notes

- Chat data is held in the Streamlit session and is not written to a database.
- Uploaded file data is kept in that active session so the model can remember recent turns.
- Local mode sends prompts and files to the Ollama address shown in the sidebar.
- Cloud mode sends them to the private model service configured by the app owner.
- The built-in cloud password is shared access protection, not a separate user-account system.

This first version does not browse the web, sign in to job sites, or submit work for you. It helps you read instructions and prepare answers; you stay in control of final submissions.
