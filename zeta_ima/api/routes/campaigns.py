"""
Campaign management routes.

GET    /campaigns
POST   /campaigns
PATCH  /campaigns/{id}
DELETE /campaigns/{id}
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update, delete

from zeta_ima.api.auth import get_current_user
from zeta_ima.memory.campaign import AsyncSessionLocal, campaigns, create_campaign, load_active_campaign

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str


class CampaignUpdate(BaseModel):
    name: str = None
    status: str = None   # active | paused | complete


@router.get("")
async def list_campaigns(user: dict = Depends(get_current_user)) -> list[dict]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(campaigns).where(campaigns.c.user_id == user["user_id"])
            .order_by(campaigns.c.created_at.desc())
        )
        rows = [dict(r._mapping) for r in result.fetchall()]
        for r in rows:
            for k in ("created_at", "updated_at"):
                if r.get(k):
                    r[k] = str(r[k])
        return rows


@router.post("")
async def create(payload: CampaignCreate, user: dict = Depends(get_current_user)) -> dict:
    return await create_campaign(user["user_id"], payload.name)


@router.patch("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    user: dict = Depends(get_current_user),
) -> dict:
    values = {k: v for k, v in payload.dict().items() if v is not None}
    if not values:
        raise HTTPException(status_code=400, detail="No fields to update")

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(campaigns)
            .where(campaigns.c.id == campaign_id, campaigns.c.user_id == user["user_id"])
            .values(**values)
        )
        await session.commit()
    return {"ok": True, "id": campaign_id, **values}


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str, user: dict = Depends(get_current_user)) -> dict:
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(campaigns).where(
                campaigns.c.id == campaign_id,
                campaigns.c.user_id == user["user_id"],
            )
        )
        await session.commit()
    return {"ok": True}
