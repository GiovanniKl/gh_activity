import datetime as dt

from fastapi import APIRouter, Query

from .. import db
from ..schemas import ActivityResponse, OrgsResponse

router = APIRouter(prefix="/api")


@router.get("/activity", response_model=ActivityResponse)
def get_activity(
    since: str | None = Query(None, description="ISO date, defaults to 365 days ago"),
    until: str | None = Query(None, description="ISO date, defaults to today"),
):
    conn = db.get_conn()
    until_dt = dt.datetime.now(dt.timezone.utc)
    since_dt = until_dt - dt.timedelta(days=365)
    since_str = since or since_dt.date().isoformat()
    until_str = until or until_dt.date().isoformat()
    # 'until' is inclusive of the whole day
    until_str_bound = f"{until_str}T23:59:59Z"
    items = db.fetch_activity(conn, since_str, until_str_bound)
    return {"items": items}


@router.get("/orgs", response_model=OrgsResponse)
def get_orgs():
    conn = db.get_conn()
    orgs = [row["org"] for row in db.fetch_orgs(conn)]
    return {"orgs": orgs}
