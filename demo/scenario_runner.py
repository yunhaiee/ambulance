"""Run one emergency-dispatch scenario through the host and print the final response.

Reads the patient text from stdin. Run via demo/run_both.sh (which boots the
remote agents first). Requires PYTHONPATH=<repo>/host_adk.
"""

import asyncio
import sys
import time
import uuid

from 구급AI에이전트.agent import HostAgent, _remote_agent_urls


async def main() -> None:
    patient = sys.stdin.read().strip()
    t0 = time.monotonic()
    host = await HostAgent.create(_remote_agent_urls())
    final = None
    async for event in host.stream(patient, f"demo-{uuid.uuid4().hex[:8]}"):
        if event.get("is_task_complete"):
            final = event.get("content")
    print(final or "(no final response)")
    print(f"\n[elapsed {time.monotonic() - t0:.1f}s]")


asyncio.run(main())
