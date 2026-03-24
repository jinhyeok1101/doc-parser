"""GT vs Central LLM reconstruct 자동 비교 스크립트.

ROUGE/BLEU 스코어 + 키워드/수치 커버리지를 계산하여 비교 보고서를 생성.

Usage:
    uv run python scripts/compare_reconstruct.py \
        --gt output/AX_sample_gemini-2.5-flash/AX_sample_reconstructed.md \
        --target output/AX_sample_gpt-oss-120b-central-v10/AX_sample_reconstructed.md \
        --output scripts/comparison_report.md
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from rouge_score import rouge_scorer


# ── ROUGE 계산 ──

def compute_rouge(gt_text: str, target_text: str) -> dict:
    """ROUGE-1, ROUGE-2, ROUGE-L 스코어 계산."""
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=False)
    scores = scorer.score(gt_text, target_text)
    return {
        "rouge1": {
            "precision": round(scores["rouge1"].precision, 4),
            "recall": round(scores["rouge1"].recall, 4),
            "fmeasure": round(scores["rouge1"].fmeasure, 4),
        },
        "rouge2": {
            "precision": round(scores["rouge2"].precision, 4),
            "recall": round(scores["rouge2"].recall, 4),
            "fmeasure": round(scores["rouge2"].fmeasure, 4),
        },
        "rougeL": {
            "precision": round(scores["rougeL"].precision, 4),
            "recall": round(scores["rougeL"].recall, 4),
            "fmeasure": round(scores["rougeL"].fmeasure, 4),
        },
    }


# ── 키워드/수치 커버리지 ──

def extract_keywords(text: str) -> set[str]:
    """텍스트에서 한글 키워드(2자 이상) 추출."""
    # 한글 단어 추출
    words = re.findall(r"[가-힣]{2,}", text)
    return set(words)


def extract_numbers(text: str) -> set[str]:
    """텍스트에서 숫자/수치 추출."""
    # 숫자 패턴: 정수, 소수, 퍼센트, 날짜 등
    numbers = re.findall(r"\d+(?:\.\d+)?%?", text)
    return set(numbers)


def compute_coverage(gt_items: set, target_items: set) -> dict:
    """GT 항목 대비 Target의 커버리지 계산."""
    if not gt_items:
        return {"coverage": 1.0, "gt_count": 0, "target_count": 0, "matched": 0, "missing": []}

    matched = gt_items & target_items
    missing = gt_items - target_items
    return {
        "coverage": round(len(matched) / len(gt_items), 4),
        "gt_count": len(gt_items),
        "target_count": len(target_items),
        "matched": len(matched),
        "missing_count": len(missing),
        "missing_sample": sorted(list(missing))[:20],  # 상위 20개만
    }


# ── 기본 통계 ──

def basic_stats(text: str) -> dict:
    """기본 텍스트 통계."""
    lines = text.split("\n")
    table_rows = sum(1 for line in lines if "|" in line)
    headings = sum(1 for line in lines if line.startswith("#"))
    br_count = text.count("<br>")
    progress_count = text.count("진행")
    return {
        "lines": len(lines),
        "chars": len(text),
        "table_rows": table_rows,
        "headings": headings,
        "br_tags": br_count,
        "progress_mentions": progress_count,
    }


# ── 보고서 생성 ──

def generate_report(
    gt_path: str,
    target_path: str,
    gt_text: str,
    target_text: str,
    rouge: dict,
    keyword_coverage: dict,
    number_coverage: dict,
    gt_stats: dict,
    target_stats: dict,
) -> str:
    """Markdown 비교 보고서 생성."""
    report = f"""# Reconstruct 비교 보고서

## 비교 대상

| 항목 | GT | Target |
|------|-----|--------|
| 파일 | `{gt_path}` | `{target_path}` |
| 줄 수 | {gt_stats['lines']} | {target_stats['lines']} |
| 문자 수 | {gt_stats['chars']} | {target_stats['chars']} |
| 테이블 행 | {gt_stats['table_rows']} | {target_stats['table_rows']} |
| 헤딩 수 | {gt_stats['headings']} | {target_stats['headings']} |
| `<br>` 태그 | {gt_stats['br_tags']} | {target_stats['br_tags']} |
| "진행" 횟수 | {gt_stats['progress_mentions']} | {target_stats['progress_mentions']} |

## ROUGE 스코어

