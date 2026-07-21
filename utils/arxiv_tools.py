"""arXiv tools for the research agent.

Uses the `arxiv` package — no API key. A single module-level Client enforces
arXiv's politeness delay (>=3s between requests) across every call, so the
subagent can fire off several searches without tripping the API's rate limit.

arXiv's export API throttles by IP, not per-client — during a workshop, many
Colab notebooks sharing Google's egress IPs can trip its 429/503 limits at
once even though each individual client is well-behaved. `_with_retries` adds
its own backoff on top of the `arxiv` package's fixed retry delay, and
`search_arxiv` caps `max_results` so one call can't request an oversized page
that's slower and more likely to land inside a rate-limited window.
"""

import time

import arxiv
from langchain.tools import tool

_client = arxiv.Client(delay_seconds=3.0, num_retries=3)
_MAX_SEARCH_RESULTS = 10


def _authors(result, limit=6):
    names = [a.name for a in result.authors]
    head = ", ".join(names[:limit])
    return head + (" et al." if len(names) > limit else "")


def _with_retries(fn, attempts=4, base_delay=5.0):
    """Retry on arXiv's transient 429/503s with growing backoff.

    The `arxiv` package's own `num_retries` only waits `delay_seconds` between
    tries, which isn't enough headroom when arXiv is rate-limiting a whole
    shared IP range (e.g. Colab during a live workshop).
    """
    for attempt in range(attempts):
        try:
            return fn()
        except arxiv.HTTPError as e:
            if e.status not in (429, 503) or attempt == attempts - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))
    raise AssertionError("unreachable")  # loop always returns or raises above


@tool(description=(
    "Search arXiv for papers matching a query. Returns compact metadata (id, "
    "title, authors, year, categories, trimmed abstract) — enough to decide "
    "what's worth filing, without flooding context."
))
def search_arxiv(query: str, max_results: int = 5) -> str:
    max_results = min(max_results, _MAX_SEARCH_RESULTS)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    try:
        results = _with_retries(lambda: list(_client.results(search)))
    except arxiv.HTTPError as e:
        return (
            f"arXiv is temporarily rate-limiting requests (HTTP {e.status}). "
            "This is common when many people hit the API at once during a "
            "workshop — wait a bit and try the search again."
        )
    blocks = []
    for r in results:
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


@tool(description=(
    "Fetch full metadata for a single arXiv paper by id. Use this once you've "
    "picked a paper from a search and need the details a citation requires — "
    "full author list, DOI, journal reference, PDF link."
))
def get_arxiv_paper(arxiv_id: str) -> str:
    try:
        results = _with_retries(lambda: list(_client.results(arxiv.Search(id_list=[arxiv_id]))))
    except arxiv.HTTPError as e:
        return (
            f"arXiv is temporarily rate-limiting requests (HTTP {e.status}). "
            "This is common when many people hit the API at once during a "
            "workshop — wait a bit and try again."
        )
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
