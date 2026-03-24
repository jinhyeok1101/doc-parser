"""Compact JSON → LLM 기반 Markdown/HTML 재구성 모듈.

Gemini, OpenRouter(Qwen, GLM 등), Central LLM 지원.
시트별 정형/비정형 분류 기능 포함.
"""
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from .llm_client import call_llm_text

logger = logging.getLogger("office_parser")

_PROMPTS_PATH = Path(__file__).parent / "prompts.yaml"
_prompts_cache = None


def _load_prompts() -> dict:
    global _prompts_cache
    if _prompts_cache is None:
        with open(_PROMPTS_PATH, "r", encoding="utf-8") as f:
            _prompts_cache = yaml.safe_load(f)
    return _prompts_cache


def classify_sheet(
    sheet_json: dict,
    model_id: str = "gemini-2.5-flash",
    provider: str = "gemini",
) -> dict:
    """시트를 pass(LLM 불필요) 또는 reconstruct(LLM 재구성 필요)로 분류.

    첫 10행만 전송하여 토큰 절약.

    Args:
        sheet_json: _sheet_to_compact() 결과 dict
        model_id: 모델 ID
        provider: "gemini", "openrouter", "central"

    Returns:
        {"classification": "pass"|"reconstruct", "reason": "..."}
    """
    prompts = _load_prompts()
    prompt = prompts["classify_sheet"]

    # 첫 10행만 추출하여 토큰 절약
    preview = dict(sheet_json)
    preview["rows"] = sheet_json.get("rows", [])[:10]

    sheet_name = preview.get("sheet_name", "Sheet")
    json_content = json.dumps(preview, ensure_ascii=False, indent=2)

    system = prompt["system"]
    user = prompt["user"].format(
        sheet_name=sheet_name,
        json_content=json_content,
    )

    try:
        result, usage = call_llm_text(model_id, system, user, provider=provider)
        # JSON 파싱 시도
        if result:
            # 코드 블록 래핑 제거
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```\w*\n?", "", cleaned)
                cleaned = re.sub(r"\n?```$", "", cleaned)
            parsed = json.loads(cleaned)
            logger.info("🏷️ Sheet '%s' classified as: %s (%s)",
                        sheet_name, parsed.get("classification"), parsed.get("reason"))
            return parsed
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("⚠️ Sheet '%s' classification failed: %s — defaulting to reconstruct", sheet_name, e)

    # 실패 시 reconstruct로 기본 처리 (안전)
    return {"classification": "reconstruct", "reason": "classification failed, defaulting to reconstruct"}


def classify_all_sheets(
    ast,
    model_id: str = "gemini-2.5-flash",
    provider: str = "gemini",
) -> dict:
    """AST의 모든 시트를 병렬로 정형/비정형 분류.

    Returns:
        {시트이름: {"classification": ..., "reason": ...}} 딕셔너리
    """
    sheet_jsons = []
    for node in ast.content:
        if node.type == "sheet":
            sheet_json = ast._sheet_to_compact(node)
            sheet_jsons.append(sheet_json)

    if not sheet_jsons:
        return {}

    logger.info("🏷️ Classifying %d sheets (provider=%s)...", len(sheet_jsons), provider)
    results = {}

    with ThreadPoolExecutor(max_workers=None) as executor:
        futures = {}
        for sj in sheet_jsons:
            name = sj.get("sheet_name", "Sheet")
            f = executor.submit(classify_sheet, sj, model_id, provider)
            futures[f] = name

        for f in as_completed(futures):
            name = futures[f]
            try:
                results[name] = f.result()
            except Exception as e:
                logger.error("❌ Classification failed for '%s': %s", name, e)
                results[name] = {"classification": "reconstruct", "reason": f"error: {e}"}

    pass_sheets = [n for n, r in results.items() if r["classification"] == "pass"]
    recon_sheets = [n for n, r in results.items() if r["classification"] == "reconstruct"]
    logger.info("📊 Classification result — pass: %d, reconstruct: %d",
                len(pass_sheets), len(recon_sheets))
    return results


def _extract_images_from_json(sheet_json: dict) -> tuple:
    """sheet JSON에서 이미지/차트 노드를 분리.

    Returns:
        (cleaned_json, images) — 이미지 제거된 JSON과 이미지 노드 리스트
    """
    images = []
    cleaned_rows = []
    for item in sheet_json.get("rows", []):
        if isinstance(item, dict) and item.get("type") in ("image", "chart"):
            images.append(item)
        else:
            cleaned_rows.append(item)

    cleaned = dict(sheet_json)
    cleaned["rows"] = cleaned_rows
    return cleaned, images


