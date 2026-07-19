"""Web search (Tavily) — shared by the notebook and the standalone agent.

arXiv metadata tells you what a paper says; the web tells you what happened
around it — the author's lab, later coverage, whether a preprint was eventually
published. The client is created lazily so importing this module doesn't require
a Tavily key until the tool is actually called.
"""

from langchain.tools import tool
from tavily import TavilyClient

@tool(description="Search the web for information on a given query.")
def tavily_search(query: str) -> str:
    client = TavilyClient()
    results = client.search(query, max_results=3)

    # Format the results into a readable string
    chunks = [
        f"## {r.get('title', 'Untitled')}\n**URL:** {r.get('url', '')}\n\n{r.get('content', '')}\n\n---\n"
        for r in results.get("results", [])
    ]

    return f"Found {len(chunks)} result(s) for '{query}':\n\n{''.join(chunks)}"