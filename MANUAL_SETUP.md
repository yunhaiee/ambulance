# 수동 설정 체크리스트 (MANUAL SETUP)

H-tier 업그레이드(2026-07) 후 사람이 직접 해야 하는 작업 목록입니다.
완료하면 체크하세요.

## 0. ⚠️ iCloud 문제 (가장 중요 — 개발이 멈추는 원인)

이 리포는 iCloud가 동기화하는 `~/Documents` 안에 있습니다. macOS가 파일 내용을
iCloud로 evict하면(dataless), 그 파일을 읽는 순간 다운로드가 끝날 때까지 프로세스가
멈춥니다. 실제로 이번 세션에서 `import google.adk`가 **7분 33초** 걸렸습니다 (CPU 0%).

- [ ] **권장: 리포를 iCloud 밖으로 이동** — 예: `mv ~/Documents/GitHub ~/dev` 후
      GitHub Desktop/에디터에서 경로 다시 지정. (또는 시스템 설정 → Apple ID →
      iCloud Drive → "데스크탑 및 문서 폴더" 동기화 해제, 또는 "Mac 저장 공간 최적화" 끄기)
- [ ] 가상환경은 이미 `~/.venvs/ambulance-*`로 옮겨 두었습니다 (iCloud 밖).
      **리포 안에 `.venv`를 다시 만들지 마세요.** 실행 시 항상
      `UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-<서비스>`를 쓰거나 아래 실행 명령을 그대로 사용.
- [ ] `node_modules`(교통 MCP 서버가 사용)도 같은 위험이 있습니다. 교통 에이전트가
      이유 없이 멈추면: `find node_modules -type f -flags +dataless | wc -l` 로 확인.

## 1. API 키 / 토큰 (.env 파일 5개)

각 서비스 폴더의 `.env.example`을 `.env`로 복사해 채우세요:
`host_adk/`, `교통AI에이전트/`, `보험AI에이전트/`, `병원AI에이전트/`

- [ ] `GOOGLE_API_KEY` — 실제 Gemini API 키 (5곳 모두)
- [ ] `A2A_AUTH_TOKEN` — `openssl rand -hex 32`로 하나 생성해서 **5곳 모두 동일하게** 설정
      (안 하면 인증 없이 동작 + 시작 시 경고)
- [ ] `KAKAO_REST_API_KEY` — 교통 에이전트만
- [ ] `SLACK_BOT_TOKEN` — 교통/보험/병원. **`SLACK_TEAM_ID`는 더 이상 필요 없음** (지워도 됨)
- [ ] `NOTION_API_KEY` — 병원 에이전트만. **보험 에이전트에서는 더 이상 필요 없음**

## 2. Slack 봇 확인

Slack MCP 서버(아카이브된 패키지)를 버리고 `chat.postMessage` 직접 호출로 바꿨습니다.

- [ ] 봇 토큰에 `chat:write` 스코프가 있는지 확인
- [ ] 봇이 세 채널에 초대되어 있는지 확인:
      교통안전공단 `C0968E2P03Z`, 보험 `C096P6A2Q66`,
      병원 `C097BQWHQGG`(선병원) / `C096L5YHEJ2`(성모병원)

## 3. Notion 공간 DB 스키마 확인 (병원 수용 판단)

수용 판단이 프롬프트에서 코드([병원AI에이전트/capacity.py](병원AI에이전트/capacity.py))로
옮겨졌습니다. 코드는 공간 DB에서 **제목에 "수술실" 또는 "베드"(병상)가 들어간 행의
숫자 속성**을 개수로 읽습니다.

- [ ] 실제 Notion 공간 DB가 이 형태인지 확인. 다르면 (예: 행 하나당 침대 1개 +
      사용중 체크박스) 알려주세요 — capacity.py 매핑을 실제 스키마에 맞추겠습니다.
- [ ] 테스트: 병원 에이전트에 "신경외과 환자 수용 가능?" 문의 → ⚠️판단불가가 나오면
      스키마 불일치입니다 (응답의 raw_spaces 값을 보내주세요).

## 4. 실행 방법 (터미널 5개)

```bash
# 1. 교통 (port 10002)
cd 교통AI에이전트 && UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-교통AI에이전트 uv run python __main__.py

# 2. 대전성모병원 (port 10003)
cd 병원AI에이전트 && HOSPITAL_PROFILE=configs/대전성모병원.env UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-병원AI에이전트 uv run python __main__.py

# 3. 대전선병원 (port 10004)
cd 병원AI에이전트 && HOSPITAL_PROFILE=configs/대전선병원.env UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-병원AI에이전트 uv run python __main__.py

# 4. 보험 (port 10005)
cd 보험AI에이전트 && UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-보험AI에이전트 uv run python __main__.py

# 5. 호스트 (위 4개가 뜬 다음에!)
cd host_adk && UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-host uv run adk web
```

- [ ] 병원 추가는 이제 `병원AI에이전트/configs/새병원.env` 파일 하나 + 호스트
      `.env`의 `REMOTE_AGENT_URLS`에 주소 추가로 끝납니다 (코드 복사 불필요).

## 5. 첫 실전 테스트 후 확인

- [ ] `adk web`에서 시나리오 1회 실행 (환자 정보 → 진단 → 병원 병렬 문의 → 보험)
- [ ] `~/.ambulance/dispatch_audit.jsonl`에서 단계별 소요시간 확인 — "1분 이내 결정"
      KPI의 실측 근거가 여기 쌓입니다. (환자정보 포함 파일이므로 외부 공유 금지)
- [ ] Slack 세 채널에 메시지가 실제로 도착했는지 확인

## 6. Git 정리 (커밋할 때)

- [ ] 추적 중인 컴파일 산출물 제거: `git rm -r --cached "**/__pycache__"` (이제 .gitignore에 있음)
- [ ] 사라진 파일들 확인: `병원AI에이전트들/`(구 병원 2개), `agent_executor.py`×2,
      `remote_agent_connection.py`는 의도적으로 삭제됨 (새 구조로 대체)
- [ ] 커밋을 원하면 Claude에게 요청
