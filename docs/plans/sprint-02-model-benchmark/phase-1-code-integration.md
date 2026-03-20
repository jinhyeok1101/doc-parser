# Phase 1 — OpenRouter 코드 통합

**목적**: `worktree-qwen` 브랜치의 OpenRouter 멀티 모델 지원 코드를 `test/glm` 브랜치에 통합

## 작업 목록

- [ ] `worktree-qwen`에서 OpenRouter 관련 변경사항 cherry-pick (커밋 `3d9b46f`)
  - `office_parser/llm_client.py` (신규)
  - `office_parser/reconstructor.py` (provider 파라미터 추가)
  - `office_parser/worker.py` (provider/vision_model_id 지원)
  - `run.py` (`--provider`, `--vision-model-id` CLI 옵션)
  - `office_parser/prompts.yaml` (영문 프롬프트)
- [ ] `.env`에 `OPENROUTER_API_KEY` 설정 확인
- [ ] `openai` 패키지 의존성 추가 (`uv add openai`)
- [ ] 간단한 연결 테스트 (Qwen 3.5로 단일 시트 reconstruct)

## 위험 사항

- cherry-pick 시 `worker.py` 충돌 가능 (출력 구조 변경됨)
- worktree-qwen에서 토큰 사용량 추적이 제거됨 → 벤치마크에 필요하면 별도 구현
