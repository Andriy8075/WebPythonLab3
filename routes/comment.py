from bson import ObjectId
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pymongo.database import Database

from auth import get_current_user
from db import get_db
from models import doc_with_id, utc_now

# Validation limits
COMMENT_CONTENT_MAX_LENGTH = 1000
COMMENT_CONTENT_MIN_LENGTH = 1

router = APIRouter(tags=["comment"])
templates = Jinja2Templates(directory="templates")


@router.post("/campaigns/{campaign_id}/comments")
def create_comment(
    campaign_id: str,
    request: Request,
    content: str = Form(..., min_length=COMMENT_CONTENT_MIN_LENGTH, max_length=COMMENT_CONTENT_MAX_LENGTH),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(campaign_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    campaign = db.charity_campaigns.find_one({"_id": oid})
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    content = content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment content cannot be empty"
        )

    doc = {
        "content": content,
        "user_id": ObjectId(current_user["id"]),
        "campaign_id": oid,
        "created_at": utc_now(),
    }
    db.comments.insert_one(doc)

    return RedirectResponse(
        url=f"/campaigns/{campaign_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/comments/{comment_id}/delete", summary="Delete comment")
def delete_comment(
    comment_id: str,
    request: Request,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(comment_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    comment = db.comments.find_one({"_id": oid})
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if str(comment["user_id"]) != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this comment"
        )

    campaign_id = str(comment["campaign_id"])

    db.comments.delete_one({"_id": oid})

    return RedirectResponse(
        url=f"/campaigns/{campaign_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/comments/{comment_id}/edit", response_class=HTMLResponse, summary="Edit comment form")
def edit_comment_form(
    comment_id: str,
    request: Request,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(comment_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    comment = db.comments.find_one({"_id": oid})
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if str(comment["user_id"]) != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this comment"
        )

    c = doc_with_id(comment)
    c["campaign_id"] = str(comment["campaign_id"])
    return templates.TemplateResponse(
        "edit_comment.html",
        {
            "request": request,
            "user": current_user,
            "comment": c,
        }
    )


@router.post("/comments/{comment_id}/edit", summary="Update comment")
def update_comment(
    comment_id: str,
    request: Request,
    content: str = Form(..., min_length=COMMENT_CONTENT_MIN_LENGTH, max_length=COMMENT_CONTENT_MAX_LENGTH),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(comment_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    comment = db.comments.find_one({"_id": oid})
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if str(comment["user_id"]) != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this comment"
        )

    content = content.strip()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment content cannot be empty"
        )

    db.comments.update_one({"_id": oid}, {"$set": {"content": content}})
    campaign_id = str(comment["campaign_id"])

    return RedirectResponse(
        url=f"/campaigns/{campaign_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )
