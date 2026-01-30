# Guia Passo-a-Passo para GPT 5.2 Codex

## Pré-Requisitos

Antes de começar, certifica-te que tens:
- [ ] Acesso ao GPT 5.2 Codex
- [ ] Um repositório Git vazio ou novo (recomendo criar um novo no GitHub)
- [ ] Os ficheiros de análise disponíveis (estão neste workspace)

---

## PASSO 1: Preparar o Contexto Inicial

### 1.1 Abre um novo agente GPT 5.2 Codex

### 1.2 Envia este PRIMEIRO PROMPT (contexto do projeto):

```
Vou desenvolver um marketplace de LEGO chamado "Brikick" com a seguinte stack:
- Backend: FastAPI (Python)
- Base de Dados: PostgreSQL
- Frontend: Next.js
- Infraestrutura: Docker Compose

O projeto tem 10 domínios principais:
1. Catalog - Items, types, categories, colors
2. Stores - Seller profiles, policies
3. Inventory/Lots - Inventory listings
4. Search - Faceted search
5. Wanted - Wanted lists
6. Cart - Multi-store cart
7. Checkout - Shipping quotes
8. Orders - Order lifecycle
9. Billing - Seller fees
10. Auth/RBAC - Users, roles, audit

Hard Rules obrigatórias:
1. Price cap em listings (bloquear se acima do limite)
2. Checkout DEVE ter shipping method selecionado
3. Untracked shipping requer upload de prova
4. Orders podem ficar PENDING_APPROVAL (risk gating)
5. Disputes requerem reason codes e auditoria

Confirma que entendes o contexto antes de avançarmos.
```

**Espera a resposta do Codex confirmar que entendeu.**

---

## PASSO 2: Setup Inicial do Projeto

### 2.1 Envia este prompt para criar a estrutura:

```
Cria a estrutura inicial do projeto FastAPI com esta organização:

brikick/
├── api/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app com health check
│   ├── deps.py                 # Dependencies (auth, db session)
│   └── v1/
│       ├── __init__.py
│       └── router.py           # Main router
├── core/
│   ├── __init__.py
│   ├── config.py               # Settings com Pydantic
│   └── security.py             # JWT utils
├── db/
│   ├── __init__.py
│   ├── session.py              # Async database session
│   └── base.py                 # Base model SQLAlchemy
├── migrations/
│   └── (vazio, Alembic vai criar)
├── tests/
│   └── conftest.py
├── docker/
│   ├── Dockerfile.api
│   └── Dockerfile.worker
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml              # Com dependencies: fastapi, uvicorn, sqlalchemy, asyncpg, alembic, pydantic-settings
└── README.md

O docker-compose.yml deve incluir:
- api (FastAPI)
- postgres (PostgreSQL 15)
- redis (Redis 7)
- minio (Object storage)

Gera todos os ficheiros necessários.
```

---

## PASSO 3: Modelos do Catálogo

### 3.1 Envia este prompt para os modelos de referência:

