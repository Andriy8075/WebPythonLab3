from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user, get_current_user_optional, require_admin
from db import get_db
from models import CharityCampaign, Donation, User

from mongo import likes_collection

# Validation limits
CAMPAIGN_TITLE_MAX_LENGTH = 200
CAMPAIGN_DESCRIPTION_MAX_LENGTH = 5000

router = APIRouter(tags=["campaign"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    campaigns = (
        db.query(CharityCampaign)
        .filter(CharityCampaign.status == "open")
        .order_by(CharityCampaign.created_at.desc())
        .all()
    )
    totals = (
        db.query(Donation.campaign_id, func.coalesce(func.sum(Donation.amount), 0))
        .group_by(Donation.campaign_id)
        .all()
    )
    totals_map = {cid: total for cid, total in totals}

    return templates.TemplateResponse(
        "campaigns_list.html",
        {
            "request": request,
            "user": current_user,
            "campaigns": campaigns,
            "totals": totals_map,
        },
    )


@router.get("/campaigns/{campaign_id}", response_class=HTMLResponse, summary="Campaign details")
def campaign_detail(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    campaign = db.get(CharityCampaign, campaign_id)
    if campaign is None or (
        campaign.status != "open"
        and (not current_user or current_user.role != "admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )

    total = (
        db.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.campaign_id == campaign.id)
        .scalar()
    )

    comment_ids = [c.id for c in campaign.comments]
    likes_count = {}
    user_likes = set()

    for comment_id in comment_ids:
        count = likes_collection.count_documents({"comment_id": comment_id})
        likes_count[comment_id] = count
        if current_user:
            if likes_collection.find_one({"comment_id": comment_id, "user_id": current_user.id}):
                user_likes.add(comment_id)
    
    return templates.TemplateResponse(
        "campaign_detail.html",
        {
            "request": request,
            "user": current_user,
            "campaign": campaign,
            "total": total,
            "likes_count": likes_count,
            "user_likes": user_likes,
        },
    )


@router.get("/admin/campaigns", response_class=HTMLResponse, summary="Admin: list all campaigns")
def admin_campaigns(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    campaigns = (
        db.query(CharityCampaign)
        .order_by(CharityCampaign.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "admin_campaigns.html",
        {
            "request": request,
            "user": current_user,
            "campaigns": campaigns,
        },
    )


@router.get("/admin/campaigns/new", response_class=HTMLResponse, summary="Admin: new campaign form")
def new_campaign_form(
    request: Request,
    current_user: User = Depends(require_admin),
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
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
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

    campaign = CharityCampaign(
        title=title,
        description=description,
        created_by_id=current_user.id,
        status=target_status,
    )
    db.add(campaign)
    db.commit()

    return RedirectResponse(
        url="/admin/campaigns",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/admin/campaigns/{campaign_id}/edit", response_class=HTMLResponse, summary="Admin: edit campaign form")
def edit_campaign_form(
    campaign_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    campaign = db.get(CharityCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )

    return templates.TemplateResponse(
        "edit_campaign.html",
        {
            "request": request,
            "user": current_user,
            "campaign": campaign,
        },
    )


@router.post("/admin/campaigns/{campaign_id}/edit", summary="Admin: update campaign")
def update_campaign(
    campaign_id: int,
    request: Request,
    title: str = Form(..., min_length=1, max_length=CAMPAIGN_TITLE_MAX_LENGTH),
    description: str = Form(
        ..., min_length=1, max_length=CAMPAIGN_DESCRIPTION_MAX_LENGTH
    ),
    status_value: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
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

    campaign = db.get(CharityCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )

    campaign.title = title
    campaign.description = description
    campaign.status = status_value

    db.commit()

    return RedirectResponse(
        url="/admin/campaigns",
        status_code=status.HTTP_303_SEE_OTHER,
    )
