# BRIKICK - Análise Completa do Projeto para GPT 5.2 Codex

> **Documento de referência técnica para desenvolvimento de marketplace LEGO**
> **Stack: FastAPI + PostgreSQL + Next.js + Docker**

---

## 1. RESUMO EXECUTIVO

### 1.1 O que é o Brikick?
**Brikick** é um marketplace de peças LEGO de classe profissional (equivalente ao BrickLink) com as seguintes características:

- **Catálogo público** com pesquisa avançada, facetas, ordenação e paginação
- **Lotes de inventário** com preços, condições, observações, políticas de loja
- **Carrinho multi-loja** (linhas agrupadas/separadas por loja)
- **Checkout obrigatório** com seleção de método de envio (sem pedidos de fatura)
- **Fluxos de comprador**: encomendas, mensagens, wanted lists, sourcing, disputas
- **Fluxos de vendedor**: gestão de inventário, mass upload (BrickStore XML), fulfillment, shipping profiles
- **Admin/Staff**: moderação, disputas, gestão de dados de referência, auditoria

### 1.2 Stack Tecnológico
| Componente | Tecnologia |
|------------|-----------|
| Backend API | FastAPI (Python) |
| Base de Dados | PostgreSQL |
| Frontend | Next.js |
| Containers | Docker Compose |
| Cache/Queue | Redis |
| Object Storage | MinIO |
| Reverse Proxy | Traefik/Nginx |
| Observability | OpenTelemetry, Sentry, Prometheus |

---

## 2. REGRAS DE NEGÓCIO CRÍTICAS ("HARD RULES")

### 2.1 Regras Obrigatórias (Backend + Frontend)

| # | Regra | Comportamento |
|---|-------|--------------|
| 1 | **Price Cap** | Bloquear save se preço acima do cap; permitir override request → PENDING_REVIEW |
| 2 | **Shipping Quote Obrigatório** | Checkout DEVE ter seleção de método de envio; se loja não consegue cotar para destino → bloquear checkout |
| 3 | **Proof Upload para Untracked** | Envios sem tracking requerem upload de prova dentro do SLA |
| 4 | **Risk Gating** | Encomendas podem ficar PENDING_APPROVAL; UI deve refletir este estado |
| 5 | **Disputes Evidence-Based** | Decisões staff requerem reason codes; tudo auditado |

### 2.2 Códigos de Erro Sugeridos
```
422 - Validation Error (campos inválidos)
409 - Conflict (concorrência, versão desatualizada)
403 - Forbidden (sem permissão, regra de negócio violada)
```

**Payload de erro sugerido:**
```json
{
  "error_code": "PRICE_CAP_EXCEEDED",
  "reason_code": "LOT_PRICE_ABOVE_CAP",
  "message": "O preço excede o limite permitido",
  "actions": ["REQUEST_OVERRIDE", "ADJUST_PRICE"],
  "trace_id": "abc123"
}
```

---

## 3. DOMÍNIOS DO SISTEMA (10 Módulos)

### 3.1 Visão Geral dos Domínios

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BRIKICK DOMAINS                              │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────┤
│   CATALOG    │    STORES    │  INVENTORY   │    SEARCH    │ WANTED  │
│  (Reference) │  (Profiles)  │   (Lots)     │  (Facets)    │ (Lists) │
├──────────────┼──────────────┼──────────────┼──────────────┼─────────┤
│     CART     │   CHECKOUT   │    ORDERS    │   BILLING    │  AUTH   │
│ (Multi-Store)│  (Shipping)  │ (Lifecycle)  │   (Fees)     │ (RBAC)  │
└──────────────┴──────────────┴──────────────┴──────────────┴─────────┘
```

---

## 4. MODELO DE DADOS (PostgreSQL)

### 4.1 DOMÍNIO: Catálogo / Dados de Referência

```sql
-- Tipos de item (Part, Set, Minifig, Book, Gear, Catalog, Instruction, Original Box)
CREATE TABLE item_types (
    id CHAR(1) PRIMARY KEY,  -- P, S, M, B, G, C, I, O
    name VARCHAR(50) NOT NULL,
    name_plural VARCHAR(50)
);

-- Categorias (1168 categorias no BrickLink)
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type_category INTEGER,
    allowed_item_types VARCHAR(20),  -- ex: "SPMGBCIO"
    parent_id INTEGER REFERENCES categories(id)
);

-- Cores (215 cores no BrickLink)
CREATE TABLE colors (
    id INTEGER PRIMARY KEY,  -- 0 = "(Not Applicable)"
    name VARCHAR(100) NOT NULL,
    rgb VARCHAR(6),
    color_group INTEGER,
    color_group_name VARCHAR(50)
);

-- Itens do catálogo (peças, sets, minifigs, etc.)
CREATE TABLE catalog_items (
    id BIGSERIAL PRIMARY KEY,
    item_no VARCHAR(50) NOT NULL,  -- Número do item (ex: "3001")
    item_seq INTEGER DEFAULT 1,    -- Sequência para variantes
    item_type CHAR(1) REFERENCES item_types(id),
    name VARCHAR(500) NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    year_released SMALLINT,
    weight_grams DECIMAL(10,2),
    dimensions_json JSONB,  -- {length, width, height}
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, RETIRED, UNAVAILABLE
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(item_no, item_type, item_seq)
);

