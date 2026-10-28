"""Code-based output-language detection for worker agents.

Static prompt rules don't reliably control the reply language, so we detect the
incoming request's language in code and prepend a dominant directive.
"""

import re

from google.adk.agents.readonly_context import ReadonlyContext

_HANGUL = re.compile(r"[\uac00-\ud7a3]")
_LATIN = re.compile(r"[A-Za-z]")

_EN_DIRECTIVE = (
    "OUTPUT LANGUAGE: ENGLISH. Write all human-readable output (and any Slack "
    "message text) in English.\n\n"
)
_KO_DIRECTIVE = (
    "OUTPUT LANGUAGE: KOREAN. The incoming request is in Korean; write all "
    "human-readable output (and any Slack message text) in Korean.\n\n"
)


def _detect_lang(context: ReadonlyContext) -> str:
    # Korean if Hangul dominates (not mere presence), so an English request that
    # contains a Korean place name is still detected as English.
    text = ""
    user_content = getattr(context, "user_content", None)
    if user_content is not None:
        for part in getattr(user_content, "parts", None) or []:
            if getattr(part, "text", None):
                text += part.text
    return "ko" if len(_HANGUL.findall(text)) > len(_LATIN.findall(text)) else "en"


def make_instruction(base_prompt: str):
    """Return an ADK instruction callable that prepends the language directive."""

    def _instruction(context: ReadonlyContext) -> str:
        directive = _EN_DIRECTIVE if _detect_lang(context) == "en" else _KO_DIRECTIVE
        return directive + base_prompt

    return _instruction
