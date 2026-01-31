# Guia de Testes para Brikick

> **Configuração completa de pytest para FastAPI + PostgreSQL async**

---

## PROMPT 1: Setup da Suite de Testes

Copia e envia este prompt ao GPT Codex:

```
Configura a suite de testes completa para o projeto Brikick.

=== ESTRUTURA ===

tests/
├── conftest.py              # Fixtures globais
├── factories/
│   ├── __init__.py
│   ├── user_factory.py
│   ├── catalog_factory.py
│   ├── store_factory.py
│   ├── lot_factory.py
│   ├── order_factory.py
│   └── rating_factory.py
├── unit/
│   ├── __init__.py
│   ├── test_price_validation.py
│   ├── test_shipping_fairness.py
│   ├── test_rating_calculation.py
│   ├── test_penalty_evaluation.py
│   └── test_sla_calculation.py
├── integration/
│   ├── __init__.py
│   ├── test_auth_endpoints.py
│   ├── test_catalog_endpoints.py
│   ├── test_cart_endpoints.py
│   ├── test_checkout_endpoints.py
│   └── test_order_endpoints.py
└── e2e/
    ├── __init__.py
    └── test_purchase_flow.py

=== DEPENDÊNCIAS ===

Adiciona ao pyproject.toml:

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[project.optional-dependencies]
test = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.24.0",
    "factory-boy>=3.3.0",
    "faker>=19.0.0",
    "aiosqlite>=0.19.0",
]

=== conftest.py ===

```python
import asyncio
from typing import AsyncGenerator, Generator
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from api.deps import get_db, get_current_user
from db.base import Base
from db.models.users import User

# Database de teste em memória
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

async_session_test = async_sessionmaker(
    engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database for each test."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session_test() as session:
        yield session
        await session.rollback()
    
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with overridden dependencies."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(
    client: AsyncClient, 
    db_session: AsyncSession,
    test_user: User
) -> AsyncClient:
    """Client with authenticated user."""
    
    async def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    return client


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    from tests.factories.user_factory import UserFactory
    user = await UserFactory.create(db_session)
    return user


