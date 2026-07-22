"""Memory visualizers — see exactly what the agent remembers.

The point of this workshop is that a Deep Agent's memory is *inspectable*. These
helpers render two very different things:

  * **thread state** — the ephemeral filesystem for ONE conversation
  * **the store** — the durable library, shared across every conversation

``show_memory`` reads the persistent store DIRECTLY (not through the agent), so
what you see is the ground truth on disk, independent of any thread. Everything
degrades to plain text when run outside a notebook.
"""

from __future__ import annotations

import difflib
import html
from pathlib import Path

from utils.memory import MEMORY_MOUNT, MEMORY_NAMESPACE

# GitHub-ish palette; reads well on Jupyter's default light background.
_BORDER = "#d0d7de"
_MUTED = "#57606a"
_BG = "#f6f8fa"
_GREEN = "#1a7f37"
_RED = "#cf222e"
_AMBER = "#9a6700"
_BLUE = "#0969da"


# ---- rendering plumbing ---------------------------------------------------
def _in_notebook() -> bool:
    try:
        from IPython import get_ipython

        return get_ipython() is not None
    except Exception:
        return False


def _display(html_str: str, text_str: str) -> None:
    if _in_notebook():
        from IPython.display import HTML, display

        display(HTML(html_str))
    else:
        print(text_str)


def _content(value) -> str:
    """Store content is a plain str (v2) but tolerate the legacy list[str]."""
    raw = value.get("content", "") if isinstance(value, dict) else value
    return "\n".join(raw) if isinstance(raw, list) else str(raw)


def _human_size(n: int) -> str:
    return f"{n} B" if n < 1024 else f"{n / 1024:.1f} KB"


def _short_ts(ts) -> str:
    if not ts:
        return ""
    return str(ts).replace("T", " ")[:19]


def _card(inner: str) -> str:
    return (
        f'<div style="border:1px solid {_BORDER};border-radius:8px;'
        f'padding:12px 14px;margin:8px 0;font-family:ui-monospace,SFMono-Regular,'
        f'Menlo,monospace;font-size:12.5px;line-height:1.5;background:white">{inner}</div>'
    )


# ---- store introspection --------------------------------------------------
def read_store(store, namespace=MEMORY_NAMESPACE, mount=MEMORY_MOUNT):
    """Read every file the store holds under ``namespace``, newest key last.

    Re-prepends the mount so keys read the way the agent sees them
    (store key ``/library/x.md`` -> ``/memories/library/x.md``).
    """
    items = store.search(namespace, limit=1000)
    out = []
    for it in items:
        value = getattr(it, "value", {}) or {}
        out.append(
            {
                "path": f"{mount}{it.key}",
                "content": _content(value),
                "created": value.get("created_at") or getattr(it, "created_at", ""),
                "modified": value.get("modified_at")
                or value.get("created_at")
                or getattr(it, "updated_at", ""),
            }
        )
    return sorted(out, key=lambda e: e["path"])


# ---- thread state (ephemeral) ---------------------------------------------
def show_state_files(result, title="Thread state — ephemeral, this conversation only"):
    """Show the in-thread virtual filesystem returned in an agent result."""
    files = (result or {}).get("files") or {}
    rows = sorted(files.items())

    if not rows:
        body_txt = "  (empty — nothing lives here once the thread ends)"
        body_html = f'<div style="color:{_MUTED}">(empty — nothing lives here once the thread ends)</div>'
    else:
        lines, htmls = [], []
        for path, data in rows:
            content = _content(data)
            lines.append(f"  {path}  ({_human_size(len(content))})")
            htmls.append(
                f'<div>📄 <b>{html.escape(path)}</b> '
                f'<span style="color:{_MUTED}">· {_human_size(len(content))}</span></div>'
            )
        body_txt = "\n".join(lines)
        body_html = "".join(htmls)

    text = f"{title}\n" + "-" * len(title) + f"\n{body_txt}\n"
    inner = f'<div style="color:{_MUTED};margin-bottom:6px">🧵 {html.escape(title)}</div>{body_html}'
    _display(_card(inner), text)


