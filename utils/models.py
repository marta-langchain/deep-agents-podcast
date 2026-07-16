"""Model configuration.

Default: Google Gemini via AI Studio (free tier) — ``gemini-flash-lite-latest``
for both the main agent and the research subagent. It's the flash-lite tier (the
most generous free-tier request budget: ~15 requests/min, ~1000/day per project),
which matters because a deep agent is chatty — planning + tool calls + subagent
fan-out all draw on the same quota. We use the ``-latest`` alias on purpose:
Google retires pinned ids (e.g. ``gemini-2.5-flash-lite``) for new keys, and the
alias always resolves to the current model. Live limits:
https://aistudio.google.com/rate-limit.

Requires GOOGLE_API_KEY in .env (free key: https://aistudio.google.com/apikey).

To swap providers, install the matching extra (see pyproject.toml), then comment
out the Gemini block and uncomment one of the alternatives below.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the repo root (utils/ -> one level up) so the model loads no
# matter which directory the notebook or server is launched from. override=True
# makes .env win over anything already set in the shell.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# The Google client also honours GEMINI_API_KEY; drop it so GOOGLE_API_KEY
# (from .env) is the key that's used.
os.environ.pop("GEMINI_API_KEY", None)

from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI

# A deep agent is bursty (planning + tool calls + subagent), and the free tier
# is ~15 requests/min per project. One shared limiter across both models keeps
# us under that ceiling so runs don't die on 429 RESOURCE_EXHAUSTED. Raise
# requests_per_second if your project has a higher quota.
_limiter = InMemoryRateLimiter(requests_per_second=0.2, check_every_n_seconds=0.1, max_bucket_size=3)

# ---- Default: Gemini (Google AI Studio, free tier) ------------------------
# disable_streaming=True forces the non-streaming `generateContent` endpoint
# instead of `streamGenerateContent`.
model = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest", temperature=0, disable_streaming=True, rate_limiter=_limiter)
sub_agent_model = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest", temperature=0, disable_streaming=True, rate_limiter=_limiter)

# For higher-quality steps, bump to the full flash tier (tighter free RPD):
# model = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, rate_limiter=_limiter)

# ---- OpenAI ---------------------------------------------------------------
# uv sync --extra openai   +   OPENAI_API_KEY in .env
# from langchain.chat_models import init_chat_model
# model = init_chat_model("openai:gpt-5.4")
# sub_agent_model = init_chat_model("openai:gpt-5.4-mini")

# ---- Anthropic ------------------------------------------------------------
# uv sync --extra anthropic   +   ANTHROPIC_API_KEY in .env
# from langchain.chat_models import init_chat_model
# model = init_chat_model("anthropic:claude-haiku-4-5")
# sub_agent_model = init_chat_model("anthropic:claude-haiku-4-5")