```
Cria os modelos SQLAlchemy para o domínio de Catálogo em db/models/catalog.py:

1. ItemType - Tipos de item (P=Part, S=Set, M=Minifig, etc.)
   - id: CHAR(1) PK
   - name: VARCHAR(50)
   - name_plural: VARCHAR(50)

2. Category - Categorias (1168 categorias)
   - id: SERIAL PK
   - name: VARCHAR(255)
   - type_category: INTEGER
   - allowed_item_types: VARCHAR(20)
   - parent_id: FK para Category (self-reference)

3. Color - Cores (215 cores, ID 0 = "Not Applicable")
   - id: INTEGER PK
   - name: VARCHAR(100)
   - rgb: VARCHAR(6)
   - color_group: INTEGER
   - color_group_name: VARCHAR(50)

4. CatalogItem - Itens do catálogo
   - id: BIGSERIAL PK
   - item_no: VARCHAR(50)
   - item_seq: INTEGER DEFAULT 1
   - item_type: FK para ItemType
   - name: VARCHAR(500)
   - category_id: FK para Category
   - year_released: SMALLINT
   - weight_grams: DECIMAL(10,2)
   - status: VARCHAR(20) DEFAULT 'ACTIVE'
   - created_at, updated_at: TIMESTAMPTZ
   - UNIQUE(item_no, item_type, item_seq)

5. CatalogItemMapping - Mapeamentos externos (BrickLink, Rebrickable, etc.)
   - id: BIGSERIAL PK
   - catalog_item_id: FK para CatalogItem
   - source: VARCHAR(20)
   - external_id: VARCHAR(100)
   - UNIQUE(catalog_item_id, source)

6. CatalogItemImage - Imagens
   - id: BIGSERIAL PK
   - catalog_item_id: FK para CatalogItem
   - color_id: FK para Color
   - image_type: CHAR(1)
   - url: VARCHAR(500)
   - is_primary: BOOLEAN

Usa SQLAlchemy 2.0 com async support. Inclui índices adequados.
```

### 3.2 Depois pede a migration:

```
Agora cria a migration Alembic para estes modelos de catálogo.
O ficheiro deve ir para migrations/versions/ com um nome descritivo.
```

---

## PASSO 4: Endpoints do Catálogo

### 4.1 Envia este prompt:

```
Cria os endpoints REST para o domínio de Catálogo em api/v1/catalog/:

Estrutura:
api/v1/catalog/
├── __init__.py
├── router.py      # Rotas
├── schemas.py     # Pydantic schemas
└── service.py     # Lógica de negócio

Endpoints a implementar:

1. GET /api/v1/catalog/item-types
   - Lista todos os tipos de item
   - Response: List[ItemTypeResponse]

2. GET /api/v1/catalog/categories
   - Lista categorias com paginação
   - Query params: parent_id, item_type, page, page_size
   - Response: PaginatedResponse[CategoryResponse]

3. GET /api/v1/catalog/categories/{id}
   - Detalhe de uma categoria
   - Response: CategoryResponse com subcategorias

4. GET /api/v1/catalog/colors
   - Lista todas as cores
   - Query params: group
   - Response: List[ColorResponse]

5. GET /api/v1/catalog/items
   - Lista/pesquisa de itens do catálogo
   - Query params: q, item_type, category_id, page, page_size
   - Response: PaginatedResponse[CatalogItemResponse]

6. GET /api/v1/catalog/items/{id}
   - Detalhe de um item
   - Response: CatalogItemDetailResponse (com imagens e mapeamentos)

Schemas de resposta devem seguir este padrão:
{
  "data": [...],
  "meta": {"total": 100, "page": 1, "page_size": 25},
  "return_code": 0,
  "return_message": ""
}

Usa async/await em todo o código.
```

---

## PASSO 5: Dados de Referência

### 5.1 Envia este prompt:

```
Cria scripts de seed para popular os dados de referência em db/seeds/:

1. seed_item_types.py - Os 8 tipos:
   P=Part, S=Set, M=Minifig, B=Book, G=Gear, C=Catalog, I=Instruction, O=Original Box

2. seed_colors.py - Preciso que cries um ficheiro JSON com pelo menos as 20 cores mais comuns:
   - 0: (Not Applicable)
   - 1: White
   - 2: Tan
   - 3: Yellow
   - 4: Orange
   - 5: Red
   - 6: Green
   - 7: Blue
   - 8: Brown
   - 9: Light Gray
   - 10: Dark Gray
   - 11: Black
   - 12: Trans-Clear
   - 15: Trans-Light Blue
   - 19: Tan (continua...)

3. seed_categories.py - Cria as principais categorias:
   - Brick, Plate, Tile, Slope, Technic, Minifig Parts, etc.

Cria também um comando CLI para executar os seeds:
python -m db.seeds.run_all
```

---

