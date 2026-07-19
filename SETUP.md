# Setup

Two ways to run the Deep Agents research-podcast workshop. Pick whichever fits.

| Path | Best for | Install time | You need |
|---|---|---|---|
| [A. Google Colab](#a-google-colab-zero-install) | Just running the notebook, nothing to install | ~1 min | A Google account and 2 free API keys |
| [B. Your own machine](#b-your-own-machine-uv) | Running the live agent (`langgraph dev`), editing code, working offline | ~3 min | git, Python 3.11–3.13, [uv](https://docs.astral.sh/uv/) |

Both paths use the same two free API keys. Get them first: [Get your API keys](#get-your-api-keys).

---

## Get your API keys

You need these for either path. Both have a free tier and neither asks for a card.

| Key | Required? | Where to get it | What it's for |
|---|---|---|---|
| `GOOGLE_API_KEY` | Required | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | The Gemini model that powers the agent (free tier) |
| `TAVILY_API_KEY` | Required | [tavily.com](https://tavily.com) | Web search for author/lab enrichment |
| `LANGSMITH_API_KEY` | Optional (recommended) | [smith.langchain.com](https://smith.langchain.com) | Traces every tool call and interrupt, so runs are visible |

> **Workshop perk: $50 in free LangSmith credits.** Instructions for claiming it will be shared during the workshop. Set `LANGSMITH_TRACING=true` in your environment.

> **Free-tier note.** The default model is `gemini-flash-lite-latest`, picked for the most generous free budget (about 15 req/min and 1000/day per project). A deep agent makes a lot of calls, so a `429 RESOURCE_EXHAUSTED` just means you hit the per-project cap. Wait a few seconds and re-run, or lower `max_results`. Live limits are at [aistudio.google.com/rate-limit](https://aistudio.google.com/rate-limit).

---

## A. Google Colab (zero install)

Everything runs in the browser, so there's nothing to install.

**1. Open the notebook in Colab**

[Open `deep_agents_workshop_colab.ipynb` in Colab](https://colab.research.google.com/github/marta-langchain/deep-agents-podcast/blob/main/deep_agents_workshop_colab.ipynb)

**2. (Recommended) Add your keys to Colab Secrets**

Click the key icon in the left sidebar and add two secrets named exactly `GOOGLE_API_KEY` and `TAVILY_API_KEY`, using the values from above. Turn on Notebook access for each. The setup cell reads them automatically. You can add `LANGSMITH_API_KEY` the same way to get trace links under each run.

**3. Run the first setup cell**

The top cell, "Run this first in Colab", handles the rest: it clones the repo, runs `pip install -e .` to install the workshop, and reads your keys from Secrets (or prompts you to paste them if you skipped step 2). A "Colab setup complete" message means it worked.

**4. Run the rest top to bottom**

Work through Parts 0–8 in order. Each `agent.invoke(...)` call takes 15–40 seconds, which is expected.

> **Note.** Colab covers the notebook and the NotebookLM podcast steps out of the box. You can also run the live agent server from Colab's built-in terminal: open a terminal, `cd deep-agents-podcast`, and run `langgraph dev` (see [Option 2](#run-it) below for what it does).

---

## B. Your own machine (uv)

The full setup: the notebook, the live agent server, and the code to edit.

**Prerequisites**

- git
- Python 3.11–3.13
- [uv](https://docs.astral.sh/uv/getting-started/installation/), the package manager this project uses

**1. Clone the repo**

```zsh
git clone https://github.com/marta-langchain/deep-agents-podcast.git
cd deep-agents-podcast
```

**2. Install dependencies**

```zsh
uv sync
```

**3. Configure your environment**

```zsh
cp .env.example .env
```

Open `.env` and fill in `GOOGLE_API_KEY` and `TAVILY_API_KEY` at minimum (see [Get your API keys](#get-your-api-keys)). `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true` are optional but recommended.

**4. Sanity-check the setup**

```zsh
uv run python env_utils.py
```

This checks that you're on a supported Python, inside the project venv, and that the required packages import. Fix anything it flags before continuing.

> **Seeing 403 Forbidden later?** Your shell may be exporting a stale `GOOGLE_API_KEY`, `GEMINI_API_KEY`, or `GOOGLE_GEMINI_BASE_URL`. `unset` them so `.env` is the only source.

### Run it

**Option 1: walk through the notebook**

```zsh
uv run jupyter lab
```

Open `deep_agents_workshop.ipynb` and run top to bottom.

**Option 2: run the agent as a live app**

```zsh
uv run langgraph dev
```

This serves the API at `http://127.0.0.1:2024`. Open the agent in Studio using the Studio UI link printed in your terminal. `langgraph dev` supplies the checkpointer and store automatically, so long-term memory and human-in-the-loop approvals work without extra setup.

### Switching model providers (optional)

The default is Gemini via Google AI Studio. To switch, edit `utils/models.py` (it has commented blocks for OpenAI and Anthropic) and install the matching extra:

```zsh
uv sync --extra openai      # then set OPENAI_API_KEY in .env
uv sync --extra anthropic   # then set ANTHROPIC_API_KEY in .env
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `429 RESOURCE_EXHAUSTED` | Free-tier rate limit. Wait a few seconds and re-run, or lower `max_results`. |
| `403 Forbidden` (local) | Bad or overridden `GOOGLE_API_KEY`. `unset` any shell exports so `.env` wins. |
| Can't reach the server (local) | Confirm `langgraph dev` is up on port 2024. The LangSmith Studio link is an alternate front end. |
| Colab setup cell prompts for keys every run | Add them to Colab Secrets with Notebook access enabled. |
| Imports fail or wrong Python (local) | Run through uv: `uv run python env_utils.py`, then re-run `uv sync`. |

Once you're set up, head back to the [README](README.md) for what to build.