@pytest.fixture
async def test_seller(db_session: AsyncSession) -> User:
    """Create a test seller with store."""
    from tests.factories.user_factory import UserFactory
    from tests.factories.store_factory import StoreFactory
    
    user = await UserFactory.create(db_session, roles=["seller"])
    store = await StoreFactory.create(db_session, user_id=user.id)
    user.store = store
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin."""
    from tests.factories.user_factory import UserFactory
    return await UserFactory.create(db_session, roles=["admin"])
```

Gera o conftest.py completo.
```

---

## PROMPT 2: Factories

```
Cria as factories para gerar dados de teste em tests/factories/:

=== user_factory.py ===

```python
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.users import User, Role, UserRole
from core.security import get_password_hash

fake = Faker()

class UserFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        email: str = None,
        username: str = None,
        password: str = "testpass123",
        roles: list[str] = None,
        **kwargs
    ) -> User:
        user = User(
            email=email or fake.email(),
            username=username or fake.user_name()[:50],
            password_hash=get_password_hash(password),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            country_code="PT",
            is_active=True,
            is_verified=True,
            **kwargs
        )
        db.add(user)
        await db.flush()
        
        # Assign roles
        if roles:
            for role_name in roles:
                role = await db.execute(
                    select(Role).where(Role.name == role_name)
                )
                role = role.scalar_one_or_none()
                if role:
                    user_role = UserRole(user_id=user.id, role_id=role.id)
                    db.add(user_role)
        
        await db.commit()
        await db.refresh(user)
        return user
```

=== catalog_factory.py ===

```python
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.catalog import CatalogItem, Color, Category, PriceGuide
from decimal import Decimal

fake = Faker()

class CatalogItemFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        item_no: str = None,
        item_type: str = "P",
        **kwargs
    ) -> CatalogItem:
        item = CatalogItem(
            item_no=item_no or fake.bothify("####"),
            item_type=item_type,
            name=fake.sentence(nb_words=3),
            status="ACTIVE",
            **kwargs
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

class PriceGuideFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        catalog_item_id: int,
        color_id: int = 0,
        condition: str = "N",
        avg_price: Decimal = Decimal("1.00"),
        **kwargs
    ) -> PriceGuide:
        price_guide = PriceGuide(
            catalog_item_id=catalog_item_id,
            color_id=color_id,
            condition=condition,
            avg_price_6m=avg_price,
            min_price_6m=avg_price * Decimal("0.5"),
            max_price_6m=avg_price * Decimal("1.5"),
            sales_count_6m=100,
            **kwargs
        )
        db.add(price_guide)
        await db.commit()
        await db.refresh(price_guide)
        return price_guide
```

=== store_factory.py ===

```python
class StoreFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        name: str = None,
        **kwargs
    ) -> Store:
        store = Store(
            user_id=user_id,
            name=name or fake.company(),
            slug=fake.slug(),
            country_code="PT",
            currency_id=2,  # EUR
            status="ACTIVE",
            min_buy_amount=Decimal("5.00"),
            **kwargs
        )
        db.add(store)
        await db.commit()
        await db.refresh(store)
        return store
```

=== lot_factory.py ===

```python
class LotFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        store_id: int,
        catalog_item_id: int,
        unit_price: Decimal = Decimal("0.50"),
        quantity: int = 10,
        **kwargs
    ) -> Lot:
        lot = Lot(
            store_id=store_id,
            catalog_item_id=catalog_item_id,
            color_id=kwargs.get("color_id", 0),
            condition=kwargs.get("condition", "N"),
            quantity=quantity,
            unit_price=unit_price,
            status="AVAILABLE",
            **kwargs
        )
        db.add(lot)
        await db.commit()
        await db.refresh(lot)
        return lot
```

Gera todas as factories completas.
```

---

## PROMPT 3: Testes de Price Validation (CRÍTICO)

```
Cria os testes unitários para validação de Price Cap em tests/unit/test_price_validation.py:

```python
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
        # Setup
        item = await CatalogItemFactory.create(db_session)
        await PriceGuideFactory.create(
            db_session,
            catalog_item_id=item.id,
            avg_price=Decimal("1.00")  # Cap will be 2.00
        )
        
        # Test
        result = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("1.50"),  # Below cap of 2.00
            store_id=1
        )
        
        # Assert
        assert result.valid is True
        assert result.error_code is None

    @pytest.mark.asyncio
    async def test_price_at_exact_cap_is_valid(self, db_session: AsyncSession):
        """Price at exactly 2x avg should be valid"""
        item = await CatalogItemFactory.create(db_session)
        await PriceGuideFactory.create(
            db_session,
            catalog_item_id=item.id,
            avg_price=Decimal("1.00")
        )
        
        result = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("2.00"),  # Exactly at cap
            store_id=1
        )
        
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_price_above_cap_is_invalid(self, db_session: AsyncSession):
        """Price above 2x avg should be invalid"""
        item = await CatalogItemFactory.create(db_session)
        await PriceGuideFactory.create(
            db_session,
            catalog_item_id=item.id,
            avg_price=Decimal("1.00")
        )
        
        result = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("2.50"),  # Above cap of 2.00
            store_id=1
        )
        
        assert result.valid is False
        assert result.error_code == "PRICE_CAP_EXCEEDED"
        assert "REQUEST_OVERRIDE" in result.actions
        assert result.data["price_cap"] == 2.00

    @pytest.mark.asyncio
    async def test_price_without_guide_is_valid(self, db_session: AsyncSession):
        """Without price guide data, any price should be valid"""
        item = await CatalogItemFactory.create(db_session)
        # No price guide created
        
        result = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("100.00"),
            store_id=1
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
            avg_price=Decimal("1.00")
        )
        
        # Create approved override
        from db.models.catalog import PriceOverrideRequest
        override = PriceOverrideRequest(
            store_id=store.id,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            requested_price=Decimal("5.00"),
            price_cap=Decimal("2.00"),
            justification="Rare variant",
            status="APPROVED"
        )
        db_session.add(override)
        await db_session.commit()
        
        result = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("4.00"),  # Above cap but below approved
            store_id=store.id
        )
        
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_different_conditions_have_different_caps(self, db_session: AsyncSession):
        """New and Used should have separate price guides"""
        item = await CatalogItemFactory.create(db_session)
        
        # New items: avg 2.00, cap 4.00
        await PriceGuideFactory.create(
            db_session,
            catalog_item_id=item.id,
            condition="N",
            avg_price=Decimal("2.00")
        )
        
        # Used items: avg 1.00, cap 2.00
        await PriceGuideFactory.create(
            db_session,
            catalog_item_id=item.id,
            condition="U",
            avg_price=Decimal("1.00")
        )
        
        # 3.00 valid for New
        result_new = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="N",
            unit_price=Decimal("3.00"),
            store_id=1
        )
        assert result_new.valid is True
        
        # 3.00 invalid for Used
        result_used = await validate_lot_price(
            db=db_session,
            catalog_item_id=item.id,
            color_id=0,
            condition="U",
            unit_price=Decimal("3.00"),
            store_id=1
        )
        assert result_used.valid is False
```

Gera os testes completos.
```

---

## PROMPT 4: Testes de Checkout (Hard Rules)

```
Cria os testes de integração para Checkout em tests/integration/test_checkout_endpoints.py:

```python
import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.user_factory import UserFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.lot_factory import LotFactory
from tests.factories.catalog_factory import CatalogItemFactory


class TestCheckoutEndpoints:
    """Tests for checkout flow with Hard Rules"""

    @pytest.mark.asyncio
    async def test_checkout_requires_shipping_method(
        self, 
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user
    ):
        """HARD RULE: Checkout without shipping method should fail"""
        # Setup: Create store, lot, add to cart
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        
        # Add to cart
        response = await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1}
        )
        assert response.status_code == 200
        
        # Prepare checkout
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id}
        )
        assert response.status_code == 200
        draft_id = response.json()["data"]["id"]
        
        # Try to submit WITHOUT selecting shipping
        response = await authenticated_client.post(
            f"/api/v1/checkout/{draft_id}/submit"
        )
        
        # Should fail
        assert response.status_code == 422
        assert response.json()["error_code"] == "SHIPPING_REQUIRED"

    @pytest.mark.asyncio
    async def test_checkout_no_hidden_fees(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user
    ):
        """No handling fees or hidden costs in checkout"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(
            db_session, 
            store_id=store.id, 
            catalog_item_id=item.id,
            unit_price=Decimal("10.00"),
            quantity=5
        )
        
        # Add shipping method
        from db.models.stores import StoreShippingMethod
        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("5.00"),
            tracking_type="FULL_TRACKING",
            is_active=True
        )
        db_session.add(shipping)
        await db_session.commit()
        
        # Add to cart
        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 2}
        )
        
        # Prepare and configure checkout
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id}
        )
        draft_id = response.json()["data"]["id"]
        
        # Set shipping
        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id}
        )
        
        # Get checkout data
        response = await authenticated_client.get(f"/api/v1/checkout/{draft_id}")
        data = response.json()["data"]
        
        # Verify totals: ONLY items + shipping
        assert data["items_total"] == 20.00  # 2 x 10.00
        assert data["shipping_total"] == 5.00
        assert data["grand_total"] == 25.00
        
        # Verify NO hidden fees fields exist
        assert "handling_fee" not in data
        assert "packaging_fee" not in data
        assert "service_fee" not in data

    @pytest.mark.asyncio
    async def test_checkout_is_automatic_no_invoice_request(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Checkout should be automatic, no 'request invoice' option"""
        # The CheckoutDraft status should never be AWAITING_INVOICE
        from db.models.checkout import CheckoutDraft
        
        # Verify the status enum/choices don't include invoice request
        valid_statuses = ["DRAFT", "PENDING_SHIPPING", "PENDING_PAYMENT", "COMPLETED", "ABANDONED"]
        
        # This is a schema/model test - verify no invoice request status exists
        # In practice, we test that the API doesn't accept/return this status

    @pytest.mark.asyncio
    async def test_untracked_shipping_requires_proof(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_seller
    ):
        """Orders with untracked shipping must require proof"""
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(
            db_session, 
            store_id=test_seller.store.id, 
            catalog_item_id=item.id
        )
        
        # Add untracked shipping method
        from db.models.stores import StoreShippingMethod
        untracked_shipping = StoreShippingMethod(
            store_id=test_seller.store.id,
            name="Regular Mail (No Tracking)",
            cost_type="FIXED",
            base_cost=Decimal("2.00"),
            tracking_type="NO_TRACKING",
            is_active=True
        )
        db_session.add(untracked_shipping)
        await db_session.commit()
        
        # Complete checkout with untracked shipping...
        # ... (setup code)
        
        # When order is marked as shipped
        # Verify shipping_proof_required is True
        # Verify shipping_proof_deadline is set to 48h from now
```

Gera os testes completos para checkout.
```

---

## PROMPT 5: Testes do Sistema de Rating

```
Cria os testes para o sistema de rating em tests/unit/test_rating_calculation.py:

```python
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from services.rating import (
    calculate_user_rating,
    calculate_sla_score,
    evaluate_badges
)
from tests.factories.user_factory import UserFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.order_factory import OrderFactory


class TestSLACalculation:
    """Tests for SLA score calculation"""

    @pytest.mark.asyncio
    async def test_all_orders_shipped_24h_gets_100(self, db_session: AsyncSession):
        """100% orders shipped within 24h = score 100"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        
        # Create 10 orders all shipped within 24h
        for _ in range(10):
            order = await OrderFactory.create(
                db_session,
                store_id=store.id,
                shipped_within_hours=12
            )
        
        score = await calculate_sla_score(db_session, store.id)
        
        assert score.shipping_sla_score == 100.0

    @pytest.mark.asyncio
    async def test_mixed_shipping_times_weighted_correctly(self, db_session: AsyncSession):
        """Mixed shipping times should be weighted: 24h=100%, 48h=80%, 72h=50%, late=0%"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        
        # 5 orders in 24h (weight 1.0)
        # 3 orders in 48h (weight 0.8)
        # 2 orders in 72h (weight 0.5)
        # Expected: (5*1.0 + 3*0.8 + 2*0.5) / 10 * 100 = 84%
        
        for _ in range(5):
            await OrderFactory.create(db_session, store_id=store.id, shipped_within_hours=20)
        for _ in range(3):
            await OrderFactory.create(db_session, store_id=store.id, shipped_within_hours=40)
        for _ in range(2):
            await OrderFactory.create(db_session, store_id=store.id, shipped_within_hours=60)
        
        score = await calculate_sla_score(db_session, store.id)
        
        assert score.shipping_sla_score == pytest.approx(84.0, rel=0.1)

    @pytest.mark.asyncio
    async def test_late_orders_penalize_heavily(self, db_session: AsyncSession):
        """Orders shipped after 72h should contribute 0 to score"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        
        # 5 on time, 5 late
        for _ in range(5):
            await OrderFactory.create(db_session, store_id=store.id, shipped_within_hours=24)
        for _ in range(5):
            await OrderFactory.create(db_session, store_id=store.id, shipped_within_hours=100)
        
        score = await calculate_sla_score(db_session, store.id)
        
        # (5*1.0 + 5*0) / 10 * 100 = 50%
        assert score.shipping_sla_score == 50.0


class TestRatingCalculation:
    """Tests for overall rating calculation"""

    @pytest.mark.asyncio
    async def test_new_seller_starts_with_neutral_rating(self, db_session: AsyncSession):
        """New seller without history should have neutral rating"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        
        rating = await calculate_user_rating(db_session, seller.id)
        
        # New sellers start at 50 (neutral)
        assert rating.overall_score == pytest.approx(50.0, abs=5)
        assert rating.score_tier == "AVERAGE"

    @pytest.mark.asyncio
    async def test_excellent_seller_gets_high_rating(self, db_session: AsyncSession):
        """Seller with excellent metrics should get high rating"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        
        # Create excellent history
        # - 100 orders, all shipped in 24h
        # - 0 disputes lost
        # - 100% message response rate
        # - Prices at market average
        # - Account 12+ months old
        
        # ... setup excellent metrics ...
        
        rating = await calculate_user_rating(db_session, seller.id)
        
        assert rating.overall_score >= 85.0
        assert rating.score_tier == "EXCELLENT"


class TestBadgeAward:
    """Tests for badge awarding"""

    @pytest.mark.asyncio
    async def test_trusted_seller_badge_requires_85_score(self, db_session: AsyncSession):
        """Trusted Seller badge requires overall score >= 85"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        
        # Mock rating at 90
        badges = await evaluate_badges(db_session, seller.id, overall_score=90.0)
        
        assert any(b.code == "TRUSTED_SELLER" for b in badges)

    @pytest.mark.asyncio
    async def test_fast_shipper_badge_requires_95_sla(self, db_session: AsyncSession):
        """Fast Shipper badge requires shipping SLA >= 95%"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        
        badges = await evaluate_badges(
            db_session, 
            seller.id, 
            shipping_sla_score=96.0
        )
        
        assert any(b.code == "FAST_SHIPPER" for b in badges)

    @pytest.mark.asyncio
    async def test_monthly_badges_expire(self, db_session: AsyncSession):
        """Monthly badges should have valid_until set"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        
        badges = await evaluate_badges(db_session, seller.id, overall_score=90.0)
        
        trusted_seller = next(b for b in badges if b.code == "TRUSTED_SELLER")
        assert trusted_seller.valid_until is not None
        assert trusted_seller.valid_until > datetime.utcnow()
```

Gera os testes completos.
```

---

## PROMPT 6: Testes de Penalizações

```
Cria os testes para penalizações em tests/unit/test_penalty_evaluation.py:

```python
import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from services.penalty_service import evaluate_user_penalties, get_active_issues
from db.models.penalties import UserIssue, UserPenalty
from tests.factories.user_factory import UserFactory


class TestPenaltyEvaluation:
    """Tests for automatic penalty evaluation"""

    @pytest.mark.asyncio
    async def test_no_issues_no_penalty(self, db_session: AsyncSession):
        """User with no issues should have no penalty"""
        user = await UserFactory.create(db_session)
        
        await evaluate_user_penalties(user.id, db_session)
        
        penalty = await db_session.execute(
            select(UserPenalty).where(UserPenalty.user_id == user.id)
        )
        assert penalty.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_3_issues_triggers_warning(self, db_session: AsyncSession):
        """3 issues should trigger WARNING"""
        user = await UserFactory.create(db_session)
        
        # Create 3 issues
        for i in range(3):
            issue = UserIssue(
                user_id=user.id,
                issue_type="DISPUTE_LOST",
                severity=2,
                expires_at=datetime.utcnow() + timedelta(days=365)
            )
            db_session.add(issue)
        await db_session.commit()
        
        await evaluate_user_penalties(user.id, db_session)
        
        penalty = await db_session.execute(
            select(UserPenalty)
            .where(UserPenalty.user_id == user.id)
            .where(UserPenalty.penalty_type == "WARNING")
        )
        assert penalty.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_5_issues_triggers_cooldown(self, db_session: AsyncSession):
        """5 issues should trigger COOLDOWN"""
        user = await UserFactory.create(db_session)
        
        for i in range(5):
            issue = UserIssue(
                user_id=user.id,
                issue_type="DISPUTE_LOST",
                severity=2,
                expires_at=datetime.utcnow() + timedelta(days=365)
            )
            db_session.add(issue)
        await db_session.commit()
        
        await evaluate_user_penalties(user.id, db_session)
        
        penalty = await db_session.execute(
            select(UserPenalty)
            .where(UserPenalty.user_id == user.id)
            .where(UserPenalty.penalty_type == "COOLDOWN")
        )
        result = penalty.scalar_one_or_none()
        assert result is not None
        assert result.ends_at is not None  # 7 days

    @pytest.mark.asyncio
    async def test_8_issues_triggers_suspension(self, db_session: AsyncSession):
        """8 issues should trigger SUSPENSION"""
        user = await UserFactory.create(db_session)
        
        for i in range(8):
            issue = UserIssue(
                user_id=user.id,
                issue_type="DISPUTE_LOST",
                severity=2,
                expires_at=datetime.utcnow() + timedelta(days=365)
            )
            db_session.add(issue)
        await db_session.commit()
        
        await evaluate_user_penalties(user.id, db_session)
        
        penalty = await db_session.execute(
            select(UserPenalty)
            .where(UserPenalty.user_id == user.id)
            .where(UserPenalty.penalty_type == "SUSPENSION")
        )
        result = penalty.scalar_one_or_none()
        assert result is not None
        assert result.restrictions.get("can_sell") is False

    @pytest.mark.asyncio
    async def test_12_issues_triggers_ban(self, db_session: AsyncSession):
        """12 issues should trigger permanent BAN"""
        user = await UserFactory.create(db_session)
        
        for i in range(12):
            issue = UserIssue(
                user_id=user.id,
                issue_type="DISPUTE_LOST",
                severity=2,
                expires_at=datetime.utcnow() + timedelta(days=365)
            )
            db_session.add(issue)
        await db_session.commit()
        
        await evaluate_user_penalties(user.id, db_session)
        
        penalty = await db_session.execute(
            select(UserPenalty)
            .where(UserPenalty.user_id == user.id)
            .where(UserPenalty.penalty_type == "BAN")
        )
        result = penalty.scalar_one_or_none()
        assert result is not None
        assert result.ends_at is None  # Permanent

    @pytest.mark.asyncio
    async def test_expired_issues_not_counted(self, db_session: AsyncSession):
        """Expired issues should not count towards penalties"""
        user = await UserFactory.create(db_session)
        
        # 5 expired issues
        for i in range(5):
            issue = UserIssue(
                user_id=user.id,
                issue_type="DISPUTE_LOST",
                severity=2,
                created_at=datetime.utcnow() - timedelta(days=400),
                expires_at=datetime.utcnow() - timedelta(days=35)  # Expired
            )
            db_session.add(issue)
        await db_session.commit()
        
        active = await get_active_issues(db_session, user.id, months=6)
        assert active == 0
        
        await evaluate_user_penalties(user.id, db_session)
        
        # No penalty should be applied
        penalty = await db_session.execute(
            select(UserPenalty).where(UserPenalty.user_id == user.id)
        )
        assert penalty.scalar_one_or_none() is None
```

Gera os testes completos.
```

---

## PROMPT 7: Executar os Testes

```
Agora que temos os testes, cria os comandos para executá-los:

=== Makefile ===

```makefile
.PHONY: test test-unit test-integration test-cov

# Run all tests
test:
	pytest tests/ -v

# Run only unit tests
test-unit:
	pytest tests/unit/ -v

# Run only integration tests
test-integration:
	pytest tests/integration/ -v

# Run with coverage
test-cov:
	pytest tests/ --cov=api --cov=services --cov=db --cov-report=html --cov-report=term-missing

# Run specific test file
test-file:
	pytest $(FILE) -v

# Run tests matching pattern
test-match:
	pytest tests/ -v -k "$(PATTERN)"
```

=== Scripts para CI ===

Cria .github/workflows/tests.yml:

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: brikick_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e ".[test]"
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/brikick_test
        run: |
          pytest tests/ -v --cov --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

Gera o Makefile e workflow de CI.
```

---

## Resumo dos Testes a Implementar

| Categoria | Ficheiro | Testes |
|-----------|----------|--------|
| **Price Cap** | test_price_validation.py | 6 testes |
| **Shipping Fairness** | test_shipping_fairness.py | 4 testes |
| **Rating** | test_rating_calculation.py | 6 testes |
| **Penalties** | test_penalty_evaluation.py | 6 testes |
| **SLA** | test_sla_calculation.py | 3 testes |
| **Auth** | test_auth_endpoints.py | 5 testes |
| **Catalog** | test_catalog_endpoints.py | 4 testes |
| **Cart** | test_cart_endpoints.py | 6 testes |
| **Checkout** | test_checkout_endpoints.py | 5 testes |
| **Orders** | test_order_endpoints.py | 6 testes |
| **E2E** | test_purchase_flow.py | 2 testes |

**Total: ~53 testes**

---

## Comando para Executar

Após implementar os prompts acima:

```bash
# Instalar dependências de teste
pip install -e ".[test]"

# Executar todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=api --cov=services --cov-report=html
```
