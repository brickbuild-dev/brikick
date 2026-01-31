# Guia Completo GPT 5.2 Codex - Brikick V2

> **Versão actualizada com as 21 features inovadoras integradas**

---

## PASSO 1: Contexto Inicial (OBRIGATÓRIO)

Copia e cola este prompt no GPT 5.2 Codex:

```
Vou desenvolver um marketplace de LEGO chamado "Brikick" com a seguinte stack:
- Backend: FastAPI (Python 3.11+)
- Base de Dados: PostgreSQL 15
- Frontend: Next.js 14
- Infraestrutura: Docker Compose + Redis + MinIO

=== VISÃO DO PROJETO ===
Brikick é um marketplace de peças LEGO que resolve os problemas das plataformas existentes (BrickLink, BrickOwl) com foco em:
1. Transparência total de preços e custos
2. Sistema de reputação justo e algorítmico
3. Anti-fraude desde a arquitectura

=== 10 DOMÍNIOS PRINCIPAIS ===
1. Catalog - Items, types, categories, colors, price guide
2. Stores - Profiles, policies, API access, sync config
3. Inventory/Lots - Lots com price cap validation
4. Search - Universal search (multi-platform IDs)
5. Wanted - Wanted lists com filtros avançados
6. Cart - Multi-store cart
7. Checkout - Automático (sem request invoice)
8. Orders - Lifecycle, SLA tracking, provas de envio
9. Billing - Fees, subscriptions premium
10. Auth/RBAC - Users, rating algorítmico, penalizações

=== HARD RULES (OBRIGATÓRIAS) ===
1. PRICE CAP: Preço máximo = 2x avg 6 meses (anti-fraude/lavagem)
2. CHECKOUT AUTOMÁTICO: Sem opção "request invoice", sempre automático
3. SEM HIDDEN FEES: Apenas items + shipping, sem handling/extras
4. SHIPPING OBRIGATÓRIO: Checkout bloqueado sem método de envio
5. PROVA DE ENVIO: Vendedor DEVE provar envio em correio normal
6. FAIR SHIPPING: Portes validados contra benchmarks
7. PENALIZAÇÕES: Sistema automático após X issues

=== SISTEMA DE RATING (substituir feedback antigo) ===
Não usar sistema de feedback tradicional. Implementar rating algorítmico baseado em:
- SLA de envios (24h/48h/72h)
- SLA de respostas a mensagens
- Taxa de disputas ganhas/perdidas
- Taxa de cancelamentos
- Preços praticados vs mercado
- Regularidade de actividade

Confirma que entendes o contexto e as Hard Rules antes de avançarmos.
```

**Espera a confirmação do Codex.**

---

## PASSO 2: Setup do Projecto

```
Cria a estrutura inicial do projeto com Docker Compose completo:

brikick/
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── deps.py
│   └── v1/
│       └── router.py
├── core/
│   ├── config.py          # Settings
│   ├── security.py        # JWT
│   └── exceptions.py      # Custom exceptions com error codes
├── db/
│   ├── session.py
│   ├── base.py
│   └── models/
├── services/
│   ├── price_guide.py     # Price cap validation
│   ├── shipping_fairness.py
│   └── rating.py
├── workers/
│   └── tasks/
├── docker/
├── docker-compose.yml
├── alembic.ini
└── pyproject.toml

docker-compose.yml deve incluir:
- api (FastAPI)
- postgres (PostgreSQL 15)
- redis (Redis 7)
- minio (Object storage)
- worker (Celery para jobs)

pyproject.toml com:
- fastapi, uvicorn[standard]
- sqlalchemy[asyncio], asyncpg
- alembic
- pydantic-settings
- celery[redis]
- python-jose[cryptography]
- passlib[bcrypt]

Gera todos os ficheiros.
```

---

## PASSO 3: Modelos Base - Users e Auth

```
Cria os modelos SQLAlchemy para Users, Roles e Audit em db/models/users.py:

=== USERS ===
User:
- id: BIGSERIAL PK
- email: VARCHAR(255) UNIQUE
- username: VARCHAR(50) UNIQUE  
- password_hash: VARCHAR(255)
- first_name, last_name: VARCHAR(100)
- country_code: CHAR(2)
- preferred_currency_id: INTEGER
- is_active, is_verified: BOOLEAN
- created_at, last_login_at

Role (dados iniciais: user, seller, staff_support, staff_finance, staff_catalog, admin):
- id: SERIAL PK
- name: VARCHAR(50) UNIQUE
- description: TEXT

Permission:
- id: SERIAL PK
- scope: VARCHAR(50)
- action: VARCHAR(50)
- UNIQUE(scope, action)

UserRole (M2M):
- user_id, role_id
- granted_at, granted_by

UserSession:
- id: BIGSERIAL PK
- user_id: FK
- token_hash: VARCHAR(255) UNIQUE
- ip_address: INET
- expires_at, revoked_at

=== AUDIT LOG (CRÍTICO) ===
AuditLog:
- id: BIGSERIAL PK
- user_id: FK
- action: VARCHAR(100)
- entity_type: VARCHAR(50)
- entity_id: BIGINT
- old_values, new_values: JSONB
- ip_address: INET
- reason: TEXT
- created_at

Inclui índices em audit_log para: user_id, entity_type+entity_id, action, created_at.
Gera também a migration Alembic.
```

