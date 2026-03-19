from typing import Any, Optional

from bson import ObjectId
from fastapi import Depends, HTTPException, Request, status
import bcrypt
from pymongo.database import Database

from db import get_db

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)


def get_current_user(
    request: Request,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    user_id: Optional[str] = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    user["id"] = str(user["_id"])
    return user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_current_user_optional(
    request: Request, db: Database = Depends(get_db)
) -> Optional[dict[str, Any]]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None
    if user is None:
        return None
    user["id"] = str(user["_id"])
    return user
