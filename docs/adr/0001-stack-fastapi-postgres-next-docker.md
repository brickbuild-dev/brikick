# 0001 - Stack inicial: FastAPI + Postgres + Next.js + Docker

## Contexto
O Brikick requer:
- API de alto desempenho e rápida iteração
- Base relacional forte (integridade, joins, reporting)
- Frontend moderno e SSR/SEO
- Ambiente reprodutível (dev/prod)

## Decisão
Adotar:
- Backend: FastAPI (Python)
- DB: Postgres
- Frontend: Next.js (TypeScript)
- Infra dev: Docker Compose (serviços isolados)

## Alternativas consideradas
- Node + NestJS (backend)
- Monólito fullstack (menos separação)
- DB NoSQL como base principal (menos adequado para domínio relacional)

## Consequências
- Melhor consistência e integridade no domínio (Postgres)
- Tipagem forte no frontend (TypeScript)
- Necessidade de migrações (Alembic) e padrões de schema/ORM