---

## PASSO 4: Catálogo e Price Guide

```
Cria os modelos para Catálogo E Price Guide em db/models/catalog.py:

=== CATÁLOGO ===
ItemType (P=Part, S=Set, M=Minifig, B=Book, G=Gear, C=Catalog, I=Instruction, O=Box, X=MOC):
- id: CHAR(1) PK
- name, name_plural: VARCHAR(50)

Category:
- id: SERIAL PK
- name: VARCHAR(255)
- parent_id: FK self-reference
- allowed_item_types: VARCHAR(20)

Color (ID 0 = "Not Applicable"):
- id: INTEGER PK
- name: VARCHAR(100)
- rgb: VARCHAR(6)
- color_group: INTEGER

CatalogItem:
- id: BIGSERIAL PK
- item_no: VARCHAR(50)
- item_seq: INTEGER DEFAULT 1
- item_type: FK ItemType
- name: VARCHAR(500)
- category_id: FK
- year_released: SMALLINT
- weight_grams: DECIMAL(10,2)
- status: VARCHAR(20) DEFAULT 'ACTIVE'
- UNIQUE(item_no, item_type, item_seq)

CatalogItemMapping (para pesquisa universal):
- id: BIGSERIAL PK
- catalog_item_id: FK
- source: VARCHAR(20) -- BRICKLINK, BRICKOWL, REBRICKABLE, LDRAW
- external_id: VARCHAR(100)
- INDEX em (source, external_id) para lookup rápido

=== PRICE GUIDE (CRÍTICO para Hard Rule #1) ===
PriceGuide:
- id: BIGSERIAL PK
- catalog_item_id: FK
- color_id: FK
- condition: VARCHAR(1) -- N, U

- avg_price_6m: DECIMAL(10,4)
- min_price_6m: DECIMAL(10,4)
- max_price_6m: DECIMAL(10,4)
- sales_count_6m: INTEGER

- price_cap: DECIMAL(10,4) GENERATED ALWAYS AS (avg_price_6m * 2.0) STORED

- last_calculated_at: TIMESTAMPTZ
- UNIQUE(catalog_item_id, color_id, condition)

PriceOverrideRequest (para casos legítimos acima do cap):
- id: BIGSERIAL PK
- lot_id: FK (nullable, pode ser antes de criar o lot)
- store_id: FK
- catalog_item_id, color_id, condition
- requested_price: DECIMAL(10,4)
- price_cap: DECIMAL(10,4)
- justification: TEXT NOT NULL

- status: VARCHAR(20) DEFAULT 'PENDING' -- PENDING, APPROVED, REJECTED
- reviewed_by: FK User
- review_notes: TEXT
- reviewed_at: TIMESTAMPTZ

- created_at: TIMESTAMPTZ

Gera migration Alembic.
```

---

## PASSO 5: Stores com API Access

