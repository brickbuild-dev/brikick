# BRIKICK - Quick Reference Card

## Stack
```
Backend:  FastAPI (Python)
Database: PostgreSQL
Frontend: Next.js
Infra:    Docker Compose + Redis + MinIO + Traefik
```

## 10 Domínios do Sistema
1. **Catalog** - Items, types, categories, colors, images
2. **Stores** - Profiles, policies, shipping/payment configs
3. **Inventory/Lots** - Lots, pricing tiers, conditions
4. **Search** - Index, facets, sorting, pagination
5. **Wanted** - Wanted lists, shop sourcing
6. **Cart** - Multi-store cart, validation
7. **Checkout** - Shipping quotes, payment session
8. **Orders** - Lifecycle, fulfillment, disputes
9. **Billing** - Invoices, fees, PSP reconciliation
10. **Auth/RBAC** - Users, roles, audit

## Hard Rules (Obrigatórias)
1. Price cap enforcement → PENDING_REVIEW se exceder
2. Checkout DEVE ter shipping quote selecionado
3. Untracked shipping → upload proof obrigatório
4. Risk gating pode bloquear orders → PENDING_APPROVAL
5. Disputes → reason codes + auditoria completa

## Dados de Referência (BLGlobalConstants)
| Dataset | Count |
|---------|-------|
| Colors | 215 |
| Categories | 1168 |
| Countries | 235 |
| Currencies | 37 |
| States | 1617 |

## Endpoints Críticos Mínimos
```
SEARCH:   GET  /search/products
LOTS:     GET  /lots/{item_id}/sellers
CART:     POST /cart/add, PUT /cart/update, GET /cart
CHECKOUT: GET  /checkout/prepare, POST /checkout/submit
ORDERS:   GET  /orders, PATCH /orders/{id}/status
STORE:    GET  /store/{id}/policy, GET /store/{id}/inventory
```

## Response Shape Padrão
```json
{
  "data": {...},
  "returnCode": 0,
  "returnMessage": "",
  "errorTicket": 0,
  "processingTime": 45,
  "traceId": "abc123"
}
```

## Error Shape
```json
{
  "error_code": "PRICE_CAP_EXCEEDED",
  "reason_code": "LOT_PRICE_ABOVE_CAP",
  "message": "Price exceeds cap",
  "actions": ["REQUEST_OVERRIDE", "ADJUST_PRICE"],
  "trace_id": "abc123"
}
```

## RBAC Roles
- `user` - Buyer
- `seller` - Seller + Store
- `staff_support` - Support team
- `staff_finance` - Finance team
- `staff_catalog` - Catalog curation
- `admin` - Full access

## Key Tables
```sql
catalog_items    -- Products
lots             -- Inventory listings
stores           -- Seller stores
carts            -- Shopping carts
cart_items       -- Cart lines
checkout_drafts  -- Checkout sessions
orders           -- Orders
order_items      -- Order lines
users            -- User accounts
audit_log        -- All actions
```

## Milestones
0. Scaffolding
1. Catalog (read-only)
2. Stores + Inventory
3. Search + Facets
4. Cart (multi-store)
5. Checkout + Shipping
6. Orders + Fulfillment
7. Messages + Disputes
8. Billing + Fees
9. Admin + Audit

## Files Reference
- `BRIKICK_PROJECT_ANALYSIS.md` - Full analysis
- `endpoints_critical_prioritized.csv` - All endpoints
- `blglobalconstants_summary.json` - Reference data sizes
- `Store*Response.schema.json` - JSON schemas
