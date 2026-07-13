# 발표 스크립트 / Presentation Script (v2, 2026-07)
슬라이드 14장 기준, 약 6–7분. 실측 수치는 감사로그(2026-07-13 실행) 기반.

---

## 🇰🇷 한국어 스크립트

**[1 표지]** 안녕하세요. MCP와 A2A 프로토콜로 구급차 응급실 이송을 자동화하는 멀티 AI 에이전트 시스템을 소개합니다. 1년 전 프로토타입으로 시작했고, 올해 전면 업그레이드해 실제 API 위에서 완주 검증까지 마친 시스템입니다.

**[2 문제]** 응급실 뺑뺑이 문제의 본질은 사람이 병원마다 전화를 돌리는 구조입니다. 소방과 병원의 데이터는 단절돼 있고, 통합 관제 주체는 없고, 정책은 수년째 제자리입니다.

**[3 사회적 요구]** 현장도 같은 말을 합니다. 구급대원 759명 설문에서 94%가 현행 응급실 상황판의 개선 또는 교체가 필요하다고 답했고, 79%는 새로운 플랫폼이 병원 선정에 도움이 될 거라 답했습니다.

**[4 제안]** 저희 답은 기관마다 AI 에이전트를 두고 실시간 협업시키는 원스톱 자동화입니다. 1년 전엔 "1분 이내 결정"이 목표였습니다. 지금은 목표가 아니라 실측치입니다 — 접수부터 병원 확정, 보험 처리까지 **평균 50초**, 전 과정이 감사로그로 기록됩니다.

**[5 MCP]** MCP는 에이전트를 도구·API에 연결하는 표준, 소프트웨어의 USB 포트입니다. 저희는 카카오 길찾기 같은 외부 API 연동에 사용합니다.

**[6 A2A]** A2A는 조직 경계를 넘어 에이전트끼리 대화하게 하는 프로토콜입니다. 참고로 A2A는 작년 리눅스 재단으로 이관되어 업계 표준으로 성숙했습니다. 1년 전 저희 기술 선택이 맞았다는 뜻이기도 합니다.

**[7 조합]** MCP가 도구를, A2A가 기관 간 협업을 맡습니다. 병원·보험사가 자기 에이전트만 세우면 시스템에 참여할 수 있습니다.

**[8 구조]** 구조를 보시죠. 구급차의 호스트 에이전트가 KTAS 중증도를 판단하고, 교통 에이전트가 실시간 교통 반영 ETA로 응급실을 정렬합니다. 핵심 개선 두 가지: 첫째, 병원 문의가 순차에서 **병렬**로 바뀌어 여러 병원에 동시에 묻습니다. 둘째, 수용 판단은 LLM의 감이 아니라 **코드에 박힌 규칙** — 수술실·병상·수술 가능 의사 실시간 조회 — 로 내립니다. LLM은 증상을 진료과로 매핑할 뿐, 판단은 결정론적입니다. 모든 통신은 상호 인증되고 감사로그로 남습니다.

**[9 데모]** 실제 데모입니다. 대전 출입국관리사무소에서 뇌졸중 의심 환자가 발생했다고 입력하면 — 시스템이 KTAS 2등급 판정, 근처 응급실 10곳을 ETA순 정렬, 가장 가까운 두 병원에 동시 문의합니다. 0.1km 옆 선병원은 "병상 없음"으로 거절, 2.9km의 성모병원이 수용 — 시스템은 무작정 가까운 곳이 아니라 **받아줄 수 있는 곳**을 고릅니다. 보험 확인 요청까지 슬랙으로 자동 전송, 총 50초. 같은 시나리오를 영어로 넣으면 전 과정이 영어로 진행됩니다.

**[10 비교]** 기존 스마트 시스템과의 차이입니다. 사람이 기다리는 확인 대신 AI 자동 응답, 주관적 판단 대신 기준 기반 매칭, 그리고 교통부터 보험까지 엔드투엔드. 음성 인식은 다음 단계로, 현재는 텍스트 기반입니다.

**[11 타당성]** 법적으로는 통신비밀보호법상 대화 당사자 녹음 허용, 개인정보보호법 15조 1항 5호의 응급상황 수집 근거를 확인했습니다. 올해는 기술적 안전장치를 실장했습니다 — 에이전트 간 인증 토큰, 비밀키 분리, 로그 개인정보 마스킹, 그리고 모든 이송 결정의 감사추적입니다.

