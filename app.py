"""Streamlit interface for a local, simple-English Ollama assistant."""

from __future__ import annotations

import base64
import binascii
import hmac
import math
from datetime import datetime
from time import monotonic
from typing import Any

import streamlit as st

from assistant.config import AppConfig, load_app_config
from assistant.files import (
    STREAMLIT_FILE_TYPES,
    FilePreparationError,
    make_model_content,
    prepare_uploads,
)
from assistant.ollama_client import OllamaClient, OllamaError
from assistant.prompts import PROFILE_PROMPTS, build_system_prompt
from assistant.settings import SettingsError, load_extra_rules, save_extra_rules

ANSWER_LENGTHS = {
    "Short": 256,
    "Medium": 512,
    "Long": 1024,
}


st.set_page_config(
    page_title="My Local Note Taker",
    page_icon="🧸",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {max-width: 980px; padding-top: 2rem;}
      [data-testid="stChatMessage"] {border-radius: 14px; padding: .35rem .65rem;}
      .small-note {color: #667085; font-size: .88rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def read_streamlit_secrets() -> dict[str, Any]:
    """Read hosted secrets without requiring a local secrets file."""

    try:
        return dict(st.secrets)
    except FileNotFoundError:
        return {}


APP_CONFIG = load_app_config(read_streamlit_secrets())


def init_state(config: AppConfig) -> None:
    saved_rules = ""
    settings_error = None
    if "extra_rules" not in st.session_state and not config.cloud_mode:
        try:
            saved_rules = load_extra_rules()
        except SettingsError as error:
            settings_error = str(error)
    defaults = {
        "messages": [],
        "selected_model": None,
        "pending_model": None,
        "ollama_url": config.ollama_base_url,
        "pull_notice": None,
        "extra_rules": saved_rules,
        "rules_notice": None,
        "settings_error": settings_error,
        "authenticated": not config.cloud_mode,
        "request_times": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def save_rules() -> None:
    """Save the rules currently held by the text-area widget."""

    if APP_CONFIG.cloud_mode:
        st.session_state.rules_notice = "Your rules will last for this session."
        return
    try:
        save_extra_rules(st.session_state.extra_rules)
        st.session_state.rules_notice = "Your rules were saved."
        st.session_state.settings_error = None
    except SettingsError as error:
        st.session_state.settings_error = str(error)


def clear_rules() -> None:
    """Clear the widget and its saved local value."""

    if APP_CONFIG.cloud_mode:
        st.session_state.extra_rules = ""
        st.session_state.rules_notice = "Your session rules were cleared."
        return
    try:
        save_extra_rules("")
        st.session_state.extra_rules = ""
        st.session_state.rules_notice = "Your saved rules were cleared."
        st.session_state.settings_error = None
    except SettingsError as error:
        st.session_state.settings_error = str(error)


def logout() -> None:
    """End access and clear private session content."""

    st.session_state.authenticated = False
    st.session_state.messages = []
    st.session_state.extra_rules = ""
    st.session_state.request_times = []


def take_request_slot(limit: int) -> int | None:
    """Reserve a per-session request slot or return seconds until retry."""

    now = monotonic()
    recent = [stamp for stamp in st.session_state.request_times if now - stamp < 60]
    st.session_state.request_times = recent
    if len(recent) >= limit:
        return max(1, math.ceil(60 - (now - recent[0])))
    st.session_state.request_times.append(now)
    return None


def make_ollama_client(base_url: str) -> OllamaClient:
    """Create a client with server-only authentication when configured."""

    return OllamaClient(
        base_url,
        api_key=APP_CONFIG.ollama_api_key,
        show_url_in_errors=not APP_CONFIG.cloud_mode,
    )


@st.cache_data(ttl=4, show_spinner=False)
def get_server_info(base_url: str, _api_key: str, cloud_mode: bool) -> dict[str, Any]:
    client = OllamaClient(
        base_url,
        api_key=_api_key,
        show_url_in_errors=not cloud_mode,
    )
    try:
        models = client.list_models()
        try:
            version = client.version()
        except OllamaError:
            version = "unknown"
        return {
            "connected": True,
            "version": version,
            "models": models,
            "error": "",
        }
    except OllamaError as error:
        return {"connected": False, "version": "", "models": [], "error": str(error)}


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def model_label(model: dict[str, Any]) -> str:
    name = str(model.get("name") or model.get("model") or "Unknown")
    details = model.get("details") or {}
    parameter_size = details.get("parameter_size")
    return f"{name} · {parameter_size}" if parameter_size else name


def show_attachments(message: dict[str, Any]) -> None:
    attachments = message.get("attachments", [])
    if attachments:
        names = " · ".join(f"📎 {item['name']}" for item in attachments)
        st.caption(names)
    for image in message.get("images", []):
        try:
            st.image(base64.b64decode(image["data"]), caption=image["name"], width=260)
        except (binascii.Error, KeyError, TypeError, ValueError):
            st.caption(f"Image: {image.get('name', 'attachment')}")


def history_for_ollama(
    messages: list[dict[str, Any]], system_prompt: str, history_turns: int
) -> list[dict[str, Any]]:
    history = messages[-(history_turns * 2 + 1) :]
    result: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for message in history:
        if message.get("error"):
            continue
        item: dict[str, Any] = {
            "role": message["role"],
            "content": message.get("model_content", message.get("content", "")),
        }
        images = message.get("images", [])
        if images:
            item["images"] = [image["data"] for image in images]
        result.append(item)
    return result


def export_chat(messages: list[dict[str, Any]]) -> str:
    lines = ["# My Local Note Taker chat", ""]
    for message in messages:
        role = "You" if message["role"] == "user" else "Assistant"
        lines.extend([f"## {role}", "", message.get("content", ""), ""])
        attachments = message.get("attachments", [])
        if attachments:
            lines.append("Files: " + ", ".join(item["name"] for item in attachments))
            lines.append("")
    return "\n".join(lines)


init_state(APP_CONFIG)

if APP_CONFIG.errors:
    st.title("Setup needed")
    st.error("The hosted app settings are not complete.")
    for config_error in APP_CONFIG.errors:
        st.code(config_error)
    st.caption("The app owner must update the Streamlit secrets, then restart the app.")
    st.stop()

if APP_CONFIG.cloud_mode and not st.session_state.authenticated:
    st.title("🧸 My Local Note Taker")
    st.caption("Enter the access password to continue.")
    with st.form("access_form", clear_on_submit=True):
        password_attempt = st.text_input("Password", type="password")
        sign_in = st.form_submit_button("Open note taker", use_container_width=True)
    if sign_in:
        if hmac.compare_digest(password_attempt, APP_CONFIG.access_password):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("That password is not right.")
    st.stop()

with st.sidebar:
    st.title("Settings")
    if APP_CONFIG.cloud_mode:
        base_url = APP_CONFIG.ollama_base_url
        st.caption("🔒 Secure cloud mode")
    else:
        base_url = st.text_input(
            "Ollama address",
            key="ollama_url",
            help="The normal local address is http://localhost:11434.",
        )
    refresh = st.button("↻ Check Ollama", use_container_width=True)
    if refresh:
        get_server_info.clear()

    server = get_server_info(
        base_url,
        APP_CONFIG.ollama_api_key,
        APP_CONFIG.cloud_mode,
    )
    if server["connected"]:
        if APP_CONFIG.cloud_mode:
            st.success("Model service is ready")
        else:
            st.success(f"Ollama is ready · v{server['version']}")
    else:
        st.error("Ollama is not ready")
        st.caption(server["error"])

    models = server["models"]
    if APP_CONFIG.cloud_mode:
        models_by_name = {
            str(model.get("name") or model.get("model")): model for model in models
        }
        models = [
            models_by_name[name]
            for name in APP_CONFIG.allowed_models
            if name in models_by_name
        ]
    model_names = [str(model.get("name") or model.get("model")) for model in models]
    if model_names:
        pending_model = st.session_state.pop("pending_model", None)
        if pending_model:
            pending_base = pending_model.split(":", maxsplit=1)[0]
            matching_model = next(
                (
                    name
                    for name in model_names
                    if name == pending_model
                    or name.split(":", maxsplit=1)[0] == pending_base
                ),
                None,
            )
            if matching_model:
                st.session_state.selected_model = matching_model
        if st.session_state.selected_model not in model_names:
            st.session_state.selected_model = model_names[0]
        selected_model = st.selectbox(
            "Model",
            options=model_names,
            key="selected_model",
            format_func=lambda name: model_label(models[model_names.index(name)]),
        )
        chosen = models[model_names.index(selected_model)]
        st.caption(f"Stored size: {human_size(int(chosen.get('size', 0) or 0))}")
    else:
        selected_model = None
        if APP_CONFIG.cloud_mode and server["connected"]:
            st.error(
                "No allowed model is available. The app owner must check the secrets."
            )
        else:
            st.info("No model is installed yet.")

    if not APP_CONFIG.cloud_mode:
        with st.expander("Install an Ollama model", expanded=not bool(model_names)):
            st.caption("Type any model name from the Ollama model library.")
            new_model = st.text_input(
                "Model name",
                placeholder="gemma3:4b",
                help="The tag after : can select a model size.",
            )
            if st.button(
                "Download model",
                disabled=not server["connected"] or not new_model.strip(),
                use_container_width=True,
            ):
                client = make_ollama_client(base_url)
                try:
                    with st.status(
                        "Starting download…", expanded=True
                    ) as download_status:
                        progress_bar = st.progress(0.0)
                        progress_text = st.empty()
                        for update in client.pull_model(new_model):
                            progress_text.write(update.status)
                            if update.progress is not None:
                                progress_bar.progress(update.progress)
                        progress_bar.progress(1.0)
                        download_status.update(
                            label=f"{new_model.strip()} is ready.",
                            state="complete",
                            expanded=False,
                        )
                    st.session_state.pull_notice = f"{new_model.strip()} is ready."
                    st.session_state.pending_model = new_model.strip()
                    get_server_info.clear()
                    st.rerun()
                except OllamaError as error:
                    st.error(str(error))

    st.divider()
    st.subheader("Note taker style")
    profile = st.selectbox(
        "Main job",
        options=list(PROFILE_PROMPTS),
        index=0,
    )
    st.caption("Very simple English is always on.")
    answer_length = st.select_slider(
        "Answer length", options=list(ANSWER_LENGTHS), value="Medium"
    )
    temperature = st.slider(
        "Creativity", min_value=0.0, max_value=1.0, value=0.2, step=0.1
    )
    history_turns = st.slider(
        "Past chat turns to remember", min_value=1, max_value=20, value=8
    )
    with st.expander("Advanced"):
        num_ctx = st.select_slider(
            "Context size",
            options=[2048, 4096, 8192, 16384, 32768],
            value=8192,
            help="More context uses more memory.",
        )
        st.text_area(
            "Extra rules",
            key="extra_rules",
            placeholder="Example: Always answer in a table.",
            max_chars=2_000,
        )
        if APP_CONFIG.cloud_mode:
            st.button(
                "Clear session rules",
                on_click=clear_rules,
                use_container_width=True,
            )
            st.caption("Rules last only for this signed-in session.")
        else:
            save_column, clear_column = st.columns(2)
            save_column.button(
                "Save rules",
                on_click=save_rules,
                use_container_width=True,
            )
            clear_column.button(
                "Clear rules",
                on_click=clear_rules,
                use_container_width=True,
            )
            st.caption("Saved rules stay on this computer.")
        if st.session_state.rules_notice:
            st.success(st.session_state.rules_notice)
            st.session_state.rules_notice = None
        if st.session_state.settings_error:
            st.error(st.session_state.settings_error)

    st.divider()
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    if st.session_state.messages:
        st.download_button(
            "Save chat as Markdown",
            data=export_chat(st.session_state.messages),
            file_name=f"local-note-taker-chat-{datetime.now().astimezone():%Y-%m-%d}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    if APP_CONFIG.cloud_mode:
        st.button("Sign out", on_click=logout, use_container_width=True)
        privacy_note = (
            "Chat and uploads stay in this signed-in session. "
            "Requests go to the private model service set by the app owner."
        )
    else:
        privacy_note = (
            "Chat stays in this browser session. Ollama runs the model on "
            "the machine at the address above."
        )
    st.markdown(
        f'<p class="small-note">{privacy_note}</p>',
        unsafe_allow_html=True,
    )

st.title("🧸 My Local Note Taker")
st.caption("A private note taker that uses simple words.")

if st.session_state.pull_notice:
    st.success(st.session_state.pull_notice)
    st.session_state.pull_notice = None

if not server["connected"]:
    st.warning(
        "Start Ollama, then press **Check Ollama**. The normal command is `ollama serve`."
    )
elif not selected_model:
    if APP_CONFIG.cloud_mode:
        st.info("No model is ready. Please tell the app owner.")
    else:
        st.info(
            "Install a model in the left panel. A small model is a good first test."
        )

if not st.session_state.messages:
    st.info(
        "Ask for help with a task. You can add text, PDF, Word, spreadsheet, "
        "code, or image files. Images need a vision model."
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message.get("content", ""))
        show_attachments(message)
        if message.get("error"):
            st.error(message["error"])

submission = st.chat_input(
    "Ask me something, or add files…",
    accept_file="multiple",
    file_type=STREAMLIT_FILE_TYPES,
    max_upload_size=15,
    disabled=not server["connected"] or not selected_model,
)

if submission:
    user_text = submission.text.strip()
    uploaded_files = list(submission.files)
    if not user_text and not uploaded_files:
        st.stop()

    if APP_CONFIG.cloud_mode:
        retry_after = take_request_slot(APP_CONFIG.requests_per_minute)
        if retry_after is not None:
            st.error(f"Too many requests. Please wait {retry_after} seconds.")
            st.stop()

    try:
        prepared = prepare_uploads(uploaded_files)
        if prepared.images:
            capabilities = make_ollama_client(base_url).model_capabilities(
                selected_model
            )
            if capabilities and "vision" not in capabilities:
                raise FilePreparationError(
                    f"{selected_model} cannot read images. Pick a model with vision."
                )
    except (FilePreparationError, OllamaError) as error:
        st.error(str(error))
        st.stop()

    visible_text = user_text or "Please look at my file and help me."
    user_message = {
        "role": "user",
        "content": visible_text,
        "model_content": make_model_content(user_text, prepared.context),
        "attachments": prepared.attachments,
        "images": prepared.images,
    }
    st.session_state.messages.append(user_message)

    with st.chat_message("user"):
        st.markdown(visible_text)
        show_attachments(user_message)
        for warning in prepared.warnings:
            st.warning(warning)

    system_prompt = build_system_prompt(profile, st.session_state.extra_rules)
    ollama_messages = history_for_ollama(
        st.session_state.messages, system_prompt, history_turns
    )

    with st.chat_message("assistant"):
        response_box = st.empty()
        full_response = ""
        try:
            client = make_ollama_client(base_url)
            for piece in client.stream_chat(
                model=selected_model,
                messages=ollama_messages,
                temperature=temperature,
                num_ctx=num_ctx,
                num_predict=ANSWER_LENGTHS[answer_length],
            ):
                full_response += piece
                response_box.markdown(full_response + "▌")
            if not full_response.strip():
                raise OllamaError("The model gave an empty answer. Please try again.")
            response_box.markdown(full_response)
        except OllamaError as error:
            response_box.empty()
            st.error(str(error))
            st.session_state.messages.append(
                {"role": "assistant", "content": "", "error": str(error)}
            )
            st.stop()

    st.session_state.messages.append(
        {"role": "assistant", "content": full_response, "model": selected_model}
    )
    st.rerun()