| 메트릭 | Precision | Recall | F1 |
|--------|-----------|--------|-----|
| ROUGE-1 | {rouge['rouge1']['precision']} | {rouge['rouge1']['recall']} | {rouge['rouge1']['fmeasure']} |
| ROUGE-2 | {rouge['rouge2']['precision']} | {rouge['rouge2']['recall']} | {rouge['rouge2']['fmeasure']} |
| ROUGE-L | {rouge['rougeL']['precision']} | {rouge['rougeL']['recall']} | {rouge['rougeL']['fmeasure']} |

## 키워드 커버리지 (한글 2자+ 단어)

| 항목 | 값 |
|------|-----|
| GT 키워드 수 | {keyword_coverage['gt_count']} |
| Target 키워드 수 | {keyword_coverage['target_count']} |
| 일치 | {keyword_coverage['matched']} |
| **커버리지** | **{keyword_coverage['coverage']:.1%}** |
| 누락 수 | {keyword_coverage['missing_count']} |

### 누락 키워드 샘플 (상위 20개)

{', '.join(keyword_coverage.get('missing_sample', [])) or '없음'}

## 수치 커버리지

| 항목 | 값 |
|------|-----|
| GT 수치 수 | {number_coverage['gt_count']} |
| Target 수치 수 | {number_coverage['target_count']} |
| 일치 | {number_coverage['matched']} |
| **커버리지** | **{number_coverage['coverage']:.1%}** |
| 누락 수 | {number_coverage['missing_count']} |

### 누락 수치 샘플 (상위 20개)

{', '.join(number_coverage.get('missing_sample', [])) or '없음'}

## 종합 평가

| 메트릭 | 스코어 | 판정 |
|--------|--------|------|
| ROUGE-1 F1 | {rouge['rouge1']['fmeasure']} | {'✅ 우수' if rouge['rouge1']['fmeasure'] >= 0.7 else '⚠️ 보통' if rouge['rouge1']['fmeasure'] >= 0.5 else '❌ 미흡'} |
| ROUGE-L F1 | {rouge['rougeL']['fmeasure']} | {'✅ 우수' if rouge['rougeL']['fmeasure'] >= 0.7 else '⚠️ 보통' if rouge['rougeL']['fmeasure'] >= 0.5 else '❌ 미흡'} |
| 키워드 커버리지 | {keyword_coverage['coverage']:.1%} | {'✅ 우수' if keyword_coverage['coverage'] >= 0.8 else '⚠️ 보통' if keyword_coverage['coverage'] >= 0.6 else '❌ 미흡'} |
| 수치 커버리지 | {number_coverage['coverage']:.1%} | {'✅ 우수' if number_coverage['coverage'] >= 0.8 else '⚠️ 보통' if number_coverage['coverage'] >= 0.6 else '❌ 미흡'} |
"""
    return report


def main():
    parser = argparse.ArgumentParser(description="GT vs Target reconstruct 비교")
    parser.add_argument("--gt", type=Path, required=True, help="GT reconstructed MD 경로")
    parser.add_argument("--target", type=Path, required=True, help="Target reconstructed MD 경로")
    parser.add_argument("--output", type=Path, default=None, help="보고서 출력 경로 (없으면 stdout)")
    args = parser.parse_args()

    gt_text = args.gt.read_text(encoding="utf-8")
    target_text = args.target.read_text(encoding="utf-8")

    # 계산
    rouge = compute_rouge(gt_text, target_text)
    gt_keywords = extract_keywords(gt_text)
    target_keywords = extract_keywords(target_text)
    keyword_cov = compute_coverage(gt_keywords, target_keywords)

    gt_numbers = extract_numbers(gt_text)
    target_numbers = extract_numbers(target_text)
    number_cov = compute_coverage(gt_numbers, target_numbers)

    gt_stats = basic_stats(gt_text)
    target_stats = basic_stats(target_text)

    # 보고서 생성
    report = generate_report(
        str(args.gt), str(args.target),
        gt_text, target_text,
        rouge, keyword_cov, number_cov,
        gt_stats, target_stats,
    )

    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"✅ 보고서 저장: {args.output}")
    else:
        print(report)

    # 요약 출력
    print(f"\n📊 요약: ROUGE-1 F1={rouge['rouge1']['fmeasure']}, "
          f"ROUGE-L F1={rouge['rougeL']['fmeasure']}, "
          f"키워드={keyword_cov['coverage']:.1%}, "
          f"수치={number_cov['coverage']:.1%}")


if __name__ == "__main__":
    main()