-- Mapeamentos externos (BrickLink, BrickOwl, Rebrickable, LDraw)
CREATE TABLE catalog_item_mappings (
    id BIGSERIAL PRIMARY KEY,
    catalog_item_id BIGINT REFERENCES catalog_items(id),
    source VARCHAR(20) NOT NULL,  -- BRICKLINK, BRICKOWL, REBRICKABLE, LDRAW
    external_id VARCHAR(100) NOT NULL,
    external_data JSONB,
    
    UNIQUE(catalog_item_id, source)
);

-- Imagens de itens
CREATE TABLE catalog_item_images (
    id BIGSERIAL PRIMARY KEY,
    catalog_item_id BIGINT REFERENCES catalog_items(id),
    color_id INTEGER REFERENCES colors(id),
    image_type CHAR(1),  -- S=small, L=large, T=thumb
    url VARCHAR(500) NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE
);

-- Co-brands / Themes (623 no BrickLink)
CREATE TABLE cobrands (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type INTEGER,
    type_name VARCHAR(100)
);

-- Países (235 países)
CREATE TABLE countries (
    code CHAR(2) PRIMARY KEY,  -- ISO 3166-1 alpha-2
    name VARCHAR(100) NOT NULL,
    continent_id INTEGER,
    currency_id INTEGER,
    address_format_id INTEGER,
    is_eu_country BOOLEAN DEFAULT FALSE,
    vat_rate DECIMAL(5,2) DEFAULT 0,
    fee_waived BOOLEAN DEFAULT FALSE
);

-- Moedas (37 moedas)
CREATE TABLE currencies (
    id INTEGER PRIMARY KEY,
    code CHAR(3) NOT NULL,  -- ISO 4217
    name VARCHAR(100) NOT NULL,
    is_paypal_available BOOLEAN DEFAULT FALSE,
    exchange_rate_to_usd DECIMAL(12,6)
);

-- Estados/Províncias (1617 estados)
CREATE TABLE states (
    id SERIAL PRIMARY KEY,
    country_code CHAR(2) REFERENCES countries(code),
    name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(10),
    parent_state_id INTEGER REFERENCES states(id),
    has_children BOOLEAN DEFAULT FALSE
);