```
Cria os modelos para Stores em db/models/stores.py:

Store:
- id: BIGSERIAL PK
- user_id: FK UNIQUE
- name: VARCHAR(255)
- slug: VARCHAR(100) UNIQUE
- country_code: CHAR(2)
- currency_id: INTEGER
- feedback_score: INTEGER DEFAULT 0 (legado, substituído por rating)
- status: VARCHAR(20) DEFAULT 'ACTIVE'
- min_buy_amount: DECIMAL(10,2)
- instant_checkout_enabled: BOOLEAN DEFAULT TRUE
- require_approval_for_risky_buyers: BOOLEAN DEFAULT FALSE  -- FEATURE #20
- risk_threshold_score: DECIMAL(5,2) DEFAULT 50.0
- created_at, updated_at

StorePolicy:
- id: BIGSERIAL PK
- store_id: FK
- terms_html: TEXT
- shipping_terms_html: TEXT
- has_vat: BOOLEAN
- version: INTEGER
- updated_at

=== API ACCESS (FEATURE #2: Admin-only authorization) ===
StoreApiAccess:
- id: BIGSERIAL PK
- store_id: FK UNIQUE

- status: VARCHAR(20) DEFAULT 'DISABLED' -- DISABLED, PENDING, APPROVED, REVOKED
- api_key_hash: VARCHAR(255)
- api_secret_hash: VARCHAR(255)
- rate_limit_per_minute: INTEGER DEFAULT 60
- rate_limit_per_day: INTEGER DEFAULT 10000

- requested_at: TIMESTAMPTZ
- request_reason: TEXT
- approved_by: FK User
- approved_at: TIMESTAMPTZ

- last_used_at: TIMESTAMPTZ
- total_requests: BIGINT DEFAULT 0

=== SYNC CONFIG (FEATURE #6: Limited to one platform) ===
StoreSyncConfig:
- id: BIGSERIAL PK
- store_id: FK UNIQUE
- sync_platform: VARCHAR(20) -- Apenas 'BRICKLINK' OU 'BRICKOWL'
- sync_enabled: BOOLEAN DEFAULT FALSE
- platform_credentials_encrypted: BYTEA
- last_sync_at: TIMESTAMPTZ
- sync_status: VARCHAR(20)
- items_synced: INTEGER
- CHECK constraint: sync_platform IN ('BRICKLINK', 'BRICKOWL')

StoreShippingMethod:
- id: BIGSERIAL PK
- store_id: FK
- name: VARCHAR(255)
- note: TEXT
- ships_to_countries: TEXT[]
- cost_type: VARCHAR(20) -- FIXED, WEIGHT_BASED, CALCULATED
- base_cost: DECIMAL(10,2)
- tracking_type: VARCHAR(20) -- FULL_TRACKING, DELIVERY_CONFIRMATION, NO_TRACKING
- insurance_available: BOOLEAN
- min_days, max_days: INTEGER
- is_active: BOOLEAN

StorePaymentMethod:
- id: BIGSERIAL PK
- store_id: FK
- method_type: VARCHAR(50)
- name: VARCHAR(100)
- is_on_site: BOOLEAN
- is_active: BOOLEAN

Gera migration.
```

---

## PASSO 6: Lotes com Price Cap Validation

```
Cria os modelos para Inventory em db/models/inventory.py:

Lot:
- id: BIGSERIAL PK
- store_id: FK NOT NULL
- catalog_item_id: FK NOT NULL
- color_id: FK

- condition: VARCHAR(1) NOT NULL -- N, U
- completeness: VARCHAR(1) -- C, B, S, X

- quantity: INTEGER NOT NULL
- bulk_quantity: INTEGER DEFAULT 1

- unit_price: DECIMAL(10,4) NOT NULL
- sale_percentage: INTEGER DEFAULT 0

-- Tier pricing
- tier1_qty, tier1_price
- tier2_qty, tier2_price  
- tier3_qty, tier3_price

- superlot_id: FK self-reference
- description: TEXT
- extended_description: TEXT
- custom_image_url: VARCHAR(500)

- status: VARCHAR(20) DEFAULT 'AVAILABLE'
- listed_at, updated_at: TIMESTAMPTZ

-- Flag se foi aprovado override de preço
- price_override_approved: BOOLEAN DEFAULT FALSE
- price_override_request_id: FK nullable

Índices em: store_id, catalog_item_id, color_id, condition, unit_price, status

=== SERVICE DE VALIDAÇÃO ===

Cria services/price_validation.py:

```python
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.catalog import PriceGuide, PriceOverrideRequest

class PriceValidationResult:
    valid: bool
    error_code: str | None
    message: str | None
    data: dict | None
    actions: list[str] | None

async def validate_lot_price(
    db: AsyncSession,
    catalog_item_id: int,
    color_id: int,
    condition: str,
    unit_price: Decimal,
    store_id: int
) -> PriceValidationResult:
    """
    HARD RULE #1: Preço não pode exceder 2x o avg 6 meses
    """
    price_guide = await db.get(PriceGuide, {
        "catalog_item_id": catalog_item_id,
        "color_id": color_id,
        "condition": condition
    })
    
    if not price_guide or not price_guide.price_cap:
        # Sem dados suficientes, permitir (mas flag para review)
        return PriceValidationResult(valid=True)
    
    if unit_price > price_guide.price_cap:
        # Verificar se há override aprovado
        override = await get_approved_override(db, store_id, catalog_item_id, color_id, condition)
        if override and unit_price <= override.requested_price:
            return PriceValidationResult(valid=True)
        
        return PriceValidationResult(
            valid=False,
            error_code="PRICE_CAP_EXCEEDED",
            message=f"Preço €{unit_price} excede o cap de €{price_guide.price_cap} (2x avg 6m: €{price_guide.avg_price_6m})",
            data={
                "your_price": float(unit_price),
                "avg_6m": float(price_guide.avg_price_6m),
                "price_cap": float(price_guide.price_cap),
                "max_allowed": float(price_guide.price_cap)
            },
            actions=["REQUEST_OVERRIDE", "ADJUST_PRICE"]
        )
    
    return PriceValidationResult(valid=True)
