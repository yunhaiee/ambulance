# Setup

## 1. Python environments

Each service has its own `pyproject.toml` and is run with [uv](https://docs.astral.sh/uv/).
Keep the virtual environments outside the repo (an iCloud-synced folder makes imports stall):

```bash
for svc in traffic hospital insurance; do
  (cd ${svc}_agent && UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-$svc uv sync)
done
(cd host_adk && UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-host uv sync)
npm install   # the traffic agent's Kakao MCP server (traffic_agent/server.js)
```

## 2. Keys and tokens

Copy each service's `.env.example` to `.env` and fill it in (`host_adk/`, `traffic_agent/`,
`hospital_agent/`, `insurance_agent/`):

- `GOOGLE_API_KEY`: a Gemini API key (all four)
- `A2A_AUTH_TOKEN`: generate one with `openssl rand -hex 32` and use **the same value everywhere**.
  Without it the agents run unauthenticated and warn at startup.
- `KAKAO_REST_API_KEY`: traffic agent only
- `SLACK_BOT_TOKEN`: traffic, hospital and insurance agents. The bot needs the `chat:write`
  scope and must be invited to each reporting channel.
- `NOTION_API_KEY`: hospital agent only

Optional: to give one hospital instance its own Gemini quota, put its key in
`hospital_agent/.env.<HOSPITAL_AGENT_NAME>` (gitignored, loaded last).

## 3. Hospital profiles

Each hospital is a profile in `hospital_agent/configs/`. Copy an `.env.example` there to
`<name>.env` and set:

- `HOSPITAL_AGENT_NAME`, `HOSPITAL_NAME`, `PORT`
- `HOSPITAL_LOCAL_NAME`: the hospital's official name exactly as Kakao Maps lists it. The host
  uses it to match ER search results to this agent.
- `NOTION_DEPARTMENT_DB_ID`, `NOTION_DOCTOR_DB_ID`, `NOTION_SPACE_DB_ID`
- `HOSPITAL_SLACK_CHANNEL_ID`

Adding a hospital is one profile plus its URL in the host's `REMOTE_AGENT_URLS`; no code changes.

### Notion schema

The acceptance rule lives in code (`hospital_agent/capacity.py`):
**operating rooms ≥ 1 AND beds ≥ 1 AND at least one surgeon not in surgery**.

| Database | Properties |
|---|---|
| Departments | `department_name` (title), `department_number` (number), `phone` (text) |
| Doctors | `doctor_name` (title), `doctor_number`, `department_number`, `in_surgery` (checkbox), `phone_number` |
| Facilities | `facility_name` (title, e.g. `operating_rooms`, `beds`), `available` (number) |

## 4. Run (five terminals)

```bash
# traffic (port 10002)
cd traffic_agent && UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-traffic uv run python __main__.py

# Daejeon St. Mary's Hospital (port 10003)
cd hospital_agent && HOSPITAL_PROFILE=configs/daejeon_st_marys.env UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-hospital uv run python __main__.py

# Daejeon Sun Hospital (port 10004)
cd hospital_agent && HOSPITAL_PROFILE=configs/daejeon_sun.env UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-hospital uv run python __main__.py

# insurance (port 10005)
cd insurance_agent && UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-insurance uv run python __main__.py

# host, after the four above are up
cd host_adk && UV_PROJECT_ENVIRONMENT=~/.venvs/ambulance-host uv run adk web
```

Or run the whole scripted scenario end to end: `bash demo/run_demo.sh`.

## 5. After a run

- `~/.ambulance/dispatch_audit.jsonl` has per-step timings for every dispatch. It contains
  patient information, so don't share it.
- Check that the Slack channels received their messages.
