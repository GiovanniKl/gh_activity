import json
import sqlite3
import threading
from contextlib import contextmanager

from . import config

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS repos (
    id INTEGER PRIMARY KEY,
    full_name TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    private INTEGER NOT NULL,
    default_branch TEXT,
    pushed_at TEXT
);

CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    date TEXT NOT NULL,
    repo_id INTEGER NOT NULL,
    org TEXT NOT NULL,
    private INTEGER NOT NULL,
    title TEXT,
    url TEXT,
    sha_or_number TEXT NOT NULL,
    on_default_branch INTEGER NOT NULL DEFAULT 1,
    UNIQUE(type, repo_id, sha_or_number)
);
CREATE INDEX IF NOT EXISTS idx_activity_date ON activity(date);

CREATE TABLE IF NOT EXISTS sync_state (
    repo_id INTEGER PRIMARY KEY,
    last_synced_at TEXT,
    branch_heads_json TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def _migrate(conn: sqlite3.Connection):
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(activity)")}
    if "on_default_branch" not in columns:
        conn.execute("ALTER TABLE activity ADD COLUMN on_default_branch INTEGER NOT NULL DEFAULT 1")


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()
        _local.conn = conn
    return conn


@contextmanager
def tx():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def upsert_repo(conn, repo: dict):
    conn.execute(
        """
        INSERT INTO repos (id, full_name, name, owner, private, default_branch, pushed_at)
        VALUES (:id, :full_name, :name, :owner, :private, :default_branch, :pushed_at)
        ON CONFLICT(id) DO UPDATE SET
            full_name=excluded.full_name, name=excluded.name, owner=excluded.owner,
            private=excluded.private, default_branch=excluded.default_branch,
            pushed_at=excluded.pushed_at
        """,
        repo,
    )


def upsert_activity(conn, item: dict):
    item = {"on_default_branch": 1, **item}
    conn.execute(
        """
        INSERT INTO activity (type, date, repo_id, org, private, title, url, sha_or_number, on_default_branch)
        VALUES (:type, :date, :repo_id, :org, :private, :title, :url, :sha_or_number, :on_default_branch)
        ON CONFLICT(type, repo_id, sha_or_number) DO UPDATE SET
            date=excluded.date, title=excluded.title, url=excluded.url, private=excluded.private,
            on_default_branch=CASE WHEN excluded.on_default_branch = 1 THEN 1 ELSE on_default_branch END
        """,
        item,
    )


def get_sync_state(conn, repo_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM sync_state WHERE repo_id = ?", (repo_id,)).fetchone()
    if not row:
        return None
    return {
        "repo_id": row["repo_id"],
        "last_synced_at": row["last_synced_at"],
        "branch_heads": json.loads(row["branch_heads_json"] or "{}"),
    }


def set_sync_state(conn, repo_id: int, last_synced_at: str, branch_heads: dict):
    conn.execute(
        """
        INSERT INTO sync_state (repo_id, last_synced_at, branch_heads_json)
        VALUES (?, ?, ?)
        ON CONFLICT(repo_id) DO UPDATE SET
            last_synced_at=excluded.last_synced_at, branch_heads_json=excluded.branch_heads_json
        """,
        (repo_id, last_synced_at, json.dumps(branch_heads)),
    )


def set_meta(conn, key: str, value: str):
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_meta(conn, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def fetch_activity(conn, since: str, until: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT a.type, a.date, a.org, a.private, a.title, a.url, a.sha_or_number, a.on_default_branch,
               r.name AS repo, r.full_name AS repo_full_name
        FROM activity a
        JOIN repos r ON r.id = a.repo_id
        WHERE a.date >= ? AND a.date <= ?
        ORDER BY a.date DESC
        """,
        (since, until),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_orgs(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT DISTINCT owner AS org FROM repos ORDER BY owner COLLATE NOCASE"
    ).fetchall()
    return [dict(row) for row in rows]
