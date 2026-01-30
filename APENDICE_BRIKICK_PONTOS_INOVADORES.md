# APÊNDICE: 21 Pontos Inovadores Fundamentais do Brikick

> **Nota de Contexto:** Este apêndice descreve os requisitos inovadores que devem ser considerados como pilares fundamentais na arquitectura e desenvolvimento da plataforma Brikick. Todos os sistemas, módulos e funcionalidades devem ser desenhados tendo estes pontos em consideração desde o início.

---

## 1. CONTROLO DE PREÇOS E ANTI-INFLAÇÃO

### 1.1 Limite Máximo de Preço de Venda
- **Regra:** Não permitir preços de venda superiores a **2x o preço base actual**
- **Preço Base:** Calculado como a média dos últimos 6 meses de vendas (avg 6 months)
- **Objectivo:** Prevenir inflação artificial, valores irreais e potenciais fraudes/lavagem de dinheiro através da plataforma
- **Implementação:** Sistema de validação automática no momento de listagem e actualização de preços

### 1.2 Portes de Envio Justos
- **Regra:** Proibir inflação nos custos de envio
- **Problema Resolvido:** Evitar que vendedores adicionem margens de lucro aos portes para fugir às fees da plataforma (que só se aplicam ao valor das peças)
- **Implementação:** Sistema de verificação/validação dos portes declarados

### 1.3 Verificação de Portes por IA (Futuro)
- **Objectivo:** Criar sistema de IA para validar se os portes cobrados são realistas
- **Complexidade:** Requer base de dados de tarifas por país, serviço de envio e peso/dimensões
- **Prioridade:** Feature avançada para implementação futura

### 1.4 Proibição de Custos Ocultos
- **Regra:** Eliminar opção de cobrar "handling fees" ou qualquer custo extra
- **Valores Válidos:** Apenas valor das peças + custos de portes de envio
- **Objectivo:** Transparência total, sem valores escondidos ou camuflados

---

## 2. SISTEMA DE CHECKOUT

### 2.1 Checkout Exclusivamente Automático
- **Regra:** Não existe opção de "request invoice"
- **Funcionamento:** Processo de compra totalmente automatizado
- **Objectivo:** Padronização e simplificação do fluxo de compra

---

## 3. INTEGRAÇÕES E SINCRONIZAÇÃO DE INVENTÁRIO

### 3.1 API de Store Controlada
- **Acesso:** Disponibilização apenas mediante autorização de administrador
- **Objectivo:** Controlo sobre quem pode integrar com a plataforma via API

### 3.2 Sync Interno Limitado (Estratégia de Negócio)
- **Regra:** O módulo interno de sync da plataforma Brikick sincroniza apenas com UMA plataforma externa (BrickLink OU BrickOwl, não ambas)
- **Objectivo Estratégico:** Forçar a utilização do serviço externo de sincronização entre as 3 plataformas (Brikick + BrickLink + BrickOwl) como produto/serviço pago separado
- **Implementação:** Módulo de sync simples integrado; serviço de sync completo como produto premium externo

### 3.3 Serviços Premium (Paywall)
- **Funcionalidades Pagas:**
  - Segunda plataforma de sincronização de inventário
  - Sistema de pick order (estilo BrickAction)
- **Modelos de Monetização:** Custo mensal de assinatura OU aumento da % de fee nas vendas

---

## 4. SISTEMA DE PESQUISA UNIFICADO

### 4.1 Pesquisa Universal Multi-Plataforma
- **Métodos de Pesquisa Suportados:**
  - Palavras-chave / referências textuais
  - Reconhecimento visual via Brickognize
  - Part_ID de qualquer plataforma (BrickLink, BrickOwl, LEGO oficial, etc.)
- **Comportamento:** Independentemente do ID pesquisado, os resultados são apresentados com os IDs oficiais do Brikick
- **Exemplo:** Pesquisar `3001` (ID do BrickLink) abre a página da peça correspondente no Brikick com o ID interno (ex: `23321`)
- **Requisito Técnico:** Tabela de mapeamento entre IDs de todas as plataformas

---

## 5. MÓDULOS ESPECIAIS

