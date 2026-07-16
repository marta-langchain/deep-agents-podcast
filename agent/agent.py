"""
A computational-longevity research agent (standalone graph).

Production-shaped port of the final notebook agent:
- AGENTS.md is read from disk and always loaded into the system prompt
- Skills under ./skills/ are loaded on demand (progressive disclosure)
- /memories/* persists across threads via StoreBackend
- Every other file lives on disk under agent/ (sandboxed via virtual_mode=True)
- Writes are gated by human-in-the-loop, so nothing enters the library
  without approval — this is what surfaces the approve/edit/reject UI in
  agentchat and LangSmith Studio.

This module exports `agent`, wired into langgraph.json so it runs under
`langgraph dev` and LangSmith Deployments. The dev server supplies the
checkpointer and store automatically, so we do NOT construct our own here.
"""

import sys
from pathlib import Path

# utils/ is a sibling of this agent/ folder; make it importable no matter where
# the process is launched from.
AGENT_DIR = Path(__file__).parent
REPO_ROOT = AGENT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend

from utils.arxiv_tools import get_arxiv_paper, search_arxiv
from utils.memory import MEMORY_NAMESPACE
from utils.models import model, sub_agent_model
from utils.search import tavily_search

TOOLS = [search_arxiv, get_arxiv_paper, tavily_search]


# ---- Subagents ------------------------------------------------------------
# Two specialists, each in an isolated context, so the main agent only sees
# their final answers: breadth (scout) and depth (analyst).
search_scout = {
    "name": "search-scout",
    "description": "Scout arXiv for a topic and return a ranked shortlist of candidate papers. Breadth, not depth.",
    "system_prompt": (
        "You are a literature scout for a computational-longevity library.\n"
        "- Run up to 3 arXiv searches for the requested topic.\n"
        "- Return a ranked shortlist of 3-5 papers: arXiv id, title, and one line\n"
        "  on why each is relevant. Dedupe.\n"
        "- Do not deep-read or file anything — that's the analyst's job."
    ),
    "model": sub_agent_model,
}

paper_analyst = {
    "name": "paper-analyst",
    "description": "Deep-read a single arXiv paper and propose how to file it. Give it one paper at a time.",
    "system_prompt": (
        "You analyze one paper for a computational-longevity research library.\n"
        "- Call get_arxiv_paper if you need the full metadata.\n"
        "- Return: a 2-3 sentence summary of the contribution, a suggested\n"
        "  topic folder in kebab-case (e.g. aging-clocks, senescence,\n"
        "  caloric-restriction, biomarkers-of-aging), and 3-6 lowercase tags.\n"
        "- Be concise. Do not file anything yourself; just report."
    ),
    "model": sub_agent_model,
}


# ---- Backend --------------------------------------------------------------
# Default: real disk under agent/ (sandboxed). AGENTS.md and skills/* load from
# here. Route: /memories/* -> StoreBackend (the durable, cross-thread library).
# StoreBackend takes no explicit store: it uses the one the dev server injects.
fs_backend = FilesystemBackend(root_dir=str(AGENT_DIR), virtual_mode=True)
backend = CompositeBackend(
    default=fs_backend,
    routes={
        "/memories/": StoreBackend(namespace=lambda rt: MEMORY_NAMESPACE),
    },
)


# ---- Agent ----------------------------------------------------------------
agent = create_deep_agent(
    model=model,
    tools=TOOLS,
    subagents=[search_scout, paper_analyst],
    system_prompt="You are a computational-longevity research agent that curates a paper library and turns it into a podcast.",
    memory=["./AGENTS.md"],  # always loaded into the system prompt
    skills=["./skills/"],  # loaded on demand via progressive disclosure
    backend=backend,
    # Gate every write so a human approves what enters the library.
    interrupt_on={
        "write_file": {"allowed_decisions": ["approve", "edit", "reject"]},
        "edit_file": {"allowed_decisions": ["approve", "edit", "reject"]},
    },
)
