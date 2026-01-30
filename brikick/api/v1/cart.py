from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user_id, get_db
from db.models.cart import Cart, CartItem, CartStore
from db.models.catalog import CatalogItem
from db.models.inventory import Lot
from db.models.stores import Store

cart_router = APIRouter(prefix="/cart", tags=["cart"])


class CartAddItemRequest(BaseModel):
    lot_id: int
    quantity: int = Field(gt=0)


class CartUpdateItemRequest(BaseModel):
    quantity: int = Field(gt=0)


def _to_float(value: Decimal | None) -> float:
    return float(value or 0)


def _to_float_or_none(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _compute_sale_price(unit_price: Decimal, sale_percentage: int | None) -> Decimal | None:
    if not sale_percentage:
        return None
    discount = Decimal(sale_percentage) / Decimal("100")
    price = unit_price * (Decimal("1") - discount)
    return price.quantize(Decimal("0.0001"))


async def _get_cart_by_user(db: AsyncSession, user_id: int) -> Cart | None:
    stmt = select(Cart).where(Cart.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def _get_or_create_cart(db: AsyncSession, user_id: int) -> Cart:
    cart = await _get_cart_by_user(db, user_id)
    if cart:
        return cart
    cart = Cart(user_id=user_id)
    db.add(cart)
    await db.flush()
    return cart


async def _get_or_create_cart_store(
    db: AsyncSession,
    cart_id: int,
    store_id: int,
) -> CartStore:
    stmt = select(CartStore).where(
        CartStore.cart_id == cart_id,
        CartStore.store_id == store_id,
    )
    result = await db.execute(stmt)
    cart_store = result.scalars().first()
    if cart_store:
        return cart_store
    cart_store = CartStore(cart_id=cart_id, store_id=store_id)
    db.add(cart_store)
    await db.flush()
    return cart_store


async def _recalculate_cart_store(db: AsyncSession, cart_store: CartStore) -> None:
    stmt = (
        select(CartItem, Lot, CatalogItem)
        .join(Lot, CartItem.lot_id == Lot.id)
        .join(CatalogItem, Lot.catalog_item_id == CatalogItem.id, isouter=True)
        .where(CartItem.cart_store_id == cart_store.id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        cart = await db.get(Cart, cart_store.cart_id)
        if cart:
            cart.updated_at = datetime.now(timezone.utc)
        await db.delete(cart_store)
        return

    total_items = 0
    total_lots = 0
    subtotal = Decimal("0")
    total_weight = 0

    for item, lot, catalog in rows:
        price = (
            item.sale_price_snapshot
            if item.sale_price_snapshot is not None
            else item.unit_price_snapshot
        )
        subtotal += price * item.quantity
        total_items += item.quantity
        total_lots += 1
        if catalog and catalog.weight_grams:
            total_weight += int(catalog.weight_grams * item.quantity)

    cart_store.total_items = total_items
    cart_store.total_lots = total_lots
    cart_store.subtotal = subtotal.quantize(Decimal("0.01"))
    cart_store.total_weight_grams = total_weight
    cart_store.updated_at = datetime.now(timezone.utc)

    cart = await db.get(Cart, cart_store.cart_id)
    if cart:
        cart.updated_at = datetime.now(timezone.utc)


async def _build_cart_response(db: AsyncSession, cart: Cart | None) -> dict:
    if cart is None:
        return {"cart_id": None, "items_total": 0.0, "stores": []}

    stmt = (
        select(CartStore, CartItem, Lot, Store)
        .join(CartItem, CartItem.cart_store_id == CartStore.id)
        .join(Lot, CartItem.lot_id == Lot.id)
        .join(Store, CartStore.store_id == Store.id)
        .where(CartStore.cart_id == cart.id)
        .order_by(CartStore.store_id, CartItem.added_at)
    )
    result = await db.execute(stmt)
    rows = result.all()

    stores: dict[int, dict] = {}
    items_total = Decimal("0")

    for cart_store, item, lot, store in rows:
        if store.id not in stores:
            stores[store.id] = {
                "store_id": store.id,
                "store_name": store.name,
                "store_slug": store.slug,
                "total_items": cart_store.total_items,
                "total_lots": cart_store.total_lots,
                "subtotal": _to_float(cart_store.subtotal),
                "total_weight_grams": cart_store.total_weight_grams,
                "shipping_estimate": None,
                "items": [],
            }
            items_total += cart_store.subtotal or Decimal("0")

        stores[store.id]["items"].append(
            {
                "id": item.id,
                "lot_id": item.lot_id,
                "quantity": item.quantity,
                "unit_price_snapshot": _to_float(item.unit_price_snapshot),
                "sale_price_snapshot": _to_float_or_none(item.sale_price_snapshot),
                "warnings": item.warnings,
            }
        )

    return {
        "cart_id": cart.id,
        "items_total": _to_float(items_total),
        "stores": list(stores.values()),
    }


@cart_router.get("")
async def get_cart(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    cart = await _get_cart_by_user(db, user_id)
    return await _build_cart_response(db, cart)


@cart_router.get("/count")
async def get_cart_count(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    cart = await _get_cart_by_user(db, user_id)
    if cart is None:
        return {"total_items": 0, "total_lots": 0}

    stmt = (
        select(
            func.coalesce(func.sum(CartItem.quantity), 0),
            func.count(CartItem.id),
        )
        .join(CartStore, CartItem.cart_store_id == CartStore.id)
        .where(CartStore.cart_id == cart.id)
    )
    result = await db.execute(stmt)
    total_items, total_lots = result.one()

    return {"total_items": int(total_items), "total_lots": int(total_lots)}


@cart_router.post("/add")
async def add_to_cart(
    payload: CartAddItemRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    lot = await db.get(Lot, payload.lot_id)
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found.")

    if lot.status != "AVAILABLE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lot is not available.",
        )

    if payload.quantity > lot.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested quantity exceeds available stock.",
        )

    store = await db.get(Store, lot.store_id)
    if not store or store.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Store is not active.",
        )

    cart = await _get_or_create_cart(db, user_id)
    cart_store = await _get_or_create_cart_store(db, cart.id, store.id)

    item_stmt = select(CartItem).where(
        CartItem.cart_store_id == cart_store.id,
        CartItem.lot_id == lot.id,
    )
    item_result = await db.execute(item_stmt)
    item = item_result.scalars().first()

    if item:
        new_qty = item.quantity + payload.quantity
        if new_qty > lot.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested quantity exceeds available stock.",
            )
        item.quantity = new_qty
    else:
        sale_price = _compute_sale_price(lot.unit_price, lot.sale_percentage)
        item = CartItem(
            cart_store_id=cart_store.id,
            lot_id=lot.id,
            quantity=payload.quantity,
            unit_price_snapshot=lot.unit_price,
            sale_price_snapshot=sale_price,
            warnings=None,
        )
        db.add(item)

    await _recalculate_cart_store(db, cart_store)
    await db.commit()

    return await _build_cart_response(db, cart)


@cart_router.put("/items/{item_id}")
async def update_cart_item(
    item_id: int,
    payload: CartUpdateItemRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    cart = await _get_cart_by_user(db, user_id)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found.")

    stmt = (
        select(CartItem, CartStore)
        .join(CartStore, CartItem.cart_store_id == CartStore.id)
        .where(CartItem.id == item_id, CartStore.cart_id == cart.id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")

    item, cart_store = row
    lot = await db.get(Lot, item.lot_id)
    if not lot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot not found.")

    if lot.status != "AVAILABLE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lot is not available.",
        )

    if payload.quantity > lot.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested quantity exceeds available stock.",
        )

    item.quantity = payload.quantity
    await _recalculate_cart_store(db, cart_store)
    await db.commit()

    return await _build_cart_response(db, cart)


@cart_router.delete("/items/{item_id}")
async def delete_cart_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    cart = await _get_cart_by_user(db, user_id)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found.")

    stmt = (
        select(CartItem, CartStore)
        .join(CartStore, CartItem.cart_store_id == CartStore.id)
        .where(CartItem.id == item_id, CartStore.cart_id == cart.id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found.")

    item, cart_store = row
    await db.delete(item)
    await _recalculate_cart_store(db, cart_store)
    await db.commit()

    return await _build_cart_response(db, cart)


@cart_router.delete("/stores/{store_id}")
async def delete_cart_store(
    store_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> dict:
    cart = await _get_cart_by_user(db, user_id)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found.")

    cart_store_stmt = select(CartStore).where(
        CartStore.cart_id == cart.id,
        CartStore.store_id == store_id,
    )
    cart_store_result = await db.execute(cart_store_stmt)
    cart_store = cart_store_result.scalars().first()
    if not cart_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart store not found.",
        )

    await db.execute(
        delete(CartItem).where(CartItem.cart_store_id == cart_store.id)
    )
    await db.delete(cart_store)
    cart.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return await _build_cart_response(db, cart)
