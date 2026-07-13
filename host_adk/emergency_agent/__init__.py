"""ASCII-named wrapper for adk web (ADK 2.x rejects non-ASCII app names).

The actual host agent lives in the 구급AI에이전트 package; this package just
re-exports its root_agent so the web UI can load it.
"""

from 구급AI에이전트.agent import root_agent  # noqa: F401
