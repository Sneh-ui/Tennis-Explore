"""
Common Ollama helper — supports both local and cloud deployments.

Local:  http://localhost:11434/api/generate  -> {prompt, options} -> {response}
Cloud:  https://ollama.com/api/chat        -> {messages, Bearer} -> {message.content}

Usage:
    from backend.shared.ollama_client import call_ollama

    answer = call_ollama(prompt, url=OLLAMA_URL, model=OLLAMA_MODEL, json_mode=True)

Env-driven defaults:
    OLLAMA_URL, OLLAMA_MODEL (or OLLAMA_MODEL_NAME), OLLAMA_API_KEY, OLLAMA_TIMEOUT
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Ensure backend/.env is loaded regardless of import order
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _is_chat_url(url: str) -> bool:
    return "/api/chat" in url or "ollama.com" in url


def _is_generate_url(url: str) -> bool:
    return "/api/generate" in url


def get_ollama_info(
    url: str | None = None,
    model: str | None = None,
) -> dict:
    """Return sanitized Ollama config for UI display (never exposes API key)."""
    url = url or os.getenv("OLLAMA_URL", "https://ollama.com/api/chat")
    model = model or os.getenv("OLLAMA_MODEL") or os.getenv("OLLAMA_MODEL_NAME", "mistral")
    is_cloud = "ollama.com" in url or "/api/chat" in url
    # Structured defaults to gemma4:31b cloud, unstructured to mistral local — expose both if needed
    return {
        "model": model,
        "url": url,
        "mode": "cloud" if is_cloud else "local",
        "is_cloud": is_cloud,
    }


def call_ollama(
    prompt: str,
    *,
    url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    timeout: int | None = None,
    json_mode: bool = False,
    temperature: float = 0.0,
) -> str:
    """
    Call Ollama and return the text answer.

    Handles both APIs transparently:
      - Cloud chat:   POST url {model, messages, stream, format} + Bearer -> message.content
      - Local generate: POST url {model, prompt, stream, options, format} -> response

    Raises RuntimeError on empty response; lets requests exceptions propagate.
    """
    # Resolve env with caller-provided overrides
    url = url or os.getenv("OLLAMA_URL", "https://ollama.com/api/chat")
    # Support both OLLAMA_MODEL and legacy OLLAMA_MODEL_NAME
    model = model or os.getenv("OLLAMA_MODEL") or os.getenv("OLLAMA_MODEL_NAME", "mistral")
    if api_key is None:
        api_key = os.getenv("OLLAMA_API_KEY")
    if timeout is None:
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    is_chat = _is_chat_url(url)
    is_generate = _is_generate_url(url)

    # Cloud chat requires API key on ollama.com; local does not
    if is_chat and "ollama.com" in url and not api_key:
        raise RuntimeError("OLLAMA_API_KEY is missing from the server environment.")

    headers = {"Content-Type": "application/json"}
    if api_key and is_chat:
        headers["Authorization"] = f"Bearer {api_key}"

    if is_chat:
        payload: dict = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"
        # Temperature via options is supported by both APIs; include for consistency
        if temperature != 0.0:
            payload["options"] = {"temperature": temperature}
    elif is_generate:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"
    else:
        # Unknown URL shape — default to chat (preserves original structured behaviour)
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    # Cloud: message.content ; Local: response ; support both for resilience
    answer = (data.get("message", {}).get("content") if isinstance(data.get("message"), dict) else None) or data.get("response") or ""
    answer = answer.strip()
    if not answer:
        raise RuntimeError("Ollama returned an empty response.")
    return answer
