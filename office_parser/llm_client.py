"""LLM Provider 추상화 — Gemini / OpenRouter / Central LLM 통합 클라이언트.

환경변수:
    LLM_PROVIDER: "gemini" (기본), "openrouter", "central"
    GOOGLE_API_KEY: Gemini API 키
    OPENROUTER_API_KEY: OpenRouter API 키
    CENTRAL_LLM_API_KEY: Central LLM (LiteLLM Proxy) API 키
    CENTRAL_LLM_BASE_URL: Central LLM Proxy 서버 주소
"""

from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger("office_parser.llm_client")

# ── 클라이언트 캐시 ──
_client_cache: dict[str, object] = {}

# ── Rate limit 설정 ──
MAX_RETRIES = 5
RETRY_DELAY = 20  # 초


def _get_gemini(api_key: str | None = None):
    """Gemini 클라이언트 (싱글턴)."""
    key = api_key or os.getenv("GOOGLE_API_KEY")
    cache_key = f"gemini:{key[:8]}" if key else "gemini:default"
    if cache_key not in _client_cache:
        from google import genai
        _client_cache[cache_key] = genai.Client(api_key=key)
    return _client_cache[cache_key]


def _get_openrouter():
    """OpenRouter 클라이언트 (OpenAI SDK 호환)."""
    if "openrouter" not in _client_cache:
        from openai import OpenAI
        _client_cache["openrouter"] = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://doc-parser.local",
                "X-Title": "doc-parser",
            },
        )
    return _client_cache["openrouter"]


def _get_central():
    """Central LLM 클라이언트 (LiteLLM Proxy, OpenAI SDK 호환)."""
    if "central" not in _client_cache:
        from openai import OpenAI
        _client_cache["central"] = OpenAI(
            api_key=os.getenv("CENTRAL_LLM_API_KEY"),
            base_url=os.getenv("CENTRAL_LLM_BASE_URL"),
        )
    return _client_cache["central"]


# ── Gemini 텍스트 호출 ──

def _call_gemini_text(model_id: str, system: str, user: str) -> tuple[str, dict]:
    """Gemini API 호출. 기존 reconstructor의 _call_gemini와 동일한 반환값.

    Returns:
        (text, usage_dict) — 응답 텍스트와 토큰 사용량
    """
    client = _get_gemini()
    response = client.models.generate_content(
        model=model_id,
        contents=user,
        config={"system_instruction": system},
    )
    usage = {"input_tokens": 0, "output_tokens": 0}
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        um = response.usage_metadata
        usage["input_tokens"] = getattr(um, "prompt_token_count", 0) or 0
        usage["output_tokens"] = getattr(um, "candidates_token_count", 0) or 0
    return response.text, usage


# ── OpenRouter 텍스트 호출 ──

def _call_openrouter_text(model_id: str, system: str, user: str) -> tuple[str, dict]:
    """OpenRouter API 호출 (OpenAI SDK 호환).

    Returns:
        (text, usage_dict) — 응답 텍스트와 토큰 사용량
    """
    client = _get_openrouter()
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    usage = {"input_tokens": 0, "output_tokens": 0}
    if response.usage:
        usage["input_tokens"] = response.usage.prompt_tokens or 0
        usage["output_tokens"] = response.usage.completion_tokens or 0
    text = response.choices[0].message.content if response.choices else ""
    return text, usage


# ── Central LLM 텍스트 호출 ──

def _call_central_text(model_id: str, system: str, user: str) -> tuple[str, dict]:
    """Central LLM (LiteLLM Proxy) API 호출 (OpenAI SDK 호환).

    Returns:
        (text, usage_dict) — 응답 텍스트와 토큰 사용량
    """
    client = _get_central()
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
    )
    usage = {"input_tokens": 0, "output_tokens": 0}
    if response.usage:
        usage["input_tokens"] = response.usage.prompt_tokens or 0
        usage["output_tokens"] = response.usage.completion_tokens or 0
    text = response.choices[0].message.content if response.choices else ""
    return text, usage


# ── 통합 호출 (재시도 포함) ──

def call_llm_text(
    model_id: str,
    system: str,
    user: str,
    provider: str = "gemini",
) -> tuple[str, dict]:
    """텍스트 전용 LLM 호출 (재시도 로직 포함).

    Args:
        model_id: 모델 ID (예: "gemini-2.5-flash", "qwen/qwen3.5-plus-02-15")
        system: 시스템 프롬프트
        user: 유저 프롬프트
        provider: "gemini" 또는 "openrouter"

    Returns:
        (text, usage_dict) — 응답 텍스트와 토큰 사용량
    """
    # provider별 호출 함수 매핑
    _provider_fns = {
        "gemini": _call_gemini_text,
        "openrouter": _call_openrouter_text,
        "central": _call_central_text,
    }
    call_fn = _provider_fns.get(provider)
    if call_fn is None:
        raise ValueError(f"지원하지 않는 LLM provider: {provider!r} (가능: {list(_provider_fns.keys())})")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return call_fn(model_id, system, user)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt < MAX_RETRIES:
                wait = RETRY_DELAY * attempt
                logger.warning("⏳ Rate limited (%s), retry %d/%d in %ds...",
                               model_id, attempt, MAX_RETRIES, wait)
                time.sleep(wait)
            else:
                raise
