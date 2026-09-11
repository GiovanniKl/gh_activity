import asyncio
import logging
import time

import httpx

from . import config

logger = logging.getLogger("gh_activity.client")


class GitHubError(RuntimeError):
    pass


class GitHubClient:
    """Thin async wrapper around the GitHub REST API with pagination,
    bounded concurrency, and rate-limit backoff."""

    def __init__(self, token: str):
        if not token:
            raise GitHubError("GITHUB_TOKEN is not set (see backend/.env.example)")
        self._client = httpx.AsyncClient(
            base_url=config.GITHUB_API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        self._sem = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)
        self.last_rate_limit: dict | None = None

    async def aclose(self):
        await self._client.aclose()

    async def _request(self, method: str, url: str, params: dict | None = None) -> httpx.Response:
        async with self._sem:
            for attempt in range(5):
                resp = await self._client.request(method, url, params=params)
                remaining = resp.headers.get("x-ratelimit-remaining")
                limit = resp.headers.get("x-ratelimit-limit")
                reset = resp.headers.get("x-ratelimit-reset")
                if remaining is not None:
                    self.last_rate_limit = {
                        "remaining": int(remaining),
                        "limit": int(limit) if limit else None,
                        "reset_at": int(reset) if reset else None,
                    }

                if resp.status_code == 403 and remaining == "0":
                    reset_at = int(reset) if reset else time.time() + 60
                    wait = max(0, reset_at - time.time()) + 1
                    logger.warning("Rate limit hit, sleeping %.0fs", wait)
                    await asyncio.sleep(min(wait, 120))
                    continue

                if resp.status_code == 202 and "search" not in url:
                    # GitHub is still computing stats (e.g. empty repo edge cases); brief retry.
                    await asyncio.sleep(1)
                    continue

                if resp.status_code >= 500:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue

                return resp
            raise GitHubError(f"Exhausted retries for {method} {url}")

    async def get(self, url: str, params: dict | None = None) -> httpx.Response:
        resp = await self._request("GET", url, params)
        if resp.status_code == 401:
            raise GitHubError("GitHub rejected the token (401 Unauthorized). Check GITHUB_TOKEN.")
        if resp.status_code == 404:
            return resp
        if resp.status_code >= 400:
            raise GitHubError(f"GET {url} failed: {resp.status_code} {resp.text[:300]}")
        return resp

    async def paginate(self, url: str, params: dict | None = None, per_page: int = 100):
        """Yield items across all pages of a standard REST list endpoint."""
        params = dict(params or {})
        params["per_page"] = per_page
        page = 1
        while True:
            params["page"] = page
            resp = await self.get(url, params=params)
            if resp.status_code == 404:
                return
            data = resp.json()
            if not data:
                return
            for item in data:
                yield item
            if len(data) < per_page or "next" not in resp.links:
                return
            page += 1

    async def paginate_search(self, url: str, query: str, per_page: int = 100, max_items: int = 1000):
        """Yield items from the Search API, which caps results at 1000 and
        has its own (lower) rate limit."""
        page = 1
        seen = 0
        while seen < max_items:
            resp = await self.get(url, params={"q": query, "per_page": per_page, "page": page})
            data = resp.json()
            items = data.get("items", [])
            if not items:
                return
            for item in items:
                yield item
                seen += 1
            if len(items) < per_page:
                return
            page += 1
            await asyncio.sleep(2)  # search API: 30 req/min limit
