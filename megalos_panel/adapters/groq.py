"""Groq adapter for the panel utility.

Groq serves an OpenAI-compatible endpoint at ``https://api.groq.com/openai/v1``,
so the existing ``openai`` SDK (already declared in the [panel] extra) is reused
here — no new pip dependency. The registry key is ``"groq/"``; this adapter
strips that prefix from the request's ``model`` before calling the API, so a
caller passing ``model="groq/openai/gpt-oss-120b"`` yields a Groq API call with
``model="openai/gpt-oss-120b"``.

This module imports the ``openai`` SDK at top-level — it is declared as a
[panel] optional extra. The package-level ``megalos_panel.adapters.__init__``
avoids importing this module unless an adapter is actually dispatched.
"""

import os

import openai

from megalos_panel.errors import RateLimitError, TransientError
from megalos_panel.types import PanelRequest

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_GROQ_PREFIX = "groq/"


class GroqAdapter:
    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        api_key: str | None = None,
    ) -> None:
        resolved = api_key if api_key is not None else os.environ.get("GROQ_API_KEY")
        if not resolved:
            raise ValueError(
                "GroqAdapter requires an API key: pass api_key=... or set "
                "the GROQ_API_KEY environment variable"
            )
        self.model = model
        self._client = openai.OpenAI(api_key=resolved, base_url=_GROQ_BASE_URL)

    def invoke(self, request: PanelRequest) -> str:
        model = request.model
        if model.startswith(_GROQ_PREFIX):
            model = model[len(_GROQ_PREFIX) :]
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": request.prompt}],
            )
        except openai.RateLimitError as exc:
            raise RateLimitError(str(exc)) from exc
        except openai.APITimeoutError as exc:
            raise TransientError(str(exc)) from exc
        except openai.APIConnectionError as exc:
            raise TransientError(str(exc)) from exc
        except openai.APIStatusError as exc:
            if 500 <= getattr(exc, "status_code", 0) < 600:
                raise TransientError(str(exc)) from exc
            raise

        choice = response.choices[0]
        content = choice.message.content
        return content if content is not None else ""
