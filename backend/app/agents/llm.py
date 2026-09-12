"""LLM access for the agents: one factory, one structured-output call.

Two ideas live here.

1. **Provider choice is configuration, not code.** All three agents call
   `structured_call()`; swapping Groq for OpenAI is an `.env` edit.

2. **Structured output or nothing.** Spec section 5 says not to rely on
   free-form text where structured data is required, so every call is bound to
   a Pydantic model. The preferred path is the provider's own structured-output
   mode; if the provider or model does not support it we fall back to asking
   for JSON and validating it ourselves. Either way the caller gets a
   validated model instance or an exception — never a string to regex.
"""
import json
import logging
import re
from functools import lru_cache
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError as PydanticValidationError

from app.core.config import get_settings
from app.core.exceptions import AIError

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)

# Providers that need a key before they can be used at all.
_KEY_FIELD = {"groq": "groq_api_key", "openai": "openai_api_key", "gemini": "google_api_key"}


def llm_available() -> bool:
    """True when a real model can be reached.

    When this is False the agents use their deterministic rule-based path, so
    the whole application still works end to end with no API key configured.
    """
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider == "fallback":
        return False
    if provider == "ollama":
        return True  # local server; reachability is discovered on first call
    field = _KEY_FIELD.get(provider)
    return bool(field and getattr(settings, field, ""))


def model_label() -> str:
    settings = get_settings()
    if not llm_available():
        return "rule-based-fallback"
    return f"{settings.llm_provider}:{settings.llm_model}"


@lru_cache
def get_llm():
    """Build the chat model once and reuse it (clients hold connection pools)."""
    settings = get_settings()
    provider = settings.llm_provider.lower()
    common = {
        "temperature": settings.llm_temperature,
        "timeout": settings.llm_timeout_seconds,
    }

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.llm_model,
            api_key=settings.groq_api_key,
            max_tokens=settings.llm_max_tokens,
            **common,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            max_tokens=settings.llm_max_tokens,
            **common,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            max_output_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            temperature=settings.llm_temperature,
        )

    raise AIError(f"Unknown llm_provider '{settings.llm_provider}'")


def structured_call(
    system_prompt: str, user_prompt: str, schema: Type[TModel], attempts: int = 2
) -> TModel:
    """Ask the model to fill `schema`. Raises `AIError` if it never does."""
    llm = get_llm()
    last_error: Optional[Exception] = None

    for attempt in range(1, attempts + 1):
        try:
            return _native_structured(llm, system_prompt, user_prompt, schema)
        except Exception as exc:  # provider/model may not support the mode
            last_error = exc
            logger.debug("Native structured output failed (attempt %s): %s", attempt, exc)
            try:
                return _json_mode(llm, system_prompt, user_prompt, schema)
            except Exception as json_exc:
                last_error = json_exc
                logger.warning("JSON fallback failed (attempt %s): %s", attempt, json_exc)

    raise AIError(f"The model did not return valid {schema.__name__}: {last_error}")


def _native_structured(llm, system_prompt: str, user_prompt: str, schema: Type[TModel]) -> TModel:
    result = llm.with_structured_output(schema).invoke(
        [("system", system_prompt), ("human", user_prompt)]
    )
    if isinstance(result, schema):
        return result
    if isinstance(result, dict):
        return schema.model_validate(result)
    raise AIError("Structured output returned an unexpected type")


def _json_mode(llm, system_prompt: str, user_prompt: str, schema: Type[TModel]) -> TModel:
    """Plain-text call plus manual JSON extraction, for models without tool use."""
    instruction = (
        f"{system_prompt}\n\n"
        "Reply with a single JSON object and nothing else — no prose, no markdown fence.\n"
        f"It must match this JSON Schema:\n{json.dumps(schema.model_json_schema())}"
    )
    response = llm.invoke([("system", instruction), ("human", user_prompt)])
    content = getattr(response, "content", response)
    if isinstance(content, list):  # some providers return content blocks
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    payload = _extract_json(str(content))
    try:
        return schema.model_validate(payload)
    except PydanticValidationError as exc:
        raise AIError(f"Model JSON did not match {schema.__name__}: {exc}") from exc


def _extract_json(text: str) -> dict:
    """Pull the JSON object out of a reply that may be wrapped in a fence."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Last resort: the outermost {...} in the reply.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise AIError("No JSON object found in the model reply")