### 5.1 Módulo de Reconhecimento (Tipo BrickIt/What The Fig)
- **Funcionalidade:** Reconhecimento visual de minifiguras e peças
- **Disponibilidade:** Exclusivo para contas de loja (não disponível para compradores individuais)
- **Objectivo:** Ferramenta premium para facilitar catalogação de inventário

### 5.2 Secção de Venda de MOC Instructions
- **Nova Categoria:** Além de peças, sets e books, criar secção dedicada para venda de instruções de MOCs (My Own Creations)
- **Referência:** Modelo similar ao praticado no Rebrickable
- **Implementação:** Categoria de produto com campos específicos (ficheiros digitais, complexidade, número de peças, etc.)

---

## 6. SISTEMA DE DISPUTAS E VERIFICAÇÃO

### 6.1 Verificação de Documentos por IA
- **Funcionalidade:** Utilizar IA para analisar recibos e documentos quando há denúncias
- **Casos de Uso:** Falta de envio, disputas sobre estado de peças, verificação de tracking
- **Objectivo:** Automatizar e agilizar processo de resolução de disputas

### 6.2 Regras de Responsabilidade no Envio
- **Correio Normal (sem tracking):** Responsabilidade do COMPRADOR
- **Correio com Tracking:** Vendedor OBRIGADO a apresentar prova de envio
- **Consequência:** Vendedor que não apresenta prova perde automaticamente a disputa
- **Racional:** Eliminar lacuna onde vendedor alega ter enviado sem possibilidade de verificação

---

## 7. SISTEMA DE PENALIZAÇÕES PROGRESSIVAS

### 7.1 Sanções por Reclamações
- **Trigger:** Após X reclamações/problemas confirmados
- **Sanções Progressivas:**
  - Cooldown temporário
  - Redução de privilégios
  - Fecho temporário de loja
  - Suspensão de compras durante X tempo
  - Ban permanente (casos graves)
- **Período de Avaliação:** Cálculo baseado em janela temporal (ex: últimos 6 meses)
- **Confidencialidade:** O número exacto de reclamações que activa sanções NÃO é público

### 7.2 Registo Interno de Cancelamentos
- **Dados Registados:** Número de encomendas canceladas (tanto por compradores como por vendedores)
- **Visibilidade:** Apenas interno, não exposto publicamente
- **Uso:** Factor no cálculo do rating e detecção de padrões problemáticos

---

## 8. SISTEMA DE RATING BASEADO EM QUALIDADE DE SERVIÇO

> **Filosofia:** Substituir o sistema tradicional de feedback (que gera vingança e avaliações enviesadas) por um algoritmo baseado em métricas objectivas de qualidade de serviço. Valorizar QUALIDADE em vez de QUANTIDADE.

### 8.1 Factores de Avaliação para VENDEDORES

| Factor | Descrição | Peso |
|--------|-----------|------|
| Peças listadas/mês | Quantidade de peças colocadas à venda | Baixo |
| Regularidade | Consistência diária de listagem de peças | Médio |
| Encomendas recebidas/mês | Volume de vendas realizadas | Médio |
| Taxa de resposta | % de mensagens respondidas vs. recebidas | Alto |
| Disputas ganhas/perdidas | Rácio de processos a favor/contra | Alto |
| Idade da conta | Tempo desde criação da conta | Baixo |
| Preços vs. base | Desvio dos preços praticados face ao avg 6 meses | Médio |
| Cancelamentos | Nº de encomendas canceladas pelo vendedor | Alto |
| Processos abertos | Nº de disputas iniciadas | Médio |

### 8.2 Factores de Avaliação para COMPRADORES

| Factor | Descrição | Peso |
|--------|-----------|------|
| Encomendas/mês | Número de compras realizadas | Médio |
| Disputas ganhas/perdidas | Rácio de processos a favor/contra | Alto |
| Idade da conta | Tempo desde criação da conta | Baixo |
| Cancelamentos | Nº de encomendas canceladas pelo comprador | Alto |
| Processos abertos | Nº de disputas iniciadas | Médio |

### 8.3 Sistema de Badges (Gamification)