## PASSO 6: Stores e Inventário

### 6.1 Envia este prompt:

```
Cria os modelos SQLAlchemy para Stores e Inventory em db/models/stores.py e db/models/inventory.py:

STORES (db/models/stores.py):

1. Store
   - id: BIGSERIAL PK
   - user_id: FK para User
   - name: VARCHAR(255)
   - slug: VARCHAR(100) UNIQUE
   - country_code: CHAR(2)
   - currency_id: INTEGER
   - feedback_score: INTEGER DEFAULT 0
   - status: VARCHAR(20) DEFAULT 'ACTIVE'
   - min_buy_amount: DECIMAL(10,2)
   - instant_checkout_enabled: BOOLEAN DEFAULT TRUE
   - created_at, updated_at

2. StorePolicy
   - id: BIGSERIAL PK
   - store_id: FK para Store
   - terms_html: TEXT
   - shipping_terms_html: TEXT
   - has_vat: BOOLEAN
   - version: INTEGER
   - updated_at

3. StoreShippingMethod
   - id: BIGSERIAL PK
   - store_id: FK para Store
   - name: VARCHAR(255)
   - note: TEXT
   - ships_to_countries: TEXT[] (array de códigos)
   - cost_type: VARCHAR(20)
   - base_cost: DECIMAL(10,2)
   - tracking_available: BOOLEAN
   - min_days, max_days: INTEGER
   - is_active: BOOLEAN

4. StorePaymentMethod
   - id: BIGSERIAL PK
   - store_id: FK para Store
   - method_type: VARCHAR(50)
   - name: VARCHAR(100)
   - is_on_site: BOOLEAN
   - is_active: BOOLEAN

INVENTORY (db/models/inventory.py):

5. Lot (tabela central do marketplace)
   - id: BIGSERIAL PK
   - store_id: FK para Store NOT NULL
   - catalog_item_id: FK para CatalogItem NOT NULL
   - color_id: FK para Color
   - condition: VARCHAR(1) NOT NULL (N=New, U=Used)
   - completeness: VARCHAR(1) (C, B, S, X)
   - quantity: INTEGER NOT NULL
   - bulk_quantity: INTEGER DEFAULT 1
   - unit_price: DECIMAL(10,4) NOT NULL
   - sale_percentage: INTEGER DEFAULT 0
   - tier1_qty, tier1_price, tier2_qty, tier2_price, tier3_qty, tier3_price
   - superlot_id: FK para Lot (self-reference)
   - description: TEXT
   - extended_description: TEXT
   - custom_image_url: VARCHAR(500)
   - status: VARCHAR(20) DEFAULT 'AVAILABLE'
   - listed_at, updated_at: TIMESTAMPTZ
   - Índices em: store_id, catalog_item_id, color_id, condition, unit_price

Gera também a migration Alembic.
```

---

## PASSO 7: Carrinho Multi-Loja

### 7.1 Envia este prompt:

```
Cria os modelos e endpoints para o Carrinho Multi-Loja.

MODELOS em db/models/cart.py:

1. Cart
   - id: BIGSERIAL PK
   - user_id: FK UNIQUE NOT NULL
   - created_at, updated_at

2. CartStore (sub-carrinho por loja)
   - id: BIGSERIAL PK
   - cart_id: FK para Cart
   - store_id: FK para Store
   - total_items, total_lots: INTEGER
   - subtotal: DECIMAL(12,2)
   - total_weight_grams: INTEGER
   - updated_at
   - UNIQUE(cart_id, store_id)

3. CartItem
   - id: BIGSERIAL PK
   - cart_store_id: FK para CartStore
   - lot_id: FK para Lot
   - quantity: INTEGER NOT NULL
   - unit_price_snapshot: DECIMAL(10,4) NOT NULL
   - sale_price_snapshot: DECIMAL(10,4)
   - warnings: JSONB
   - added_at
   - UNIQUE(cart_store_id, lot_id)

ENDPOINTS em api/v1/cart/:

1. GET /api/v1/cart
   - Retorna carrinho do utilizador com split por loja
   - Response shape:
   {
     "stores": [{
       "store_id": 123,
       "store_name": "BricksNL",
       "items": [{
         "lot_id": 456,
         "item_name": "Brick 2x4",
         "quantity": 5,
         "unit_price": "0.15",
         "line_total": "0.75"
       }],
       "totals": {
         "items": 5,
         "lots": 1,
         "subtotal": "0.75"
       }
     }],
     "grand_total": "0.75"
   }

2. POST /api/v1/cart/add
   - Body: {"lot_id": 123, "quantity": 5}
   - Validações:
     - Lot existe e está disponível
     - Quantidade disponível
     - Não excede stock
   - Cria CartStore se não existir para a loja

3. PUT /api/v1/cart/items/{item_id}
   - Body: {"quantity": 10}
   - Atualiza quantidade

4. DELETE /api/v1/cart/items/{item_id}
   - Remove item do carrinho
   - Se último item da loja, remove CartStore

5. DELETE /api/v1/cart/stores/{store_id}
   - Remove todos os itens de uma loja

6. GET /api/v1/cart/count
   - Response: {"count": 5}

Inclui service layer com lógica de validação.
```

---

## PASSO 8: Checkout com Shipping Obrigatório

### 8.1 Envia este prompt:

```
Cria o fluxo de Checkout com a HARD RULE: shipping method é OBRIGATÓRIO.

MODELOS em db/models/checkout.py:

1. UserAddress
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

2. CheckoutDraft
   - id: BIGSERIAL PK
   - cart_store_id: FK
   - user_id: FK
   - store_id: FK
   - status: VARCHAR(20) DEFAULT 'DRAFT'
   - shipping_address_id: FK NULLABLE
   - shipping_method_id: FK NULLABLE
   - shipping_cost: DECIMAL(10,2)
   - payment_method_id: FK NULLABLE
   - items_total, shipping_total, tax_total, grand_total: DECIMAL(12,2)
   - quote_snapshot: JSONB
   - payment_session_id: VARCHAR(255)
   - created_at, updated_at, expires_at

ENDPOINTS em api/v1/checkout/:

1. POST /api/v1/checkout/prepare
   - Body: {"store_id": 123}
   - Cria CheckoutDraft a partir do CartStore
   - Retorna métodos de envio disponíveis

2. GET /api/v1/checkout/{draft_id}/shipping-methods
   - Lista métodos de envio da loja para o destino
   - Inclui quotes de preço

3. PUT /api/v1/checkout/{draft_id}/shipping
   - Body: {"shipping_method_id": 456, "address_id": 789}
   - HARD RULE: Se shipping_method_id é null → HTTP 422
   - Error response:
   {
     "error_code": "SHIPPING_REQUIRED",
     "message": "Shipping method must be selected",
     "actions": ["SELECT_SHIPPING_METHOD"]
   }

4. PUT /api/v1/checkout/{draft_id}/payment
   - Body: {"payment_method_id": 101}

5. POST /api/v1/checkout/{draft_id}/submit
   - Validações finais:
     - shipping_method_id NOT NULL (HARD RULE)
     - payment_method_id NOT NULL
     - address completo
     - Stock ainda disponível
   - Cria Order
   - Limpa CartStore
   - Retorna order_id

Implementa validação rigorosa do shipping method em todas as operações.
```

---

## PASSO 9: Orders e Lifecycle

### 9.1 Envia este prompt:

