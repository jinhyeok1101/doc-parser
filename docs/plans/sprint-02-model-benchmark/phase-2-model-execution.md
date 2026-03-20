# Phase 2 — 모델별 AX_sample 파싱 실행

**목적**: 3개 후보 모델로 AX_sample.xlsx를 reconstruct하여 출력 생성

## 작업 목록

- [ ] Qwen 3.5 Plus 실행
  ```bash
  python run.py docs/test_docs/AX_sample.xlsx \
    --output output \
    --model-id qwen/qwen3.5-plus-02-15 \
    --provider openrouter \
    --reconstruct
  ```
- [ ] GLM-4.7 Flash 실행
  ```bash
  python run.py docs/test_docs/AX_sample.xlsx \
    --output output \
    --model-id zhipu/glm-4.7-flash \
    --provider openrouter \
    --reconstruct
  ```
- [ ] GPT-OSS-120B 실행
  ```bash
  python run.py docs/test_docs/AX_sample.xlsx \
    --output output \
    --model-id openai/gpt-oss-120b \
    --provider openrouter \
    --reconstruct
  ```

## 출력 위치

| 모델 | 출력 디렉토리 |
|------|-------------|
| Qwen 3.5 Plus | `output/AX_sample_qwen3.5-plus/` |
| GLM-4.7 Flash | `output/AX_sample_glm-4.7-flash/` |
| GPT-OSS-120B | `output/AX_sample_gpt-oss-120b/` |

## 위험 사항

- OpenRouter 무료 티어 Rate Limit (RPM 제한) → `workers=1`로 순차 실행
- 모델별 컨텍스트 윈도우 차이 → 대형 시트에서 truncation 가능
- Rate limit 429 에러 시 재시도 로직 (MAX_RETRIES=5, RETRY_DELAY=20s)