-- Formatos de endereço (35 formatos)
CREATE TABLE address_formats (
    id INTEGER PRIMARY KEY,
    title_address1 VARCHAR(50),
    title_address2 VARCHAR(50),
    title_city VARCHAR(50),
    title_postal_code VARCHAR(50),
    title_state VARCHAR(50),
    field_requirements JSONB  -- Quais campos são obrigatórios
);
```

### 4.2 DOMÍNIO: Lojas (Stores)

```sql
-- Lojas/Vendedores
CREATE TABLE stores (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    country_code CHAR(2) REFERENCES countries(code),
    currency_id INTEGER REFERENCES currencies(id),
    feedback_score INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, VACATION, SUSPENDED, CLOSED
    min_buy_amount DECIMAL(10,2),
    instant_checkout_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Políticas da loja (termos, condições)
CREATE TABLE store_policies (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT REFERENCES stores(id),
    terms_html TEXT,
    shipping_terms_html TEXT,
    has_vat BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Moedas aceites pela loja
CREATE TABLE store_accepted_currencies (
    store_id BIGINT REFERENCES stores(id),
    currency_id INTEGER REFERENCES currencies(id),
    note TEXT,
    PRIMARY KEY (store_id, currency_id)
);

-- Métodos de pagamento da loja
CREATE TABLE store_payment_methods (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT REFERENCES stores(id),
    method_type VARCHAR(50) NOT NULL,  -- PAYPAL, STRIPE, BANK_TRANSFER, etc.
    name VARCHAR(100) NOT NULL,
    note TEXT,
    is_on_site BOOLEAN DEFAULT FALSE,  -- Processado na plataforma?
    countries_available TEXT[],  -- Países onde está disponível
    is_active BOOLEAN DEFAULT TRUE
);

-- Métodos de envio da loja
CREATE TABLE store_shipping_methods (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT REFERENCES stores(id),
    name VARCHAR(255) NOT NULL,
    note TEXT,
    ships_to_countries TEXT[],  -- Lista de códigos de países
    ships_to_continents INTEGER[],
    cost_type VARCHAR(20),  -- FIXED, WEIGHT_BASED, CALCULATED
    base_cost DECIMAL(10,2),
    insurance_available BOOLEAN DEFAULT FALSE,
    insurance_cost DECIMAL(10,2),
    tracking_available BOOLEAN DEFAULT FALSE,
    tracking_fee DECIMAL(10,2),
    min_days INTEGER,
    max_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE
);

-- Taxas de envio por método
CREATE TABLE store_shipping_rates (
    id BIGSERIAL PRIMARY KEY,
    shipping_method_id BIGINT REFERENCES store_shipping_methods(id),
    weight_min_grams INTEGER,
    weight_max_grams INTEGER,
    price_min DECIMAL(10,2),
    price_max DECIMAL(10,2),
    rate DECIMAL(10,2) NOT NULL
);
```

### 4.3 DOMÍNIO: Lotes / Inventário

```sql
-- Lotes de inventário (o coração do marketplace)
CREATE TABLE lots (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT REFERENCES stores(id) NOT NULL,
    catalog_item_id BIGINT REFERENCES catalog_items(id) NOT NULL,
    color_id INTEGER REFERENCES colors(id),
    
    -- Condição e completude
    condition VARCHAR(1) NOT NULL,  -- N=New, U=Used
    completeness VARCHAR(1),  -- C=Complete, B=Incomplete, S=Sealed, X=Unknown
    
    -- Quantidades
    quantity INTEGER NOT NULL DEFAULT 1,
    bulk_quantity INTEGER DEFAULT 1,  -- Mínimo de compra
    
    -- Preços (sempre na moeda da loja)
    unit_price DECIMAL(10,4) NOT NULL,
    sale_percentage INTEGER DEFAULT 0,  -- 0-100
    
    -- Preços por quantidade (tier pricing)
    tier1_qty INTEGER,
    tier1_price DECIMAL(10,4),
    tier2_qty INTEGER,
    tier2_price DECIMAL(10,4),
    tier3_qty INTEGER,
    tier3_price DECIMAL(10,4),
    
    -- Superlot (lotes agrupados)
    superlot_id BIGINT REFERENCES lots(id),
    
    -- Descrição e observações
    description TEXT,
    extended_description TEXT,
    
    -- Imagem customizada do lote
    custom_image_url VARCHAR(500),
    
    -- Metadados
    status VARCHAR(20) DEFAULT 'AVAILABLE',  -- AVAILABLE, RESERVED, SOLD, HIDDEN
    listed_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Índices para performance
    INDEX idx_lots_store (store_id),
    INDEX idx_lots_item (catalog_item_id),
    INDEX idx_lots_color (color_id),
    INDEX idx_lots_condition (condition),
    INDEX idx_lots_price (unit_price)
);

-- Histórico de alterações de lotes (auditoria)
CREATE TABLE lot_audit_log (
    id BIGSERIAL PRIMARY KEY,
    lot_id BIGINT REFERENCES lots(id),
    action VARCHAR(20) NOT NULL,  -- CREATE, UPDATE, DELETE, RESERVE, SELL
    old_values JSONB,
    new_values JSONB,
    changed_by BIGINT REFERENCES users(id),
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET
);
```

### 4.4 DOMÍNIO: Pesquisa (Search)

```sql
-- Configuração de índice de pesquisa (para Elasticsearch/Meilisearch)
-- Esta tabela guarda metadata, o índice real estará no search engine

CREATE TABLE search_index_metadata (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,  -- CATALOG_ITEM, LOT, STORE
    last_full_reindex TIMESTAMPTZ,
    last_incremental_update TIMESTAMPTZ,
    document_count BIGINT
);

-- Cache de facetas (para performance)
CREATE TABLE search_facet_cache (
    id BIGSERIAL PRIMARY KEY,
    facet_type VARCHAR(50) NOT NULL,  -- CATEGORY, COLOR, CONDITION, PRICE_RANGE
    facet_key VARCHAR(100) NOT NULL,
    facet_value VARCHAR(255),
    count INTEGER,
    store_id BIGINT REFERENCES stores(id),  -- NULL para facetas globais
    cached_at TIMESTAMPTZ DEFAULT NOW(),
    
    INDEX idx_facet_type_key (facet_type, facet_key)
);
```

### 4.5 DOMÍNIO: Wanted Lists

```sql
-- Listas de wanted (desejos)
CREATE TABLE wanted_lists (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Itens das wanted lists
CREATE TABLE wanted_list_items (
    id BIGSERIAL PRIMARY KEY,
    wanted_list_id BIGINT REFERENCES wanted_lists(id) ON DELETE CASCADE,
    catalog_item_id BIGINT REFERENCES catalog_items(id),
    color_id INTEGER REFERENCES colors(id),
    condition VARCHAR(1),  -- N, U, ou NULL para qualquer
    
    -- Quantidades
    quantity_wanted INTEGER NOT NULL DEFAULT 1,
    quantity_filled INTEGER DEFAULT 0,
    
    -- Preço máximo desejado
    max_price DECIMAL(10,2),
    
    -- Notas
    notes TEXT,
    
    -- Prioridade
    is_mandatory BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(wanted_list_id, catalog_item_id, color_id, condition)
);
```

### 4.6 DOMÍNIO: Carrinho (Cart)

```sql
-- Carrinhos (um por utilizador)
CREATE TABLE carts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sub-carrinhos por loja
CREATE TABLE cart_stores (
    id BIGSERIAL PRIMARY KEY,
    cart_id BIGINT REFERENCES carts(id) ON DELETE CASCADE,
    store_id BIGINT REFERENCES stores(id),
    
    -- Totais calculados (cache)
    total_items INTEGER DEFAULT 0,
    total_lots INTEGER DEFAULT 0,
    subtotal DECIMAL(12,2) DEFAULT 0,
    subtotal_native DECIMAL(12,2) DEFAULT 0,  -- Na moeda do comprador
    total_weight_grams INTEGER DEFAULT 0,
    
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(cart_id, store_id)
);

-- Itens do carrinho
CREATE TABLE cart_items (
    id BIGSERIAL PRIMARY KEY,
    cart_store_id BIGINT REFERENCES cart_stores(id) ON DELETE CASCADE,
    lot_id BIGINT REFERENCES lots(id),
    
    -- Quantidade no carrinho
    quantity INTEGER NOT NULL,
    
    -- Snapshot do preço no momento de adicionar
    unit_price_snapshot DECIMAL(10,4) NOT NULL,
    sale_price_snapshot DECIMAL(10,4),
    
    -- Warnings
    warnings JSONB,  -- [{code, message}]
    
    added_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(cart_store_id, lot_id)
);
```

### 4.7 DOMÍNIO: Checkout

```sql
-- Rascunhos de checkout (um por cart_store)
CREATE TABLE checkout_drafts (
    id BIGSERIAL PRIMARY KEY,
    cart_store_id BIGINT REFERENCES cart_stores(id),
    user_id BIGINT REFERENCES users(id),
    store_id BIGINT REFERENCES stores(id),
    
    -- Estado
    status VARCHAR(20) DEFAULT 'DRAFT',  -- DRAFT, PENDING_SHIPPING, PENDING_PAYMENT, COMPLETED, ABANDONED
    
    -- Endereço de envio
    shipping_address_id BIGINT REFERENCES user_addresses(id),
    
    -- Método de envio selecionado
    shipping_method_id BIGINT REFERENCES store_shipping_methods(id),
    shipping_cost DECIMAL(10,2),
    insurance_requested BOOLEAN DEFAULT FALSE,
    insurance_cost DECIMAL(10,2),
    tracking_requested BOOLEAN DEFAULT FALSE,
    tracking_fee DECIMAL(10,2),
    
    -- Método de pagamento selecionado
    payment_method_id BIGINT REFERENCES store_payment_methods(id),
    payment_currency_id INTEGER REFERENCES currencies(id),
    
    -- Totais
    items_total DECIMAL(12,2),
    shipping_total DECIMAL(12,2),
    tax_total DECIMAL(12,2),
    grand_total DECIMAL(12,2),
    
    -- Snapshot de dados para auditoria
    quote_snapshot JSONB,
    
    -- Sessão de pagamento (se PSP)
    payment_session_id VARCHAR(255),
    payment_provider VARCHAR(50),  -- STRIPE, PAYPAL
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Endereços do utilizador
CREATE TABLE user_addresses (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state_name VARCHAR(100),
    state_id INTEGER REFERENCES states(id),
    postal_code VARCHAR(20),
    country_code CHAR(2) REFERENCES countries(code) NOT NULL,
    phone VARCHAR(30),
    
    is_default BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.8 DOMÍNIO: Encomendas (Orders)

```sql
-- Estado da encomenda (máquina de estados)
CREATE TYPE order_status AS ENUM (
    'PENDING',           -- Aguarda pagamento
    'PENDING_APPROVAL',  -- Risk gate, aguarda aprovação
    'PAID',              -- Pago, aguarda envio
    'PROCESSING',        -- Em processamento pelo vendedor
    'SHIPPED',           -- Enviado
    'DELIVERED',         -- Entregue (confirmado)
    'COMPLETED',         -- Finalizado
    'CANCELLED',         -- Cancelado
    'REFUNDED',          -- Reembolsado
    'DISPUTED'           -- Em disputa
);

-- Encomendas
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    order_number VARCHAR(20) UNIQUE NOT NULL,  -- Número legível
    
    buyer_id BIGINT REFERENCES users(id) NOT NULL,
    store_id BIGINT REFERENCES stores(id) NOT NULL,
    
    status order_status DEFAULT 'PENDING',
    
    -- Valores
    items_total DECIMAL(12,2) NOT NULL,
    shipping_cost DECIMAL(12,2) NOT NULL,
    insurance_cost DECIMAL(12,2) DEFAULT 0,
    tracking_fee DECIMAL(12,2) DEFAULT 0,
    tax_amount DECIMAL(12,2) DEFAULT 0,
    grand_total DECIMAL(12,2) NOT NULL,
    
    -- Moedas
    store_currency_id INTEGER REFERENCES currencies(id),
    buyer_currency_id INTEGER REFERENCES currencies(id),
    exchange_rate DECIMAL(12,6),
    
    -- Envio
    shipping_method_id BIGINT REFERENCES store_shipping_methods(id),
    shipping_address_snapshot JSONB NOT NULL,
    
    -- Pagamento
    payment_method_id BIGINT REFERENCES store_payment_methods(id),
    payment_status VARCHAR(20),  -- PENDING, PROCESSING, COMPLETED, FAILED
    payment_reference VARCHAR(255),
    paid_at TIMESTAMPTZ,
    
    -- Tracking
    tracking_number VARCHAR(100),
    tracking_url VARCHAR(500),
    shipped_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    
    -- Proof (para envios sem tracking)
    shipping_proof_url VARCHAR(500),
    shipping_proof_uploaded_at TIMESTAMPTZ,
    
    -- Notas
    buyer_notes TEXT,
    seller_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    INDEX idx_orders_buyer (buyer_id),
    INDEX idx_orders_store (store_id),
    INDEX idx_orders_status (status)
);

-- Itens da encomenda (snapshot dos lotes)
CREATE TABLE order_items (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(id) ON DELETE CASCADE,
    lot_id BIGINT REFERENCES lots(id),  -- Referência original
    
    -- Snapshot completo do item
    item_snapshot JSONB NOT NULL,  -- Nome, número, cor, condição, etc.
    
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,4) NOT NULL,
    sale_price DECIMAL(10,4),
    line_total DECIMAL(12,2) NOT NULL
);

-- Histórico de estados da encomenda
CREATE TABLE order_status_history (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(id),
    old_status order_status,
    new_status order_status NOT NULL,
    changed_by BIGINT REFERENCES users(id),
    reason TEXT,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Disputas
CREATE TABLE disputes (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(id) UNIQUE,
    opened_by BIGINT REFERENCES users(id),
    
    status VARCHAR(20) DEFAULT 'OPEN',  -- OPEN, UNDER_REVIEW, RESOLVED, CLOSED
    reason_code VARCHAR(50) NOT NULL,
    description TEXT,
    
    -- Decisão
    resolved_by BIGINT REFERENCES users(id),
    resolution_code VARCHAR(50),
    resolution_notes TEXT,
    resolved_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evidências de disputas
CREATE TABLE dispute_evidence (
    id BIGSERIAL PRIMARY KEY,
    dispute_id BIGINT REFERENCES disputes(id),
    uploaded_by BIGINT REFERENCES users(id),
    
    evidence_type VARCHAR(50),  -- IMAGE, DOCUMENT, TEXT
    file_url VARCHAR(500),
    description TEXT,
    
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reembolsos
CREATE TABLE refunds (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(id),
    
    amount DECIMAL(12,2) NOT NULL,
    reason_code VARCHAR(50),
    notes TEXT,
    
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, PROCESSING, COMPLETED, FAILED
    
    processed_by BIGINT REFERENCES users(id),
    payment_reference VARCHAR(255),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);
```

### 4.9 DOMÍNIO: Billing / Fees

```sql
-- Faturas mensais da plataforma para vendedores
CREATE TABLE seller_invoices (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT REFERENCES stores(id),
    
    invoice_number VARCHAR(30) UNIQUE NOT NULL,
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    
    -- Valores
    gross_sales DECIMAL(12,2),
    platform_fee_rate DECIMAL(5,4),  -- Ex: 0.03 = 3%
    platform_fee_amount DECIMAL(12,2),
    other_fees DECIMAL(12,2),
    total_due DECIMAL(12,2),
    
    -- Estado
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, PAID, OVERDUE
    
    due_date DATE,
    paid_at TIMESTAMPTZ,
    payment_reference VARCHAR(255),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Linhas de fee detalhadas
CREATE TABLE seller_fee_lines (
    id BIGSERIAL PRIMARY KEY,
    invoice_id BIGINT REFERENCES seller_invoices(id),
    
    fee_type VARCHAR(50) NOT NULL,  -- SALE_FEE, LISTING_FEE, PAYMENT_PROCESSING
    description TEXT,
    quantity INTEGER DEFAULT 1,
    unit_amount DECIMAL(10,4),
    total_amount DECIMAL(12,2),
    
    -- Referência à ordem (se aplicável)
    order_id BIGINT REFERENCES orders(id)
);

-- Pagamentos de fees
CREATE TABLE fee_payments (
    id BIGSERIAL PRIMARY KEY,
    invoice_id BIGINT REFERENCES seller_invoices(id),
    
    amount DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(50),  -- PAYPAL, STRIPE, BANK_TRANSFER
    payment_reference VARCHAR(255),
    
    status VARCHAR(20) DEFAULT 'PENDING',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

### 4.10 DOMÍNIO: Auth / RBAC / Auditoria

```sql
-- Utilizadores
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    country_code CHAR(2) REFERENCES countries(code),
    preferred_currency_id INTEGER REFERENCES currencies(id),
    preferred_language VARCHAR(5) DEFAULT 'en',
    
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Roles
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- Dados iniciais de roles
-- INSERT: user, seller, staff_support, staff_finance, staff_catalog, admin

-- Permissões
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    scope VARCHAR(50) NOT NULL,   -- orders, catalog, billing, etc.
    action VARCHAR(50) NOT NULL,  -- read, write, delete, admin
    
    UNIQUE(scope, action)
);

-- Role -> Permissions
CREATE TABLE role_permissions (
    role_id INTEGER REFERENCES roles(id),
    permission_id INTEGER REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);

-- User -> Roles
CREATE TABLE user_roles (
    user_id BIGINT REFERENCES users(id),
    role_id INTEGER REFERENCES roles(id),
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by BIGINT REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

-- Sessões
CREATE TABLE user_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);

-- Log de auditoria geral
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id BIGINT,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice para queries de auditoria
CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_date ON audit_log(created_at);
```

---

## 5. CONTRATOS DE API (Endpoints Observados)

### 5.1 Endpoints Críticos por Domínio

#### SEARCH (Pesquisa)
| Método | Endpoint | Query Keys | Descrição |
|--------|----------|------------|-----------|
| GET | `/ajax/clone/search/searchproduct.ajax` | q, st, cond, type, cat, yf, yt, loc, reg, ca, ss, pmt, nmp, color, min, max, minqty, nosuperlot, incomplete, showempty, rpp, pi, ci | Pesquisa de produtos |
| GET | `/ajax/clone/search/searchproductADP.ajax` | q | Autocomplete de pesquisa |
| POST | `/_ajax/getSearchQuick.ajax` | - | Pesquisa rápida |

#### LOTS / INVENTORY
| Método | Endpoint | Query Keys | Descrição |
|--------|----------|------------|-----------|
| GET | `/ajax/clone/catalogifs.ajax` | itemid, ss, cond, reg, iconly, ca, loc, max, min, minqty, nmp, nosuperlot, pi, pmt, rpp, st | Lista sellers/lots por item |
| GET | `/store/searchitems.ajax` | sid, desc, invID, pgSize, sort | Pesquisa inventário de loja |
| POST | `/ajax/renovate/storeInventoryDetail/list.ajax` | - | Lista detalhe inventário |
| POST | `/ajax/renovate/storeInventoryDetail/update.ajax` | - | Atualiza inventário |

#### CART (Carrinho)
| Método | Endpoint | Query Keys | Descrição |
|--------|----------|------------|-----------|
| GET | `/v3api/cart/count` | - | Contagem itens carrinho |
| GET | `/v3api/cart/summary` | cartCountLimit | Sumário carrinho |
| GET | `/ajax/clone/cart/list.ajax` | sid, sum | Lista carrinho por loja |
| POST | `/ajax/clone/cart/add.ajax` | itemArray, sid, srcLocation | Adicionar ao carrinho |
| POST | `/ajax/clone/cart/update.ajax` | itemArray, sid | Atualizar carrinho |
| POST | `/ajax/renovate/cart/delete.ajax` | - | Remover do carrinho |

#### CHECKOUT
| Método | Endpoint | Query Keys | Descrição |
|--------|----------|------------|-----------|
| GET | `/ajax/clone/store/preparecheckout.ajax` | sid, action | Preparar checkout |
| GET | `/ajax/clone/store/checkoutdata.ajax` | sid, action, shipMethodID, pmtMethodID, postalCode, jsonAddress, ... | Dados de checkout e quotes |
| GET | `/ajax/clone/store/checkout.ajax` | sid, invoiceType, pmtMethodID, shipMethodID, strAddress1, ... | Submeter checkout |
| GET | `/ajax/clone/store/updateaddress.ajax` | strAddress1, strCity, codeCountry, strPostalCode, ... | Atualizar endereço |

#### WANTED LISTS
| Método | Endpoint | Query Keys | Descrição |
|--------|----------|------------|-----------|
| POST | `/ajax/renovate/wanted/getStoreResult.ajax` | listWantedItems, country_filter, currency_filter, ... | Encontrar lojas com wanted items |
| POST | `/ajax/renovate/wanted/getWantedListSuggest.ajax` | listWantedItems, ... | Sugestões para wanted list |
| POST | `/ajax/clone/wanted/edit.ajax` | - | Editar wanted item |
| POST | `/ajax/clone/wanted/editList.ajax` | - | Editar wanted list |
| POST | `/ajax/clone/wanted/upload.ajax` | - | Upload wanted list |

#### ORDERS
| Método | Endpoint | Query Keys | Descrição |
|--------|----------|------------|-----------|
| GET | `/ajax/clone/store/orderconfirmation.ajax` | orderID, type | Confirmação de encomenda |
| POST | `/_ajax/orders/updateRefund.ajax` | idOrder, typeAction | Processar reembolso |

#### MY STORE / POLICIES
| Método | Endpoint | Query Keys | Descrição |
|--------|----------|------------|-----------|
| GET | `/ajax/clone/store/policy.ajax` | sid | Obter políticas da loja |
| POST | `/ajax/renovate/mystore/terms.ajax` | action | Atualizar termos |
| POST | `/ajax/renovate/mystore/shipping.ajax` | - | Atualizar shipping |
| POST | `/ajax/renovate/mystore/payment.ajax` | - | Atualizar pagamentos |
| GET/POST | `/ajax/renovate/mystore/shipping_method.ajax` | action, id | Gerir métodos de envio |

#### BILLING / FEES
| Método | Endpoint | Query Keys | Descrição |
|--------|----------|------------|-----------|
| POST | `/ajax/renovate/mystore/getStoreFeeActivity.ajax` | - | Obter atividade de fees |
| GET | `/ajax/renovate/mystore/payfee.ajax` | action, mPaymentTotal | Preparar pagamento de fee |
| GET | `/files/renovate/mystore/downloadinvoice.file` | year, month | Download fatura |

### 5.2 Response Shapes Observados

#### Search Response
```json
{
  "result": {
    "typeList": [{
      "type": "P",
      "count": 100,
      "items": [{
        "idItem": 280,
        "typeItem": "P",
        "strItemNo": "3001",
        "strItemName": "Brick 2 x 4",
        "idColor": 11,
        "n4NewQty": 1500,
        "n4NewSellerCnt": 200,
        "mNewMinPrice": "0.05",
        "mNewMaxPrice": "2.00",
        "strCategory": "Brick"
      }]
    }],
    "nCustomItemCnt": 0
  },
  "returnCode": 0,
  "returnMessage": "",
  "errorTicket": 0,
  "procssingTime": 45,
  "strRefNo": "abc123"
}
```

#### Lot/Seller Response (catalogifs.ajax)
```json
{
  "total_count": 500,
  "idColor": 11,
  "rpp": 25,
  "pi": 1,
  "list": [{
    "idInv": 417583725,
    "strDesc": "Good condition",
    "codeNew": "U",
    "codeComplete": "C",
    "n4Qty": 10,
    "mDisplaySalePrice": "€0.15",
    "mInvSalePrice": "0.15",
    "nTier1Qty": 10,
    "nTier1DisplayPrice": "0.12",
    "strStorename": "BricksNL",
    "strSellerUsername": "bricksnl",
    "n4SellerFeedbackScore": 5000,
    "strSellerCountryCode": "NL",
    "mMinBuy": "5.00"
  }],
  "returnCode": 0
}
```

#### Cart Response
```json
{
  "carts": [{
    "sellerID": 123456,
    "sellerName": "BricksNL",
    "storeName": "BricksNL Store",
    "countryID": "NL",
    "feedback": 5000,
    "current_cart": {
      "items": [{
        "itemName": "Brick 2 x 4",
        "invID": 417583725,
        "invQty": 10,
        "cartQty": 5,
        "invPrice": "0.15",
        "salePrice": "0.12",
        "colorName": "Red",
        "itemNo": "3001"
      }],
      "totalItems": 5,
      "totalLots": 1,
      "totalPrice": "€0.60",
      "totalWeightGrams": 50
    }
  }],
  "totStoreCartCnt": 1,
  "returnCode": 0
}
```

#### Checkout Data Response
```json
{
  "checkout": {
    "shippingMethods": [{
      "id": 318780,
      "name": "Standard Post",
      "costType": "weight",
      "minDays": 5,
      "maxDays": 10,
      "quoteAvailable": true,
      "trackingOptions": true,
      "insuranceOptions": true,
      "insuranceCost": "€2.00",
      "trackingFee": "€1.50"
    }],
    "selectedShippingMethodId": 318780,
    "price": {
      "cartItemTotal": "€10.00",
      "shippingCost": "€5.00",
      "salesTax": "€0.00",
      "orderTotal": "€15.00"
    },
    "hasShippingTerms": true
  },
  "returnCode": 0
}
```

---

## 6. DADOS DE REFERÊNCIA (BLGlobalConstants)

### 6.1 Sumário dos Datasets

| Dataset | Registos | Campos Chave |
|---------|----------|--------------|
| colors | 215 | idColor, strColorName, rgb, group |
| categories | 1168 | idCategory, strCatName, types, typeCategory |
| cobrands | 623 | idCoBrand, strCoBrandName, typeCoBrand |
| countries | 235 | idCountry, strCountryName, idCurrency, isEUCountry, mVATRate |
| currencies | 37 | idCurrency, codeCurrency, strCurrencyName, isPaypalAvailable |
| continents | 7 | idContinent, strContinentName |
| languages | 37 | idLanguage, codeLanguage, strLanguageName |
| states_legacy | 1431 | idStateLegacy, strStateName, codeCountryRoot |
| states_new | 1617 | idStateNew, strStateName, codeCountryRoot |
| address_formats | 35 | idAddressFormat, field labels and types |
| address_format_orders | 31 | Por país, ordem dos campos |

### 6.2 Notas Importantes sobre Dados

1. **Color ID 0** = "(Not Applicable)" - deve ser suportado
2. **Countries** inclui `isEUCountry` e `mVATRate` para cálculos de IVA
3. **Currencies** inclui `isPaypalAvailable` para validação de pagamentos
4. **Address Formats** variam significativamente por país

---

## 7. RBAC RECOMENDADO

### 7.1 Roles

| Role | Descrição | Permissões |
|------|-----------|------------|
| `user` | Comprador básico | orders:read, cart:*, wanted:*, messages:read/write |
| `seller` | Vendedor com loja | + inventory:*, store:*, orders:manage |
| `staff_support` | Suporte ao cliente | + orders:admin, disputes:manage, messages:admin |
| `staff_finance` | Financeiro | + billing:admin, refunds:admin |
| `staff_catalog` | Curadoria do catálogo | + catalog:admin, images:admin |
| `admin` | Administrador total | ALL permissions |

### 7.2 Scopes de Permissão

```
orders:read, orders:write, orders:admin
catalog:read, catalog:write, catalog:admin
inventory:read, inventory:write
billing:read, billing:write, billing:admin
disputes:read, disputes:manage
users:read, users:admin
audit:read
```

---

## 8. ESTRUTURA DO PROJETO (FastAPI)

```
brikick/
├── api/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── deps.py                 # Dependencies (auth, db)
│   └── v1/
│       ├── __init__.py
│       ├── router.py           # Main router
│       ├── catalog/
│       │   ├── router.py
│       │   ├── schemas.py
│       │   └── service.py
│       ├── stores/
│       ├── inventory/
│       ├── search/
│       ├── wanted/
│       ├── cart/
│       ├── checkout/
│       ├── orders/
│       ├── billing/
│       └── auth/
├── core/
│   ├── __init__.py
│   ├── config.py               # Settings
│   ├── security.py             # JWT, hashing
│   └── exceptions.py           # Custom exceptions
├── db/
│   ├── __init__.py
│   ├── session.py              # Database session
│   ├── base.py                 # Base model
│   └── models/
│       ├── __init__.py
│       ├── catalog.py
│       ├── stores.py
│       ├── inventory.py
│       ├── cart.py
│       ├── orders.py
│       ├── billing.py
│       └── users.py
├── services/
│   ├── __init__.py
│   ├── search_service.py       # Elasticsearch/Meilisearch
│   ├── payment_service.py      # Stripe/PayPal
│   ├── email_service.py
│   └── file_service.py         # S3/MinIO
├── workers/
│   ├── __init__.py
│   ├── celery_app.py
│   └── tasks/
│       ├── import_tasks.py     # Mass upload
│       ├── image_tasks.py
│       └── notification_tasks.py
├── migrations/
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_catalog.py
│   ├── test_cart.py
│   └── ...
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── Dockerfile.web
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
└── README.md
```

---

## 9. DOCKER COMPOSE

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://brikick:brikick@postgres:5432/brikick
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
    depends_on:
      - postgres
      - redis
      - minio

  web:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    depends_on:
      - api

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    environment:
      - DATABASE_URL=postgresql://brikick:brikick@postgres:5432/brikick
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=brikick
      - POSTGRES_PASSWORD=brikick
      - POSTGRES_DB=brikick
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"

  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
    ports:
      - "80:80"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

---

## 10. MILESTONES DE IMPLEMENTAÇÃO

### Phase 0: Scaffolding (Fundação)
- [ ] Setup repositório, estrutura de pastas
- [ ] Configurar Docker Compose
- [ ] Setup FastAPI base com health check
- [ ] Configurar Alembic para migrations
- [ ] Setup OpenAPI/Swagger
- [ ] Configurar linting (ruff, black, mypy)
- [ ] Setup Next.js base

### Phase 1: Catálogo (Read-Only)
- [ ] Modelos: item_types, categories, colors, catalog_items
- [ ] Seed de dados de referência
- [ ] API: GET /catalog/items, /catalog/categories, /catalog/colors
- [ ] Frontend: Página de catálogo, browse por categoria

### Phase 2: Lojas e Inventário
- [ ] Modelos: stores, lots, store_policies
- [ ] API: CRUD de lojas, CRUD de lotes
- [ ] Frontend: Página de loja, listagem de inventário

### Phase 3: Pesquisa com Facetas
- [ ] Integrar Meilisearch/Elasticsearch
- [ ] API: /search com facetas, paginação, ordenação
- [ ] Frontend: Página de pesquisa avançada

### Phase 4: Carrinho Multi-Loja
- [ ] Modelos: carts, cart_stores, cart_items
- [ ] API: Gestão completa de carrinho
- [ ] Frontend: Página de carrinho com split por loja

### Phase 5: Checkout com Shipping
- [ ] Modelos: checkout_drafts, user_addresses
- [ ] API: Fluxo de checkout, quotes de shipping
- [ ] Hard rule: Bloquear checkout sem método de envio
- [ ] Frontend: Fluxo de checkout step-by-step

### Phase 6: Encomendas e Fulfillment
- [ ] Modelos: orders, order_items, order_status_history
- [ ] API: Ciclo de vida de encomendas
- [ ] Frontend: Dashboard de encomendas (buyer/seller)

### Phase 7: Mensagens e Disputas
- [ ] Modelos: messages, disputes, dispute_evidence
- [ ] API: Sistema de mensagens, abertura de disputas
- [ ] Frontend: Interface de mensagens

### Phase 8: Billing e Fees
- [ ] Modelos: seller_invoices, seller_fee_lines
- [ ] API: Gestão de fees, download de faturas
- [ ] Integração Stripe/PayPal para pagamento de fees

### Phase 9: Admin e Auditoria
- [ ] API: Endpoints admin/staff
- [ ] Audit log completo
- [ ] Frontend: Consola de administração

---

## 11. RISCOS E LACUNAS IDENTIFICADAS

### 11.1 Lacunas nos Dados Capturados

| Lacuna | Impacto | Mitigação |
|--------|---------|-----------|
| Search facets response body | Médio | Implementar schema próprio, adaptar após validação |
| MyStore SAVE payloads | Médio | Desenhar contratos próprios extensíveis |
| Mass upload multipart | Baixo | Implementar formato BrickStore XML standard |
| Checkout pós-seleção | Médio | Inferir fluxo, feature flag para ajustes |
| Monthly invoice schema | Baixo | Desenhar schema próprio |

### 11.2 Restrições de Design

1. **Não copiar BrickLink**: Usar IDs internos, BL IDs apenas como mapeamento
2. **GDPR/PII**: Data minimization, encriptação, direito ao esquecimento
3. **EU Compliance**: VAT já disponível nos dados de países
4. **Independência**: Sistema funciona sem depender de scraping

---

## 12. APÊNDICE: MAPEAMENTO DE FICHEIROS

| Ficheiro | Uso no Projeto |
|----------|----------------|
| `Prompt.txt` | Especificação do projeto, requisitos |
| `README.md` | Contexto dos contratos observados |
| `implementation_notes_fastapi_postgres_nextjs.md` | Guia de módulos e estratégia |
| `endpoints_critical_prioritized.csv` | Lista de endpoints para implementar |
| `endpoints_union_api_like_v6.csv` | União de todos os endpoints API |
| `blglobalconstants_summary.json` | Tamanhos dos datasets de referência |
| `StoreItemAjaxResponse.schema.json` | Schema de detalhe de lot |
| `StoreSearchItemsAjaxResponse.schema.json` | Schema de pesquisa de inventário |
| `StorePolicyAjaxResponse.schema.json` | Schema de políticas de loja |
| `*.keys.json` | Lista de keys para validação |
| `har_manifest.csv` | Cobertura de HAR captures |
| `js_extracted_endpoints.csv` | Endpoints descobertos em JS |
| `artifact_inventory.csv` | Inventário completo de artefactos |

---

## 13. PRÓXIMOS PASSOS PARA GPT 5.2 CODEX

### 13.1 Sequência Recomendada de Prompts

1. **"Cria o setup inicial do projeto FastAPI com a estrutura de pastas documentada"**

2. **"Implementa os modelos SQLAlchemy para o domínio de Catálogo (item_types, categories, colors, catalog_items)"**

3. **"Cria as migrations Alembic para os modelos de catálogo"**

4. **"Implementa os endpoints REST para /api/v1/catalog com schemas Pydantic"**

5. **"Implementa os modelos e endpoints para Lojas e Inventário"**

6. **"Implementa o sistema de pesquisa com integração Meilisearch"**

7. **"Implementa o carrinho multi-loja com todas as operações CRUD"**

8. **"Implementa o fluxo de checkout com hard rules de shipping obrigatório"**

9. **"Implementa o ciclo de vida de encomendas com máquina de estados"**

10. **"Implementa o sistema de billing e fees para vendedores"**

### 13.2 Contexto Essencial para Cada Prompt

Inclua sempre:
- Stack: FastAPI + PostgreSQL + Next.js
- A regra de negócio relevante (das "Hard Rules")
- O schema de resposta esperado (do contrato observado)
- Os campos do modelo de dados

---

*Documento gerado automaticamente a partir da análise do compêndio Brikick v1*
*Data: Janeiro 2026*
