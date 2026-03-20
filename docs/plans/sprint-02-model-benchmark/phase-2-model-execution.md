# Phase 2 — 모델별 AX_sample 파싱 실행

**목적**: 후보 모델로 AX_sample.xlsx를 reconstruct하여 출력 생성

## 실행 결과

### GPT-OSS-120B — 10/10 성공

```bash
python run.py docs/test_docs/AX_sample.xlsx \
  --output output \
  --model-id openai/gpt-oss-120b:free \
  --provider openrouter \
  --reconstruct
```
- 소요 시간: ~418s
- 토큰: in 61,238 / out 34,822
- 출력: `output/AX_sample_gpt-oss-120b/`

### GLM-4.5 Air — 일부 성공 (재시도 필요)

```bash
python run.py docs/test_docs/AX_sample.xlsx \
  --output output \
  --model-id z-ai/glm-4.5-air:free \
  --provider openrouter \
  --reconstruct
```
- 1차 실행: 10/10 성공했으나 출력 디렉토리 삭제로 저장 실패
- 2차 실행: 일일 무료 한도(50 req/day) 초과, 일부 시트만 성공
- 출력: `output/AX_sample_glm-4.5-air/` (불완전)

### GLM-4.6V — 미실행

```bash
python run.py docs/test_docs/AX_sample.xlsx \
  --output output \
  --model-id z-ai/glm-4.6v \
  --provider openrouter \
  --reconstruct
```
- 유료 모델 ($0.30/$0.90 per M tokens), 크레딧 충전 필요

### 실패한 모델들

| 모델 | 실패 사유 |
|------|----------|
| Qwen 3.5 Plus | Privacy 설정 충돌 (ZDR + Allowed Providers) |
| Qwen3-32B | 크레딧 부족 (402) |
| QwQ-32B:free | 엔드포인트 미존재 |
| Qwen2.5-72B:free | 엔드포인트 미존재 |
| Qwen3-Coder:free | Rate limit 초과, ~1/10 성공 |

## 위험 사항

- OpenRouter 무료 티어: 일일 50 requests 제한, 초과 시 10 크레딧 충전 필요
- Rate limit 429 에러 시 재시도 로직 (MAX_RETRIES=5, RETRY_DELAY=20s)
- `:free` suffix 모델은 출력 디렉토리가 `AX_sample_free`로 충돌 → `split(":")[0]`으로 수정 완료