```
Cria o sistema de Orders com máquina de estados.

ESTADOS POSSÍVEIS:
PENDING → PENDING_APPROVAL (risk gate) → PAID → PROCESSING → SHIPPED → DELIVERED → COMPLETED
                                                                    ↓
                                                               DISPUTED
PENDING pode ir para CANCELLED
PAID pode ir para REFUNDED

MODELOS em db/models/orders.py:

1. Order
   - id: BIGSERIAL PK
   - order_number: VARCHAR(20) UNIQUE (formato: BK-2026-XXXXX)
   - buyer_id, store_id: FK NOT NULL
   - status: ENUM dos estados acima
   - items_total, shipping_cost, tax_amount, grand_total: DECIMAL
   - store_currency_id, buyer_currency_id, exchange_rate
   - shipping_method_id: FK
   - shipping_address_snapshot: JSONB
   - payment_method_id: FK
   - payment_status, payment_reference, paid_at
   - tracking_number, tracking_url, shipped_at, delivered_at
   - shipping_proof_url, shipping_proof_uploaded_at
   - buyer_notes, seller_notes
   - created_at, updated_at

2. OrderItem
   - id: BIGSERIAL PK
   - order_id: FK
   - lot_id: FK
   - item_snapshot: JSONB
   - quantity: INTEGER
   - unit_price, sale_price, line_total: DECIMAL

3. OrderStatusHistory
   - id: BIGSERIAL PK
   - order_id: FK
   - old_status, new_status
   - changed_by: FK
   - reason: TEXT
   - changed_at

ENDPOINTS em api/v1/orders/:

1. GET /api/v1/orders
   - Query: status, role (buyer/seller), page
   - Filtra por buyer_id ou store.user_id conforme role

2. GET /api/v1/orders/{id}
   - Detalhe completo com itens e histórico

3. PATCH /api/v1/orders/{id}/status
   - Body: {"status": "SHIPPED", "tracking_number": "...", "reason": "..."}
   - Valida transição de estado permitida
   - Regista em OrderStatusHistory

4. POST /api/v1/orders/{id}/shipping-proof
   - Upload de prova de envio (para untracked)
   - Multipart form com ficheiro

5. POST /api/v1/orders/{id}/refund
   - Body: {"amount": 10.00, "reason_code": "ITEM_NOT_RECEIVED"}
   - Só permitido em estados PAID, SHIPPED, DELIVERED

Implementa a máquina de estados com validação rigorosa de transições.
```

---

## PASSO 10: Auth e RBAC

### 10.1 Envia este prompt:

```
Cria o sistema de autenticação e RBAC.

MODELOS em db/models/users.py:

1. User
   - id: BIGSERIAL PK
   - email: VARCHAR(255) UNIQUE
   - username: VARCHAR(50) UNIQUE
   - password_hash: VARCHAR(255)
   - first_name, last_name: VARCHAR(100)
   - country_code: CHAR(2)
   - preferred_currency_id: INTEGER
   - is_active, is_verified: BOOLEAN
   - created_at, last_login_at

2. Role
   - id: SERIAL PK
   - name: VARCHAR(50) UNIQUE
   - description: TEXT
   
   Roles pré-definidas: user, seller, staff_support, staff_finance, staff_catalog, admin

3. Permission
   - id: SERIAL PK
   - scope: VARCHAR(50) - orders, catalog, billing, etc.
   - action: VARCHAR(50) - read, write, delete, admin
   - UNIQUE(scope, action)

4. RolePermission (M2M)
   - role_id, permission_id: PKs

5. UserRole (M2M)
   - user_id, role_id: PKs
   - granted_at, granted_by

6. UserSession
   - id: BIGSERIAL PK
   - user_id: FK
   - token_hash: VARCHAR(255) UNIQUE
   - ip_address: INET
   - user_agent: TEXT
   - created_at, expires_at, revoked_at

7. AuditLog
   - id: BIGSERIAL PK
   - user_id: FK
   - action: VARCHAR(100)
   - entity_type: VARCHAR(50)
   - entity_id: BIGINT
   - old_values, new_values: JSONB
   - ip_address: INET
   - reason: TEXT
   - created_at

ENDPOINTS em api/v1/auth/:

1. POST /api/v1/auth/register
2. POST /api/v1/auth/login
3. POST /api/v1/auth/logout
4. POST /api/v1/auth/refresh
5. GET /api/v1/auth/me

DEPENDENCIES em api/deps.py:

1. get_current_user - Extrai user do JWT
2. require_permission(scope, action) - Decorator para validar permissões
3. audit_action(action) - Decorator para registar em AuditLog

Exemplo de uso:
@router.delete("/items/{id}")
@require_permission("catalog", "delete")
@audit_action("DELETE_CATALOG_ITEM")
async def delete_item(id: int, current_user: User = Depends(get_current_user)):
    ...
```