```

Gera migration e o service.
```

---

## PASSO 7: Sistema de Rating Algorítmico

```
Cria os modelos para Rating em db/models/rating.py:

=== CONFIGURAÇÃO DE FACTORES ===
RatingFactor:
- id: SERIAL PK
- factor_code: VARCHAR(50) UNIQUE
- factor_name: VARCHAR(100)
- description: TEXT
- applies_to: VARCHAR(20) -- SELLER, BUYER, BOTH
- weight: DECIMAL(5,2) -- Peso no cálculo total
- higher_is_better: BOOLEAN
- is_active: BOOLEAN DEFAULT TRUE

Dados iniciais (INSERT):
SELLER factors:
- ITEMS_LISTED_MONTHLY (weight 0.05, higher=true)
- LISTING_REGULARITY (weight 0.05, higher=true)
- ORDERS_RECEIVED_MONTHLY (weight 0.10, higher=true)
- MESSAGE_RESPONSE_RATE (weight 0.15, higher=true)
- DISPUTES_WON_RATE (weight 0.15, higher=true)
- SHIPPING_SLA_SCORE (weight 0.20, higher=true)
- PRICE_FAIRNESS (weight 0.10, higher=true)
- CANCELLATION_RATE (weight 0.10, higher=false)
- ACCOUNT_AGE_MONTHS (weight 0.05, higher=true)
- COMPLAINTS_RATE (weight 0.05, higher=false)

BUYER factors:
- ORDERS_PLACED_MONTHLY (weight 0.15, higher=true)
- PAYMENT_SPEED (weight 0.20, higher=true)
- DISPUTES_OPENED_RATE (weight 0.15, higher=false)
- CANCELLATION_RATE_BUYER (weight 0.20, higher=false)
- CHARGEBACK_HISTORY (weight 0.25, higher=false)
- ACCOUNT_AGE_MONTHS_BUYER (weight 0.05, higher=true)

=== SLA CONFIG ===
SlaConfig:
- id: SERIAL PK
- shipping_excellent_hours: INTEGER DEFAULT 24
- shipping_good_hours: INTEGER DEFAULT 48
- shipping_acceptable_hours: INTEGER DEFAULT 72
- message_excellent_hours: INTEGER DEFAULT 24
- message_good_hours: INTEGER DEFAULT 48
- message_acceptable_hours: INTEGER DEFAULT 72

=== MÉTRICAS CALCULADAS ===
UserRatingMetrics:
- id: BIGSERIAL PK
- user_id: FK
- period_start: DATE
- period_end: DATE
- metrics_json: JSONB -- Raw metrics
- factor_scores: JSONB -- Normalized scores 0-100
- overall_score: DECIMAL(5,2)
- score_tier: VARCHAR(20) -- EXCELLENT, GOOD, AVERAGE, POOR, CRITICAL
- calculated_at: TIMESTAMPTZ

SlaMetrics:
- id: BIGSERIAL PK
- store_id: FK
- period_start, period_end: DATE
- orders_shipped_total: INTEGER
- orders_shipped_24h, orders_shipped_48h, orders_shipped_72h, orders_shipped_late: INTEGER
- avg_shipping_hours: DECIMAL(10,2)
- messages_received, messages_replied_24h, messages_replied_48h, messages_replied_72h: INTEGER
- shipping_sla_score, message_sla_score: DECIMAL(5,2)
- calculated_at: TIMESTAMPTZ

=== BADGES ===
Badge:
- id: SERIAL PK
- code: VARCHAR(50) UNIQUE
- name: VARCHAR(100)
- description: TEXT
- icon_url: VARCHAR(500)
- badge_type: VARCHAR(20) -- ACHIEVEMENT, MONTHLY, MILESTONE
- criteria: JSONB
- is_active: BOOLEAN

Dados iniciais:
- TRUSTED_SELLER (monthly, score >= 85)
- FAST_SHIPPER (monthly, shipping_sla >= 95)
- HIGH_ACCURACY (monthly, disputes_won >= 95%)
- LOYALTY_1Y (milestone, account >= 12 months)
- MILESTONE_100 (achievement, 100 orders)
- MILESTONE_1000 (achievement, 1000 orders)

UserBadge:
- user_id, badge_id: PK
- awarded_at: TIMESTAMPTZ
- valid_until: TIMESTAMPTZ nullable -- NULL para permanentes

Gera migration.
```

---

## PASSO 8: Penalizações

