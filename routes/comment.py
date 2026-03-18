from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth import get_current_user
from db import get_db
from models import Comment, CharityCampaign, User

from mongo import likes_collection
from datetime import datetime

# Validation limits
COMMENT_CONTENT_MAX_LENGTH = 1000
COMMENT_CONTENT_MIN_LENGTH = 1

router = APIRouter(tags=["comment"])
templates = Jinja2Templates(directory="templates")


@router.post("/campaigns/{campaign_id}/comments")
def create_comment(
    campaign_id: int,
    request: Request,
    content: str = Form(..., min_length=COMMENT_CONTENT_MIN_LENGTH, max_length=COMMENT_CONTENT_MAX_LENGTH),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = db.get(CharityCampaign, campaign_id)
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

    comment = Comment(
        content=content,
        user_id=current_user.id,
        campaign_id=campaign_id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return RedirectResponse(
        url=f"/campaigns/{campaign_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/comments/{comment_id}/delete", summary="Delete comment")
def delete_comment(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this comment"
        )

    campaign_id = comment.campaign_id

    db.delete(comment)
    db.commit()

    return RedirectResponse(
        url=f"/campaigns/{campaign_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/comments/{comment_id}/edit", response_class=HTMLResponse, summary="Edit comment form")
def edit_comment_form(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if comment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this comment"
        )

    return templates.TemplateResponse(
        "edit_comment.html",
        {
            "request": request,
            "user": current_user,
            "comment": comment,
        }
    )


@router.post("/comments/{comment_id}/edit", summary="Update comment")
def update_comment(
    comment_id: int,
    request: Request,
    content: str = Form(..., min_length=COMMENT_CONTENT_MIN_LENGTH, max_length=COMMENT_CONTENT_MAX_LENGTH),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if comment.user_id != current_user.id and current_user.role != "admin":
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

    comment.content = content
    db.commit()
    db.refresh(comment)

    return RedirectResponse(
        url=f"/campaigns/{comment.campaign_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )

@router.post("/comments/{comment_id}/like")
def like_comment(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404)
    
    existing = likes_collection.find_one({
        "comment_id": comment_id,
        "user_id": current_user.id
    })
    
    if existing:
        likes_collection.delete_one({"_id": existing["_id"]})
    else:
        likes_collection.insert_one({
            "comment_id": comment_id,
            "user_id": current_user.id,
            "created_at": datetime.utcnow()
        })

    count = likes_collection.count_documents({"comment_id": comment_id})
    liked = likes_collection.find_one({"comment_id": comment_id, "user_id": current_user.id}) is not None
    
    return {"count": count, "liked": liked}