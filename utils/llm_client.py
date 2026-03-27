"""
LLM Client abstraction for AI Waifu Vtuber.

Supports multiple LLM providers (OpenAI, MiniMax) via the OpenAI-compatible SDK.
MiniMax models (MiniMax-M2.7, MiniMax-M2.7-highspeed) are accessible through
their OpenAI-compatible endpoint at https://api.minimax.io/v1.
"""

import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# Provider presets: base_url and default model for each provider
PROVIDER_PRESETS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-3.5-turbo",
        "env_key": "OPENAI_API_KEY",
    },
    "minimax": {
        "base_url": "https://api.minimax.io/v1",
        "default_model": "MiniMax-M2.7",
        "env_key": "MINIMAX_API_KEY",
    },
}

# Models available for each provider
PROVIDER_MODELS = {
    "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini"],
    "minimax": ["MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5", "MiniMax-M2.5-highspeed"],
}


def _clamp_temperature(provider, temperature):
    """Clamp temperature to valid range for the provider."""
    if provider == "minimax" and temperature is not None:
        # MiniMax requires temperature in (0.0, 1.0]
        return max(0.01, min(1.0, temperature))
    return temperature


def _strip_think_tags(text):
    """Strip <think>...</think> tags from model output (MiniMax reasoning artifacts)."""
    import re
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


class LLMClient:
    """
    Unified LLM client that supports OpenAI and MiniMax providers.

    Usage:
        from utils.llm_client import LLMClient

        # Auto-detect provider from config or env
        client = LLMClient(provider="minimax", api_key="your-key")
        reply = client.chat(messages, max_tokens=128, temperature=1.0)
    """

    def __init__(self, provider=None, api_key=None, model=None, base_url=None):
        """
        Initialize the LLM client.

        Args:
            provider: "openai" or "minimax". Auto-detected from env if not set.
            api_key: API key. Read from env if not provided.
            model: Model name. Uses provider default if not set.
            base_url: Custom base URL. Uses provider preset if not set.
        """
        if OpenAI is None:
            raise ImportError(
                "openai package is required. Install with: pip install openai>=1.0"
            )

        self.provider = self._resolve_provider(provider, api_key)
        preset = PROVIDER_PRESETS[self.provider]

        self.api_key = api_key or os.environ.get(preset["env_key"], "")
        self.model = model or preset["default_model"]
        self.base_url = base_url or preset["base_url"]

        if not self.api_key:
            raise ValueError(
                f"API key required for {self.provider}. "
                f"Set {preset['env_key']} env var or pass api_key parameter."
            )

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @staticmethod
    def _resolve_provider(provider, api_key):
        """Auto-detect provider from env vars if not explicitly set."""
        if provider:
            provider = provider.lower()
            if provider not in PROVIDER_PRESETS:
                raise ValueError(
                    f"Unknown provider '{provider}'. "
                    f"Supported: {list(PROVIDER_PRESETS.keys())}"
                )
            return provider

        # Auto-detect: check MINIMAX_API_KEY first, then fall back to OpenAI
        if api_key or os.environ.get("MINIMAX_API_KEY"):
            if os.environ.get("MINIMAX_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
                return "minimax"
        return "openai"

    def chat(self, messages, max_tokens=128, temperature=1.0, top_p=0.9, **kwargs):
        """
        Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
            top_p: Top-p sampling parameter.
            **kwargs: Additional parameters passed to the API.

        Returns:
            str: The assistant's response text.
        """
        temperature = _clamp_temperature(self.provider, temperature)

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            **kwargs,
        )

        text = response.choices[0].message.content or ""

        # Strip thinking tags for MiniMax models
        if self.provider == "minimax":
            text = _strip_think_tags(text)

        return text

    def list_models(self):
        """Return the list of known models for the current provider."""
        return PROVIDER_MODELS.get(self.provider, [])

    def __repr__(self):
        return f"LLMClient(provider={self.provider!r}, model={self.model!r})"