```
Cria os modelos para Penalizações em db/models/penalties.py:

=== CONFIG (thresholds não públicos) ===
UserPenaltyConfig:
- id: SERIAL PK
- warning_threshold: INTEGER DEFAULT 3
- cooldown_threshold: INTEGER DEFAULT 5
- suspension_threshold: INTEGER DEFAULT 8
- ban_threshold: INTEGER DEFAULT 12
- evaluation_period_months: INTEGER DEFAULT 6
- issue_decay_months: INTEGER DEFAULT 12

=== ISSUES (eventos negativos) ===
UserIssue:
- id: BIGSERIAL PK
- user_id: FK
- issue_type: VARCHAR(50) -- DISPUTE_LOST, COMPLAINT, SHIPPING_VIOLATION, PRICE_VIOLATION, SHIPPING_LATE, MESSAGE_TIMEOUT
- severity: INTEGER -- 1-5
- related_order_id: FK nullable
- related_dispute_id: FK nullable
- description: TEXT
- created_at: TIMESTAMPTZ
- expires_at: TIMESTAMPTZ -- created_at + decay period

=== PENALIDADES ===
UserPenalty:
- id: BIGSERIAL PK
- user_id: FK
- penalty_type: VARCHAR(20) -- WARNING, COOLDOWN, SUSPENSION, BAN
- reason_code: VARCHAR(50)
- description: TEXT

- starts_at: TIMESTAMPTZ
- ends_at: TIMESTAMPTZ nullable -- NULL para ban permanente

- restrictions: JSONB -- {can_sell, can_buy, api_disabled, etc.}

- appeal_status: VARCHAR(20) -- NULL, PENDING, APPROVED, REJECTED
- appeal_text: TEXT
- appeal_reviewed_by: FK
- appeal_reviewed_at: TIMESTAMPTZ

- created_by: FK
- created_at: TIMESTAMPTZ

=== SERVICE ===
Cria services/penalty_service.py com:

async def evaluate_user_penalties(user_id: int, db: AsyncSession):
    """Chamado por job diário ou após novo issue"""
    config = await get_penalty_config(db)
    
    # Contar issues activos (não expirados) no período
    active_issues = await count_active_issues(
        db, user_id, config.evaluation_period_months
    )
    
    current_penalty = await get_current_penalty(db, user_id)
    
    if active_issues >= config.ban_threshold:
        new_type = "BAN"
        duration = None
    elif active_issues >= config.suspension_threshold:
        new_type = "SUSPENSION"
        duration = timedelta(days=30)
    elif active_issues >= config.cooldown_threshold:
        new_type = "COOLDOWN"
        duration = timedelta(days=7)
    elif active_issues >= config.warning_threshold:
        new_type = "WARNING"
        duration = timedelta(days=0)
    else:
        return  # Sem penalização
    
    # Apenas aplicar se mais severa que actual
    if should_escalate(current_penalty, new_type):
        await apply_penalty(db, user_id, new_type, duration)

Gera migration e service.
```

---

## PASSO 9: Carrinho (sem hidden fees)

```
Cria os modelos para Cart em db/models/cart.py:

Cart:
- id: BIGSERIAL PK
- user_id: FK UNIQUE
- created_at, updated_at

CartStore:
- id: BIGSERIAL PK
- cart_id: FK
- store_id: FK
- total_items, total_lots: INTEGER
- subtotal: DECIMAL(12,2)
- total_weight_grams: INTEGER
- updated_at
- UNIQUE(cart_id, store_id)

CartItem:
- id: BIGSERIAL PK
- cart_store_id: FK
- lot_id: FK
- quantity: INTEGER NOT NULL
- unit_price_snapshot: DECIMAL(10,4) NOT NULL
- sale_price_snapshot: DECIMAL(10,4)
- warnings: JSONB
- added_at
- UNIQUE(cart_store_id, lot_id)

=== ENDPOINTS (api/v1/cart/) ===
Implementa os seguintes endpoints:

GET /api/v1/cart
- Retorna carrinho completo com split por loja

POST /api/v1/cart/add
- Body: {lot_id, quantity}
- Validações: stock disponível, loja activa

PUT /api/v1/cart/items/{item_id}
- Body: {quantity}

DELETE /api/v1/cart/items/{item_id}

DELETE /api/v1/cart/stores/{store_id}
- Remove todos os itens de uma loja

GET /api/v1/cart/count

=== HARD RULE ===
O total do carrinho é APENAS:
- items_total (soma dos preços dos itens)
- Estimativa de shipping (opcional neste ponto)

NÃO EXISTE:
- handling_fee ❌
- packaging_fee ❌
- service_fee ❌
- other_fees ❌

Gera migration e endpoints completos.
```

---

## PASSO 10: Checkout Automático

