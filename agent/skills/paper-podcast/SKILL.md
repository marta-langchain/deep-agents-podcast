---
name: paper-podcast
description: Generate the next podcast EPISODE from the library and log it for continuity. Use when asked for a podcast, an audio overview, a briefing, or "the next episode".
---

# Paper Podcast Episode Skill

Turn the library into a **numbered podcast episode** that NotebookLM can read
aloud, keeping continuity across episodes via memory. You write the *material*;
NotebookLM produces the two-host audio.

## Continuity — do this first
1. Read `/memories/podcast_log.md`. If it doesn't exist, this is **Episode 1**.
2. Each logged episode lists the papers it covered. Compare against
   `/memories/library/` and find the papers **not yet covered** — those are this
   episode's focus. If every paper has already been covered, say so and stop
   (don't pad with invented content).
3. This episode's number = highest logged episode number + 1.

## Write the briefing → `/briefing.md`
- Title line: `# Episode <N>`.
- If N > 1, open with a short recap (2-3 sentences) of where the last episode left off.
- Cover the new papers in plain prose — what it found, the method in
  listener-friendly terms, why it matters, and how it connects to the rest of the
  library. Group by topic and give each paper its own full paragraph or two, with
  authors + year inline. Aim for ~700-1200 words.

## Record the episode → `/memories/podcast_log.md`
Append (do not overwrite) this block so the next episode knows what's covered:

```
## Episode <N>
- papers: <comma-separated arXiv ids covered>
- topics: <topic folders touched>
- summary: <one line>
```

This log lives in long-term memory, so continuity survives across conversations.
