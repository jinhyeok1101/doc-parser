# Phase 3 — sampe_drink.xlsx GT 벤치마크

**상태**: 완료 (2026-03-19)

## 테스트 대상

- **파일**: `docs/test_docs/sampe_drink.xlsx`
- **특징**: 음료 데이터, 일반 표 구조
- **시트 목록**: 맥주, 소주 (2시트)

## 실행 명령어

```bash
uv run python run.py docs/test_docs/sampe_drink.xlsx -o output --model-id gemini-2.5-flash --no-summary --reconstruct -v
uv run python run.py docs/test_docs/sampe_drink.xlsx -o output --model-id gemini-2.5-pro --no-summary --reconstruct -v
```

## 결과 요약

| 항목 | gemini-2.5-flash | gemini-2.5-pro |
|------|------------------|----------------|
| 시트 수 | 2 | 2 |
| 재구성 성공 | 2/2 | 2/2 |
| Input tokens | 4,210 | 4,210 |
| Output tokens | 449 | 453 |
| 소요 시간 | 16.3s | 12.6s |

## 시트별 토큰 사용량

### gemini-2.5-flash

| 시트 | Input | Output |
|------|------:|-------:|
| 맥주 | 2,103 | 221 |
| 소주 | 2,107 | 228 |

### gemini-2.5-pro

| 시트 | Input | Output |
|------|------:|-------:|
| 맥주 | 2,103 | 223 |
| 소주 | 2,107 | 230 |

## 이슈

- 없음. Flash/Pro 모두 정상 완료.

## 산출물

```
output/sampe_drink_gemini-2.5-flash/
output/sampe_drink_gemini-2.5-pro/
```