```
Cria os modelos para Checkout em db/models/checkout.py:

NOTA: NÃO existe estado "AWAITING_INVOICE" - checkout é sempre automático.

UserAddress:
- id: BIGSERIAL PK
- user_id: FK
- first_name, last_name: VARCHAR(100)
- address_line1, address_line2: VARCHAR(255)
- city: VARCHAR(100)
- state_name: VARCHAR(100)
- postal_code: VARCHAR(20)
- country_code: CHAR(2)
- phone: VARCHAR(30)
- is_default: BOOLEAN

CheckoutDraft:
- id: BIGSERIAL PK
- cart_store_id: FK
- user_id, store_id: FK

- status: VARCHAR(20) DEFAULT 'DRAFT' 
  -- Valores permitidos: DRAFT, PENDING_SHIPPING, PENDING_PAYMENT, COMPLETED, ABANDONED
  -- NÃO EXISTE: AWAITING_INVOICE

- shipping_address_id: FK nullable
- shipping_method_id: FK nullable
- shipping_cost: DECIMAL(10,2)
- insurance_cost: DECIMAL(10,2) DEFAULT 0
- tracking_fee: DECIMAL(10,2) DEFAULT 0

- payment_method_id: FK nullable
- payment_currency_id: FK

-- Totais (SEM HIDDEN FEES)
- items_total: DECIMAL(12,2)
- shipping_total: DECIMAL(12,2)
- tax_total: DECIMAL(12,2) -- Apenas se obrigatório por lei
- grand_total: DECIMAL(12,2)

- quote_snapshot: JSONB
- payment_session_id: VARCHAR(255)
- payment_provider: VARCHAR(50)

- created_at, updated_at, expires_at

=== ENDPOINTS ===

POST /api/v1/checkout/prepare
- Body: {store_id}
- Cria draft, retorna shipping methods

GET /api/v1/checkout/{draft_id}/shipping-methods

PUT /api/v1/checkout/{draft_id}/shipping
- Body: {shipping_method_id, address_id}
- HARD RULE: Se shipping_method_id é null → HTTP 422

PUT /api/v1/checkout/{draft_id}/payment
- Body: {payment_method_id}

POST /api/v1/checkout/{draft_id}/submit
- Validações:
  1. shipping_method_id NOT NULL (HARD RULE)
  2. payment_method_id NOT NULL
  3. Address completo
  4. Stock ainda disponível
  5. Buyer não tem penalização que bloqueie compras
  6. Se buyer é risky E store requer approval → criar OrderApproval
- Cria Order
- Limpa CartStore

=== ERROR RESPONSES ===

Shipping não selecionado:
{
  "error_code": "SHIPPING_REQUIRED",
  "message": "Um método de envio deve ser selecionado",
  "actions": ["SELECT_SHIPPING_METHOD"]
}

Buyer com penalização:
{
  "error_code": "BUYER_RESTRICTED",
  "message": "A sua conta tem restrições activas",
  "data": {"restriction": "CANNOT_BUY", "ends_at": "2026-02-15"}
}

Gera migration e endpoints.
```

---

## PASSO 11: Orders com Prova de Envio

```
Cria os modelos para Orders em db/models/orders.py:

Order:
- id: BIGSERIAL PK
- order_number: VARCHAR(20) UNIQUE -- Formato: BK-2026-XXXXX
- buyer_id, store_id: FK NOT NULL

- status: VARCHAR(20)
  -- PENDING, PENDING_APPROVAL, PAID, PROCESSING, SHIPPED, DELIVERED, COMPLETED, CANCELLED, REFUNDED, DISPUTED

-- Valores (SEM HIDDEN FEES)
- items_total: DECIMAL(12,2)
- shipping_cost: DECIMAL(12,2)
- insurance_cost: DECIMAL(12,2) DEFAULT 0
- tax_amount: DECIMAL(12,2) DEFAULT 0
- grand_total: DECIMAL(12,2)

- store_currency_id, buyer_currency_id, exchange_rate

-- Shipping
- shipping_method_id: FK
- shipping_address_snapshot: JSONB
- tracking_type: VARCHAR(20) -- Do método: FULL_TRACKING, DELIVERY_CONFIRMATION, NO_TRACKING

-- Payment
- payment_method_id: FK
- payment_status: VARCHAR(20)
- payment_reference: VARCHAR(255)
- paid_at: TIMESTAMPTZ

-- Tracking
- tracking_number: VARCHAR(100)
- tracking_url: VARCHAR(500)
- shipped_at: TIMESTAMPTZ
- delivered_at: TIMESTAMPTZ

-- FEATURE #10: Prova para envio sem tracking
- shipping_proof_required: BOOLEAN GENERATED ALWAYS AS (tracking_type = 'NO_TRACKING') STORED
- shipping_proof_url: VARCHAR(500)
- shipping_proof_uploaded_at: TIMESTAMPTZ
- shipping_proof_deadline: TIMESTAMPTZ -- 48h após shipped_at

- buyer_notes, seller_notes: TEXT
- created_at, updated_at

OrderItem:
- id: BIGSERIAL PK
- order_id: FK
- lot_id: FK
- item_snapshot: JSONB
- quantity: INTEGER
- unit_price, sale_price, line_total: DECIMAL

OrderStatusHistory:
- id: BIGSERIAL PK
- order_id: FK
- old_status, new_status: VARCHAR(20)
- changed_by: FK
- reason: TEXT
- changed_at

=== PRE-APPROVAL (FEATURE #20) ===
OrderApproval:
- id: BIGSERIAL PK
- order_id: FK UNIQUE
- reason: VARCHAR(50) -- LOW_BUYER_RATING, CHARGEBACK_HISTORY, NEW_ACCOUNT, HIGH_VALUE
- buyer_risk_score: DECIMAL(5,2)
- status: VARCHAR(20) DEFAULT 'PENDING' -- PENDING, APPROVED, REJECTED
- decided_by: FK
- decision_notes: TEXT
- decided_at: TIMESTAMPTZ
- auto_cancel_at: TIMESTAMPTZ -- Se não decidido em X horas
- created_at

=== FLUXO SHIPPED SEM TRACKING ===

Quando vendedor marca como SHIPPED e tracking_type = NO_TRACKING:
1. Definir shipping_proof_deadline = NOW() + 48 hours
2. Notificar vendedor que deve enviar prova

Job verifica:
- Se deadline passou E proof_url is NULL:
  - Criar disputa automática a favor do comprador
  - Criar UserIssue para vendedor

Gera migration.
```