# ---- long-term memory (durable) -------------------------------------------
def show_memory(
    store,
    namespace=MEMORY_NAMESPACE,
    mount=MEMORY_MOUNT,
    preview=500,
    title="Long-term memory — durable, shared across every thread",
):
    """Read the persistent store directly and render each file with a preview."""
    entries = read_store(store, namespace, mount)
    backing = type(store).__name__

    if not entries:
        text = f"{title}\n(empty — the library has no files yet)\n"
        inner = (
            f'<div style="color:{_MUTED}">📚 {html.escape(title)}</div>'
            f'<div style="color:{_MUTED};margin-top:6px">(empty — the library has no files yet)</div>'
        )
        _display(_card(inner), text)
        return

    text_lines = [title, "=" * len(title), f"{mount}/  ({len(entries)} file(s), backed by {backing})"]
    html_files = []
    for e in entries:
        folder, _, name = e["path"].rpartition("/")
        meta = f"{_human_size(len(e['content']))}"
        if e["modified"]:
            meta += f" · modified {_short_ts(e['modified'])}"
        body = e["content"]
        clipped = body[:preview] + ("  …" if len(body) > preview else "")

        text_lines += [
            "",
            f"  {e['path']}   [{meta}]",
            *(f"    | {ln}" for ln in clipped.splitlines()),
        ]
        html_files.append(
            "<div style='margin-top:10px'>"
            f"<div><span style='color:{_MUTED}'>{html.escape(folder)}/</span>"
            f"<b>{html.escape(name)}</b></div>"
            f"<div style='color:{_MUTED};font-size:11.5px'>{meta}</div>"
            f"<pre style='margin:6px 0 0;padding:8px 10px;background:{_BG};"
            f"border-radius:6px;white-space:pre-wrap;overflow-x:auto'>"
            f"{html.escape(clipped)}</pre></div>"
        )

    header = (
        f"<div style='color:{_MUTED}'>📚 {html.escape(title)}</div>"
        f"<div style='margin-top:4px'><b>{html.escape(mount)}/</b> "
        f"<span style='color:{_MUTED}'>· {len(entries)} file(s) · backed by {backing}</span></div>"
    )
    _display(_card(header + "".join(html_files)), "\n".join(text_lines) + "\n")


def show_library(store, namespace=MEMORY_NAMESPACE, mount=MEMORY_MOUNT):
    """A 'shelf' view of the library: each topic file -> its filed entries.

    Entries are counted as blank-line-separated blocks, so it works whether the
    agent files papers as BibTeX records or markdown bullets.
    """
    entries = [e for e in read_store(store, namespace, mount) if "/library/" in e["path"]]

    if not entries:
        _display(
            _card(f"<div style='color:{_MUTED}'>📚 The shelf is empty.</div>"),
            "The shelf is empty.\n",
        )
        return

    text_lines = ["Library shelf", "=" * len("Library shelf")]
    shelves = []
    for e in entries:
        topic = e["path"].rpartition("/library/")[2].removesuffix(".md")
        blocks = [b.strip() for b in e["content"].split("\n\n") if b.strip()]
        titles = [b.splitlines()[0].lstrip("#-* ").strip()[:80] for b in blocks]

        text_lines.append(f"\n  📁 {topic}  ({len(blocks)} entr{'y' if len(blocks) == 1 else 'ies'})")
        text_lines += [f"     • {t}" for t in titles]

        items = "".join(f"<li>{html.escape(t)}</li>" for t in titles)
        shelves.append(
            f"<div style='margin-top:8px'><b>📁 {html.escape(topic)}</b>"
            f"<span style='color:{_MUTED}'> · {len(blocks)} "
            f"entr{'y' if len(blocks) == 1 else 'ies'}</span>"
            f"<ul style='margin:4px 0 0 18px;padding:0'>{items}</ul></div>"
        )

    _display(_card("".join(shelves)), "\n".join(text_lines) + "\n")


