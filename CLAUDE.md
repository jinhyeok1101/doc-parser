# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Key Conventions

### Code Style
- Python 주석을 통해 코드에 대한 설명을 달아줘.

### Git
- Repository: https://github.com/jinhyeok1101/doc-parser.git
- Branch: `feat/`, `fix/`, `refactor/`, `test/`, `docs/`, `chore/`
- Conventional commits (feat, fix, test, refactor, docs, chore)
- Co-authored by Claude when AI-assisted

### README 유지보수
- 코드 변경사항이 있으면 `README.md`도 반드시 함께 업데이트할 것
  - 새 파일/모듈 추가 시 → 프로젝트 구조 섹션 업데이트
  - CLI 옵션 변경 시 → 사용법/CLI 옵션 테이블 업데이트
  - 파이프라인 흐름 변경 시 → Excel 파싱 워크플로우의 mermaid flowchart 업데이트
  - 출력 포맷 변경 시 → 출력 구조/포맷별 비교 섹션 업데이트
  - 의존성 변경 시 → 설치/환경 설정 섹션 업데이트
- `README.md` 내 mermaid chart는 실제 코드 흐름과 항상 동기화 유지

### Planning
- 인덱스: `docs/plans/README.md`
- v1 플랜 아카이브: `docs/plans/archive/`

**새 스프린트 시작 절차**:
1. `docs/plans/sprint-NN-<name>/` 폴더 생성
2. `overview.md` 작성 — 목표, phase 요약 테이블, 의존 관계 다이어그램, 진행 규칙
3. phase별 `phase-N-<name>.md` 작성 — 목적, 작업 목록, 위험 사항, 독립 수행이 가능하다면 Sub Agent 로 독립수행 , Phase 내 작업 단위는 하나의 커밋으로
4. `docs/plans/README.md` 스프린트 인덱스에 한 줄 추가
5. 완료 시 overview.md 상단에 `상태: 완료 (YYYY-MM-DD)` 표기

### Skills
커스텀 검증 및 유지보수 스킬은 `.claude/skills/`에 정의되어 있습니다.
| Skill | Purpose |
| --- | --- |
| `verify-implementation` | 프로젝트의 모든 verify 스킬을 순차 실행하여 통합 검증 보고서를 생성합니다 |
| `manage-skills` | 세션 변경사항을 분석하고, 검증 스킬을 생성/업데이트하며, CLAUDE.md를 관리합니다 |




