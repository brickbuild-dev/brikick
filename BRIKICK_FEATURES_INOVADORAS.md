# BRIKICK - Análise das Features Inovadoras

> **Análise rigorosa dos 21 pontos diferenciadores do projeto**

---

## RESUMO EXECUTIVO

Os 21 pontos apresentados dividem-se em **5 categorias estratégicas**:

| Categoria | Pontos | Impacto |
|-----------|--------|---------|
| **Anti-fraude/Transparência** | 1, 3, 4, 5, 9, 10, 20 | Confiança na plataforma |
| **Sistema de Reputação** | 11, 12, 13, 14, 15 | Substituir feedback vingativo |
| **Experiência do Utilizador** | 7, 8, 16, 17, 18, 21 | Melhor UX que concorrência |
| **Modelo de Negócio** | 2, 6, 19 | Receita e controlo |
| **Expansão de Catálogo** | MOC Instructions | Novo mercado |

---

## ANÁLISE DETALHADA POR PONTO

### PONTO 1: Price Cap Anti-Inflação/Fraude

**Descrição:**
> Não permitir mais do dobro do valor de venda sobre o preço base actual (avg 6 meses) para não criar inflação nem valores irreais ou possíveis fraudes/lavagem de dinheiro.

**Análise Técnica:**

```
REGRA: unit_price <= (avg_price_6_months * 2.0)
```

**Implementação necessária:**

1. **Tabela de Price Guide (histórico de preços)**
```sql
CREATE TABLE price_guide (
    id BIGSERIAL PRIMARY KEY,
    catalog_item_id BIGINT REFERENCES catalog_items(id),
    color_id INTEGER REFERENCES colors(id),
    condition VARCHAR(1),  -- N, U
    
    -- Métricas calculadas (atualizar diariamente via job)
    avg_price_6m DECIMAL(10,4),
    min_price_6m DECIMAL(10,4),
    max_price_6m DECIMAL(10,4),
    sales_count_6m INTEGER,
    
    -- Price cap calculado
    price_cap DECIMAL(10,4) GENERATED ALWAYS AS (avg_price_6m * 2.0) STORED,
    
    last_calculated_at TIMESTAMPTZ,
    
    UNIQUE(catalog_item_id, color_id, condition)
);
```

2. **Validação no save de Lot**
```python
async def validate_lot_price(lot: LotCreate, db: AsyncSession) -> ValidationResult:
    price_guide = await get_price_guide(lot.catalog_item_id, lot.color_id, lot.condition)
    
    if price_guide and lot.unit_price > price_guide.price_cap:
        return ValidationResult(
            valid=False,
            error_code="PRICE_CAP_EXCEEDED",
            message=f"Preço {lot.unit_price} excede o cap de {price_guide.price_cap} (2x avg 6m)",
            data={
                "your_price": lot.unit_price,
                "avg_6m": price_guide.avg_price_6m,
                "price_cap": price_guide.price_cap
            },
            actions=["REQUEST_OVERRIDE", "ADJUST_PRICE"]
        )
    return ValidationResult(valid=True)
```

3. **Override Request (para casos legítimos)**
```sql
CREATE TABLE price_override_requests (
    id BIGSERIAL PRIMARY KEY,
    lot_id BIGINT REFERENCES lots(id),
    requested_price DECIMAL(10,4),
    price_cap DECIMAL(10,4),
    justification TEXT NOT NULL,
    
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, APPROVED, REJECTED
    reviewed_by BIGINT REFERENCES users(id),
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Impacto Arquitectural:** 
- Job diário para calcular price guide
- Validação em todos os endpoints de criação/edição de lotes
- Painel admin para override requests

---

### PONTO 2: API de Store por Autorização Admin

**Descrição:**
> API de store por disponibilidade por autorização apenas de admin.

**Análise:**
Controlar quem pode usar a API programática para gerir a loja. Isto evita bots abusivos e permite monetizar o acesso.

**Implementação:**

```sql
CREATE TABLE store_api_access (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT REFERENCES stores(id) UNIQUE,
    
    -- Estado
    status VARCHAR(20) DEFAULT 'DISABLED',  -- DISABLED, PENDING, APPROVED, REVOKED
    
    -- Credenciais
    api_key_hash VARCHAR(255),
    api_secret_hash VARCHAR(255),
    
    -- Limites
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_day INTEGER DEFAULT 10000,
    
    -- Aprovação
    requested_at TIMESTAMPTZ,
    request_reason TEXT,
    approved_by BIGINT REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    
    -- Auditoria
    last_used_at TIMESTAMPTZ,
    total_requests BIGINT DEFAULT 0
);
```

**Middleware de validação:**
```python
async def validate_store_api_access(api_key: str, store_id: int) -> bool:
    access = await get_store_api_access(store_id)
    if not access or access.status != 'APPROVED':
        raise HTTPException(403, "Store API access not authorized")
    if not verify_api_key(api_key, access.api_key_hash):
        raise HTTPException(401, "Invalid API key")
    await check_rate_limits(access)
    return True