**[12 기대효과]** 사회적으로는 뺑뺑이 감소와 골든타임 확보, 기술적으로는 LLM+MCP+A2A의 실환경 검증, 경제적으로는 병원 인건비와 행정 부담 절감입니다.

**[13 로드맵]** 1단계 프로토타입은 완료됐고, 올해 검증까지 마쳤습니다 — 최신 프레임워크 마이그레이션, 병렬 문의, 인증·감사로그, 그리고 실 API 6종 위에서의 완주. 다음은 음성 인식 연동, 국립중앙의료원 실시간 가용병상 공공 API 연결, 그리고 1–2개 병원 파일럿입니다.

**[14 마무리]** 정리합니다. 응급실 확정까지 실측 50초. 30분 내 도착 보장이 저희 목표입니다. MCP·A2A를 응급의료에 적용한 국내 첫 시스템이고, 병원 추가는 설정 파일 하나면 됩니다. 기술은 준비됐습니다. 필요한 건 현장 파일럿입니다. 감사합니다.

---

## 🇺🇸 English Script

**[1 Title]** Hello. This is a multi-AI-agent system that automates ambulance-to-ER dispatch using the MCP and A2A protocols. It started as a prototype a year ago; this year we rebuilt it and verified it end-to-end on live APIs.

**[2 Problem]** The essence of Korea's "ER bounce-around" problem is a human making phone calls hospital by hospital. Fire-department and hospital data are disconnected, no central authority coordinates, and policy has stalled for years.

**[3 Social need]** The field agrees. In a survey of 759 paramedics, 94% said current ER dashboards need improvement or replacement, and 79% said a new platform would help hospital selection.

**[4 Proposal]** Our answer: a one-stop automated flow where AI agents across institutions collaborate in real time. A year ago, "decision within one minute" was a goal. Today it is a measurement — intake to hospital confirmation to insurance takes **about 50 seconds**, and every step is audit-logged.

**[5 MCP]** MCP is the standard that connects agents to tools and APIs — the USB port of software. We use it for external APIs like Kakao Mobility routing.

**[6 A2A]** A2A lets agents talk across organizational boundaries. Notably, A2A moved to the Linux Foundation last year and matured into an industry standard — our technology bet from a year ago proved right.

**[7 Together]** MCP handles tools; A2A handles cross-organization collaboration. A hospital or insurer joins the system simply by standing up its own agent.

**[8 Architecture]** Here's the structure. The host agent in the ambulance performs KTAS triage; the traffic agent ranks nearby ERs by traffic-aware ETA. Two key upgrades this year: first, hospital inquiries went from sequential to **parallel** — we ask multiple hospitals simultaneously. Second, acceptance is decided not by an LLM's intuition but by **rules in code** — live queries of operating rooms, beds, and available surgeons. The LLM only maps symptoms to a specialty; the decision is deterministic. All traffic is mutually authenticated and audit-logged.

**[9 Demo]** A real run: a suspected stroke at the Daejeon Immigration Office. The system grades KTAS 2, ranks ten ERs by ETA, and queries the two nearest hospitals in parallel. Sun Hospital, 100 meters away, declines — no beds. St. Mary's, 2.9 km away, accepts. The system picks not the nearest hospital, but the nearest one that **can take the patient**. The insurance request goes out via Slack automatically. Total: 50 seconds. Feed the same scenario in English, and the entire pipeline responds in English.

**[10 Comparison]** Against existing smart systems: AI auto-response instead of humans waiting on confirmations, criteria-based matching instead of subjective judgment, end-to-end from traffic to insurance. Voice recognition is next phase; today the input is text.

**[11 Feasibility]** Legally: one-party call recording is permitted, and emergency data collection is grounded in Article 15-1-5 of the Personal Information Protection Act. This year we added the technical safeguards — inter-agent auth tokens, secret isolation, PII-masked logging, and a full audit trail of every dispatch decision.

**[12 Impact]** Socially: fewer bounce-arounds, golden hour secured. Technically: real-world validation of LLM+MCP+A2A. Economically: lower hospital labor and administrative costs.

**[13 Roadmap]** Phase one is complete and verified — migrated to the latest frameworks, parallel dispatch, auth and audit, and a full run on six live APIs. Next: voice input, the national real-time ER-bed open API, and a pilot with one or two hospitals.

**[14 Close]** To recap: 50 seconds, measured, to a confirmed ER. Our target is arrival within 30 minutes. It's Korea's first emergency-care system built on MCP and A2A, and adding a hospital takes one config file. The technology is ready. What we need now is a field pilot. Thank you.
