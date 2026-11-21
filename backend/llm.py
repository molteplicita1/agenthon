"""One function: prompt + pydantic schema -> parsed object (Gemini structured output)."""
import os

from pydantic import BaseModel

_client = None


class LLMError(Exception):
    pass


def _get_client():
    global _client
    if _client is None:
        from google import genai
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise LLMError("GEMINI_API_KEY is not set")
        vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
        _client = genai.Client(vertexai=vertex, api_key=key,
                               http_options={"timeout": 25_000})  # ms; a stuck call must not hang the demo
    return _client


def ask_json(prompt: str, schema: type[BaseModel]) -> BaseModel:
    if os.environ.get("BRAIN_NO_LLM") == "1":
        raise LLMError("model disabled (BRAIN_NO_LLM=1)")
    model = os.environ.get("GEMINI_MODEL") or "gemini-3.8-flash"
    last = None
    for _ in range(2):  # one retry
        try:
            r = _get_client().models.generate_content(
                model=model, contents=prompt,
                config={"response_mime_type": "application/json", "response_schema": schema,
                        "temperature": 0,
                        # default thinking can run until the server deadline (504); low takes ~4 s
                        "thinking_config": {"thinking_level": os.environ.get("GEMINI_THINKING", "low")}},
            )
            return r.parsed if isinstance(r.parsed, schema) else schema.model_validate_json(r.text)
        except Exception as e:  # noqa: BLE001 - any failure is "external service failed"
            last = e
    raise LLMError(f"model call failed: {type(last).__name__}")