| Badge | Descrição | Tipo |
|-------|-----------|------|
| 🏆 **Trusted Seller** | Vendedor de confiança comprovada | Cumulativo |
| 🚀 **Fast Shipper** | Consistentemente rápido nos envios | Mensal |
| 🎯 **High Accuracy** | Alta precisão nas descrições | Cumulativo |
| 💎 **Loyalty** | Fidelidade à plataforma | Cumulativo |
| 🏅 **Milestone Achievements** | Marcos específicos atingidos | Cumulativo |

- **Badges Cumulativos:** Uma vez obtidos, mantêm-se permanentemente
- **Badges Mensais:** Renovam-se baseados no desempenho do mês anterior

### 8.4 Benefícios por Bom Ranking
- Sistema de recompensas para vendedores/compradores com alto rating
- Possíveis benefícios: visibilidade aumentada, fees reduzidas, acesso a funcionalidades premium, badges exclusivos
- **Nota:** Detalhes específicos dos benefícios a definir

---

## 9. SLAs (Service Level Agreements)

### 9.1 Níveis de Resposta

| Nível | Tempo de Resposta | Impacto no Rating |
|-------|-------------------|-------------------|
| Excelente | 24-48 horas | Positivo |
| Aceitável | 48-72 horas | Neutro |
| Insuficiente | 72+ horas | Negativo |

- **Aplicação:** Envio de encomendas e resposta a mensagens
- **Medição:** Tracking automático de timestamps

---

## 10. WANTED LIST AVANÇADA

### 10.1 Filtros Granulares
- **Filtros Disponíveis:**
  - Localização do vendedor (país/região)
  - Intervalo de preços (mín-máx)
  - Condição das peças (novo/usado/graus)
  - Quantidade mínima disponível
  - Rating mínimo do vendedor
- **Objectivo:** Aumentar relevância dos alertas de wanted list
- **Configuração:** Utilizador define filtros ao subscrever notificações

---

## 11. SISTEMA DE MENSAGENS

### 11.1 Anexos em Mensagens
- **Funcionalidade:** Permitir anexar ficheiros às mensagens
- **Tipos Suportados:** Imagens, PDFs, documentos
- **Objectivo:** Facilitar resolução de problemas sem necessidade de descrever tudo por texto
- **Casos de Uso:** Fotos de peças danificadas, comprovativos de envio, screenshots

---

## 12. INTEGRAÇÃO COM TRANSPORTADORAS

### 12.1 Integração com Correios
- **Prioridade 1:** Correios locais do país da plataforma
- **Prioridade 2:** Transportadoras multinacionais (DHL, FedEx, UPS, etc.)
- **Funcionalidades:**
  - Cotação automática de portes
  - Geração de etiquetas de envio
  - Tracking integrado na plataforma

### 12.2 APIs de Cotação de Frete
- **Objectivo:** Cálculo automático e transparente de custos de envio
- **Benefício:** Elimina necessidade de "pedir orçamento" manual
- **Implementação:** Integração com APIs de transportadoras (CTT, Canada Post, FedEx, etc.)

---

## 13. SEGURANÇA E PREVENÇÃO DE FRAUDE

### 13.1 Pré-Aprovação de Compradores Suspeitos
- **Trigger:** Comprador com:
  - Histórico de chargebacks
  - Muitas queixas registadas
  - Rating baixo na plataforma
- **Funcionamento:** Vendedor pode exigir aprovar o pedido ANTES do pagamento ser capturado
- **Objectivo:** Dar controlo ao vendedor em casos de risco elevado
- **Implementação:** Flag automática em compradores que atingem thresholds de risco

---

## RESUMO EXECUTIVO

A plataforma Brikick deve ser construída sobre estes pilares fundamentais:

1. **Transparência Radical** - Zero custos ocultos, preços controlados, portes verificáveis
2. **Meritocracia por Qualidade** - Rating baseado em serviço, não em volume
3. **Anti-Fraude Sistémico** - Limites de preço, verificação por IA, responsabilidades claras
4. **Justiça nas Disputas** - Regras objectivas, documentação obrigatória
5. **Gamification Inteligente** - Recompensas por bom comportamento contínuo
6. **Ecossistema Estratégico** - Sync limitado interno + serviços premium externos
7. **Automação Total** - Checkout automático, cotações automáticas, verificações automáticas

---

*Este apêndice deve ser considerado como requisitos obrigatórios no design e desenvolvimento de todas as funcionalidades da plataforma Brikick.*
