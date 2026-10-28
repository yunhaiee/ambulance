#!/bin/bash
# Boot the four remote agents, run the demo scenario through the host, save the
# output, and stop the servers.
#
# Prereqs: a Gemini key in each agent's .env (host_adk/, traffic_agent/,
# hospital_agent/, insurance_agent/), venvs at ~/.venvs/ambulance-*, and free-tier
# quota left for the day. Usage:  bash demo/run_demo.sh
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
V="$HOME/.venvs"
M="gemini-2.5-flash"          # per-minute quota; better than flash-lite's 20/day for demos
D="$HOME/.ambulance/demo"
LOG="/tmp/ambulance-demo"
mkdir -p "$D" "$LOG"

echo "== Checking free-tier quota (host key) =="
KEY=$(grep '^GOOGLE_API_KEY=' "$REPO/host_adk/.env" | cut -d= -f2-)
CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$KEY" \
  -H "Content-Type: application/json" -d '{"contents":[{"parts":[{"text":"OK"}]}]}')
if [ "$CODE" != "200" ]; then
  echo "Host key is over quota (HTTP $CODE). Try again after midnight Pacific time."
  exit 1
fi
echo "OK"

echo "== Starting the four remote agents =="
(cd "$REPO/traffic_agent"   && AGENT_MODEL=$M AMBULANCE_DATA_DIR="$D" "$V/ambulance-traffic/bin/python" __main__.py >"$LOG/traffic.log" 2>&1 &)
(cd "$REPO/hospital_agent"  && HOSPITAL_PROFILE=configs/daejeon_st_marys.env AGENT_MODEL=$M AMBULANCE_DATA_DIR="$D" "$V/ambulance-hospital/bin/python" __main__.py >"$LOG/st_marys.log" 2>&1 &)
(cd "$REPO/hospital_agent"  && HOSPITAL_PROFILE=configs/daejeon_sun.env      AGENT_MODEL=$M AMBULANCE_DATA_DIR="$D" "$V/ambulance-hospital/bin/python" __main__.py >"$LOG/sun.log" 2>&1 &)
(cd "$REPO/insurance_agent" && AGENT_MODEL=$M AMBULANCE_DATA_DIR="$D" "$V/ambulance-insurance/bin/python" __main__.py >"$LOG/insurance.log" 2>&1 &)

echo "== Waiting for the agents =="
up=0
for _ in $(seq 1 40); do
  up=0; for p in 10002 10003 10004 10005; do curl -s -m 2 "http://localhost:$p/.well-known/agent-card.json" >/dev/null 2>&1 && up=$((up+1)); done
  [ "$up" -eq 4 ] && break; sleep 2
done
echo "agents up: $up/4"

echo ""; echo "================= scenario ================="
( cd "$REPO/host_adk" && AGENT_MODEL=$M PYTHONPATH="$REPO/host_adk" AMBULANCE_DATA_DIR="$D" \
    "$V/ambulance-host/bin/python" "$REPO/demo/scenario_runner.py" < "$REPO/demo/scenario.txt" ) 2>/dev/null | tee "$REPO/demo/out.txt"

echo ""; echo "== Stopping the agents =="
pkill -f "ambulance-.*/bin/python __main__.py" 2>/dev/null
echo "Done. Output saved to demo/out.txt"
