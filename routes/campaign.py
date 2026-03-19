from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pymongo.database import Database

from auth import get_current_user_optional, require_admin
from db import get_db
from models import doc_with_id, utc_now

# Validation limits
CAMPAIGN_TITLE_MAX_LENGTH = 200
CAMPAIGN_DESCRIPTION_MAX_LENGTH = 5000

router = APIRouter(tags=["campaign"])
templates = Jinja2Templates(directory="templates")


def _campaign_doc(doc: dict) -> dict:
    d = doc_with_id(doc)
    d["created_by_id"] = str(doc.get("created_by_id", ""))
    return d


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    db: Database = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    campaigns = list(
        db.charity_campaigns.find({"status": "open"}).sort("created_at", -1)
    )
    totals_map = {}
    for c in campaigns:
        cid = c["_id"]
        agg = db.donations.aggregate([
            {"$match": {"campaign_id": cid}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ])
        row = next(agg, None)
        totals_map[str(cid)] = row["total"] if row else 0

    return templates.TemplateResponse(
        "campaigns_list.html",
        {
            "request": request,
            "user": current_user,
            "campaigns": [_campaign_doc(c) for c in campaigns],
            "totals": totals_map,
        },
    )


@router.get("/campaigns/{campaign_id}", response_class=HTMLResponse, summary="Campaign details")
def campaign_detail(
    campaign_id: str,
    request: Request,
    db: Database = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    try:
        oid = ObjectId(campaign_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    campaign = db.charity_campaigns.find_one({"_id": oid})
    if campaign is None or (
        campaign.get("status") != "open"
        and (not current_user or current_user.get("role") != "admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )

    agg = db.donations.aggregate([
        {"$match": {"campaign_id": oid}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ])
    row = next(agg, None)
    total = row["total"] if row else 0

    comments = list(
        db.comments.find({"campaign_id": oid}).sort("created_at", -1)
    )
    user_ids = {c["user_id"] for c in comments}
    users_map = {str(u["_id"]): u for u in db.users.find({"_id": {"$in": list(user_ids)}})}
    
    likes_collection = db['comment_likes']

    likes_count = {}
    user_likes = set()
    
    for c in comments:
        c["id"] = str(c["_id"])
        c["user_id"] = str(c["user_id"])
        u = users_map.get(c["user_id"])
        c["user"] = {"email": u["email"]} if u else {"email": "?"}

        count = likes_collection.count_documents({"comment_id": c["_id"]})
        likes_count[c["id"]] = count
        if current_user:
            if likes_collection.find_one({"comment_id": c["_id"], "user_id": ObjectId(current_user["id"])}):
                user_likes.add(c["id"])

    campaign_doc = _campaign_doc(campaign)
    campaign_doc["comments"] = comments

    return templates.TemplateResponse(
        "campaign_detail.html",
        {
            "request": request,
            "user": current_user,
            "campaign": campaign_doc,
            "total": total,
            "likes_count": likes_count,
            "user_likes": user_likes,
        },
    )


@router.get("/admin/campaigns", response_class=HTMLResponse, summary="Admin: list all campaigns")
def admin_campaigns(
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db),
):
    campaigns = list(
        db.charity_campaigns.find({}).sort("created_at", -1)
    )
    return templates.TemplateResponse(
        "admin_campaigns.html",
        {
            "request": request,
            "user": current_user,
            "campaigns": [_campaign_doc(c) for c in campaigns],
        },
    )


@router.get("/admin/campaigns/new", response_class=HTMLResponse, summary="Admin: new campaign form")
def new_campaign_form(
    request: Request,
    current_user: dict = Depends(require_admin),
):
    return templates.TemplateResponse(
        "new_campaign.html",
        {"request": request, "user": current_user},
    )


@router.post("/admin/campaigns", summary="Admin: create campaign")
def create_campaign(
    request: Request,
    title: str = Form(..., min_length=1, max_length=CAMPAIGN_TITLE_MAX_LENGTH),
    description: str = Form(
        ..., min_length=1, max_length=CAMPAIGN_DESCRIPTION_MAX_LENGTH
    ),
    target_status: str = Form("open"),
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db),
):
    title = title.strip()
    description = description.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Title is required."
        )
    if not description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Description is required.",
        )

    if target_status not in ("open", "closed"):
        target_status = "open"

    doc = {
        "title": title,
        "description": description,
        "created_by_id": ObjectId(current_user["id"]),
        "created_at": utc_now(),
        "status": target_status,
    }
    db.charity_campaigns.insert_one(doc)

    return RedirectResponse(
        url="/admin/campaigns",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/admin/campaigns/{campaign_id}/edit", response_class=HTMLResponse, summary="Admin: edit campaign form")
def edit_campaign_form(
    campaign_id: str,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db),
):
    try:
        oid = ObjectId(campaign_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    campaign = db.charity_campaigns.find_one({"_id": oid})
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )

    return templates.TemplateResponse(
        "edit_campaign.html",
        {
            "request": request,
            "user": current_user,
            "campaign": _campaign_doc(campaign),
        },
    )


@router.post("/admin/campaigns/{campaign_id}/edit", summary="Admin: update campaign")
def update_campaign(
    campaign_id: str,
    request: Request,
    title: str = Form(..., min_length=1, max_length=CAMPAIGN_TITLE_MAX_LENGTH),
    description: str = Form(
        ..., min_length=1, max_length=CAMPAIGN_DESCRIPTION_MAX_LENGTH
    ),
    status_value: str = Form(...),
    current_user: dict = Depends(require_admin),
    db: Database = Depends(get_db),
):
    title = title.strip()
    description = description.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Title is required."
        )
    if not description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Description is required.",
        )
    if status_value not in ("open", "closed"):
        status_value = "open"

    try:
        oid = ObjectId(campaign_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    result = db.charity_campaigns.update_one(
        {"_id": oid},
        {"$set": {"title": title, "description": description, "status": status_value}},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )

    return RedirectResponse(
        url="/admin/campaigns",
        status_code=status.HTTP_303_SEE_OTHER,
    )
