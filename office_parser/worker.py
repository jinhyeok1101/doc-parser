"""Single file parsing worker — separate module for ProcessPoolExecutor pickling."""
import json
import logging
import time
from pathlib import Path

from office_parser import OfficeParser, OfficeParserConfig

logger = logging.getLogger("office_parser")


def _serialize_ast(ast_obj) -> str:
    """AST 객체를 JSON 문자열로 직렬화 (attachments 바이너리 제외)."""
    from dataclasses import asdict

    def _default(obj):
        if isinstance(obj, bytes):
            return f"<binary {len(obj)} bytes>"
        return str(obj)

    raw = asdict(ast_obj)
    # 바이너리 데이터 제거 (파일 크기 절약)
    for att in (raw.get("attachments") or []):
        att.pop("data", None)
    return json.dumps(raw, default=_default, indent=2, ensure_ascii=False)


def parse_single(
    file_path: str,
    config: OfficeParserConfig,
    output_format: str,
    output_dir: str | None = None,
    model_name: str | None = None,
) -> Path:
    """Parse a single file → save all outputs. Returns: output directory path.

    항상 4가지 파일을 출력:
      1. {stem}_ast.json          — raw AST (워크플로우 3단계)
      2. {stem}.md                — AST → 사람읽기용 Markdown
      3. {stem}_compact.json      — Compact JSON, 재구성 직전 (워크플로우 5단계)
      4. {stem}_reconstructed.md  — Gemini 재구성 최종 MD
    """
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    logging.getLogger("botocore").setLevel(logging.WARNING)

    file_path = Path(file_path)
    stem = file_path.stem
    name = file_path.name
    t0 = time.time()
    logger.info("📄 [%s] Parsing started", name)

    ast = OfficeParser.parse_office(str(file_path), config)

    # output/{파일명}_{모델명}/ 디렉토리 생성
    if model_name:
        dir_name = f"{stem}_{model_name}"
    else:
        dir_name = stem
    doc_output = Path(output_dir) / dir_name if output_dir else file_path.parent / dir_name
    doc_output.mkdir(parents=True, exist_ok=True)

    # 첨부파일 → pictures/ 폴더에 저장
    pictures_dir = doc_output / "pictures"
    image_dir = None
    if config.extract_attachments and ast.attachments:
        pictures_dir.mkdir(parents=True, exist_ok=True)
        for att in ast.attachments:
            (pictures_dir / att.filename).write_bytes(att.data)
        image_dir = "pictures"

    # ① AST raw JSON (워크플로우 3단계 — AST 생성 결과)
    ast_path = doc_output / f"{stem}_ast.json"
    ast_path.write_text(_serialize_ast(ast), encoding="utf-8")
    logger.info("📦 [%s] AST saved → %s", name, ast_path.name)

    # ② 사람읽기용 Markdown (워크플로우 5단계 — AST → MD 변환)
    md_path = doc_output / f"{stem}.md"
    md_path.write_text(ast.to_markdown(image_dir=image_dir), encoding="utf-8")
    logger.info("📝 [%s] Markdown saved → %s", name, md_path.name)

    # ③ Compact JSON (워크플로우 5단계 — 재구성 직전)
    compact_path = doc_output / f"{stem}_compact.json"
    compact_path.write_text(ast.to_json_compact(), encoding="utf-8")
    logger.info("🗜️ [%s] Compact JSON saved → %s", name, compact_path.name)

    # ④ Gemini 재구성 MD (워크플로우 6단계 — 최종 결과)
    token_usage = {"model": model_name or "unknown", "input_tokens": 0, "output_tokens": 0}
    if config.reconstruct:
        from office_parser.reconstructor import reconstruct_all_sheets
        model_id = config.reconstruct_model or config.gemini_model_id
        provider = config.llm_provider

        # from_json 모드 (기본): Compact JSON → LLM → Markdown
        logger.info("🔄 [%s] Reconstructing to MD (provider=%s, model=%s)...", name, provider, model_id)
        try:
            rc_md, usage = reconstruct_all_sheets(ast, "md", model_id, provider)
            rc_md_path = doc_output / f"{stem}_reconstructed.md"
            rc_md_path.write_text(rc_md, encoding="utf-8")
            token_usage["input_tokens"] += usage["input_tokens"]
            token_usage["output_tokens"] += usage["output_tokens"]
            logger.info("✅ [%s] Reconstructed MD → %s", name, rc_md_path.name)
        except Exception as e:
            logger.error("❌ [%s] MD reconstruct failed: %s", name, e)

        # from_md 모드 (compare_input_formats 활성화 시): AST Markdown → LLM → 정제 Markdown
        if config.compare_input_formats:
            from office_parser.reconstructor import reconstruct_all_sheets_from_md
            logger.info("🔄 [%s] Reconstructing from MD (provider=%s, model=%s)...", name, provider, model_id)
            try:
                rc_from_md, usage_md = reconstruct_all_sheets_from_md(ast, model_id, provider)
                rc_from_md_path = doc_output / f"{stem}_reconstructed_from_md.md"
                rc_from_md_path.write_text(rc_from_md, encoding="utf-8")
                token_usage["input_tokens"] += usage_md["input_tokens"]
                token_usage["output_tokens"] += usage_md["output_tokens"]
                logger.info("✅ [%s] Reconstructed from MD → %s", name, rc_from_md_path.name)
            except Exception as e:
                logger.error("❌ [%s] from_md reconstruct failed: %s", name, e)

    # 토큰 사용량 리포트 저장
    usage_path = doc_output / f"{stem}_token_usage.json"
    usage_path.write_text(
        json.dumps(token_usage, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("📊 [%s] Token usage — in: %d, out: %d → %s",
                name, token_usage["input_tokens"], token_usage["output_tokens"], usage_path.name)

    logger.info("✅ [%s] Done → %s (%.1fs)", name, doc_output, time.time() - t0)
    return doc_output
