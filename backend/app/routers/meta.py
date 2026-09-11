import json

from fastapi import APIRouter

from .. import db
from ..schemas import MetaResponse

router = APIRouter(prefix="/api")


@router.get("/meta", response_model=MetaResponse)
def get_meta():
    conn = db.get_conn()
    last_synced_at = db.get_meta(conn, "last_full_sync")
    username = db.get_meta(conn, "username")
    rate_limit_raw = db.get_meta(conn, "last_rate_limit")
    rate_limit = json.loads(rate_limit_raw) if rate_limit_raw else None
    return {"last_synced_at": last_synced_at, "rate_limit": rate_limit, "username": username}