# ---- diffing memory across an operation -----------------------------------
def snapshot(store, namespace=MEMORY_NAMESPACE, mount=MEMORY_MOUNT):
    """Freeze the current store contents as {path: content} for diffing."""
    return {e["path"]: e["content"] for e in read_store(store, namespace, mount)}


def render_diff(before: dict, after: dict, title="What changed in memory"):
    """Show added / modified / removed files between two snapshots."""
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    modified = sorted(k for k in before.keys() & after.keys() if before[k] != after[k])

    if not (added or removed or modified):
        _display(
            _card(f"<div style='color:{_MUTED}'>🟰 {html.escape(title)}: no change.</div>"),
            f"{title}: no change.\n",
        )
        return

    text_lines = [title, "=" * len(title)]
    html_rows = []

    def block(label, color, path, detail_txt, detail_html):
        text_lines.append(f"\n  {label} {path}")
        if detail_txt:
            text_lines.extend(f"      {ln}" for ln in detail_txt)
        rows = (
            f"<pre style='margin:4px 0 0;padding:6px 10px;background:{_BG};"
            f"border-radius:6px;white-space:pre-wrap'>{detail_html}</pre>"
            if detail_html
            else ""
        )
        html_rows.append(
            f"<div style='border-left:3px solid {color};padding-left:10px;margin:8px 0'>"
            f"<span style='color:{color}'><b>{label}</b></span> "
            f"<code>{html.escape(path)}</code>{rows}</div>"
        )

    for p in added:
        preview = after[p].splitlines()[:6]
        block("＋ added", _GREEN, p, preview, html.escape("\n".join(preview)))
    for p in modified:
        diff = [
            ln
            for ln in difflib.unified_diff(
                before[p].splitlines(), after[p].splitlines(), lineterm="", n=1
            )
        ][2:]  # drop the +++/--- header
        colored = []
        for ln in diff:
            c = _GREEN if ln.startswith("+") else _RED if ln.startswith("-") else _MUTED
            colored.append(f"<span style='color:{c}'>{html.escape(ln)}</span>")
        block("~ modified", _AMBER, p, diff, "\n".join(colored))
    for p in removed:
        block("－ removed", _RED, p, [], "")

    _display(_card(f"<div style='color:{_MUTED};margin-bottom:4px'>🔎 {html.escape(title)}</div>" + "".join(html_rows)), "\n".join(text_lines) + "\n")


# ---- backend routing map --------------------------------------------------
def route_map():
    """Static diagram of how the CompositeBackend routes file paths."""
    rows = [
        (f"{MEMORY_MOUNT}/*", "StoreBackend", "durable · every thread in the namespace", _GREEN),
        ("everything else", "StateBackend", "ephemeral · this thread only", _MUTED),
    ]
    text = "Backend routing\n" + "-" * 15 + "\n"
    html_rows = ""
    for pattern, backend, who, color in rows:
        text += f"  {pattern:<18} -> {backend:<14} ({who})\n"
        html_rows += (
            f"<tr><td style='padding:4px 12px'><code>{html.escape(pattern)}</code></td>"
            f"<td style='padding:4px 12px'>→</td>"
            f"<td style='padding:4px 12px;color:{color}'><b>{backend}</b></td>"
            f"<td style='padding:4px 12px;color:{_MUTED}'>{who}</td></tr>"
        )
    inner = (
        f"<div style='color:{_MUTED};margin-bottom:4px'>🗂 CompositeBackend routing "
        f"— who can see the files?</div><table style='border-collapse:collapse'>{html_rows}</table>"
    )
    _display(_card(inner), text)


# ---- agent responses (chat-style) -----------------------------------------
_TOOL_ICON = {
    "write_todos": "📝", "task": "👥", "search_arxiv": "🔎", "get_arxiv_paper": "📄",
    "tavily_search": "🌐", "write_file": "✏️", "edit_file": "✏️",
    "read_file": "📂", "ls": "📂", "glob": "📂", "grep": "📂",
}


