from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pymongo.database import Database

from auth import get_current_user, get_current_user_optional
from db import get_db
from models import doc_with_id, utc_now

# Validation limits
DONATION_AMOUNT_MIN = 1
DONATION_AMOUNT_MAX = 999_999_999

router = APIRouter(tags=["donation"])
templates = Jinja2Templates(directory="templates")


@router.get("/me/donations", response_class=HTMLResponse)
def my_donations(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    donations = list(
        db.donations.find({"user_id": ObjectId(current_user["id"])}).sort("created_at", -1)
    )
    campaign_ids = [d["campaign_id"] for d in donations]
    campaigns_map = {str(c["_id"]): c for c in db.charity_campaigns.find({"_id": {"$in": campaign_ids}})}

    result = []
    for d in donations:
        r = doc_with_id(d)
        r["campaign"] = campaigns_map.get(str(d["campaign_id"]), {"title": "?"})
        result.append(r)

    return templates.TemplateResponse(
        "my_donations.html",
        {
            "request": request,
            "user": current_user,
            "donations": result,
        },
    )


@router.post("/campaigns/{campaign_id}/donate", summary="Donate to campaign")
def donate(
    campaign_id: str,
    request: Request,
    amount: int = Form(...),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if amount < DONATION_AMOUNT_MIN or amount > DONATION_AMOUNT_MAX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount must be between {DONATION_AMOUNT_MIN} and {DONATION_AMOUNT_MAX}.",
        )

    try:
        oid = ObjectId(campaign_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid campaign")

    campaign = db.charity_campaigns.find_one({"_id": oid})
    if campaign is None or campaign.get("status") != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This campaign is not available for donations.",
        )

    doc = {
        "user_id": ObjectId(current_user["id"]),
        "campaign_id": oid,
        "amount": amount,
        "created_at": utc_now(),
    }
    db.donations.insert_one(doc)

    return RedirectResponse(
        url=f"/campaigns/{campaign_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )

@router.get("/top-donors", response_class=HTMLResponse)
def top_donors(
    request: Request,
    db: Database = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    pipeline = [
        {"$group": {
            "_id": "$user_id",
            "donations_count": {"$sum": 1},
            "total_amount": {"$sum": "$amount"},
        }},
        {"$sort": {"total_amount": -1}},
        {"$limit": 10},
        {"$lookup": {
            "from": "users",
            "localField": "_id",
            "foreignField": "_id",
            "as": "user",
        }},
        {"$unwind": "$user"},
        {"$project": {
            "email": "$user.email",
            "donations_count": 1,
            "total_amount": 1,
        }},
    ]
    donors = list(db.donations.aggregate(pipeline))

    return templates.TemplateResponse(
        "top_donors.html",
        {
            "request": request,
            "user": current_user,
            "donors": donors,
        },
    )