---

## PASSO 12: Shipping Fairness

```
Cria os modelos para Fair Shipping em db/models/shipping_fairness.py:

=== CONFIG ===
ShippingFairnessConfig:
- id: SERIAL PK
- max_markup_percentage: DECIMAL(5,2) DEFAULT 15.0 -- Max 15% acima do real
- alert_threshold_percentage: DECIMAL(5,2) DEFAULT 25.0
- auto_flag_threshold: DECIMAL(5,2) DEFAULT 50.0
- updated_at

=== BENCHMARKS ===
ShippingCostBenchmark:
- id: BIGSERIAL PK
- origin_country: CHAR(2)
- destination_country: CHAR(2)
- destination_region: VARCHAR(50) -- Para países grandes
- carrier: VARCHAR(50)
- service_type: VARCHAR(50) -- STANDARD, EXPRESS, TRACKED
- weight_min_grams, weight_max_grams: INTEGER
- benchmark_cost: DECIMAL(10,2)
- benchmark_currency: CHAR(3)
- source: VARCHAR(50) -- API, MANUAL, CROWDSOURCED
- last_updated: TIMESTAMPTZ

=== FLAGS ===
ShippingFairnessFlag:
- id: BIGSERIAL PK
- order_id: FK
- store_id: FK
- charged_shipping: DECIMAL(10,2)
- estimated_real_cost: DECIMAL(10,2)
- markup_percentage: DECIMAL(5,2)
- flag_type: VARCHAR(20) -- WARNING, VIOLATION
- status: VARCHAR(20) DEFAULT 'OPEN' -- OPEN, REVIEWED, DISMISSED, CONFIRMED
- reviewed_by: FK
- review_notes: TEXT
- created_at

=== SERVICE ===
Cria services/shipping_fairness.py:

async def validate_shipping_cost(
    origin_country: str,
    destination_country: str,
    weight_grams: int,
    charged_cost: Decimal,
    store_id: int,
    order_id: int,
    db: AsyncSession
) -> ShippingValidation:
    """Valida se o custo de envio está dentro do aceitável"""
    
    benchmark = await get_shipping_benchmark(
        db, origin_country, destination_country, weight_grams
    )
    
    if not benchmark:
        return ShippingValidation(valid=True, warning="No benchmark available")
    
    markup = ((charged_cost - benchmark.cost) / benchmark.cost) * 100
    config = await get_fairness_config(db)
    
    if markup > config.auto_flag_threshold:
        await create_shipping_flag(
            db, order_id, store_id, charged_cost, 
            benchmark.cost, markup, "VIOLATION"
        )
        # Criar issue para o vendedor
        await create_user_issue(
            db, store.user_id, "SHIPPING_VIOLATION", severity=3
        )
        return ShippingValidation(
            valid=False,
            error_code="SHIPPING_COST_EXCESSIVE",
            message=f"Custo de envio {markup:.0f}% acima do benchmark"
        )
    
    elif markup > config.alert_threshold:
        await create_shipping_flag(
            db, order_id, store_id, charged_cost,
            benchmark.cost, markup, "WARNING"
        )
    
    return ShippingValidation(valid=True)

Gera migration e service.
```

