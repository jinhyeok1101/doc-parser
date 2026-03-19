# Phase 2 — demo_irregular_v2.xlsx GT 벤치마크

**상태**: 완료 (2026-03-19)

## 테스트 대상

- **파일**: `docs/test_docs/demo_irregular_v2.xlsx`
- **특징**: 비정형 다중 표, 가짜 병합 패턴, WBS 공정표
- **시트 목록**: WBS공정표 (1시트)

## 실행 명령어

```bash
uv run python run.py docs/test_docs/demo_irregular_v2.xlsx -o output --model-id gemini-2.5-flash --no-summary --reconstruct -v
uv run python run.py docs/test_docs/demo_irregular_v2.xlsx -o output --model-id gemini-2.5-pro --no-summary --reconstruct -v
```

## 결과 요약

| 항목 | gemini-2.5-flash | gemini-2.5-pro |
|------|------------------|----------------|
| 시트 수 | 1 | 1 |
| 재구성 성공 | 1/1 | 1/1 |
| Input tokens | 6,755 | 6,755 |
| Output tokens | 1,501 | 1,274 |
| 소요 시간 | 71.4s | 43.3s |

## 이슈

- 초기 실행 시 `_serialize_ast`에서 `attachments`가 `None`인 경우 `TypeError` 발생. `(raw.get("attachments") or [])` 로 수정하여 해결.
- 재실행 후 Flash/Pro 모두 정상 완료.

## 산출물

```
output/demo_irregular_v2_gemini-2.5-flash/
output/demo_irregular_v2_gemini-2.5-pro/
```