def _msg_text(m) -> str:
    """Text of a message, flattening Gemini's list-of-blocks content."""
    c = getattr(m, "content", "")
    if isinstance(c, list):
        return "".join(
            (b.get("text") or b.get("content") or "") if isinstance(b, dict) else str(b)
            for b in c
        )
    return c if isinstance(c, str) else str(c)


def _tool_summary(name: str, args: dict) -> str:
    args = args or {}
    if name == "write_todos":
        return f"{len(args.get('todos', []))} step(s)"
    if name == "task":
        return f"→ {args.get('subagent_type', 'subagent')}: {str(args.get('description', '')).strip()[:80]}"
    for k in ("query", "file_path", "arxiv_id", "path", "pattern"):
        if k in args:
            return str(args[k])[:90]
    return ", ".join(f"{k}={str(v)[:30]}" for k, v in args.items())[:90]


def show_response(result, title="🤖 Research agent"):
    """Render the agent's final message as Markdown — headings, lists, code."""
    msgs = result.get("messages", []) or []
    text = _msg_text(msgs[-1]) if msgs else ""
    if _in_notebook():
        from IPython.display import HTML, Markdown, display

        display(HTML(f"<div style='font:600 12px ui-monospace,monospace;color:{_MUTED};margin:8px 0 2px'>{html.escape(title)}</div>"))
        display(Markdown(text))
    else:
        print(f"{title}\n{'-' * len(title)}\n{text}\n")


def show_run(result, title="🤖 Research agent"):
    """Show what the agent *did* — its tool calls and delegations — then the
    final answer as Markdown. Turns a wall of text into an agent transcript."""
    msgs = result.get("messages", []) or []
    steps = []
    for m in msgs:
        if getattr(m, "type", "") == "ai":
            for tc in (getattr(m, "tool_calls", None) or []):
                nm = tc.get("name", "?")
                steps.append((_TOOL_ICON.get(nm, "🔧"), nm, _tool_summary(nm, tc.get("args"))))

    if _in_notebook():
        from IPython.display import HTML, display

        if steps:
            rows = "".join(
                f"<div style='margin:3px 0'><span style='font-size:13px'>{ic}</span> "
                f"<code style='background:{_BG};padding:1px 5px;border-radius:4px'>{html.escape(nm)}</code> "
                f"<span style='color:{_MUTED}'>{html.escape(summ)}</span></div>"
                for ic, nm, summ in steps
            )
            display(HTML(_card(
                f"<div style='color:{_MUTED};font:600 11.5px ui-monospace,monospace;"
                f"margin-bottom:4px'>🧭 trajectory · {len(steps)} step(s)</div>{rows}")))
        show_response(result, title=title)
    else:
        print(f"trajectory ({len(steps)} step(s)):")
        for ic, nm, summ in steps:
            print(f"  {nm}: {summ}")
        show_response(result, title=title)


# ---- architecture + memory, assembled part by part ------------------------
# One blueprint, styled with JupyterLab's own theme variables so it adapts to
# light/dark. A step tracker shows where we are in the build; the left column is
# what the agent can do (lighting up part by part) and the right column is what
# it remembers — memory that GROWS: ephemeral thread state from the start, with
# the durable store staying a quiet "arrives in Part 6" until we actually wire it.
_ARCH_ORDER = ["harness", "tools", "subagent", "hitl", "memory", "skills"]

# Left panel: the agent's *capabilities*, in the order the workshop adds them.
_ARCH_CAPABILITIES = [
    ("Model", "gemini-flash-lite-latest", "harness"),
    ("Filesystem", "ls · read · write · edit", "harness"),
    ("Planning", "write_todos", "harness"),
    ("Tools", "search_arxiv · get_paper · web", "tools"),
    ("Subagents", "paper-analyst · context isolation", "subagent"),
    ("Human-in-the-loop", "approve · edit · reject", "hitl"),
    ("AGENTS.md", "editable identity", "skills"),
    ("Skills", "bibtex · related-work · podcast", "skills"),
]


def _stage_state(stage, current, built):
    """Where a stage sits relative to the Part we're on."""
    if stage == current:
        return "now"
    if stage in built:
        return "built"
    return "soon"