---

## PASSO 13: Workers (Jobs Background)

```
Cria os Celery tasks em workers/tasks/:

=== workers/celery_app.py ===
Setup Celery com Redis broker

=== workers/tasks/price_guide.py ===
@celery.task
def calculate_price_guides():
    """
    Job DIÁRIO
    Calcula avg 6 meses para todas as combinações item+color+condition
    Atualiza tabela price_guide
    """

=== workers/tasks/rating.py ===
@celery.task
def calculate_user_ratings():
    """
    Job SEMANAL
    Para cada user activo:
    1. Calcular métricas raw
    2. Normalizar para 0-100
    3. Aplicar pesos dos factores
    4. Calcular score final
    5. Atribuir tier
    """

@celery.task
def calculate_sla_metrics():
    """
    Job DIÁRIO
    Para cada store:
    1. Contar orders por tier de shipping time
    2. Contar mensagens por tier de response time
    3. Calcular scores
    """

=== workers/tasks/badges.py ===
@celery.task
def award_badges():
    """
    Job DIÁRIO
    1. Verificar badges mensais (expirar os do mês anterior)
    2. Atribuir novos badges baseado em critérios
    3. Verificar milestones atingidos
    """

=== workers/tasks/penalties.py ===
@celery.task
def evaluate_penalties():
    """
    Job DIÁRIO
    Para cada user com issues recentes:
    1. Contar issues activos
    2. Avaliar se deve escalar penalização
    """

=== workers/tasks/shipping_proof.py ===
@celery.task
def check_shipping_proof_deadlines():
    """
    Job HORÁRIO
    1. Encontrar orders sem tracking com deadline expirado
    2. Se não há prova: criar disputa automática
    3. Criar issue para vendedor
    """

=== workers/tasks/order_approval.py ===
@celery.task
def auto_cancel_unapproved_orders():
    """
    Job HORÁRIO
    1. Encontrar OrderApprovals com auto_cancel_at expirado
    2. Cancelar order
    3. Libertar stock
    4. Notificar buyer
    """

Gera todos os ficheiros de tasks.
```

---

## PASSO 14: Frontend Base (Next.js)

```
Cria a estrutura do frontend Next.js em /frontend:

frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── catalog/
│   │   ├── page.tsx
│   │   └── [itemId]/page.tsx
│   ├── search/
│   │   └── page.tsx
│   ├── store/
│   │   └── [storeSlug]/page.tsx
│   ├── cart/
│   │   └── page.tsx
│   ├── checkout/
│   │   └── [draftId]/page.tsx
│   ├── orders/
│   │   ├── page.tsx
│   │   └── [orderId]/page.tsx
│   └── dashboard/
│       ├── page.tsx
│       ├── inventory/page.tsx
│       ├── orders/page.tsx
│       └── settings/page.tsx
├── components/
│   ├── ui/           # shadcn/ui
│   ├── layout/
│   ├── catalog/
│   ├── cart/
│   ├── checkout/
│   └── rating/
│       └── RatingBadges.tsx  # Mostrar badges do vendedor
├── lib/
│   ├── api.ts
│   └── utils.ts
├── hooks/
│   ├── use-cart.ts
│   └── use-auth.ts
├── types/
│   └── index.ts
├── Dockerfile
├── package.json (Next.js 14, React 18, Tailwind, shadcn/ui)
└── next.config.js

Na UI, mostrar sempre:
- Rating score do vendedor (não feedback count)
- Badges activos
- SLA metrics (tempo médio de envio)
- NUNCA mostrar campos de hidden fees

Gera os ficheiros base.
```

---

## RESUMO: Ordem de Implementação

| Fase | Prompts | Duração Est. |
|------|---------|--------------|
| 1. Setup | 1-2 | 1 sessão |
| 2. Auth + Catalog | 3-4 | 1-2 sessões |
| 3. Stores + Lots | 5-6 | 1-2 sessões |
| 4. Rating + Penalties | 7-8 | 2 sessões |
| 5. Cart + Checkout | 9-10 | 2 sessões |
| 6. Orders | 11 | 1-2 sessões |
| 7. Fair Shipping | 12 | 1 sessão |
| 8. Workers | 13 | 1 sessão |
| 9. Frontend | 14 | 2-3 sessões |

---

## Ficheiros de Referência no Repositório

1. **BRIKICK_PROJECT_ANALYSIS.md** - Análise técnica completa
2. **BRIKICK_FEATURES_INOVADORAS.md** - Detalhe das 21 features
3. **BRIKICK_QUICK_REFERENCE.md** - Resumo rápido
4. **Este ficheiro** - Prompts prontos a usar

Boa sorte!