def _insert_images_md(text: str, images: list) -> str:
    """Gemini 재구성 결과에 이미지를 삽입.

    이미지는 문서 summary 뒤, 본문 시작 전에 배치.
    """
    if not images:
        return text

    img_lines = []
    for img in images:
        if img.get("type") == "chart":
            chart_type = img.get("chart_type", "Chart")
            title = img.get("title", "")
            img_lines.append(f"**[{chart_type}]** {title}\n")
        else:
            filename = img.get("filename", "")
            summary = img.get("summary", "")
            if not filename:
                continue
            alt = summary or "이미지"
            img_lines.append(f"![{alt}]({filename})\n")

    if not img_lines:
        return text

    img_block = "\n".join(img_lines)

    # summary 블록(첫 번째 문단) 뒤에 삽입 시도, 없으면 문서 앞에
    lines = text.split("\n")
    insert_idx = 0
    for i, line in enumerate(lines):
        # 첫 번째 빈 줄(summary 끝)을 찾으면 그 뒤에 삽입
        if i > 0 and line.strip() == "" and lines[i - 1].strip():
            insert_idx = i + 1
            break
    else:
        insert_idx = 0

    lines.insert(insert_idx, "\n" + img_block)
    return "\n".join(lines)


def reconstruct_sheet(
    sheet_json: dict,
    output_format: str,
    model_id: str = "gemini-2.5-flash",
    provider: str = "gemini",
) -> str:
    """단일 시트 JSON을 LLM으로 재구성.

    이미지/차트는 LLM에 보내지 않고, 후처리로 삽입.

    Args:
        sheet_json: _sheet_to_compact() 결과 dict
        output_format: "md" 또는 "html"
        model_id: 모델 ID (예: "gemini-2.5-flash", "qwen/qwen3.5-plus-02-15")
        provider: "gemini" 또는 "openrouter"

    Returns:
        재구성된 (text, usage) 튜플
    """
    # 이미지/차트 분리 → LLM은 테이블/텍스트 재구성에만 집중
    cleaned_json, images = _extract_images_from_json(sheet_json)

    prompts = _load_prompts()
    prompt_key = "reconstruct_md" if output_format == "md" else "reconstruct_html"
    prompt = prompts[prompt_key]

    sheet_name = cleaned_json.get("sheet_name", "Sheet")
    json_content = json.dumps(cleaned_json, ensure_ascii=False, indent=2)

    system = prompt["system"]
    user = prompt["user"].format(
        sheet_name=sheet_name,
        json_content=json_content,
    )

    result, usage = call_llm_text(model_id, system, user, provider=provider)

    if not result:
        return "", usage

    # 코드 블록 래핑 제거
    if result.startswith("```markdown"):
        result = result[len("```markdown"):].strip()
    if result.startswith("```html"):
        result = result[len("```html"):].strip()
    if result.startswith("```"):
        result = result[3:].strip()
    if result.endswith("```"):
        result = result[:-3].strip()

    # 이미지/차트 후처리 삽입
    if output_format == "md":
        result = _insert_images_md(result, images)

    return result, usage


def reconstruct_sheet_from_md(
    sheet_name: str,
    md_content: str,
    model_id: str = "gemini-2.5-flash",
    provider: str = "gemini",
) -> tuple:
    """단일 시트 Markdown을 LLM으로 재구성 (from_md 모드).

    Args:
        sheet_name: 시트 이름
        md_content: AST에서 생성된 시트별 Markdown 텍스트
        model_id: 모델 ID
        provider: "gemini", "openrouter", "central"

    Returns:
        (text, usage) 튜플
    """
    prompts = _load_prompts()
    prompt = prompts["reconstruct_md_from_md"]

    system = prompt["system"]
    user = prompt["user"].format(
        sheet_name=sheet_name,
        md_content=md_content,
    )

    result, usage = call_llm_text(model_id, system, user, provider=provider)

    if not result:
        return "", usage

    # 코드 블록 래핑 제거
    if result.startswith("```markdown"):
        result = result[len("```markdown"):].strip()
    if result.startswith("```"):
        result = result[3:].strip()
    if result.endswith("```"):
        result = result[:-3].strip()

    return result, usage


