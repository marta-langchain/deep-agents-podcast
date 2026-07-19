# A personalized research podcast, powered by deep agents

An agent that reads the latest research, files the papers you approve, and
remembers them across sessions — then turns your growing library into a **podcast
series** where each episode covers only what's new. A hands-on tour of
[LangChain Deep Agents](https://docs.langchain.com/oss/python/deepagents/) with
two ideas in the spotlight — **long-term memory** and **human-in-the-loop** — and
memory *visualizers* at every step so you can see exactly what the agent stores
and recalls. Shown on computational longevity (aging clocks, senescence, caloric
restriction, biological-age ML), pulling from arXiv.

Ships as an **interactive notebook** (`deep_agents_workshop.ipynb`, 9 parts) and a
**standalone agent** (`agent/agent.py`) you can drive from a chat UI.

Runs on the **free tier** of Google's Gemini API.

## What you'll learn

- A basic Deep Agent with built-in filesystem + planning tools
- Custom tools: arXiv search (`utils/arxiv_tools.py`) + web search
- Backends — `StateBackend`, `FilesystemBackend`, `StoreBackend`, `CompositeBackend`
- Subagents for context isolation (`search-scout` + `paper-analyst`)
- Human-in-the-loop approval before anything enters the library
- Long-term memory with `/memories/*` routed to a SQLite-backed store
- Inspecting that memory directly (`utils/viz.py`)
- `AGENTS.md` identity + on-demand `SKILL.md` capabilities

## Setup

**See [SETUP.md](SETUP.md) for the full guide** — two paths:

- **Google Colab** (zero install) — open the notebook, add two free keys, run the setup cell.
- **Your own machine** (uv) — clone, `uv sync`, fill `.env`, and you also get the live agent server.

The short version for local:

```zsh
uv sync                          # install (needs uv + Python 3.11–3.13)
cp .env.example .env             # then fill in GOOGLE_API_KEY + TAVILY_API_KEY
uv run python env_utils.py       # sanity-check
```

Get free keys at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) (Gemini) and
[tavily.com](https://tavily.com) (web search); optional `LANGSMITH_API_KEY` +
`LANGSMITH_TRACING=true` for trace observability.

> **Free-tier note.** The default model is `gemini-flash-lite-latest`, chosen for the
> most generous free request budget (~15 req/min, ~1000/day per project). A deep
> agent is chatty, so if you hit a `429 RESOURCE_EXHAUSTED`, that's the per-project
> cap — slow down, lower `max_results`, or check your live limits at
> [aistudio.google.com/rate-limit](https://aistudio.google.com/rate-limit).

## Run it

### A. Walk through the notebook

```zsh
uv run jupyter lab
```

Open `deep_agents_workshop.ipynb` and run top to bottom. Part 6 (long-term memory)
writes a real `library_memory.db` — restart the kernel and re-run the "It's really
on disk" cell to watch the library survive.

### B. Run the agent as a live app

`agent/agent.py` packages the agent as a graph (`langgraph.json` registers it
under the id **`agent`**). Start the local server:

```zsh
uv run langgraph dev
```

It serves the API at `http://127.0.0.1:2024`. Open the agent in Studio by clicking the **Studio UI link** displayed in your terminal.

Try: *"Find 3 papers on epigenetic aging clocks and file the best one."* You'll get
an **approve / edit / reject** prompt before anything is filed; approve it, then
start a new thread and ask *"what's in my library?"* — it's still there.
`langgraph dev` supplies the checkpointer + store automatically.

> **Troubleshooting**
> - **403 Forbidden** in the server logs → your `GOOGLE_API_KEY` in `.env` must be a valid
>   Google AI Studio key. If your shell also exports `GOOGLE_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_GEMINI_BASE_URL`
>   unset them so `.env` is the only source.
> - **Can't reach the server** → confirm it's up on port 2024. The [LangSmith Studio](https://smith.langchain.com)
>   link printed on startup is an alternative front end for the same server.

### C. Turn your library into a podcast (zero-code)

Part 8 treats the podcast as a **series**. The agent writes an episode
briefing to `episode_<N>_briefing.md` and logs it to `/memories/podcast_log.md`, so
each new episode covers only papers added since the last one. Turn a briefing
into two-host audio with [NotebookLM](https://notebooklm.google.com), no code:

1. New notebook → **Add source** → upload `episode_1_briefing.md`.
2. **Studio** → **Audio Overview → Generate** (use **Customize** to focus or
   cap the length).
3. Play it, or download the audio from the **⋮** menu.

The deployed agent knows this too — ask it for *"the next episode"* (the
`paper-podcast` skill) and it picks up from the logged history.

## Where the interesting bits live

| File | What it is |
|---|---|
| `deep_agents_workshop.ipynb` | The 9-part workshop |
| `agent/agent.py` | Standalone agent graph (arXiv + Tavily, 2 subagents, HITL, memory) |
| `agent/AGENTS.md` | The agent's editable identity + filing rules |
| `agent/skills/` | On-demand skills (`bibtex-export`, `related-work`, `paper-podcast`) |
| `utils/memory.py` | Memory namespace + SQLite store helper |
| `utils/viz.py` | Memory visualizers (`show_memory`, `show_library`, `render_diff`, …) |
| `utils/models.py` | Model config (swap providers here) |

## Model providers

Default is Gemini via Google AI Studio (free tier). To switch, edit
`utils/models.py` (commented blocks for OpenAI and Anthropic are included) and
install the matching extra:

```zsh
uv sync --extra openai      # OpenAI
uv sync --extra anthropic   # Anthropic
```
