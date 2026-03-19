from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference
from starlette.middleware.sessions import SessionMiddleware

from routes.user import router as user_router
from routes.campaign import router as campaign_router
from routes.donation import router as donation_router
from routes.comment import router as comment_router

app = FastAPI(
    title="Charity Fundraising API",
    description="API for managing charity campaigns, donations, and comments.",
    version="1.0.0",
)


@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )

app.add_middleware(SessionMiddleware, secret_key="CHANGE_ME_SECRET_KEY")

app.include_router(user_router)
app.include_router(campaign_router)
app.include_router(donation_router)
app.include_router(comment_router)
