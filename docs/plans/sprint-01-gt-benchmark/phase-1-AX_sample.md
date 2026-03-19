# Phase 1 — AX_sample.xlsx GT 벤치마크

**상태**: 완료 (2026-03-19)

## 테스트 대상

- **파일**: `docs/test_docs/AX_sample.xlsx`
- **특징**: 사장님보고용, 10시트, 복잡한 표/병합/간트차트
- **시트 목록**: To-do, KPI 운영 Issue, (Summary) 추진 계획, ① 과제 재분류 방안, ② KPI 운영안, ③-1 TMO set-up, ③-2. TMO 운영안, ④ 플랫폼 프로젝트 추진안, 보고파일 제외>>, 중점과제(Ideation)

## 실행 명령어

```bash
uv run python run.py docs/test_docs/AX_sample.xlsx -o output --model-id gemini-2.5-flash --no-summary --reconstruct -v
uv run python run.py docs/test_docs/AX_sample.xlsx -o output --model-id gemini-2.5-pro --no-summary --reconstruct -v
```

## 결과 요약

| 항목 | gemini-2.5-flash | gemini-2.5-pro |
|------|------------------|----------------|
| 시트 수 | 10 | 10 |
| 재구성 성공 | 9/10 | 10/10 |
| Input tokens | 65,594 | 67,181 |
| Output tokens | 18,169 | 18,710 |
| 소요 시간 | 171.6s | 67.6s |

## 시트별 토큰 사용량

### gemini-2.5-flash

| 시트 | Input | Output |
|------|------:|-------:|
| To-do | 7,144 | 1,434 |
| KPI 운영 Issue | 4,561 | 2,697 |
| (Summary) 추진 계획 | 4,706 | 1,443 |
| ① 과제 재분류 방안 | 7,129 | 1,093 |
| ② KPI 운영안 | 16,382 | 5,595 |
| ③-1 TMO set-up | 4,850 | 764 |
| ③-2. TMO 운영안 | 4,666 | 624 |
| ④ 플랫폼 프로젝트 추진안 | 10,643 | 2,725 |
| 보고파일 제외>> | - | 실패 |
| 중점과제(Ideation) | 5,513 | 1,794 |

### gemini-2.5-pro

| 시트 | Input | Output |
|------|------:|-------:|
| To-do | 7,144 | 1,339 |
| KPI 운영 Issue | 4,561 | 2,838 |
| (Summary) 추진 계획 | 4,706 | 1,412 |
| ① 과제 재분류 방안 | 7,129 | 1,112 |
| ② KPI 운영안 | 16,382 | 5,618 |
| ③-1 TMO set-up | 4,850 | 1,177 |
| ③-2. TMO 운영안 | 4,666 | 542 |
| ④ 플랫폼 프로젝트 추진안 | 10,643 | 2,810 |
| 보고파일 제외>> | 1,587 | 16 |
| 중점과제(Ideation) | 5,513 | 1,846 |

## 이슈

- **Flash '보고파일 제외>>' 시트 실패**: Gemini가 빈 응답을 반환하여 `reconstruct_sheet`에서 튜플 언패킹 에러 발생. 빈 응답 시 `("", usage)` 반환하도록 버그 수정 완료.
- Pro는 동일 시트를 16토큰(거의 빈 내용)으로 성공 처리.

## 산출물

```
output/AX_sample_gemini-2.5-flash/
output/AX_sample_gemini-2.5-pro/
```
