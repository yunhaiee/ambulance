#!/bin/bash
# Boot the 4 remote agents, run the Korean scenario then the English scenario
# through the host, save both outputs, and stop the servers.
#
# Prereqs: 5 per-agent Gemini keys already set (host/교통/보험 .env + 병원 .env.<name>),
# venvs at ~/.venvs/ambulance-*, and the daily free-tier quota available
# (resets ~16:00 KST). Usage:  bash demo/run_both.sh
set -u
REPO="/Users/yunhaiee/Downloads/GitHub/ambulance"
V="$HOME/.venvs"
M="gemini-2.5-flash"          # per-minute reset; better than flash-lite's 20/day for demos
D="$HOME/.ambulance/demo"
LOG="/tmp/ambulance-demo"
mkdir -p "$D" "$LOG"

echo "== 무료 한도 확인 (host key) =="
KEY=$(grep '^GOOGLE_API_KEY=' "$REPO/host_adk/.env" | cut -d= -f2-)
CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$KEY" \
  -H "Content-Type: application/json" -d '{"contents":[{"parts":[{"text":"OK"}]}]}')
if [ "$CODE" != "200" ]; then
  echo "⚠️ host key가 아직 한도 초과(HTTP $CODE). 태평양 자정(≈16:00 KST) 이후 다시 시도하세요."
  exit 1
fi
echo "OK (한도 사용 가능)"

echo "== 원격 에이전트 4개 기동 =="
(cd "$REPO/교통AI에이전트"  && AGENT_MODEL=$M AMBULANCE_DATA_DIR="$D" "$V/ambulance-교통AI에이전트/bin/python" __main__.py >"$LOG/traffic.log" 2>&1 &)
(cd "$REPO/병원AI에이전트" && HOSPITAL_PROFILE=configs/대전성모병원.env AGENT_MODEL=$M AMBULANCE_DATA_DIR="$D" "$V/ambulance-병원AI에이전트/bin/python" __main__.py >"$LOG/stmary.log" 2>&1 &)
(cd "$REPO/병원AI에이전트" && HOSPITAL_PROFILE=configs/대전선병원.env  AGENT_MODEL=$M AMBULANCE_DATA_DIR="$D" "$V/ambulance-병원AI에이전트/bin/python" __main__.py >"$LOG/sun.log" 2>&1 &)
(cd "$REPO/보험AI에이전트"  && AGENT_MODEL=$M AMBULANCE_DATA_DIR="$D" "$V/ambulance-보험AI에이전트/bin/python" __main__.py >"$LOG/insurance.log" 2>&1 &)

echo "== 준비 대기 =="
up=0
for _ in $(seq 1 40); do
  up=0; for p in 10002 10003 10004 10005; do curl -s -m 2 "http://localhost:$p/.well-known/agent-card.json" >/dev/null 2>&1 && up=$((up+1)); done
  [ "$up" -eq 4 ] && break; sleep 2
done
echo "servers up: $up/4"

run_one() {  # $1=input  $2=output  $3=label
  echo ""; echo "================= [$3] ================="
  ( cd "$REPO/host_adk" && AGENT_MODEL=$M PYTHONPATH="$REPO/host_adk" AMBULANCE_DATA_DIR="$D" \
      "$V/ambulance-host/bin/python" "$REPO/demo/scenario_runner.py" < "$1" ) 2>/dev/null | tee "$2"
}

run_one "$REPO/demo/scenario_ko.txt" "$REPO/demo/out_ko.txt" "한국어 / KOREAN"
run_one "$REPO/demo/scenario_en.txt" "$REPO/demo/out_en.txt" "영어 / ENGLISH"

echo ""; echo "== 서버 정리 =="
pkill -f "ambulance-.*/bin/python __main__.py" 2>/dev/null
echo "완료. 결과 저장: demo/out_ko.txt, demo/out_en.txt"