def _lib_name(path, mount=MEMORY_MOUNT):
    """/memories/library/aging-clocks.md -> library/aging-clocks.md"""
    return path[len(mount):].lstrip("/") if path.startswith(mount) else path


def _mem_chips(names, max_n=4):
    """Render file names as compact chips, with a '+N more' tail."""
    shown, extra = names[:max_n], max(0, len(names) - max_n)
    chips = "".join(f"<span class='chip'>{html.escape(n)}</span>" for n in shown)
    if extra:
        chips += (
            "<span style='font-size:10.5px;color:var(--jp-content-font-color2,#8b949e)'>"
            f"+{extra} more</span>"
        )
    return f"<div>{chips}</div>"


# Nicer labels for a couple of stage ids in the step tracker.
_STEP_LABELS = {"hitl": "HITL"}

# All colors/fonts come from JupyterLab theme variables (with light fallbacks for
# other front ends), so the card adapts to the notebook's light or dark theme.
_ARCH_CSS = """<style>
.da-arch{font-family:var(--jp-ui-font-family,system-ui,-apple-system,'Segoe UI',sans-serif);background:var(--jp-layout-color1,#fff);border:1px solid var(--jp-border-color2,#e6e8eb);border-radius:14px;padding:16px 18px;max-width:920px;}
.da-arch *{box-sizing:border-box;}
.da-arch .da-title{font-size:15px;font-weight:600;color:var(--jp-content-font-color0,#1f2328);}
.da-arch .da-title .s{color:var(--jp-content-font-color2,#8b949e);font-weight:400;}
.da-arch .da-steps{display:flex;flex-wrap:wrap;gap:5px;margin:13px 0 17px;}
.da-arch .da-step{display:flex;align-items:center;gap:6px;font-size:11px;padding:3px 11px;border-radius:999px;color:var(--jp-content-font-color2,#8b949e);}
.da-arch .da-step .dot{width:6px;height:6px;border-radius:50%;background:currentColor;opacity:.45;}
.da-arch .da-step.done{color:var(--jp-success-color1,#1a7f37);}
.da-arch .da-step.done .dot{opacity:1;}
.da-arch .da-step.now{color:#fff;background:var(--jp-brand-color1,#0969da);font-weight:600;}
.da-arch .da-step.now .dot{opacity:1;background:#fff;}
.da-arch .da-step.todo{opacity:.5;}
.da-arch .da-cols{display:flex;gap:16px;align-items:flex-start;}
.da-arch .da-col{flex:1;min-width:0;}
.da-arch .da-colhead{font-size:10px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--jp-content-font-color2,#8b949e);margin-bottom:9px;}
.da-arch .da-row{background:var(--jp-layout-color1,#fff);border:1px solid var(--jp-border-color2,#e6e8eb);border-left:3px solid var(--jp-border-color2,#e6e8eb);border-radius:10px;padding:9px 12px;margin-bottom:8px;}
.da-arch .da-row .rt{font-size:13px;font-weight:600;color:var(--jp-content-font-color0,#1f2328);display:flex;align-items:center;gap:8px;}
.da-arch .da-row .rd{font-size:11.5px;color:var(--jp-content-font-color2,#8b949e);margin-top:3px;font-family:var(--jp-code-font-family,ui-monospace,Menlo,monospace);}
.da-arch .da-row.now{border-left-color:var(--jp-brand-color1,#0969da);}
.da-arch .da-row.built{border-left-color:var(--jp-success-color1,#1a7f37);}
.da-arch .da-row.soon{opacity:.5;border-left-style:dashed;}
.da-arch .tag{font-size:10px;font-weight:600;}
.da-arch .tag.now{color:var(--jp-brand-color1,#0969da);}
.da-arch .tag.built{color:var(--jp-success-color1,#1a7f37);}
.da-arch .tag.soon{color:var(--jp-content-font-color3,#aeb4bb);font-weight:500;}
.da-arch .chip{display:inline-block;font-family:var(--jp-code-font-family,ui-monospace,Menlo,monospace);font-size:10.5px;padding:1px 7px;border-radius:6px;background:var(--jp-layout-color2,#f2f4f6);color:var(--jp-content-font-color1,#57606a);margin:4px 4px 0 0;}
.da-arch .router{font-size:10px;color:var(--jp-content-font-color2,#8b949e);text-align:center;margin:8px 0;}
.da-arch .router code{font-family:var(--jp-code-font-family,monospace);background:var(--jp-layout-color2,#f2f4f6);padding:0 4px;border-radius:4px;}
.da-arch .mem-coming{font-size:11px;color:var(--jp-content-font-color3,#aeb4bb);margin-top:8px;padding-left:3px;display:flex;align-items:center;gap:7px;}
.da-arch .mem-coming .plus{font-size:13px;}
</style>"""


