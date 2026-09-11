from fastapi import APIRouter

from .. import sync as sync_module
from ..schemas import SyncResult

router = APIRouter(prefix="/api")


@router.post("/sync", response_model=SyncResult)
async def trigger_sync():
    result = await sync_module.run_sync()
    return result
