from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text

from auth import get_current_user, get_current_user_optional
from db import get_db
from models import CharityCampaign, Donation, User

# Validation limits
DONATION_AMOUNT_MIN = 1
DONATION_AMOUNT_MAX = 999_999_999

router = APIRouter(tags=["donation"])
templates = Jinja2Templates(directory="templates")


@router.get("/me/donations", response_class=HTMLResponse)
def my_donations(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    donations = (
        db.query(Donation)
        .filter(Donation.user_id == current_user.id)
        .order_by(Donation.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "my_donations.html",
        {
            "request": request,
            "user": current_user,
            "donations": donations,
        },
    )


@router.post("/campaigns/{campaign_id}/donate", summary="Donate to campaign")
def donate(
    campaign_id: int,
    request: Request,
    amount: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if amount < DONATION_AMOUNT_MIN or amount > DONATION_AMOUNT_MAX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount must be between {DONATION_AMOUNT_MIN} and {DONATION_AMOUNT_MAX}.",
        )

    campaign = db.get(CharityCampaign, campaign_id)
    if campaign is None or campaign.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This campaign is not available for donations.",
        )

    donation = Donation(
        user_id=current_user.id,
        campaign_id=campaign.id,
        amount=amount,
    )
    db.add(donation)
    db.commit()

    return RedirectResponse(
        url=f"/campaigns/{campaign_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )

@router.get("/top-donors", response_class=HTMLResponse)
def top_donors(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    donors = db.execute(
        text("""
        SELECT 
            u.email,
            COUNT(d.id) as donations_count,
            SUM(d.amount) as total_amount
        FROM users u
        JOIN donations d ON u.id = d.user_id
        GROUP BY u.id, u.email
        ORDER BY total_amount DESC
        LIMIT 10
        """)
    ).all()
    
    return templates.TemplateResponse(
        "top_donors.html",
        {
            "request": request, 
            "user": current_user, 
            "donors": donors
        }
    )