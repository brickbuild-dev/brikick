# GitHub Copilot Instructions (Brikick)

Copilot deve respeitar rigorosamente estas regras ao sugerir código.

## Objetivo
Implementar o Brikick (marketplace Lego) com consistência de arquitetura, segurança e qualidade.

## Stack fixa
- Backend: Python + FastAPI
- DB: Postgres
- ORM/Migrations: SQLAlchemy 2.x + Alembic
- Validation: Pydantic v2
- Frontend: Next.js (App Router) + TypeScript
- Infra: Docker/Compose
- Tests: pytest (backend) e Playwright (frontend) quando aplicável

## Regras gerais (não negociar)
1. Não inventar endpoints, tabelas ou campos sem criar/atualizar também os docs em `/docs`.
2. Não introduzir dependências novas sem justificar e atualizar ADR.
3. Não escrever código “mágico”: preferir funções pequenas, nomes explícitos, tipagem completa.
4. Toda mudança DB requer migration Alembic e atualização do ERD (`docs/domain/erd.mmd`) quando impacta o modelo.
5. Segurança por defeito:
   - validar input (Pydantic)
   - autorizar por RBAC/ownership
   - nunca expor stack traces ao cliente
   - logs sem dados sensíveis (password, tokens, card data)

## Convenções de repositório (backend)
### Estrutura sugerida
- `backend/app/api/` routers (por domínio)
- `backend/app/domain/` entidades e regras
- `backend/app/schemas/` DTOs Pydantic (request/response)
- `backend/app/services/` casos de uso (business logic)
- `backend/app/repos/` acesso a dados (queries)
- `backend/app/db/` sessão, models SQLAlchemy, migrations
- `backend/app/core/` config, logging, auth, rbac
- `backend/tests/` testes

### Padrão de endpoint
- Router chama Service
- Service valida regras de negócio
- Repo executa queries
- DB constraints e índices quando aplicável
- Respostas com schemas Pydantic

### Padrões obrigatórios
- Todos os endpoints devem declarar `response_model=...`
- Erros: usar `HTTPException` com mensagens curtas e códigos corretos
- Paginação padrão: `limit` (max 100) + `cursor`/`offset`
- Sorting e filtering: parâmetros explícitos, nunca SQL concatenado

## Convenções (frontend)
- Usar TypeScript sempre
- App Router: `app/` com `route.ts` apenas quando necessário
- Fetch client centralizado (ex.: `lib/api.ts`) com tratamento uniforme de erros
- Componentes: preferir “server components” quando fizer sentido; forms interativos como client

## RBAC / Ownership
- Seller só pode gerir recursos do seu `store_id`
- Buyer só pode ver/gerir os seus `orders`
- Mod/Admin podem agir conforme permissões definidas em `docs/domain/rbac.mmd`

## Dados externos (BrickLink/BrickOwl/Rebrickable)
- Tratar BOID como opcional; se faltar, seguir BL-only (não bloquear pipeline)
- Registar `skip_reason` quando dados são ignorados por ausência de BOID
- Nunca falhar pipeline por peso em falta: usar fallback ou marcar como pendente

## Outputs desejados ao gerar código
Quando for pedido para implementar uma feature, Copilot deve produzir:
1) alterações necessárias em schemas + models + migrations + endpoints
2) testes (pelo menos happy path + 1 caso de erro)
3) atualização breve em docs quando houver mudança de contrato

## Anti-padrões (proibidos)
- lógica de negócio dentro do router
- queries SQL inseguras por concatenação
- tratar “0” como falsy em IDs (ex.: `if color_id:` é proibido)
- endpoints sem autenticação/autorizações quando exigido
