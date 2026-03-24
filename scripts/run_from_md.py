"""from_md 전용 실행 스크립트 — AST Markdown → LLM → 정제 Markdown.

Usage:
    uv run python scripts/run_from_md.py docs/test_docs/AX_sample.xlsx \
        --output-dir output_md/AX_sample_from_md_v01 \
        --provider central \
        -v
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("run_from_md")


def main():
    parser = argparse.ArgumentParser(description="from_md reconstruct 전용 실행")
    parser.add_argument("input", type=Path, help="Excel 파일 경로")
    parser.add_argument("--output-dir", type=Path, required=True, help="출력 디렉토리")
    parser.add_argument("--provider", choices=["gemini", "openrouter", "central"], default="central")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    # 로깅 설정
    fmt = "%(asctime)s %(levelname)-5s %(name)s — %(message)s"
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.input.stem
    t0 = time.time()

    # 파싱
    from office_parser import OfficeParserConfig
    from office_parser.parser import OfficeParser

    config = OfficeParserConfig(summarize=False, reconstruct=False, llm_provider=args.provider)
    ast = OfficeParser.parse_office(str(args.input), config)
    # _image_dir 설정 (from_md에서 _sheet_to_markdown이 참조)
    ast._image_dir = str(args.output_dir / "pictures")
    logger.info("📄 Parsed %s (%d sheets)", args.input.name, len([n for n in ast.content if n.type == "sheet"]))

    # from_md reconstruct
    from office_parser.reconstructor import reconstruct_all_sheets_from_md

    logger.info("🔄 Reconstructing from MD (provider=%s)...", args.provider)
    result, usage = reconstruct_all_sheets_from_md(ast, provider=args.provider)

    # 저장
    out_path = args.output_dir / f"{stem}_reconstructed_from_md.md"
    out_path.write_text(result, encoding="utf-8")
    logger.info("✅ Saved → %s", out_path)

    usage_path = args.output_dir / f"{stem}_token_usage.json"
    usage_path.write_text(json.dumps(usage, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("📊 Tokens — in: %d, out: %d (%.1fs)", usage["input_tokens"], usage["output_tokens"], time.time() - t0)


if __name__ == "__main__":
    main()