def show_architecture(through="harness", store=None, result=None, title="Your deep agent"):
    """Blueprint of the agent as we build it, styled to match the notebook theme.

    A step tracker across the top shows where we are in the build. The left
    column is **what it can do** (capabilities lighting up: activating now → ✓
    built → soon). The right column is **what it remembers**, and it grows: the
    ephemeral thread state is on from the start, while the durable store stays a
    quiet "arrives in Part 6" until the ``memory`` stage wires it in.

    Pass ``store=`` to show what's actually filed in durable memory, and
    ``result=`` to show the current thread's scratch files. Both are optional.
    """
    order = _ARCH_ORDER
    upto = order.index(through) if through in order else len(order) - 1
    current = order[upto]          # the stage we're activating in this Part
    built = set(order[:upto])      # stages finished in earlier Parts

    # ---- live memory readout (optional) ----
    thread_files = sorted(((result or {}).get("files") or {}).keys())
    entries = []
    if store is not None:
        try:
            entries = read_store(store)
        except Exception:
            entries = []
    lib_names = [_lib_name(e["path"]) for e in entries]
    mem_state = _stage_state("memory", current, built)

    if _in_notebook():
        from IPython.display import HTML, display

        # -- step tracker --
        steps = ""
        for st in order:
            scls = "now" if st == current else ("done" if st in built else "todo")
            steps += (
                f"<div class='da-step {scls}'><span class='dot'></span>"
                f"{html.escape(_STEP_LABELS.get(st, st))}</div>"
            )

        # -- left column: capabilities --
        tag_txt = {"now": "· activating now", "built": "✓", "soon": "· soon"}
        rows = ""
        for label, detail, stage in _ARCH_CAPABILITIES:
            state = _stage_state(stage, current, built)
            rows += (
                f"<div class='da-row {state}'><div class='rt'>{html.escape(label)}"
                f"<span class='tag {state}'>{tag_txt[state]}</span></div>"
                f"<div class='rd'>{html.escape(detail)}</div></div>"
            )
        left = f"<div class='da-col'><div class='da-colhead'>What it can do</div>{rows}</div>"

        # -- right column: memory that grows --
        eph = (
            "<div class='da-row built'><div class='rt'>🧵 Thread state"
            "<span class='tag built'>· on now</span></div>"
            "<div class='rd'>ephemeral · this conversation only</div>"
            f"{_mem_chips(thread_files) if thread_files else ''}</div>"
        )
        if mem_state == "soon":
            mem = eph + (
                "<div class='mem-coming'><span class='plus'>＋</span> "
                "Durable store — arrives in Part 6</div>"
            )
        else:
            if mem_state == "now":
                dcls, dtag = "now", "· activating now"
                dsub = (
                    "/memories · survives every thread"
                    if lib_names
                    else "/memories · files written here now survive every thread"
                )
            else:  # built
                dcls = "built"
                dtag = f"· {len(entries)} files ✓" if entries else "✓"
                dsub = (
                    "/memories · survives every thread"
                    if lib_names
                    else "/memories · survives every thread · inspect with show_memory()"
                )
            dur = (
                f"<div class='da-row {dcls}'><div class='rt'>📚 Durable store"
                f"<span class='tag {dcls}'>{dtag}</span></div>"
                f"<div class='rd'>{dsub}</div>"
                f"{_mem_chips(lib_names) if lib_names else ''}</div>"
            )
            router = (
                "<div class='router'>router: <code>/memories/*</code> → durable"
                " · everything else → thread</div>"
            )
            mem = eph + router + dur
        right = f"<div class='da-col'><div class='da-colhead'>What it remembers</div>{mem}</div>"

        head = (
            f"<div class='da-title'>🧩 {html.escape(title)} "
            f"<span class='s'>— so far</span></div>"
        )
        html_out = (
            f"{_ARCH_CSS}<div class='da-arch'>{head}"
            f"<div class='da-steps'>{steps}</div>"
            f"<div class='da-cols'>{left}{right}</div></div>"
        )
        display(HTML(html_out))
    else:
        prog = " → ".join(
            _STEP_LABELS.get(s, s).upper() if s == current else _STEP_LABELS.get(s, s)
            for s in order
        )
        lines = [f"{title} — so far   [{prog}]", "", "WHAT IT CAN DO:"]
        for label, detail, stage in _ARCH_CAPABILITIES:
            state = _stage_state(stage, current, built)
            mark = "▶" if state == "now" else ("✓" if state == "built" else "○")
            lines.append(f"  {mark} {label}: {detail}")
        lines += ["", "WHAT IT REMEMBERS:"]
        lines.append(
            "  🧵 Thread state (ephemeral): "
            + (", ".join(thread_files) if thread_files else "on now · this conversation only")
        )
        if mem_state == "soon":
            lines.append("  ＋ Durable store — arrives in Part 6")
        elif lib_names:
            lines.append(f"  📚 Durable store ({len(entries)} files): " + ", ".join(lib_names))
        elif mem_state == "now":
            lines.append("  📚 Durable store: activating now — files here survive every thread")
        else:
            lines.append("  📚 Durable store: durable — inspect with show_memory()")
        print("\n".join(lines))