```

---

### PONTO 3: Portes Justos (Anti-Inflação de Shipping)

**Descrição:**
> Não andar a criar inflação no envio para ganhar mais dinheiro e fugir ao algoritmo de pagamento de fees.

**Problema identificado:**
Vendedores inflacionam shipping para reduzir o valor tributável em fees (que só incidem sobre produtos).

**Solução: Shipping Fairness System**

```sql
CREATE TABLE shipping_fairness_config (
    id SERIAL PRIMARY KEY,
    
    -- Tolerância máxima sobre o custo real
    max_markup_percentage DECIMAL(5,2) DEFAULT 15.0,  -- Max 15% sobre custo real
    
    -- Alertas
    alert_threshold_percentage DECIMAL(5,2) DEFAULT 25.0,
    auto_flag_threshold DECIMAL(5,2) DEFAULT 50.0,
    
    updated_at TIMESTAMPTZ
);

CREATE TABLE shipping_cost_benchmarks (
    id BIGSERIAL PRIMARY KEY,
    
    -- Origem e destino
    origin_country CHAR(2),
    destination_country CHAR(2),
    destination_region VARCHAR(50),  -- Para países grandes
    
    -- Carrier e serviço
    carrier VARCHAR(50),
    service_type VARCHAR(50),  -- STANDARD, EXPRESS, TRACKED
    
    -- Pesos
    weight_min_grams INTEGER,
    weight_max_grams INTEGER,
    
    -- Custo de referência
    benchmark_cost DECIMAL(10,2),
    benchmark_currency CHAR(3),
    
    -- Fonte
    source VARCHAR(50),  -- API, MANUAL, SCRAPED
    last_updated TIMESTAMPTZ
);

