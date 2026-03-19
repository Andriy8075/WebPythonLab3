from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pymongo.database import Database

from auth import get_password_hash, verify_password
from db import get_db

# Validation limits
EMAIL_MAX_LENGTH = 64
PASSWORD_MAX_LENGTH = 255

router = APIRouter(tags=["user"])
templates = Jinja2Templates(directory="templates")


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {"request": request},
    )


@router.post("/register", summary="Create new user account")
def register(
    request: Request,
    email: str = Form(..., max_length=EMAIL_MAX_LENGTH),
    password: str = Form(..., min_length=1, max_length=PASSWORD_MAX_LENGTH),
    db: Database = Depends(get_db),
):
    email = email.strip().lower()
    if not email:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Email is required."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    existing = db.users.find_one({"email": email})
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": "A user with this email already exists.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    is_first_user = db.users.count_documents({}) == 0
    role = "admin" if is_first_user else "user"

    doc = {
        "email": email,
        "hashed_password": get_password_hash(password),
        "role": role,
    }
    result = db.users.insert_one(doc)
    user_id = str(result.inserted_id)

    request.session["user_id"] = user_id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse, summary="Login form")
def login_form(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request},
    )


@router.post("/login", summary="Authenticate user")
def login(
    request: Request,
    email: str = Form(..., max_length=EMAIL_MAX_LENGTH),
    password: str = Form(..., max_length=PASSWORD_MAX_LENGTH),
    db: Database = Depends(get_db),
):
    email = email.strip().lower()
    user = db.users.find_one({"email": email})
    if not user or not verify_password(password, user["hashed_password"]):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Incorrect email or password.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    request.session["user_id"] = str(user["_id"])
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout", summary="End user session")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