# ---- LangSmith trace link + graph rendering -------------------------------
import contextlib


@contextlib.contextmanager
def trace_link(label="run"):
    """If LangSmith tracing is configured, print a link to this run's trace."""
    import os

    on = bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")) and str(
        os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2") or ""
    ).lower() in ("1", "true", "yes")
    if not on:
        yield
        return
    from langchain_core.tracers.context import collect_runs

    with collect_runs() as cb:
        yield
    try:
        print(f"🔗 {label}: {_run_url(cb.traced_runs[0])}")
    except Exception:
        pass


def _run_url(run):
    # Client.get_run_url() builds a `/r/<run_id>?poll=true` link, which its own
    # docstring says isn't meant for runtime use — LangSmith's v2 lookup for that
    # route needs an exact project + start_time match and often 404s on a run
    # that was just traced. The project-view "peek" link below is what the
    # LangSmith UI itself generates when you open a run, and works reliably.
    from langsmith import Client
    from langsmith import utils as ls_utils

    client = Client()
    tenant_id = client._get_tenant_id()
    session_id = getattr(run, "session_id", None)
    if session_id is None:
        session_id = client.read_project(project_name=ls_utils.get_tracer_project()).id

    peek_start = run.start_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return (
        f"https://smith.langchain.com/o/{tenant_id}/projects/p/{session_id}"
        f"?peek={run.id}&peek_start={peek_start}&peek_project={session_id}"
        f"&trace_id={run.trace_id}&run_id={run.id}&peeked_trace={run.trace_id}"
    )


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def save_briefing(src="agent/briefing.md", dst="episode_briefing.md"):
    """Copy the briefing the agent wrote (under agent/) into ``output/``."""
    src = Path(src)
    if not src.exists():
        print(f"No briefing found at {src}.")
        return
    dest = Path(dst)
    if not dest.is_absolute():
        dest = OUTPUT_DIR / dest.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(src.read_text())
    print(f"Saved {dest} ({src.stat().st_size} bytes) — upload to NotebookLM.")
