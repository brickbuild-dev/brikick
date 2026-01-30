# Brikick Docs

Este diretório contém documentação versionada do Brikick (diagramas + fluxos + decisões).

## Arquitetura
- System Context: `architecture/system-context.mmd`
- Container: `architecture/container.mmd`
- Deployment: `architecture/deployment.mmd`

## Domínio
- Glossário: `domain/glossary.md`
- ERD (database): `domain/erd.mmd`
- RBAC (roles/permissions): `domain/rbac.mmd`

## Fluxos críticos
- Checkout: `flows/checkout-sequence.mmd`
- Publicação de listing: `flows/listing-publish-sequence.mmd`
- Disputes/claims: `flows/dispute-flow.mmd`

## ADR (Architecture Decision Records)
- Guia: `adr/README.md`
- Decisão inicial do stack: `adr/0001-stack-fastapi-postgres-next-docker.md`

> Nota: o GitHub renderiza Mermaid diretamente em Markdown usando blocos ```mermaid```; estes ficheiros `.mmd` podem ser embebidos/colados em `.md` se preferires.
