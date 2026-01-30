from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user_id, get_db
from db.models.cart import Cart, CartItem, CartStore
from db.models.checkout import CheckoutApproval, CheckoutDraft, UserAddress
from db.models.inventory import Lot
from db.models.penalties import UserPenalty
from db.models.rating import UserRatingMetrics
from db.models.stores import Store, StorePaymentMethod, StoreShippingMethod
from db.models.users import User
from services.penalty_service import get_current_penalty

checkout_router = APIRouter(prefix="/checkout", tags=["checkout"])


class CheckoutPrepareRequest(BaseModel):
    store_id: int


class CheckoutShippingRequest(BaseModel):
    shipping_method_id: int | None = None
    address_id: int | None = None


class CheckoutPaymentRequest(BaseModel):
    payment_method_id: int | None = None


def _to_float(value: Decimal | None) -> float:
    return float(value or 0)


def _to_float_or_none(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _shipping_required_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "SHIPPING_REQUIRED",
            "message": "Um metodo de envio deve ser selecionado",
            "actions": ["SELECT_SHIPPING_METHOD"],
        },
    )


def _buyer_restricted_response(penalty: UserPenalty) -> JSONResponse:
    ends_at = penalty.ends_at.isoformat() if penalty.ends_at else None
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error_code": "BUYER_RESTRICTED",
            "message": "A sua conta tem restricoes activas",
            "data": {"restriction": "CANNOT_BUY", "ends_at": ends_at},
        },
    )


def _payment_required_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "PAYMENT_REQUIRED",
            "message": "Um metodo de pagamento deve ser selecionado",
            "actions": ["SELECT_PAYMENT_METHOD"],
        },
    )


def _address_required_response() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "ADDRESS_REQUIRED",
            "message": "Endereco de envio incompleto",
            "actions": ["UPDATE_ADDRESS"],
        },
    )


def _is_address_complete(address: UserAddress | None) -> bool:
    if address is None:
        return False
    required = [
        address.first_name,
        address.last_name,
        address.address_line1,
        address.city,
        address.postal_code,
        address.country_code,
        address.phone,
    ]
    return all(value and str(value).strip() for value in required)


def _calculate_totals(
    items_total: Decimal,
    shipping_cost: Decimal | None,
    insurance_cost: Decimal | None,
    tracking_fee: Decimal | None,
    tax_total: Decimal,
) -> tuple[Decimal, Decimal]:
    shipping_cost_value = shipping_cost or Decimal("0")
    insurance_value = insurance_cost or Decimal("0")
    tracking_value = tracking_fee or Decimal("0")
    shipping_total = shipping_cost_value + insurance_value + tracking_value
    grand_total = items_total + shipping_total + tax_total
    return shipping_total, grand_total


