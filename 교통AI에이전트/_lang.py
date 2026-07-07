"""Code-based output-language detection for worker agents.

Static prompt rules don't reliably beat a long Korean prompt, so we detect the
incoming request's language in code and prepend a dominant directive.
"""

import re

from google.adk.agents.readonly_context import ReadonlyContext

_HANGUL = re.compile(r"[가-힣]")
_LATIN = re.compile(r"[A-Za-z]")

_EN_DIRECTIVE = (
    "OUTPUT LANGUAGE: ENGLISH ONLY. The incoming request is in English; write ALL "
    "human-readable output (and any Slack message text) in English. The prompt below "
    "is written in Korean for reference only — do NOT reply in Korean; translate any "
    "Korean labels into English.\n\n"
)
_KO_DIRECTIVE = "출력 언어: 한국어. 사람이 읽는 모든 출력(및 Slack 메시지)을 한국어로 작성하세요.\n\n"


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
