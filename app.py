"""Streamlit interface for a local, simple-English Ollama assistant."""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import streamlit as st

from assistant.files import (
    STREAMLIT_FILE_TYPES,
    FilePreparationError,
    make_model_content,
    prepare_uploads,
)
from assistant.ollama_client import OllamaClient, OllamaError
from assistant.prompts import PROFILE_PROMPTS, build_system_prompt
from assistant.settings import SettingsError, load_extra_rules, save_extra_rules

OLLAMA_URL = "http://127.0.0.1:11434"
DOWNLOAD_URL = "https://github.com/damilp36/personal_ai_assistant/releases/latest"
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


def is_streamlit_cloud_url(url: str) -> bool:
    """Return whether the page is running on Streamlit Community Cloud."""

    hostname = urlparse(url).hostname or ""
    return hostname == "streamlit.app" or hostname.endswith(".streamlit.app")


def init_state() -> None:
    saved_rules = ""
    settings_error = None
    if "extra_rules" not in st.session_state:
        try:
            saved_rules = load_extra_rules()
        except SettingsError as error:
            settings_error = str(error)

    defaults = {
        "messages": [],
        "selected_model": None,
        "pending_model": None,
        "pull_notice": None,
        "extra_rules": saved_rules,
        "rules_notice": None,
        "settings_error": settings_error,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def save_rules() -> None:
    """Save the rules currently held by the text-area widget."""

    try:
        save_extra_rules(st.session_state.extra_rules)
        st.session_state.rules_notice = "Your rules were saved."
        st.session_state.settings_error = None
    except SettingsError as error:
        st.session_state.settings_error = str(error)


def clear_rules() -> None:
    """Clear the widget and its saved local value."""

    try:
        save_extra_rules("")
        st.session_state.extra_rules = ""
        st.session_state.rules_notice = "Your saved rules were cleared."
        st.session_state.settings_error = None
    except SettingsError as error:
        st.session_state.settings_error = str(error)


@st.cache_data(ttl=4, show_spinner=False)
def get_server_info() -> dict[str, Any]:
    client = OllamaClient(OLLAMA_URL)
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


init_state()

if is_streamlit_cloud_url(str(st.context.url)):
    st.title("🧸 My Local Note Taker")
    st.error("This application must run on your own computer.")
    st.write(
        "Download the local application. It uses Ollama and models installed on "
        "your computer. No hosted model service is used."
    )
    st.link_button("Download the local application", DOWNLOAD_URL)
    st.stop()

with st.sidebar:
    st.title("Settings")
    st.caption("Ollama runs only on this computer.")
    refresh = st.button("↻ Check Ollama", use_container_width=True)
    if refresh:
        get_server_info.clear()

    server = get_server_info()
    if server["connected"]:
        st.success(f"Ollama is ready · v{server['version']}")
    else:
        st.error("Ollama is not ready")
        st.caption(server["error"])
        st.link_button(
            "Install Ollama",
            "https://ollama.com/download",
            use_container_width=True,
        )

    models = server["models"]
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
        st.info("No model is installed yet.")

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
            client = OllamaClient(OLLAMA_URL)
            try:
                with st.status("Starting download…", expanded=True) as download_status:
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
    st.markdown(
        '<p class="small-note">Chat, files, rules, and model requests stay on '
        "this computer.</p>",
        unsafe_allow_html=True,
    )

st.title("🧸 My Local Note Taker")
st.caption("A private note taker that uses simple words.")

if st.session_state.pull_notice:
    st.success(st.session_state.pull_notice)
    st.session_state.pull_notice = None

if not server["connected"]:
    st.warning("Install or start Ollama, then press **Check Ollama**.")
elif not selected_model:
    st.info("Install a model in the left panel. A small model is a good first test.")

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

    try:
        prepared = prepare_uploads(uploaded_files)
        if prepared.images:
            capabilities = OllamaClient(OLLAMA_URL).model_capabilities(selected_model)
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
            client = OllamaClient(OLLAMA_URL)
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
