"""LLM Provider 추상화 — Gemini / OpenRouter 통합 클라이언트.

환경변수:
    LLM_PROVIDER: "gemini" (기본) 또는 "openrouter"
    GOOGLE_API_KEY: Gemini API 키
    OPENROUTER_API_KEY: OpenRouter API 키
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Optional

logger = logging.getLogger("office_parser.llm_client")

# ── 클라이언트 캐시 ──
_client_cache: dict[str, object] = {}


def _get_provider(config) -> str:
    """config 또는 환경변수에서 provider 결정."""
    return getattr(config, "llm_provider", None) or os.getenv("LLM_PROVIDER", "gemini")


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


# ── 텍스트 전용 호출 (reconstruct, summarize_text 등) ──

def call_llm_text(
    model_id: str,
    system: str,
    user: str,
    provider: str = "gemini",
) -> str:
    """텍스트 전용 LLM 호출. 이미지 없이 system + user prompt.

    Args:
        model_id: 모델 ID (예: "gemini-2.5-flash", "qwen/qwen3-32b")
        system: 시스템 프롬프트
        user: 유저 프롬프트
        provider: "gemini" 또는 "openrouter"

    Returns:
        LLM 응답 텍스트
    """
    if provider == "openrouter":
        return _call_openrouter_text(model_id, system, user)
    else:
        return _call_gemini_text(model_id, system, user)


def _call_gemini_text(model_id: str, system: str, user: str) -> str:
    client = _get_gemini()
    response = client.models.generate_content(
        model=model_id,
        contents=user,
        config={"system_instruction": system},
    )
    return response.text


def _call_openrouter_text(model_id: str, system: str, user: str) -> str:
    client = _get_openrouter()
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        extra_body={"provider": {"allow_fallbacks": True, "data_collection": "allow", "require_parameters": False}},
    )
    return response.choices[0].message.content


# ── 이미지 포함 호출 (image/slide/table 요약) ──

def call_llm_vision(
    model_id: str,
    prompt: str,
    image_data: bytes,
    mime_type: str = "image/png",
    provider: str = "gemini",
) -> str:
    """이미지 + 텍스트 멀티모달 LLM 호출.

    Args:
        model_id: 모델 ID
        prompt: 텍스트 프롬프트
        image_data: 이미지 바이트
        mime_type: 이미지 MIME 타입
        provider: "gemini" 또는 "openrouter"

    Returns:
        LLM 응답 텍스트
    """
    if provider == "openrouter":
        return _call_openrouter_vision(model_id, prompt, image_data, mime_type)
    else:
        return _call_gemini_vision(model_id, prompt, image_data, mime_type)


def _call_gemini_vision(
    model_id: str, prompt: str, image_data: bytes, mime_type: str,
) -> str:
    from google import genai
    client = _get_gemini()
    response = client.models.generate_content(
        model=model_id,
        contents=[
            genai.types.Part.from_bytes(data=image_data, mime_type=mime_type),
            prompt,
        ],
    )
    return response.text


def _call_openrouter_vision(
    model_id: str, prompt: str, image_data: bytes, mime_type: str,
) -> str:
    client = _get_openrouter()
    b64 = base64.b64encode(image_data).decode("utf-8")
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        extra_body={"provider": {"data_collection": "allow"}},
    )
    return response.choices[0].message.content


# ── 텍스트 전용 (시스템 프롬프트 없이) ──

def call_llm_simple(
    model_id: str,
    prompt: str,
    provider: str = "gemini",
) -> str:
    """시스템 프롬프트 없이 단순 텍스트 호출."""
    if provider == "openrouter":
        client = _get_openrouter()
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            extra_body={"provider": {"data_collection": "allow"}},
        )
        return response.choices[0].message.content
    else:
        client = _get_gemini()
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
        )
        return response.text
