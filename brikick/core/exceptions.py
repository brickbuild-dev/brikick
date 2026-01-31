from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ErrorCodes:
    PRICE_CAP_EXCEEDED = "price_cap_exceeded"
    FAIR_SHIPPING_VIOLATION = "fair_shipping_violation"
    INVALID_TOKEN = "invalid_token"


class BrikickError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class PriceCapExceededError(BrikickError):
    def __init__(self, *, price: Any, limit: Any, avg_price_6m: Any) -> None:
        super().__init__(
            code=ErrorCodes.PRICE_CAP_EXCEEDED,
            message="Price exceeds allowed cap.",
            status_code=400,
            details={
                "price": str(price),
                "limit": str(limit),
                "avg_price_6m": str(avg_price_6m),
            },
        )


class FairShippingError(BrikickError):
    def __init__(self, *, shipping_cost: Any, benchmark_max: Any) -> None:
        super().__init__(
            code=ErrorCodes.FAIR_SHIPPING_VIOLATION,
            message="Shipping cost exceeds fair shipping benchmark.",
            status_code=400,
            details={
                "shipping_cost": str(shipping_cost),
                "benchmark_max": str(benchmark_max),
            },
        )


class InvalidTokenError(BrikickError):
    def __init__(self) -> None:
        super().__init__(
            code=ErrorCodes.INVALID_TOKEN,
            message="Invalid authentication token.",
            status_code=401,
            details={},
        )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BrikickError)
    async def brikick_error_handler(
        request: Request,
        exc: BrikickError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )
