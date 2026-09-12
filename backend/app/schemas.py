from pydantic import BaseModel


class ActivityItem(BaseModel):
    type: str  # commit | pr | issue | review
    date: str  # ISO date (YYYY-MM-DD)
    org: str
    private: bool
    title: str | None
    url: str | None
    sha_or_number: str
    on_default_branch: bool
    repo: str
    repo_full_name: str


class ActivityResponse(BaseModel):
    items: list[ActivityItem]


class OrgsResponse(BaseModel):
    orgs: list[str]


class RateLimitInfo(BaseModel):
    remaining: int | None = None
    limit: int | None = None
    reset_at: int | None = None


class SyncResult(BaseModel):
    ok: bool
    repos_scanned: int
    items_upserted: int
    duration_seconds: float
    rate_limit: RateLimitInfo | None = None
    error: str | None = None


class MetaResponse(BaseModel):
    last_synced_at: str | None
    rate_limit: RateLimitInfo | None = None
    username: str | None = None
