"""Web search (Tavily) — shared by the notebook and the standalone agent.

arXiv metadata tells you what a paper says; the web tells you what happened
around it — the author's lab, later coverage, whether a preprint was eventually
published. The client is created lazily so importing this module doesn't require
a Tavily key until the tool is actually called.
"""

from langchain.tools import tool
from tavily import TavilyClient

_tavily = None


def _client():
    global _tavily
    if _tavily is None:
        _tavily = TavilyClient()  # reads TAVILY_API_KEY from the environment
    return _tavily


@tool(parse_docstring=True)
def tavily_search(query: str) -> str:
    """Search the web for information on a given query.

    Args:
        query: Search query to execute.
    """
    results = _client().search(query, max_results=3, topic="general")
    chunks = [
        f"## {r['title']}\n**URL:** {r['url']}\n\n{r.get('content', '')}\n\n---\n"
        for r in results.get("results", [])
    ]
    return f"Found {len(chunks)} result(s) for '{query}':\n\n{''.join(chunks)}"
