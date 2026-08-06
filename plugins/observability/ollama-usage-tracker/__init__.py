"""Ollama usage tracker plugin — logs every API call to the shared usage file.

Hooks post_api_request to capture token counts from every Ollama Cloud call
made by Hermes itself, so the cost tracker reflects real spend.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

USAGE_FILE = "/root/agentwallet/data/ollama_usage.json"


def _append_usage(model: str, prompt_tokens: int, completion_tokens: int,
                  total_duration_ns: int = 0, done_reason: str = "stop") -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_duration_ns": total_duration_ns,
        "done_reason": done_reason,
    }
    try:
        data: list[dict[str, Any]] = []
        if os.path.exists(USAGE_FILE):
            try:
                with open(USAGE_FILE) as f:
                    data = json.load(f)
            except Exception:
                data = []
        data.append(entry)
        with open(USAGE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning("Failed to log Ollama usage: %s", e)


def on_post_api_request(
    *,
    provider: str = "",
    model: str = "",
    usage: Any = None,
    api_duration: float = 0.0,
    finish_reason: str = "",
    **_: Any,
) -> None:
    """Hook: log every Ollama Cloud API call to the shared usage tracker."""
    if provider != "ollama-cloud":
        return
    if not model:
        return

    prompt_tokens = 0
    completion_tokens = 0

    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens", 0) or 0
        completion_tokens = usage.get("completion_tokens", 0) or 0
    elif usage is not None and hasattr(usage, "prompt_tokens"):
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0

    if prompt_tokens == 0 and completion_tokens == 0:
        return

    duration_ns = int(api_duration * 1_000_000_000) if api_duration else 0
    _append_usage(model, prompt_tokens, completion_tokens, duration_ns, finish_reason or "stop")


def register(ctx) -> None:
    ctx.register_hook("post_api_request", on_post_api_request)
