"""LM Studio local server (OpenAI-compatible API). All chat completions use this backend only."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def _user_config():
    try:
        import config as user_config  # noqa: F401 — optional local overrides (gitignored)
        return user_config
    except ImportError:
        return None


def _pick(module, attr: str, env_key: str, default: str) -> str:
    if module is not None and hasattr(module, attr):
        return str(getattr(module, attr))
    v = os.environ.get(env_key)
    return str(v) if v not in (None, "") else default


def normalize_api_base(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if not u.endswith("/v1"):
        u = f"{u}/v1"
    return u


def load_lm_settings():
    """Resolve URL, API key, and model id (env > config.py > defaults)."""
    mod = _user_config()
    base = normalize_api_base(_pick(mod, "LM_STUDIO_BASE_URL", "LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1"))
    key = _pick(mod, "LM_STUDIO_API_KEY", "LM_STUDIO_API_KEY", "lm-studio")
    model = _pick(mod, "LM_STUDIO_MODEL", "LM_STUDIO_MODEL", "local-model")
    return base, key, model


def pick_owner_name() -> str:
    mod = _user_config()
    return _pick(mod, "owner_name", "VTUBER_OWNER_NAME", "Ardha")


def assert_lm_studio_reachable(base_url: str, api_key: str) -> None:
    """Fail fast if the LM Studio local server is not running."""
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        print(
            "Could not reach LM Studio at",
            base_url,
            f"(HTTP {e.code}).\n"
            "Open LM Studio, load a model, enable the local server (default port 1234), then retry.\n",
        )
        sys.exit(1)
    except Exception as e:
        print(
            "Could not reach LM Studio at",
            base_url,
            "\nStart LM Studio, load a model, and turn on the local API server.\n"
            "Tip: set LM_STUDIO_BASE_URL if you use a non-default host/port.\n"
            "Error:",
            e,
        )
        sys.exit(1)


def apply_openai_module(openai_module, base_url: str, api_key: str) -> None:
    """Point the legacy openai package at LM Studio only (never api.openai.com)."""
    openai_module.api_base = base_url
    openai_module.api_key = api_key
