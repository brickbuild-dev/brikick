from fastapi import APIRouter

from api.v1.cart import cart_router

api_router = APIRouter()

api_router.include_router(cart_router)


@api_router.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}
