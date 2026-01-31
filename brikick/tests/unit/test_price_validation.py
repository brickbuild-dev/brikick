import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from services.price_validation import validate_lot_price, PriceValidationResult
from tests.factories.catalog_factory import CatalogItemFactory, PriceGuideFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.user_factory import UserFactory


class TestPriceValidation:
    """Tests for HARD RULE #1: Price cap at 2x avg 6 months"""

    @pytest.mark.asyncio
    async def test_price_within_cap_is_valid(self, db_session: AsyncSession):
        """Price at or below 2x avg should be valid"""
        item = await CatalogItemFactory.create(db_session)
        await PriceGuideFactory.create(
            db_session,
            catalog_item_id=item.id,
            avg_price=Decimal("1.00"),
        )

        result = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("1.50"),
            store_id=1,
        )

        assert result.valid is True
        assert result.error_code is None

    @pytest.mark.asyncio
    async def test_price_at_exact_cap_is_valid(self, db_session: AsyncSession):
        """Price at exactly 2x avg should be valid"""
        item = await CatalogItemFactory.create(db_session)
        await PriceGuideFactory.create(
            db_session,
            catalog_item_id=item.id,
            avg_price=Decimal("1.00"),
        )

        result = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("2.00"),
            store_id=1,
        )

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_price_above_cap_is_invalid(self, db_session: AsyncSession):
        """Price above 2x avg should be invalid"""
        item = await CatalogItemFactory.create(db_session)
        await PriceGuideFactory.create(
            db_session,
            catalog_item_id=item.id,
            avg_price=Decimal("1.00"),
        )

        result = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("2.50"),
            store_id=1,
        )

        assert result.valid is False
        assert result.error_code == "PRICE_CAP_EXCEEDED"
        assert "REQUEST_OVERRIDE" in result.actions
        assert result.data["price_cap"] == 2.00

    @pytest.mark.asyncio
    async def test_price_without_guide_is_valid(self, db_session: AsyncSession):
        """Without price guide data, any price should be valid"""
        item = await CatalogItemFactory.create(db_session)

        result = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("100.00"),
            store_id=1,
        )

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_approved_override_allows_higher_price(self, db_session: AsyncSession):
        """With approved override, price above cap should be valid"""
        user = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=user.id)
        item = await CatalogItemFactory.create(db_session)
        await PriceGuideFactory.create(
            db_session,
            catalog_item_id=item.id,
            avg_price=Decimal("1.00"),
        )

        from db.models.catalog import PriceOverrideRequest

        override = PriceOverrideRequest(
            store_id=store.id,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            requested_price=Decimal("5.00"),
            price_cap=Decimal("2.00"),
            justification="Rare variant",
            status="APPROVED",
        )
        db_session.add(override)
        await db_session.commit()

        result = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("4.00"),
            store_id=store.id,
        )

        assert result.valid is True

    @pytest.mark.asyncio
    async def test_different_conditions_have_different_caps(self, db_session: AsyncSession):
        """New and Used should have separate price guides"""
        item = await CatalogItemFactory.create(db_session)

        await PriceGuideFactory.create(
            db_session,
            catalog_item_id=item.id,
            condition="N",
            avg_price=Decimal("2.00"),
        )

        await PriceGuideFactory.create(
            db_session,
            catalog_item_id=item.id,
            condition="U",
            avg_price=Decimal("1.00"),
        )

        result_new = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("3.00"),
            store_id=1,
        )
        assert result_new.valid is True

        result_used = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="U",
            unit_price=Decimal("3.00"),
            store_id=1,
        )
        assert result_used.valid is False