CREATE TABLE shipping_fairness_flags (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(id),
    store_id BIGINT REFERENCES stores(id),
    
    -- Valores
    charged_shipping DECIMAL(10,2),
    estimated_real_cost DECIMAL(10,2),
    markup_percentage DECIMAL(5,2),
    
    -- Estado
    flag_type VARCHAR(20),  -- WARNING, VIOLATION
    status VARCHAR(20) DEFAULT 'OPEN',  -- OPEN, REVIEWED, DISMISSED, CONFIRMED
    
    -- Resolução
    reviewed_by BIGINT REFERENCES users(id),
    review_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Lógica de validação no checkout:**
```python
async def validate_shipping_fairness(
    store_id: int,
    shipping_cost: Decimal,
    weight_grams: int,
    origin_country: str,
    destination_country: str
) -> ShippingValidation:
    
    benchmark = await get_shipping_benchmark(
        origin_country, destination_country, weight_grams
    )
    
    if benchmark:
        markup = ((shipping_cost - benchmark.cost) / benchmark.cost) * 100
        config = await get_fairness_config()
        
        if markup > config.auto_flag_threshold:
            await create_shipping_flag(
                store_id, shipping_cost, benchmark.cost, markup, "VIOLATION"
            )
            return ShippingValidation(
                valid=False,
                error_code="SHIPPING_COST_EXCESSIVE",
                message=f"Shipping cost {markup:.0f}% above benchmark"
            )
        elif markup > config.alert_threshold:
            await create_shipping_flag(
                store_id, shipping_cost, benchmark.cost, markup, "WARNING"
            )
    
    return ShippingValidation(valid=True)
```

---

### PONTO 4: IA para Verificar Portes

**Descrição:**
> Pensei em criar IA para verificar os portes de envio, mas são muitos países e muitos serviços.

**Solução Prática:**

1. **Fase 1: Integração com APIs de carriers**
   - APIs reais: CTT, DHL, FedEx, UPS, etc.
   - Obter quotes automáticas

2. **Fase 2: ML para detecção de anomalias**
```python
# Modelo simples de detecção de anomalias
class ShippingAnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1)
    
    def detect_anomaly(self, shipping_data: dict) -> float:
        features = [
            shipping_data['cost'],
            shipping_data['weight'],
            shipping_data['distance_km'],
            shipping_data['historical_avg_for_route']
        ]
        return self.model.predict([features])[0]
```

3. **Fase 3: Crowdsourced verification**
   - Compradores reportam custos reais de envio
   - Criar baseline mais preciso

---

### PONTO 5: Sem Request Invoice (Checkout Automático)

**Descrição:**
> Não quero a opção de pedir request invoice, o checkout funciona apenas por método automático.

**Implementação:**
- Remover completamente o fluxo de "Request Invoice"
- Checkout é sempre: Selecionar → Pagar → Encomenda criada
- Sem estado intermediário de "aguardar fatura do vendedor"

```python
# Checkout states permitidos
class CheckoutStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_PAYMENT = "PENDING_PAYMENT"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    
    # NÃO EXISTE: AWAITING_INVOICE
```

**Implicação:** Todos os métodos de envio devem ter preço calculável automaticamente.

---

### PONTO 6: Sem Handling Fees / Custos Escondidos

**Descrição:**
> Retirar opção de cobrar handling ou outro custo extra nas encomendas.

**Implementação:**

```sql
-- Na tabela de checkout/orders, NÃO existem estes campos:
-- handling_fee ❌
-- packaging_fee ❌
-- service_fee ❌
-- other_fees ❌

-- Apenas permitido:
-- items_total ✓
-- shipping_cost ✓
-- tax_amount ✓ (se aplicável por lei)
```

**Validação:**
```python
async def calculate_order_total(checkout: CheckoutDraft) -> OrderTotal:
    items_total = sum(item.line_total for item in checkout.items)
    shipping_total = checkout.shipping_cost + checkout.insurance_cost
    tax_total = calculate_tax_if_required(items_total, checkout.destination)
    
    return OrderTotal(
        items_total=items_total,
        shipping_total=shipping_total,
        tax_total=tax_total,
        grand_total=items_total + shipping_total + tax_total
        # SEM: handling, packaging, service fees, etc.
    )
```

---

### PONTO 7: Sync Limitado + Serviço Externo

**Descrição:**
> Criar um módulo próprio na plataforma para apenas sync automático com BrickLink OU BrickOwl (apenas uma), para obrigar a usar o nosso serviço externo de sync entre as 3 plataformas.

**Estratégia de Negócio:**
- Brikick oferece sync gratuito com UMA plataforma
- Para sync com TODAS (Brikick + BL + BO), é necessário serviço externo pago

```sql
CREATE TABLE store_sync_config (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT REFERENCES stores(id) UNIQUE,
    
    -- Apenas UMA permitida gratuitamente
    sync_platform VARCHAR(20),  -- 'BRICKLINK' ou 'BRICKOWL'
    sync_enabled BOOLEAN DEFAULT FALSE,
    
    -- Credenciais (encriptadas)
    platform_credentials_encrypted BYTEA,
    
    -- Estado
    last_sync_at TIMESTAMPTZ,
    sync_status VARCHAR(20),
    items_synced INTEGER,
    
    created_at TIMESTAMPTZ
);

-- Constraint: apenas uma plataforma
ALTER TABLE store_sync_config 
ADD CONSTRAINT one_platform_only 
CHECK (sync_platform IN ('BRICKLINK', 'BRICKOWL'));
```

---

### PONTO 8: Pesquisa Universal (Multi-Platform ID)

**Descrição:**
> Permitir pesquisar por part_id de todas as plataformas no mesmo campo de pesquisa, mas os resultados devem ser apresentados como os oficiais do Brikick.

**Implementação:**

```sql
-- Já temos a tabela de mapeamentos
CREATE TABLE catalog_item_mappings (
    catalog_item_id BIGINT REFERENCES catalog_items(id),
    source VARCHAR(20),  -- BRICKLINK, BRICKOWL, REBRICKABLE, LDRAW
    external_id VARCHAR(100),
    
    -- Índice para pesquisa rápida
    INDEX idx_external_lookup (source, external_id)
);
```

**Search Service:**
```python
async def universal_search(query: str) -> SearchResults:
    # 1. Tentar encontrar por ID externo
    if looks_like_part_number(query):
        # Procurar em todos os mapeamentos
        mapping = await db.execute(
            select(CatalogItemMapping)
            .where(CatalogItemMapping.external_id == query)
        )
        if mapping:
            # Retornar o item Brikick correspondente
            return await get_catalog_item(mapping.catalog_item_id)
    
    # 2. Pesquisa normal por nome/descrição
    return await fulltext_search(query)
```

**UX:** 
- User pesquisa "3001" (BrickLink ID)
- Sistema encontra mapeamento BL → Brikick
- Mostra o item com ID Brikick (ex: "BK-23321")

---

### PONTO 9: Módulo Brickit para Lojas

**Descrição:**
> Ter o módulo do Brickit (semelhante ao What The Fig) integrado apenas para lojas.

**Funcionalidade:**
- Upload de foto de peças
- IA identifica as peças
- Adiciona automaticamente ao inventário

```sql
CREATE TABLE brickit_scans (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT REFERENCES stores(id),
    
    -- Imagem
    image_url VARCHAR(500),
    
    -- Resultados
    status VARCHAR(20),  -- PROCESSING, COMPLETED, FAILED
    identified_items JSONB,  -- [{catalog_item_id, color_id, confidence, quantity}]
    
    -- Acções tomadas
    items_added_to_inventory INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ
);
```

**Integração:**
- Usar API do Brickognize ou treinar modelo próprio
- Disponível apenas para lojas (não compradores)

---

### PONTO 10: IA para Verificar Recibos/Documentos

**Descrição:**
> Usar IA para verificar recibos quando há denúncias de falta de envio ou outros documentos.

**Implementação:**

```sql
CREATE TABLE document_verifications (
    id BIGSERIAL PRIMARY KEY,
    dispute_id BIGINT REFERENCES disputes(id),
    
    -- Documento
    document_type VARCHAR(50),  -- SHIPPING_RECEIPT, TRACKING_PROOF, PAYMENT_PROOF
    document_url VARCHAR(500),
    
    -- Verificação IA
    ai_verification_status VARCHAR(20),  -- PENDING, VERIFIED, SUSPICIOUS, FAILED
    ai_confidence_score DECIMAL(5,4),
    ai_extracted_data JSONB,  -- {date, tracking_number, sender, recipient, amount}
    ai_flags JSONB,  -- [{flag_type, description}]
    
    -- Revisão humana (se necessário)
    requires_human_review BOOLEAN DEFAULT FALSE,
    human_review_status VARCHAR(20),
    reviewed_by BIGINT REFERENCES users(id),
    review_notes TEXT,
    
    created_at TIMESTAMPTZ
);
```

**AI Service:**
```python
class DocumentVerificationAI:
    async def verify_shipping_receipt(self, image_url: str) -> VerificationResult:
        # 1. OCR para extrair texto
        text = await self.ocr_service.extract(image_url)
        
        # 2. Extrair campos relevantes
        extracted = await self.extract_shipping_fields(text)
        # {date, tracking_number, sender_address, recipient_address, weight, cost}
        
        # 3. Verificar consistência
        flags = []
        if extracted.date > datetime.now():
            flags.append({"type": "FUTURE_DATE", "severity": "HIGH"})
        if not self.validate_tracking_format(extracted.tracking_number):
            flags.append({"type": "INVALID_TRACKING", "severity": "MEDIUM"})
        
        # 4. Calcular confiança
        confidence = self.calculate_confidence(extracted, flags)
        
        return VerificationResult(
            status="VERIFIED" if confidence > 0.8 else "SUSPICIOUS",
            confidence=confidence,
            extracted_data=extracted,
            flags=flags
        )
```

---

### PONTO 11: Responsabilidade Envio Sem Tracking

**Descrição:**
> O comprador é responsável por correio normal. O vendedor é obrigado a apresentar prova ou perde razão.

**Regra Clara:**

| Tipo de Envio | Responsabilidade | Prova Necessária |
|---------------|------------------|------------------|
| Com Tracking | Vendedor até entrega confirmada | Tracking number |
| Sem Tracking | Comprador aceita risco | Vendedor DEVE enviar foto do recibo |

```sql
ALTER TABLE store_shipping_methods ADD COLUMN 
    tracking_type VARCHAR(20);  -- FULL_TRACKING, DELIVERY_CONFIRMATION, NO_TRACKING

ALTER TABLE orders ADD COLUMN
    buyer_accepted_untracked_risk BOOLEAN DEFAULT FALSE;

-- Para envios sem tracking, exigir prova
ALTER TABLE orders ADD COLUMN
    untracked_proof_required BOOLEAN GENERATED ALWAYS AS (
        tracking_type = 'NO_TRACKING'
    ) STORED;
    
ALTER TABLE orders ADD COLUMN
    untracked_proof_deadline TIMESTAMPTZ;  -- 48h após marcar como enviado
```

**Fluxo:**
1. Vendedor marca como enviado (sem tracking)
2. Sistema exige upload de prova em 48h
3. Se não apresentar → disputa automática a favor do comprador
4. Se apresentar → IA verifica + comprador pode contestar

---

### PONTO 12: Sistema de Penalizações

**Descrição:**
> Ao fim de "X" reclamações/problemas o vendedor leva kick/ban/cooldown/redução de privilégios.

**Implementação:**

```sql
CREATE TABLE user_penalty_config (
    id SERIAL PRIMARY KEY,
    
    -- Thresholds (não públicos)
    warning_threshold INTEGER DEFAULT 3,      -- 3 issues = warning
    cooldown_threshold INTEGER DEFAULT 5,     -- 5 issues = cooldown
    suspension_threshold INTEGER DEFAULT 8,   -- 8 issues = suspension
    ban_threshold INTEGER DEFAULT 12,         -- 12 issues = ban
    
    -- Período de avaliação
    evaluation_period_months INTEGER DEFAULT 6,
    
    -- Decay (issues "expiram" após X meses)
    issue_decay_months INTEGER DEFAULT 12
);

CREATE TABLE user_penalties (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    
    penalty_type VARCHAR(20),  -- WARNING, COOLDOWN, SUSPENSION, BAN
    reason_code VARCHAR(50),
    description TEXT,
    
    -- Duração
    starts_at TIMESTAMPTZ DEFAULT NOW(),
    ends_at TIMESTAMPTZ,  -- NULL para ban permanente
    
    -- Restrições aplicadas
    restrictions JSONB,  -- {can_sell: false, can_buy: false, api_disabled: true}
    
    -- Apelo
    appeal_status VARCHAR(20),
    appeal_text TEXT,
    appeal_reviewed_by BIGINT,
    
    created_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_issues (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    
    issue_type VARCHAR(50),  -- DISPUTE_LOST, COMPLAINT, SHIPPING_VIOLATION, PRICE_VIOLATION
    severity INTEGER,  -- 1-5
    related_order_id BIGINT,
    related_dispute_id BIGINT,
    
    -- Para decay calculation
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ  -- created_at + decay period
);
```

**Serviço de Penalização:**
```python
async def evaluate_user_penalties(user_id: int):
    config = await get_penalty_config()
    
    # Contar issues activos (não expirados)
    active_issues = await count_active_issues(user_id, config.evaluation_period_months)
    
    # Aplicar penalização apropriada
    if active_issues >= config.ban_threshold:
        await apply_penalty(user_id, "BAN", duration=None)
    elif active_issues >= config.suspension_threshold:
        await apply_penalty(user_id, "SUSPENSION", duration_days=30)
    elif active_issues >= config.cooldown_threshold:
        await apply_penalty(user_id, "COOLDOWN", duration_days=7)
    elif active_issues >= config.warning_threshold:
        await apply_penalty(user_id, "WARNING", duration_days=0)
```

---

### PONTO 13: SLA de Envios e Mensagens

**Descrição:**
> SLA envios de encomendas e resposta a mensagens: 24-48h, 48-72h, 72h+

**Implementação:**

```sql
CREATE TABLE sla_config (
    id SERIAL PRIMARY KEY,
    
    -- Shipping SLAs
    shipping_excellent_hours INTEGER DEFAULT 24,
    shipping_good_hours INTEGER DEFAULT 48,
    shipping_acceptable_hours INTEGER DEFAULT 72,
    
    -- Message Response SLAs
    message_excellent_hours INTEGER DEFAULT 24,
    message_good_hours INTEGER DEFAULT 48,
    message_acceptable_hours INTEGER DEFAULT 72
);

CREATE TABLE sla_metrics (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT REFERENCES stores(id),
    period_start DATE,
    period_end DATE,
    
    -- Shipping metrics
    orders_shipped_total INTEGER,
    orders_shipped_24h INTEGER,
    orders_shipped_48h INTEGER,
    orders_shipped_72h INTEGER,
    orders_shipped_late INTEGER,
    avg_shipping_hours DECIMAL(10,2),
    
    -- Message metrics
    messages_received INTEGER,
    messages_replied_24h INTEGER,
    messages_replied_48h INTEGER,
    messages_replied_72h INTEGER,
    messages_not_replied INTEGER,
    avg_response_hours DECIMAL(10,2),
    
    -- Scores calculados
    shipping_sla_score DECIMAL(5,2),  -- 0-100
    message_sla_score DECIMAL(5,2),   -- 0-100
    
    calculated_at TIMESTAMPTZ
);
```

**Cálculo de Score:**
```python
def calculate_sla_score(metrics: SLAMetrics) -> float:
    # Peso por tier
    weights = {
        "excellent": 1.0,   # 24h
        "good": 0.8,        # 48h
        "acceptable": 0.5,  # 72h
        "late": 0.0         # 72h+
    }
    
    total = metrics.orders_shipped_total
    if total == 0:
        return 100.0
    
    score = (
        (metrics.orders_shipped_24h * weights["excellent"]) +
        (metrics.orders_shipped_48h * weights["good"]) +
        (metrics.orders_shipped_72h * weights["acceptable"]) +
        (metrics.orders_shipped_late * weights["late"])
    ) / total * 100
    
    return round(score, 2)
```

---

### PONTO 14: Sistema de Rating Algorítmico

**Descrição:**
> Rigoroso tracking de eventos para cálculo de rating, substituindo o sistema de feedback do BrickLink.

**MODELO COMPLETO:**

```sql
-- Factores de rating (configuráveis)
CREATE TABLE rating_factors (
    id SERIAL PRIMARY KEY,
    factor_code VARCHAR(50) UNIQUE,
    factor_name VARCHAR(100),
    description TEXT,
    
    -- Aplica-se a
    applies_to VARCHAR(20),  -- SELLER, BUYER, BOTH
    
    -- Peso no cálculo
    weight DECIMAL(5,2),
    
    -- Direcção (mais é melhor ou pior?)
    higher_is_better BOOLEAN,
    
    is_active BOOLEAN DEFAULT TRUE
);

-- Dados iniciais
INSERT INTO rating_factors (factor_code, factor_name, applies_to, weight, higher_is_better) VALUES
-- VENDEDOR
('ITEMS_LISTED_MONTHLY', 'Peças listadas por mês', 'SELLER', 0.05, true),
('LISTING_REGULARITY', 'Regularidade de listagem', 'SELLER', 0.05, true),
('ORDERS_RECEIVED_MONTHLY', 'Encomendas recebidas/mês', 'SELLER', 0.10, true),
('MESSAGE_RESPONSE_RATE', 'Taxa resposta mensagens', 'SELLER', 0.15, true),
('DISPUTES_WON_RATE', 'Taxa disputas ganhas', 'SELLER', 0.15, true),
('SHIPPING_SLA_SCORE', 'Score SLA envios', 'SELLER', 0.20, true),
('PRICE_FAIRNESS', 'Preços justos (vs avg)', 'SELLER', 0.10, true),
('CANCELLATION_RATE', 'Taxa cancelamentos', 'SELLER', 0.10, false),
('ACCOUNT_AGE_MONTHS', 'Idade da conta', 'SELLER', 0.05, true),
('COMPLAINTS_RATE', 'Taxa de queixas', 'SELLER', 0.05, false),

-- COMPRADOR
('ORDERS_PLACED_MONTHLY', 'Encomendas feitas/mês', 'BUYER', 0.15, true),
('PAYMENT_SPEED', 'Velocidade pagamento', 'BUYER', 0.20, true),
('DISPUTES_OPENED_RATE', 'Taxa disputas abertas', 'BUYER', 0.15, false),
('CANCELLATION_RATE_BUYER', 'Taxa cancelamentos', 'BUYER', 0.20, false),
('CHARGEBACK_HISTORY', 'Histórico chargebacks', 'BUYER', 0.25, false),
('ACCOUNT_AGE_MONTHS_BUYER', 'Idade da conta', 'BUYER', 0.05, true);

-- Métricas calculadas por utilizador
CREATE TABLE user_rating_metrics (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    period_start DATE,
    period_end DATE,
    
    -- Raw metrics
    metrics_json JSONB,
    /*
    {
        "items_listed": 150,
        "active_listing_days": 25,
        "orders_received": 45,
        "messages_received": 100,
        "messages_replied": 95,
        "disputes_total": 3,
        "disputes_won": 2,
        "avg_price_vs_market": 1.15,
        "orders_cancelled": 1,
        "complaints_received": 2,
        ...
    }
    */
    
    -- Normalized scores por factor (0-100)
    factor_scores JSONB,
    
    -- Score final
    overall_score DECIMAL(5,2),
    score_tier VARCHAR(20),  -- EXCELLENT, GOOD, AVERAGE, POOR, CRITICAL
    
    calculated_at TIMESTAMPTZ
);

-- Histórico para tracking de evolução
CREATE TABLE user_rating_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    score DECIMAL(5,2),
    tier VARCHAR(20),
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Badges de Gamification:**

```sql
CREATE TABLE badges (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE,
    name VARCHAR(100),
    description TEXT,
    icon_url VARCHAR(500),
    
    -- Tipo
    badge_type VARCHAR(20),  -- ACHIEVEMENT, MONTHLY, MILESTONE
    
    -- Critérios (JSON para flexibilidade)
    criteria JSONB,
    /*
    Exemplos:
    {"type": "threshold", "metric": "overall_score", "min_value": 90}
    {"type": "streak", "metric": "orders_shipped_24h", "days": 30}
    {"type": "milestone", "metric": "total_orders", "value": 1000}
    */
    
    is_active BOOLEAN DEFAULT TRUE
);

INSERT INTO badges (code, name, badge_type, criteria) VALUES
('TRUSTED_SELLER', 'Trusted Seller', 'MONTHLY', 
 '{"type": "threshold", "metric": "overall_score", "min_value": 85, "min_orders": 10}'),
('FAST_SHIPPER', 'Fast Shipper', 'MONTHLY',
 '{"type": "threshold", "metric": "shipping_sla_score", "min_value": 95}'),
('HIGH_ACCURACY', 'High Accuracy', 'MONTHLY',
 '{"type": "threshold", "metric": "disputes_won_rate", "min_value": 95}'),
('LOYALTY_1Y', 'Loyalty - 1 Year', 'MILESTONE',
 '{"type": "milestone", "metric": "account_age_months", "value": 12}'),
('MILESTONE_100', '100 Orders', 'ACHIEVEMENT',
 '{"type": "milestone", "metric": "total_orders_completed", "value": 100}'),
('MILESTONE_1000', '1000 Orders', 'ACHIEVEMENT',
 '{"type": "milestone", "metric": "total_orders_completed", "value": 1000}');

CREATE TABLE user_badges (
    user_id BIGINT REFERENCES users(id),
    badge_id INTEGER REFERENCES badges(id),
    
    awarded_at TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,  -- NULL para permanentes, data para mensais
    
    PRIMARY KEY (user_id, badge_id)
);
```

---

### PONTO 15: MOC Instructions Sales

**Descrição:**
> Criar uma secção de venda para MOC instructions tal como é praticado no Rebrickable.

**Implementação:**

```sql
-- Novo tipo de catálogo
INSERT INTO item_types (id, name, name_plural) VALUES 
('X', 'MOC Instructions', 'MOC Instructions');

CREATE TABLE moc_instructions (
    id BIGSERIAL PRIMARY KEY,
    catalog_item_id BIGINT REFERENCES catalog_items(id),
    creator_id BIGINT REFERENCES users(id),
    
    -- Metadados MOC
    title VARCHAR(255) NOT NULL,
    description TEXT,
    difficulty_level VARCHAR(20),  -- EASY, MEDIUM, HARD, EXPERT
    piece_count INTEGER,
    
    -- Ficheiros
    preview_images JSONB,  -- [{url, is_primary}]
    instruction_file_url VARCHAR(500),  -- PDF ou link
    parts_list_url VARCHAR(500),  -- XML/CSV
    
    -- Preço (do criador)
    price DECIMAL(10,2),
    currency_id INTEGER REFERENCES currencies(id),
    
    -- Se usa peças de sets específicos
    based_on_sets BIGINT[],  -- Array de catalog_item_ids de sets
    
    -- Stats
    downloads_count INTEGER DEFAULT 0,
    rating_avg DECIMAL(3,2),
    rating_count INTEGER DEFAULT 0,
    
    status VARCHAR(20) DEFAULT 'DRAFT',
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE moc_purchases (
    id BIGSERIAL PRIMARY KEY,
    moc_id BIGINT REFERENCES moc_instructions(id),
    buyer_id BIGINT REFERENCES users(id),
    
    price_paid DECIMAL(10,2),
    currency_id INTEGER,
    
    -- Download access
    download_token VARCHAR(255),
    downloads_remaining INTEGER DEFAULT 5,
    
    purchased_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### PONTO 16: Wanted List Melhorada

**Descrição:**
> Filtros mais granulares: localização do vendedor, intervalo de preços, condição das peças.

**Implementação:**

```sql
ALTER TABLE wanted_list_items ADD COLUMN
    -- Filtros de notificação
    notify_max_price DECIMAL(10,2),
    notify_min_quantity INTEGER,
    notify_seller_countries TEXT[],  -- Códigos de países aceites
    notify_seller_continents INTEGER[],
    notify_condition VARCHAR(1),  -- N, U, ou NULL para ambos
    notify_min_seller_rating DECIMAL(5,2);

CREATE TABLE wanted_list_notifications (
    id BIGSERIAL PRIMARY KEY,
    wanted_list_id BIGINT REFERENCES wanted_lists(id),
    
    -- Configuração global da lista
    is_active BOOLEAN DEFAULT TRUE,
    notify_email BOOLEAN DEFAULT TRUE,
    notify_push BOOLEAN DEFAULT TRUE,
    
    -- Frequência
    notification_frequency VARCHAR(20),  -- INSTANT, DAILY, WEEKLY
    
    -- Último envio
    last_notified_at TIMESTAMPTZ
);

CREATE TABLE wanted_matches (
    id BIGSERIAL PRIMARY KEY,
    wanted_item_id BIGINT REFERENCES wanted_list_items(id),
    lot_id BIGINT REFERENCES lots(id),
    
    -- Match score (quão bem corresponde aos critérios)
    match_score DECIMAL(5,2),
    
    -- Estado
    notified BOOLEAN DEFAULT FALSE,
    notified_at TIMESTAMPTZ,
    
    -- Acção do utilizador
    user_action VARCHAR(20),  -- VIEWED, ADDED_TO_CART, PURCHASED, DISMISSED
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### PONTO 17: Anexos em Mensagens

**Descrição:**
> Poder anexar ficheiros às mensagens enviadas.

```sql
CREATE TABLE message_attachments (
    id BIGSERIAL PRIMARY KEY,
    message_id BIGINT REFERENCES messages(id),
    
    file_name VARCHAR(255),
    file_type VARCHAR(50),  -- image/jpeg, application/pdf, etc.
    file_size_bytes INTEGER,
    file_url VARCHAR(500),
    
    -- Verificação de segurança
    virus_scanned BOOLEAN DEFAULT FALSE,
    scan_result VARCHAR(20),
    
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Limites
-- Max 5 attachments per message
-- Max 10MB per file
-- Allowed types: images, PDF, XML (for BrickStore files)
```

---

### PONTO 18: Integração com Correios

**Descrição:**
> Integração com correios locais directamente.

**Implementação:**

```sql
CREATE TABLE shipping_carriers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE,
    name VARCHAR(100),
    
    -- Países onde opera
    countries_served TEXT[],
    
    -- Integração
    integration_type VARCHAR(20),  -- API, MANUAL, PLUGIN
    api_endpoint VARCHAR(500),
    api_credentials_encrypted BYTEA,
    
    -- Capacidades
    supports_label_generation BOOLEAN,
    supports_tracking BOOLEAN,
    supports_pickup_scheduling BOOLEAN,
    
    is_active BOOLEAN DEFAULT TRUE
);

INSERT INTO shipping_carriers (code, name, countries_served, integration_type) VALUES
('CTT', 'CTT Portugal', ARRAY['PT'], 'API'),
('DHL', 'DHL Express', ARRAY['*'], 'API'),
('FEDEX', 'FedEx', ARRAY['*'], 'API'),
('UPS', 'UPS', ARRAY['*'], 'API'),
('ROYALMAIL', 'Royal Mail', ARRAY['UK', 'GB'], 'API'),
('USPS', 'USPS', ARRAY['US'], 'API'),
('CANADAPOST', 'Canada Post', ARRAY['CA'], 'API'),
('DEUTSCHEPOST', 'Deutsche Post', ARRAY['DE'], 'API'),
('LAPOSTE', 'La Poste', ARRAY['FR'], 'API'),
('POSTNL', 'PostNL', ARRAY['NL'], 'API');

CREATE TABLE shipping_quotes (
    id BIGSERIAL PRIMARY KEY,
    
    -- Request
    origin_country CHAR(2),
    origin_postal_code VARCHAR(20),
    destination_country CHAR(2),
    destination_postal_code VARCHAR(20),
    weight_grams INTEGER,
    dimensions_cm JSONB,  -- {length, width, height}
    
    -- Response
    carrier_id INTEGER REFERENCES shipping_carriers(id),
    service_code VARCHAR(50),
    service_name VARCHAR(100),
    price DECIMAL(10,2),
    currency CHAR(3),
    estimated_days_min INTEGER,
    estimated_days_max INTEGER,
    tracking_included BOOLEAN,
    
    -- Cache
    quoted_at TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ
);
```

---

### PONTO 19: Paywall para Features Premium

**Descrição:**
> Sync de inventário e sistema de pick order disponíveis perante paywall.

```sql
CREATE TABLE subscription_plans (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE,
    name VARCHAR(100),
    
    -- Preço
    price_monthly DECIMAL(10,2),
    price_yearly DECIMAL(10,2),
    currency CHAR(3),
    
    -- Ou aumento de fee
    fee_increase_percentage DECIMAL(5,2),  -- Alternativa: +0.5% nas vendas
    
    -- Features incluídas
    features JSONB,
    /*
    {
        "multi_platform_sync": true,
        "pick_order_system": true,
        "priority_support": true,
        "api_access": true,
        "advanced_analytics": true
    }
    */
    
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE store_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT REFERENCES stores(id),
    plan_id INTEGER REFERENCES subscription_plans(id),
    
    billing_type VARCHAR(20),  -- MONTHLY, YEARLY, FEE_BASED
    
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    auto_renew BOOLEAN DEFAULT TRUE,
    
    -- Pagamento
    payment_method_id BIGINT,
    last_payment_at TIMESTAMPTZ,
    next_payment_at TIMESTAMPTZ,
    
    status VARCHAR(20) DEFAULT 'ACTIVE'
);
```

---

### PONTO 20: Pré-Aprovação de Compradores Suspeitos

**Descrição:**
> Sistema de pré-aprovação para compradores sinalizados como problemáticos.

```sql
ALTER TABLE stores ADD COLUMN
    require_approval_for_risky_buyers BOOLEAN DEFAULT FALSE,
    risk_threshold_score DECIMAL(5,2) DEFAULT 50.0;  -- Abaixo disto = requer aprovação

CREATE TABLE order_approvals (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(id) UNIQUE,
    
    -- Razão
    reason VARCHAR(50),  -- LOW_BUYER_RATING, CHARGEBACK_HISTORY, NEW_ACCOUNT, HIGH_VALUE
    buyer_risk_score DECIMAL(5,2),
    
    -- Estado
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, APPROVED, REJECTED
    
    -- Acção
    decided_by BIGINT REFERENCES users(id),  -- store owner
    decision_notes TEXT,
    decided_at TIMESTAMPTZ,
    
    -- Deadlines
    auto_cancel_at TIMESTAMPTZ,  -- Se não decidido em X horas
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Fluxo:**
1. Comprador com rating < threshold faz checkout
2. Pagamento fica em HOLD (autorizado mas não capturado)
3. Vendedor recebe notificação para aprovar/rejeitar
4. Se aprovado → captura pagamento, cria ordem
5. Se rejeitado → cancela autorização, notifica comprador
6. Se timeout → auto-rejeita

---

### PONTO 21: APIs de Cotação de Frete

**Descrição:**
> Integrar serviços de transportadoras ou APIs de cotação diretamente.

*Já coberto no Ponto 18 - Integração com Correios*

---

## RESUMO: IMPACTO NA ARQUITECTURA

### Novas Tabelas Necessárias (28 tabelas adicionais)

```
ANTI-FRAUDE:
- price_guide
- price_override_requests
- shipping_fairness_config
- shipping_cost_benchmarks
- shipping_fairness_flags
- document_verifications

RATING:
- rating_factors
- user_rating_metrics
- user_rating_history
- badges
- user_badges
- sla_config
- sla_metrics

PENALIZAÇÕES:
- user_penalty_config
- user_penalties
- user_issues

NEGÓCIO:
- store_api_access
- store_sync_config
- subscription_plans
- store_subscriptions
- shipping_carriers
- shipping_quotes
- order_approvals

MOC:
- moc_instructions
- moc_purchases

MENSAGENS:
- message_attachments

WANTED:
- wanted_list_notifications
- wanted_matches

BRICKIT:
- brickit_scans
```

### Jobs Necessários (Background Workers)

1. **PriceGuideCalculator** - Diário, calcula avg 6 meses
2. **SLAMetricsCalculator** - Diário, calcula métricas SLA
3. **RatingCalculator** - Semanal, recalcula ratings
4. **BadgeAwarder** - Diário, atribui/remove badges
5. **PenaltyEvaluator** - Diário, avalia penalizações
6. **ShippingBenchmarkUpdater** - Semanal, atualiza benchmarks
7. **WantedMatcher** - Contínuo, procura matches para wanted lists

### Integrações Externas

1. **Shipping Carriers APIs** - CTT, DHL, FedEx, UPS, etc.
2. **Brickognize/Brickit** - Reconhecimento de peças
3. **OCR Service** - Para verificação de documentos
4. **Payment Providers** - Stripe, PayPal (com holds)

---

## SEQUÊNCIA DE IMPLEMENTAÇÃO RECOMENDADA

### Fase 0: Core (já planeado)
- Estrutura base, catálogo, auth

### Fase 1: Anti-Fraude Básico
- Price guide + price cap
- Sem handling fees

### Fase 2: Checkout Automático
- Remover request invoice
- Shipping method obrigatório

### Fase 3: Rating System v1
- SLA tracking
- Métricas básicas

### Fase 4: Penalizações
- Sistema de issues
- Penalidades automáticas

### Fase 5: Integrações Shipping
- APIs de carriers
- Cotações automáticas

### Fase 6: Shipping Fairness
- Benchmarks
- Verificação de portes

### Fase 7: Rating System v2
- Rating algorítmico completo
- Badges

### Fase 8: Features Premium
- Sync multi-plataforma
- Paywall

### Fase 9: IA Features
- Verificação documentos
- Brickit integration

### Fase 10: Expansões
- MOC Instructions
- Pre-approval system