---

## PASSO 11: Frontend Next.js (Básico)

### 11.1 Envia este prompt:

```
Cria a estrutura inicial do frontend Next.js em /frontend:

frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                 # Homepage
│   ├── catalog/
│   │   ├── page.tsx             # Browse catalog
│   │   └── [itemId]/page.tsx    # Item detail
│   ├── search/
│   │   └── page.tsx             # Search results
│   ├── store/
│   │   └── [storeId]/page.tsx   # Store page
│   ├── cart/
│   │   └── page.tsx             # Cart
│   ├── checkout/
│   │   └── [draftId]/page.tsx   # Checkout flow
│   └── orders/
│       ├── page.tsx             # My orders
│       └── [orderId]/page.tsx   # Order detail
├── components/
│   ├── ui/                      # Shadcn/ui components
│   ├── catalog/
│   ├── cart/
│   └── checkout/
├── lib/
│   ├── api.ts                   # API client
│   └── utils.ts
├── hooks/
│   └── use-cart.ts
├── types/
│   └── index.ts                 # TypeScript types
├── Dockerfile
├── package.json
├── tailwind.config.ts
└── next.config.js

Usa:
- Next.js 14 com App Router
- TypeScript
- Tailwind CSS
- Shadcn/ui para componentes
- React Query para data fetching

Gera os ficheiros base com setup completo.
```

---

## RESUMO: Ordem dos Prompts

| # | Prompt | Resultado |
|---|--------|-----------|
| 1 | Contexto do projeto | Codex entende o scope |
| 2 | Estrutura FastAPI | Scaffold completo |
| 3 | Modelos Catalog | 6 tabelas + migration |
| 4 | Endpoints Catalog | API REST completa |
| 5 | Dados de referência | Seeds de cores/categorias |
| 6 | Stores + Inventory | 5 tabelas + migration |
| 7 | Cart Multi-Loja | 3 tabelas + 6 endpoints |
| 8 | Checkout | Hard rule shipping |
| 9 | Orders | State machine completa |
| 10 | Auth + RBAC | Sistema de permissões |
| 11 | Frontend | Next.js scaffold |

---

## DICAS IMPORTANTES

1. **Espera sempre a resposta completa** antes de enviar o próximo prompt

2. **Se o Codex "esquecer" contexto**, relembra:
   ```
   Lembra-te: estamos a desenvolver o Brikick, marketplace LEGO com FastAPI + PostgreSQL + Next.js.
   ```

3. **Para corrigir erros**, sê específico:
   ```
   O endpoint GET /cart está a retornar 500. O erro é: [cola o erro].
   Corrige o service layer para usar async corretamente.
   ```

4. **Para adicionar features**, referencia o domínio:
   ```
   No domínio de Orders, adiciona suporte para disputas.
   Uma disputa tem: order_id, reason_code, description, status, evidence (ficheiros).
   ```

5. **Guarda o código gerado** regularmente no teu repositório Git

---

## Ficheiros de Referência

Se precisares de dar mais contexto ao Codex, copia secções do ficheiro `BRIKICK_PROJECT_ANALYSIS.md`:

- **Secção 4** - Modelos de dados completos
- **Secção 5** - Contratos de API observados
- **Secção 6** - Dados de referência
- **Secção 9** - Estrutura de pastas

Boa sorte com o desenvolvimento!
