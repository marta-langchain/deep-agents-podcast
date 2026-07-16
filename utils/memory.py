"""Long-term memory config, shared by the notebook, the agent, and the viz.

The agent mounts a persistent ``StoreBackend`` at ``/memories/``. The
``CompositeBackend`` strips that prefix before delegating, so a file the agent
sees at ``/memories/library/aging-clocks.md`` is stored under the key
``/library/aging-clocks.md`` inside ``MEMORY_NAMESPACE``. The visualizers read
the store back with exactly that namespace, then re-prepend the mount.
"""

import sqlite3

# One namespace for the whole library. Swap "shared" for a user id to get
# per-user memory (see the notebook's Part 8 "next steps").
MEMORY_NAMESPACE = ("library", "shared")

# Route the persistent store is mounted on. Everything else stays ephemeral.
MEMORY_MOUNT = "/memories"
DEFAULT_DB = "library_memory.db"


def open_memory_store(path: str = DEFAULT_DB):
    """Open (or create) a SQLite-backed long-term memory store.

    ``setup()`` runs ``CREATE TABLE IF NOT EXISTS``, so this is safe whether or
    not the database already exists — that's what lets the library survive a
    kernel restart.
    """
    from langgraph.store.sqlite import SqliteStore

    conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    # WAL lets multiple connections read/write the same file without tripping
    # "readonly database" — e.g. the notebook opens a second handle to prove
    # the library really lives on disk.
    conn.execute("PRAGMA journal_mode=WAL")
    store = SqliteStore(conn)
    store.setup()
    return store
