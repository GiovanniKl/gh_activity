import datetime as dt
import json
import logging
import time

from . import config, db
from .github_client import GitHubClient, GitHubError

logger = logging.getLogger("gh_activity.sync")

_TS_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _iso(d: dt.datetime) -> str:
    return d.strftime(_TS_FMT)


def _parse(s: str) -> dt.datetime:
    return dt.datetime.strptime(s, _TS_FMT).replace(tzinfo=dt.timezone.utc)


def _repo_row(repo: dict) -> dict:
    return {
        "id": repo["id"],
        "full_name": repo["full_name"],
        "name": repo["name"],
        "owner": repo["owner"]["login"],
        "private": 1 if repo.get("private") else 0,
        "default_branch": repo.get("default_branch"),
        "pushed_at": repo.get("pushed_at"),
    }


async def _get_username(client: GitHubClient) -> str:
    if config.GITHUB_USERNAME:
        return config.GITHUB_USERNAME
    resp = await client.get("/user")
    return resp.json()["login"]


async def _fetch_repos(client: GitHubClient) -> list[dict]:
    repos = []
    async for repo in client.paginate(
        "/user/repos",
        params={
            "affiliation": "owner,collaborator,organization_member",
            "sort": "pushed",
            "direction": "desc",
        },
    ):
        repos.append(repo)
    return repos


async def _sync_commits_for_repo(client, conn, repo_row, username, since_dt, until_dt) -> int:
    repo_id = repo_row["id"]
    full_name = repo_row["full_name"]
    state = db.get_sync_state(conn, repo_id) or {}
    branch_heads = state.get("branch_heads", {})
    new_heads = dict(branch_heads)
    upserted = 0
    seen_shas = set()

    branches = []
    async for branch in client.paginate(f"/repos/{full_name}/branches"):
        branches.append(branch)

    since_str = _iso(since_dt)
    until_str = _iso(until_dt)

    for branch in branches:
        name = branch["name"]
        head_sha = branch["commit"]["sha"]
        new_heads[name] = head_sha
        if branch_heads.get(name) == head_sha:
            continue  # branch tip unchanged since last sync, nothing new to fetch

        async for commit in client.paginate(
            f"/repos/{full_name}/commits",
            params={"sha": name, "author": username, "since": since_str, "until": until_str},
        ):
            sha = commit["sha"]
            if sha in seen_shas:
                continue
            seen_shas.add(sha)
            db.upsert_activity(
                conn,
                {
                    "type": "commit",
                    "date": commit["commit"]["author"]["date"],
                    "repo_id": repo_id,
                    "org": repo_row["owner"],
                    "private": repo_row["private"],
                    "title": (commit["commit"]["message"] or "").split("\n")[0][:300],
                    "url": commit["html_url"],
                    "sha_or_number": sha,
                },
            )
            upserted += 1

    db.set_sync_state(conn, repo_id, _iso(until_dt), new_heads)
    return upserted


async def _resolve_repo_id(client: GitHubClient, conn, full_name: str, cache: dict) -> int:
    if full_name in cache:
        return cache[full_name]
    row = conn.execute("SELECT id FROM repos WHERE full_name = ?", (full_name,)).fetchone()
    if row:
        cache[full_name] = row["id"]
        return row["id"]
    resp = await client.get(f"/repos/{full_name}")
    repo = resp.json()
    db.upsert_repo(conn, _repo_row(repo))
    cache[full_name] = repo["id"]
    return repo["id"]


async def _sync_search_activity(client: GitHubClient, conn, username: str, since_dt, until_dt) -> int:
    since_date = since_dt.date().isoformat()
    until_date = until_dt.date().isoformat()
    cache: dict = {}
    upserted = 0

    queries = [
        ("pr", f"author:{username} is:pr created:{since_date}..{until_date}", "created_at"),
        ("issue", f"author:{username} is:issue created:{since_date}..{until_date}", "created_at"),
        ("review", f"reviewed-by:{username} is:pr updated:{since_date}..{until_date}", "updated_at"),
    ]

    for item_type, query, date_field in queries:
        async for item in client.paginate_search("/search/issues", query):
            full_name = item["repository_url"].split("/repos/", 1)[1]
            repo_id = await _resolve_repo_id(client, conn, full_name, cache)
            owner = full_name.split("/")[0]
            row = conn.execute("SELECT private FROM repos WHERE id = ?", (repo_id,)).fetchone()
            private = row["private"] if row else 0
            db.upsert_activity(
                conn,
                {
                    "type": item_type,
                    "date": item[date_field],
                    "repo_id": repo_id,
                    "org": owner,
                    "private": private,
                    "title": item.get("title"),
                    "url": item.get("html_url"),
                    "sha_or_number": str(item["number"]),
                },
            )
            upserted += 1
    return upserted


async def run_sync() -> dict:
    start = time.time()
    conn = db.get_conn()
    client: GitHubClient | None = None
    try:
        client = GitHubClient(config.GITHUB_TOKEN)
        username = await _get_username(client)
        until_dt = dt.datetime.now(dt.timezone.utc)
        last_full_sync = db.get_meta(conn, "last_full_sync")
        since_dt = _parse(last_full_sync) if last_full_sync else until_dt - dt.timedelta(
            days=config.DEFAULT_LOOKBACK_DAYS
        )

        repos = await _fetch_repos(client)
        with db.tx():
            for repo in repos:
                db.upsert_repo(conn, _repo_row(repo))

        repos_scanned = 0
        items_upserted = 0

        for repo in repos:
            repo_row = _repo_row(repo)
            state = db.get_sync_state(conn, repo_row["id"])
            repo_since = _parse(state["last_synced_at"]) if state and state.get("last_synced_at") else since_dt

            pushed_at = repo_row["pushed_at"]
            if pushed_at and _parse(pushed_at) < repo_since:
                continue  # nothing new pushed to this repo since it was last scanned

            repos_scanned += 1
            with db.tx():
                items_upserted += await _sync_commits_for_repo(
                    client, conn, repo_row, username, repo_since, until_dt
                )

        with db.tx():
            items_upserted += await _sync_search_activity(client, conn, username, since_dt, until_dt)
            db.set_meta(conn, "last_full_sync", _iso(until_dt))
            db.set_meta(conn, "username", username)
            if client.last_rate_limit:
                db.set_meta(conn, "last_rate_limit", json.dumps(client.last_rate_limit))

        return {
            "ok": True,
            "repos_scanned": repos_scanned,
            "items_upserted": items_upserted,
            "duration_seconds": time.time() - start,
            "rate_limit": client.last_rate_limit,
        }
    except GitHubError as e:
        logger.exception("sync failed")
        return {
            "ok": False,
            "repos_scanned": 0,
            "items_upserted": 0,
            "duration_seconds": time.time() - start,
            "error": str(e),
        }
    finally:
        if client is not None:
            await client.aclose()
