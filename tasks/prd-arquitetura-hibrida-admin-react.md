# PRD: Arquitetura Híbrida — Streamlit BI + Admin React/API

## Introduction

O Portal BI de Entregas (TMB) já possui dashboards funcionais em Streamlit (KPIs de atraso, filtros, gráficos e detalhamento). A gestão administrativa (usuários/filiais) foi iniciada na mesma stack, porém a navegação e o CRUD não atendem um padrão de UX de produto (menu hierárquico, dropdown e modais).

Esta evolução adota a **Opção B (híbrida)**: manter a **Visualização** em Streamlit e construir o módulo **Administração** em React, consumindo uma API FastAPI que reutiliza as camadas `services` / `repositories` já existentes em Python + PostgreSQL.

## Goals

- Preservar os dashboards Streamlit já prontos e estáveis
- Entregar UX administrativa moderna: menu lateral/grupos, dropdown quando necessário, modais de inclusão/edição
- Expor autenticação e CRUD de usuários via API REST, reutilizando `UserService` / `UserRepository`
- Implantar o conjunto (Streamlit + API + frontend admin + Postgres) na VPS Hostinger com nginx
- Manter os padrões `prb_*`, auditoria e migrations incrementais

## User Stories

### US-001: Definir topologia híbrida e contratos de integração
**Description:** Como desenvolvedor, quero um desenho claro de execução (Streamlit, API, React, Postgres, nginx) para que os deploys local e na VPS permaneçam consistentes.

**Acceptance Criteria:**
- [ ] Mapa de fluxo documentado: navegador → nginx → (admin estático | /api | /bi Streamlit)
- [ ] Estratégia de autenticação compartilhada definida (sessão/JWT) entre admin e link do BI
- [ ] `.env.example` lista URLs da API, do BI e `DATABASE_URL`
- [ ] Documentation complete

### US-002: API FastAPI sobre os services existentes
**Description:** Como desenvolvedor, quero endpoints REST de login e usuários para que o admin React não acesse o banco diretamente.

**Acceptance Criteria:**
- [ ] Aplicação FastAPI em `app/api/` (ou equivalente) com routers de auth e users
- [ ] Endpoints usam apenas `AuthService` / `UserService` (sem SQL nos controllers)
- [ ] CRUD de usuários: listagem (busca/paginação/ordenação), criação, alteração e exclusão lógica
- [ ] OpenAPI/Swagger disponível em desenvolvimento
- [ ] Tests pass

### US-003: Shell React da Administração
**Description:** Como usuário administrador, quero um shell administrativo profissional com navegação clara para acessar Usuários e Configurações com facilidade.

**Acceptance Criteria:**
- [ ] App Vite + React (ex.: `frontend/` ou `admin/`) com tokens de cor TMB (navy/laranja)
- [ ] Navegação lateral/topo com grupo Administração (Usuários, Configurações)
- [ ] Link/entrada para o BI Visualização (URL do Streamlit)
- [ ] Uso desktop-first adequado ao admin
- [ ] Verify in browser

### US-004: CRUD de usuários com modal
**Description:** Como administrador, quero criar e editar usuários em modais para que a listagem continue utilizável e focada.

**Acceptance Criteria:**
- [ ] Tabela de usuários com busca, paginação e ordenação
- [ ] Inclusão abre modal (não formulário longo abaixo da lista)
- [ ] Edição abre modal preenchido; senha opcional na alteração
- [ ] Exclusão lógica/desativação com confirmação
- [ ] Campos alinhados a `prb_users` (login, name, display_name, code, profile, branch, enabled)
- [ ] Verify in browser

### US-005: Autenticação unificada (fase 1)
**Description:** Como usuário, quero entrar no app admin mantendo as regras de acesso (admin vs filial) para que as permissões sejam iguais às do portal atual.

**Acceptance Criteria:**
- [ ] Tela de login no admin React
- [ ] Perfil admin acessa Usuários; não-admin não acessa
- [ ] Tokens/credenciais não versionados no Git
- [ ] BI Streamlit continua funcionando com login atual (usuários no Postgres) até a fase 2 de SSO
- [ ] Typecheck passes

### US-006: Item Configurações (placeholder)
**Description:** Como administrador, quero um item de menu Configurações para que a interface já esteja preparada para futuras configurações.

**Acceptance Criteria:**
- [ ] Item Configurações visível em Administração
- [ ] Página placeholder informando que a funcionalidade virá depois
- [ ] Verify in browser

### US-007: Deploy na VPS (nginx + serviços)
**Description:** Como operador, quero Streamlit, API, arquivos estáticos React e Postgres rodando na VPS para que o cliente use o portal híbrido.

