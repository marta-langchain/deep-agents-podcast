"""arXiv tools for the research agent.

Uses the `arxiv` package — no API key. A single module-level Client enforces
arXiv's politeness delay (>=3s between requests) across every call, so the
subagent can fire off several searches without tripping the API's rate limit.
"""

import arxiv
from langchain.tools import tool

_client = arxiv.Client(delay_seconds=3.0, num_retries=3)


def _authors(result, limit=6):
    names = [a.name for a in result.authors]
    head = ", ".join(names[:limit])
    return head + (" et al." if len(names) > limit else "")


@tool(parse_docstring=True)
def search_arxiv(query: str, max_results: int = 5) -> str:
    """Search arXiv for papers matching a query.

    Returns compact metadata (id, title, authors, year, categories, trimmed
    abstract) — enough to decide what's worth filing, without flooding context.

    Args:
        query: Search terms, e.g. "epigenetic aging clock biological age".
        max_results: How many papers to return. Keep it small to save quota.
    """
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    blocks = []
    for r in _client.results(search):
        blocks.append(
            f"### {r.title}\n"
            f"- id: {r.get_short_id()}\n"
            f"- authors: {_authors(r)}\n"
            f"- published: {r.published.date()}\n"
            f"- categories: {', '.join(r.categories)}\n"
            f"- abstract: {r.summary.strip()[:1000]}"
        )
    if not blocks:
        return f"No arXiv results for {query!r}."
    return f"Found {len(blocks)} result(s) for {query!r}:\n\n" + "\n\n".join(blocks)


@tool(parse_docstring=True)
def get_arxiv_paper(arxiv_id: str) -> str:
    """Fetch full metadata for a single arXiv paper by id.

    Use this once you've picked a paper from a search and need the details a
    citation requires — full author list, DOI, journal reference, PDF link.

    Args:
        arxiv_id: Short arXiv id, e.g. "2302.12345" or "2302.12345v2".
    """
    results = list(_client.results(arxiv.Search(id_list=[arxiv_id])))
    if not results:
        return f"No arXiv paper found with id {arxiv_id!r}."
    r = results[0]
    lines = [
        f"# {r.title}",
        f"- id: {r.get_short_id()}",
        f"- authors: {', '.join(a.name for a in r.authors)}",
        f"- published: {r.published.date()}",
        f"- updated: {r.updated.date()}",
        f"- primary_category: {r.primary_category}",
        f"- categories: {', '.join(r.categories)}",
        f"- pdf_url: {r.pdf_url}",
    ]
    if r.doi:
        lines.append(f"- doi: {r.doi}")
    if r.journal_ref:
        lines.append(f"- journal_ref: {r.journal_ref}")
    if r.comment:
        lines.append(f"- comment: {r.comment}")
    lines.append(f"\nabstract:\n{r.summary.strip()}")
    return "\n".join(lines)