def reconstruct_all_sheets_from_md(
    ast,
    model_id: str = "gemini-2.5-flash",
    provider: str = "gemini",
) -> tuple:
    """AST의 모든 시트를 MD 입력으로 재구성하여 하나의 문서로 합침.

    Args:
        ast: OfficeParserAST 인스턴스
        model_id: 모델 ID
        provider: "gemini", "openrouter", "central"

    Returns:
        (전체 재구성 문서, total_usage) 튜플
    """
    # 시트별 Markdown 생성
    sheet_mds = []
    for node in ast.content:
        if node.type == "sheet":
            meta = node.metadata or {}
            name = meta.get("sheetName", "Sheet")
            md = ast._sheet_to_markdown(node)
            sheet_mds.append((name, md))

    if not sheet_mds:
        return "", {"input_tokens": 0, "output_tokens": 0}

    max_workers = 1 if provider == "openrouter" else None
    logger.info("🔄 Reconstructing %d sheets from MD (%s, workers=%s)...",
                len(sheet_mds), provider, max_workers or "auto")
    results = {}
    total_usage = {"input_tokens": 0, "output_tokens": 0}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, (name, md) in enumerate(sheet_mds):
            f = executor.submit(reconstruct_sheet_from_md, name, md, model_id, provider)
            futures[f] = (i, name)

        for f in as_completed(futures):
            idx, name = futures[f]
            try:
                text, usage = f.result()
                results[idx] = text
                total_usage["input_tokens"] += usage["input_tokens"]
                total_usage["output_tokens"] += usage["output_tokens"]
                logger.info("✅ [from_md] Reconstructed '%s' (in: %d, out: %d tokens)",
                            name, usage["input_tokens"], usage["output_tokens"])
            except Exception as e:
                logger.error("❌ [from_md] Reconstruct failed for '%s': %s", name, e)
                results[idx] = f"<!-- Reconstruct failed: {name} -->"

    logger.info("📊 [from_md] Total — input: %d, output: %d",
                total_usage["input_tokens"], total_usage["output_tokens"])

    ordered = [results[i] for i in sorted(results.keys())]
    return "\n\n---\n\n".join(ordered), total_usage


def reconstruct_all_sheets(
    ast,
    output_format: str,
    model_id: str = "gemini-2.5-flash",
    provider: str = "gemini",
    skip_sheets: set | None = None,
) -> str:
    """AST의 모든 시트를 병렬로 재구성하여 하나의 문서로 합침.

    Args:
        ast: OfficeParserAST 인스턴스
        output_format: "md" 또는 "html"
        model_id: 모델 ID
        provider: "gemini", "openrouter", "central"
        skip_sheets: 정형으로 분류되어 reconstruct를 skip할 시트 이름 set

    Returns:
        전체 재구성된 문서 문자열
    """
    skip_sheets = skip_sheets or set()

    # 시트별 compact JSON 생성
    sheet_jsons = []
    for node in ast.content:
        if node.type == "sheet":
            sheet_json = ast._sheet_to_compact(node)
            sheet_jsons.append(sheet_json)

    if not sheet_jsons:
        return ""

    # 병렬 재구성 (OpenRouter 무료 모델은 RPM 제한 → workers=1)
    max_workers = 1 if provider == "openrouter" else None
    logger.info("🔄 Reconstructing %d sheets (%s, %s, workers=%s)...",
                len(sheet_jsons), output_format, provider, max_workers or "auto")
    results = {}
    total_usage = {"input_tokens": 0, "output_tokens": 0}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, sj in enumerate(sheet_jsons):
            name = sj.get("sheet_name", f"Sheet_{i}")
            # 정형 시트는 reconstruct skip — raw compact JSON을 간단 MD로 변환
            if name in skip_sheets:
                logger.info("⏭️ Skipping pass sheet '%s' — raw MD in .md file", name)
                continue
            f = executor.submit(reconstruct_sheet, sj, output_format, model_id, provider)
            futures[f] = (i, name)

        for f in as_completed(futures):
            idx, name = futures[f]
            try:
                text, usage = f.result()
                results[idx] = text
                total_usage["input_tokens"] += usage["input_tokens"]
                total_usage["output_tokens"] += usage["output_tokens"]
                logger.info("✅ Reconstructed sheet '%s' (in: %d, out: %d tokens)",
                            name, usage["input_tokens"], usage["output_tokens"])
            except Exception as e:
                logger.error("❌ Reconstruct failed for '%s': %s", name, e)
                results[idx] = f"<!-- Reconstruct failed: {name} -->"

    logger.info("📊 Total token usage — input: %d, output: %d",
                total_usage["input_tokens"], total_usage["output_tokens"])

    # 순서대로 합치기
    ordered = [results[i] for i in sorted(results.keys())]

    if output_format == "md":
        return "\n\n---\n\n".join(ordered), total_usage
    else:
        # HTML: wrap in full document
        body = "\n<hr />\n".join(ordered)
        title = ast.metadata.title or "Reconstructed Document"
        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
body {{ font-family: 'Pretendard', -apple-system, sans-serif; background: #f8f9fa; color: #374151; line-height: 1.6; padding: 2rem; max-width: 1400px; margin: 0 auto; }}
table {{ border-collapse: collapse; margin: 1rem 0; font-size: 0.85rem; }}
th, td {{ padding: 0.5rem 0.7rem; border: 1px solid #d1d5db; text-align: left; vertical-align: top; }}
th {{ background: #f1f5f9; font-weight: 600; }}
h1, h2, h3 {{ color: #1f2937; margin: 1rem 0 0.5rem; }}
hr {{ border: none; height: 1px; background: #e2e8f0; margin: 2rem 0; }}
</style>
</head>
<body>
{body}
</body>
</html>""", total_usage