**Acceptance Criteria:**
- [ ] systemd (ou equivalente) para API e Streamlit
- [ ] Rotas nginx: `/` admin estático, `/api` → FastAPI, `/bi` → Streamlit
- [ ] HTTPS via Certbot quando o domínio estiver pronto
- [ ] Migrations do Postgres aplicadas na VPS
- [ ] Documentation complete

### US-008: Remover/desativar CRUD Streamlit legado
**Description:** Como desenvolvedor, quero descontinuar a tela admin de usuários no Streamlit após o cutover React para haver uma única UX administrativa.

**Acceptance Criteria:**
- [ ] Streamlit mantém Meu → Visualização
- [ ] UI de usuários na Administração Streamlit removida ou redirecionada para a URL do admin React
- [ ] Sem regressão nos KPIs do dashboard
- [ ] Verify in browser

## Functional Requirements

- FR-1: Os dashboards permanecem em Streamlit no caminho `/bi` (ou URL acordada)
- FR-2: O SPA admin é a interface principal de gestão de usuários
- FR-3: A API é o único caminho de escrita do admin React para o PostgreSQL
- FR-4: Exclusão lógica continua com `enabled = false` e grava auditoria pelos triggers existentes
- FR-5: Hash de senha permanece compatível com o salt atual (`tmb-logistica-bi` / env)
- FR-6: nginx termina TLS e faz proxy reverso da API e do Streamlit
- FR-7: Local e VPS usam o mesmo runner de migrations (`database/deploy/run_migrations.py`)

## Non-Goals

- Reescrever os dashboards Plotly em React nesta fase
- SSO/OAuth completo com o fornecedor do TMS
- Redesign admin mobile-first
- Implementar o módulo real de Configurações além do placeholder
- Alterar as regras de negócio de atraso
- Multi-tenant além do deploy atual da TMB

## Design Considerations

- Manter identidade visual TMB: navy `#1E3056`, laranja `#F6A532`, fontes Inter/Manrope ou equivalentes web
- Admin: desktop-first, tabela densa, formulários em modal (criar/editar), confirmação ao desativar
- Navegação: sidebar agrupada (Administração) — dropdown aceitável se o grupo crescer
- Link do BI rotulado claramente como “Visualização” / “Portal de entregas”

## Technical Considerations

- Reutilizar: `app/services/*`, `app/repositories/*`, `app/models/*`, `prb_users` / auditoria
- Novo: FastAPI em `app/api/`, React+Vite em `frontend/` (nome final na implementação)
- Auth fase 1: JWT (ou cookie httpOnly) para a API; Streamlit pode manter login próprio até SSO opcional na fase 2
- VPS já possui Ubuntu + PostgreSQL + `/opt/portal-bi-tmb` — adequada ao híbrido
- Processos sugeridos na VPS: `portal-api.service`, `portal-bi.service`, site nginx
- RAM: preferir ≥ 2 GB (4 GB mais seguro com Streamlit + API + artefatos do build React)

## Success Metrics

- Admin consegue criar/editar/desativar usuário sem sair do contexto da listagem (fluxo em modal)
- BI permanece disponível durante o rollout do admin (URL do BI continua no ar)
- Fonte única da verdade para usuários: PostgreSQL `prb_users`
- Deploy reproduzível via migrations + passos documentados de nginx/systemd

## Open Questions

- [x] Paths públicos: `cliente.com/bi` (Streamlit) + `cliente.com/admin` (React) — **decidido**
- [x] Auth: **unificar login do Streamlit com o admin nesta entrega** (mesmo mecanismo/JWT) — **decidido**
- [x] Pasta do frontend: `frontend/` — **decidido**
- [x] Hospedagem do build React: **nginx static na mesma VPS** (sem CDN nesta fase) — **decidido**

### Decisões fechadas (resumo)

| Tema | Decisão |
|---|---|
| Paths | `/bi` + `/admin` no mesmo domínio |
| Login | Unificado nesta entrega (admin + Streamlit) |
| Frontend | pasta `frontend/` |
| Hosting admin | nginx na VPS Hostinger |

*Nenhuma open question pendente. Aguardando sinal para iniciar implementação.*

---

## Anexo — A VPS contempla?

**Sim.** A VPS Hostinger (Ubuntu) já prevista comporta o modelo híbrido:

| Componente | Na VPS |
|---|---|
| PostgreSQL | Já criado (`portal_bi_tmb`) |
| Streamlit (BI) | systemd + proxy `/bi` |
| FastAPI | systemd + proxy `/api` |
| React (admin) | build estático servido pelo nginx |
| HTTPS | Certbot no domínio |

Não é necessário outro servidor só por causa da Opção B. Pode ser preciso **aumentar a RAM** se Streamlit + API ficarem pesados no mesmo plano básico.

## Anexo — Fora desta PRD (já feito / paralelo)

- Camadas Python + `prb_users` + auditoria + seed
- Migrations locais aplicadas
- CRUD Streamlit atual (será substituído pelo React após a US-008)