async def _get_cart_store_for_user(
    db: AsyncSession,
    user_id: int,
    store_id: int,
) -> CartStore | None:
    stmt = (
        select(CartStore)
        .join(Cart, CartStore.cart_id == Cart.id)
        .where(Cart.user_id == user_id, CartStore.store_id == store_id)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def _get_active_cart_items(
    db: AsyncSession,
    cart_store_id: int,
) -> list[CartItem]:
    stmt = select(CartItem).where(CartItem.cart_store_id == cart_store_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _calculate_items_total(items: list[CartItem]) -> Decimal:
    total = Decimal("0")
    for item in items:
        price = item.sale_price_snapshot or item.unit_price_snapshot
        total += price * item.quantity
    return total.quantize(Decimal("0.01"))


def _serialize_draft(draft: CheckoutDraft) -> dict:
    return {
        "id": draft.id,
        "cart_store_id": draft.cart_store_id,
        "user_id": draft.user_id,
        "store_id": draft.store_id,
        "status": draft.status,
        "shipping_address_id": draft.shipping_address_id,
        "shipping_method_id": draft.shipping_method_id,
        "shipping_cost": _to_float_or_none(draft.shipping_cost),
        "insurance_cost": _to_float(draft.insurance_cost),
        "tracking_fee": _to_float(draft.tracking_fee),
        "payment_method_id": draft.payment_method_id,
        "payment_currency_id": draft.payment_currency_id,
        "items_total": _to_float(draft.items_total),
        "shipping_total": _to_float(draft.shipping_total),
        "tax_total": _to_float(draft.tax_total),
        "grand_total": _to_float(draft.grand_total),
        "quote_snapshot": draft.quote_snapshot,
        "payment_session_id": draft.payment_session_id,
        "payment_provider": draft.payment_provider,
        "created_at": draft.created_at.isoformat(),
        "updated_at": draft.updated_at.isoformat(),
        "expires_at": draft.expires_at.isoformat() if draft.expires_at else None,
    }


async def _get_draft_for_user(
    db: AsyncSession,
    user_id: int,
    draft_id: int,
) -> CheckoutDraft | None:
    stmt = select(CheckoutDraft).where(
        CheckoutDraft.id == draft_id,
        CheckoutDraft.user_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def _get_store_shipping_methods(
    db: AsyncSession,
    store_id: int,
) -> list[StoreShippingMethod]:
    stmt = select(StoreShippingMethod).where(
        StoreShippingMethod.store_id == store_id,
        or_(
            StoreShippingMethod.is_active.is_(None),
            StoreShippingMethod.is_active.is_(True),
        ),
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _serialize_shipping_method(method: StoreShippingMethod) -> dict:
    return {
        "id": method.id,
        "name": method.name,
        "note": method.note,
        "ships_to_countries": method.ships_to_countries,
        "cost_type": method.cost_type,
        "base_cost": _to_float_or_none(method.base_cost),
        "tracking_type": method.tracking_type,
        "insurance_available": method.insurance_available,
        "min_days": method.min_days,
        "max_days": method.max_days,
        "is_active": method.is_active,
    }


@checkout_router.post("/prepare")
async def prepare_checkout(
    payload: CheckoutPrepareRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    cart_store = await _get_cart_store_for_user(db, user_id, payload.store_id)
    if cart_store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart store not found.")

    store = await db.get(Store, payload.store_id)
    if not store or store.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Store is not active.",
        )

    items = await _get_active_cart_items(db, cart_store.id)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart store is empty.",
        )

    user = await db.get(User, user_id)
    currency_id = store.currency_id or (user.preferred_currency_id if user else None)
    if currency_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment currency not available.",
        )

    items_total = await _calculate_items_total(items)
    shipping_total, grand_total = _calculate_totals(
        items_total,
        shipping_cost=None,
        insurance_cost=Decimal("0"),
        tracking_fee=Decimal("0"),
        tax_total=Decimal("0"),
    )

    draft_stmt = (
        select(CheckoutDraft)
        .where(
            CheckoutDraft.cart_store_id == cart_store.id,
            CheckoutDraft.user_id == user_id,
            CheckoutDraft.status.in_(["DRAFT", "PENDING_SHIPPING", "PENDING_PAYMENT"]),
        )
        .order_by(CheckoutDraft.updated_at.desc())
    )
    draft_result = await db.execute(draft_stmt)
    draft = draft_result.scalars().first()

    quote_snapshot = {
        "store_id": store.id,
        "items": [
            {
                "lot_id": item.lot_id,
                "quantity": item.quantity,
                "unit_price_snapshot": _to_float(item.unit_price_snapshot),
                "sale_price_snapshot": _to_float_or_none(item.sale_price_snapshot),
            }
            for item in items
        ],
    }

    if draft is None:
        draft = CheckoutDraft(
            cart_store_id=cart_store.id,
            user_id=user_id,
            store_id=store.id,
            payment_currency_id=currency_id,
            items_total=items_total,
            shipping_total=shipping_total,
            tax_total=Decimal("0"),
            grand_total=grand_total,
            quote_snapshot=quote_snapshot,
        )
        db.add(draft)
        await db.flush()
    else:
        draft.payment_currency_id = currency_id
        draft.items_total = items_total
        draft.shipping_total = shipping_total
        draft.tax_total = Decimal("0")
        draft.grand_total = grand_total
        draft.quote_snapshot = quote_snapshot
        draft.updated_at = datetime.now(timezone.utc)

    shipping_methods = await _get_store_shipping_methods(db, store.id)
    await db.commit()

    return {
        "draft": _serialize_draft(draft),
        "shipping_methods": [
            _serialize_shipping_method(method) for method in shipping_methods
        ],
    }


@checkout_router.get("/{draft_id}/shipping-methods")
async def get_shipping_methods(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    draft = await _get_draft_for_user(db, user_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkout draft not found.")

    shipping_methods = await _get_store_shipping_methods(db, draft.store_id)
    return {"shipping_methods": [_serialize_shipping_method(m) for m in shipping_methods]}


@checkout_router.put("/{draft_id}/shipping")
async def update_shipping(
    draft_id: int,
    payload: CheckoutShippingRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    if payload.shipping_method_id is None:
        return _shipping_required_response()

    draft = await _get_draft_for_user(db, user_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkout draft not found.")

    method = await db.get(StoreShippingMethod, payload.shipping_method_id)
    if not method or method.store_id != draft.store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipping method not found.")

    if method.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipping method is not active.",
        )

    address = None
    if payload.address_id is not None:
        address = await db.get(UserAddress, payload.address_id)
        if not address or address.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found.")

    if not _is_address_complete(address):
        return _address_required_response()

    items = await _get_active_cart_items(db, draft.cart_store_id)
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart store is empty.")

    items_total = await _calculate_items_total(items)
    shipping_cost = method.base_cost or Decimal("0")
    shipping_total, grand_total = _calculate_totals(
        items_total,
        shipping_cost=shipping_cost,
        insurance_cost=draft.insurance_cost,
        tracking_fee=draft.tracking_fee,
        tax_total=draft.tax_total,
    )

    draft.shipping_method_id = method.id
    draft.shipping_address_id = address.id if address else None
    draft.shipping_cost = shipping_cost
    draft.items_total = items_total
    draft.shipping_total = shipping_total
    draft.grand_total = grand_total
    draft.status = "PENDING_PAYMENT"
    draft.updated_at = datetime.now(timezone.utc)

    await db.commit()
    return {"draft": _serialize_draft(draft)}


@checkout_router.put("/{draft_id}/payment")
async def update_payment(
    draft_id: int,
    payload: CheckoutPaymentRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    if payload.payment_method_id is None:
        return _payment_required_response()

    draft = await _get_draft_for_user(db, user_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkout draft not found.")

    method = await db.get(StorePaymentMethod, payload.payment_method_id)
    if not method or method.store_id != draft.store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found.")

    if method.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment method is not active.",
        )

    draft.payment_method_id = method.id
    draft.payment_provider = method.method_type
    draft.status = "PENDING_PAYMENT"
    draft.updated_at = datetime.now(timezone.utc)

    await db.commit()
    return {"draft": _serialize_draft(draft)}


@checkout_router.post("/{draft_id}/submit")
async def submit_checkout(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    draft = await _get_draft_for_user(db, user_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkout draft not found.")

    if draft.shipping_method_id is None:
        return _shipping_required_response()

    if draft.payment_method_id is None:
        return _payment_required_response()

    address = await db.get(UserAddress, draft.shipping_address_id)
    if not _is_address_complete(address):
        return _address_required_response()

    cart_store = await db.get(CartStore, draft.cart_store_id)
    if cart_store is None or cart_store.store_id != draft.store_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart store not found.")

    store = await db.get(Store, draft.store_id)
    if not store or store.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Store is not active.",
        )

    items = await _get_active_cart_items(db, cart_store.id)
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart store is empty.")

    lots_stmt = (
        select(Lot)
        .where(Lot.id.in_([item.lot_id for item in items]))
    )
    lots_result = await db.execute(lots_stmt)
    lots = {lot.id: lot for lot in lots_result.scalars().all()}

    for item in items:
        lot = lots.get(item.lot_id)
        if not lot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found.")
        if lot.status != "AVAILABLE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Lot is not available.",
            )
        if item.quantity > lot.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Lot stock changed.",
            )

    penalty = await get_current_penalty(db, user_id)
    if penalty and (
        penalty.penalty_type in {"BAN", "SUSPENSION"}
        or (penalty.restrictions or {}).get("can_buy") is False
    ):
        return _buyer_restricted_response(penalty)

    approval_required = False
    if store.require_approval_for_risky_buyers:
        rating_stmt = (
            select(UserRatingMetrics)
            .where(UserRatingMetrics.user_id == user_id)
            .order_by(UserRatingMetrics.calculated_at.desc())
            .limit(1)
        )
        rating_result = await db.execute(rating_stmt)
        rating = rating_result.scalars().first()
        if rating and rating.overall_score is not None:
            approval_required = rating.overall_score < store.risk_threshold_score

    items_total = await _calculate_items_total(items)
    shipping_total, grand_total = _calculate_totals(
        items_total,
        shipping_cost=draft.shipping_cost,
        insurance_cost=draft.insurance_cost,
        tracking_fee=draft.tracking_fee,
        tax_total=draft.tax_total,
    )
    draft.items_total = items_total
    draft.shipping_total = shipping_total
    draft.grand_total = grand_total
    draft.status = "COMPLETED"
    draft.updated_at = datetime.now(timezone.utc)

    if approval_required:
        approval = CheckoutApproval(
            checkout_draft_id=draft.id,
            user_id=user_id,
            store_id=store.id,
        )
        db.add(approval)

    await db.execute(delete(CartItem).where(CartItem.cart_store_id == cart_store.id))
    cart_store.total_items = 0
    cart_store.total_lots = 0
    cart_store.subtotal = Decimal("0")
    cart_store.total_weight_grams = 0
    cart_store.updated_at = datetime.now(timezone.utc)

    cart = await db.get(Cart, cart_store.cart_id)
    if cart:
        cart.updated_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "draft": _serialize_draft(draft),
        "approval_required": approval_required,
    }
