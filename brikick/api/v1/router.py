from fastapi import APIRouter

from api.v1.auth import auth_router
from api.v1.cart import cart_router
from api.v1.catalog import catalog_router
from api.v1.checkout import checkout_router
from api.v1.orders import orders_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(cart_router)
api_router.include_router(catalog_router)
api_router.include_router(checkout_router)
api_router.include_router(orders_router)


@api_router.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}
