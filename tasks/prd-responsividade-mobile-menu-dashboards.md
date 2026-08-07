# PRD: Responsividade mobile — Menu (Fase 1) e Dashboards (Fase 2)

## Introduction

O Portal BI TMB (Admin React + BI Streamlit embutido em iframe) é **desktop-first**. Em smartphones e tablets a navegação empilha a sidebar sem drawer, o iframe compete por altura com o menu, e os dashboards (Operacional/Histórico) mantêm KPIs em 4 colunas, gráficos lado a lado, tabelas densas e drill por clique em Plotly — frágil no toque.

Esta entrega cobre as **Fases 1 e 2** do plano de responsividade: (1) shell/menu Admin utilizável no mobile + área útil do iframe; (2) dashboards Operacional e Histórico legíveis e operáveis no toque. Decisões de produto já fechadas: o cliente usará o mobile para **todas** as funções (consulta, importação e admin) a médio prazo — este PRD deixa a **navegação** pronta para isso; adequação visual das telas de Importação e CRUDs admin fica em PRD seguinte. **Tablet** usa layout **intermediário** (não espelho do desktop). **PWA** (“Adicionar à tela inicial”) entra no escopo desta entrega, sem exigir app nativo nem offline completo do BI.

## Goals

- Oferecer navegação Admin por **drawer/hamburger** em phone, preservando sidebar fixa no desktop
- Maximizar a área útil do iframe do BI no mobile (menu recolhido por padrão na rota Visualização)
- Tornar Operacional e Histórico usáveis em phone/tablet (KPIs, filtros, gráficos, tabelas, drill) **sem perda de funcionalidade**
- Definir layout **intermediário** para tablet (≈769–1024px)
- Permitir instalação como PWA leve (manifest + ícones + meta tags)
- Não degradar a experiência desktop atual (Chrome/Edge em monitor)
- Compatibilidade alvo: Android + iOS; Chrome, Edge e Safari

## User Stories

### US-001: Breakpoints e baseline de aceite
**Description:** As a developer, I need shared breakpoints and an acceptance checklist so Admin and BI adapt consistently without regressing desktop.

**Acceptance Criteria:**
- [x] Documentar em `docs/` (ex.: `docs/responsividade-mobile.md`) breakpoints: phone ≤768px, tablet 769–1024px, desktop ≥1025px
- [x] Checklist de aceite smoke: nav drawer, Visualização/iframe, Operacional, Histórico — phone + tablet + desktop
- [x] Referenciar o plano `.atlas/plans/2026-08-03-responsividade-mobile.md`
- [x] Documentation complete

### US-002: Drawer / hamburger no Shell Admin (Fase 1)
**Description:** As a mobile user, I want a collapsible navigation drawer so the menu does not consume the whole screen before content.

**Acceptance Criteria:**
- [x] Em viewport ≤768px (e tablet se aplicável ao shell): botão hamburger abre/fecha drawer overlay; sidebar **não** fica empilhada permanentemente acima do conteúdo
- [x] Drawer contém os mesmos grupos/links atuais (Meu / Administração / Configurações), chip de usuário e Sair
- [x] Desktop (≥1025px): sidebar fixa 250px inalterada em comportamento
- [x] Fechar drawer ao navegar para uma rota ou ao tocar no overlay
- [x] Verify in browser

### US-003: Iframe BI com altura útil no mobile (Fase 1)
**Description:** As a user opening Visualização on a phone, I want the BI iframe to use most of the screen without nested scroll fighting the Admin chrome.

**Acceptance Criteria:**
- [x] Na rota Visualização em phone/tablet: drawer fechado por padrão; header compacto (hamburger + título mínimo)
- [x] Altura do embed usa `100dvh` (ou equivalente) menos a barra superior; evita `100vh` + sidebar empilhada
- [x] Scroll principal preferencialmente dentro do BI; documentar comportamento iOS/Safari no doc de responsividade
- [x] Desktop: layout atual do iframe preservado
- [x] Verify in browser

### US-004: Empilhar layout Streamlit no phone (Fase 2)
**Description:** As a mobile user, I want KPI rows, chart pairs and detail fields to stack vertically so content is readable without horizontal squeeze.

**Acceptance Criteria:**
- [x] CSS `@media` (phone) em `estilo.py` e/ou `embed.py` força empilhamento de blocos horizontais Streamlit relevantes (KPIs, pares de gráfico, detalhe NF)
- [x] Desktop continua com `st.columns` atuais (4 KPIs, gráficos `[1.3,1]`, etc.)
- [x] Tablet (769–1024): layout intermediário — KPIs 2×2; **gráficos Operacional sempre empilhados** (também em landscape), não lado a lado
- [x] Verify in browser

### US-005: KPIs e gráficos Operacional mobile-friendly (Fase 2)
**Description:** As a branch or admin user, I want Operational KPIs and charts readable and tappable on a small screen.

**Acceptance Criteria:**
- [x] Phone: tipografia/KPI cards legíveis (sem fatias estreitas de 4 colunas)
- [x] Phone: gráfico de barras e distribuição (pizza ou equivalente) empilhados; altura ~240–280px (ou valor documentado)
- [x] Limitar categorias no gráfico de filiais no mobile (ex.: top/tail N) sem remover drill — excesso acessível via filtro/tabela
- [x] ModeBar Plotly permanece desligado no Operacional
- [x] Verify in browser

### US-006: Drill por toque (alternativa ao clique Plotly) (Fase 2)
**Description:** As a mobile user, I want to filter by filial/situação (and history day) without relying only on Plotly tap gestures.

**Acceptance Criteria:**
- [x] Operacional: controles (selectbox/chips) para Filial e Situação de drill, além do clique no gráfico; botão Limpar drill visível fora do expander de filtros
- [x] Histórico: selectbox/caminho explícito de “Dia para detalhar” como primário no phone; clique na barra permanece no desktop/tablet quando viável
- [x] Estado de drill sincronizado com os mesmos `session_state` keys já usados
- [x] Verify in browser

### US-007: Tabelas e detalhe NF no mobile (Fase 2)
**Description:** As a user, I want delivery tables and NF detail usable on a phone without six cramped columns.

**Acceptance Criteria:**
- [x] Phone: detalhe da NF em coluna única (empilhado), não `st.columns(6)`
- [x] Phone: dataframe Operacional prioriza colunas essenciais (ex.: NF, Cliente, Situação, Filial, Prazo) — demais acessíveis no detalhe ou scroll horizontal documentado
- [x] Histórico — tabela do dia: reduzir colunas no phone ou scroll horizontal explícito com colunas prioritárias primeiro
- [x] Seleção de linha / detalhe continua funcional no toque
- [x] Verify in browser

### US-008: Filtros BI no mobile (Fase 2)
**Description:** As a user, I want filters easy to open and use with touch, without three narrow multiselects side by side.

**Acceptance Criteria:**
- [x] Phone: widgets do expander “Filtros” em coluna única
- [x] Com expander fechado, indicar filtros ativos (chips/resumo) quando houver seleção
- [x] Desktop: painel atual (colunas) preservado ou equivalente
- [x] Verify in browser

### US-009: Histórico — ModeBar e densidade (Fase 2)
**Description:** As a user on Histórico, I want a clean chart without Plotly toolbar clutter and denser-but-usable day detail on mobile.

**Acceptance Criteria:**
- [x] Série diária do Histórico usa `displayModeBar: False` (como o Operacional)
- [x] Altura do gráfico adaptada no phone; muitos dias (60/90) permanecem roláveis/legíveis o suficiente para escolher o dia via selectbox
- [x] Breakdown do dia (barras + KPIs) empilha no phone conforme US-004
- [x] Verify in browser

### US-010: PWA — instalar na tela inicial
**Description:** As a field user, I want to add the Portal Admin to my home screen so I can open it like an app.

**Acceptance Criteria:**
- [x] `manifest.webmanifest` (ou equivalente) para o Admin: name, short_name, start_url `/admin/`, display `standalone`, theme/background colors alinhados à marca
- [x] Ícones PWA (pelo menos 192 e 512) gerados a partir do logo existente `frontend/public/logos/logo.png` (e/ou `logo_full.png` se necessário para proporção), referenciados no manifest e em `index.html`
- [x] Meta `apple-mobile-web-app-capable` / title adequados para iOS
- [x] **Service worker mínimo obrigatório** nesta entrega: cache estático do shell Admin (HTML/JS/CSS/ícones); **não** cachear respostas da API nem o iframe/BI offline
- [x] Registrar o SW no bootstrap do Admin (`main.tsx` ou equivalente), com escopo adequado a `/admin/`
- [x] Documentar no doc de responsividade como instalar (Android Chrome / iOS Safari)
- [x] Verify in browser

### US-011: Regressão desktop e documentação final
**Description:** As a stakeholder, I want assurance that desktop UX is unchanged and that mobile behavior is documented for QA/VPS.

**Acceptance Criteria:**
- [x] Smoke desktop (≥1025px): sidebar fixa, Operacional e Histórico com layout wide atual (colunas/gráficos lado a lado)
- [x] Atualizar `docs/responsividade-mobile.md` com o que foi entregue (Fases 1–2 + PWA) e o que fica para o próximo PRD (Importação + CRUDs admin)
- [x] Atualizar plano `.atlas/plans/2026-08-03-responsividade-mobile.md` (status/passos Fases 1–2)
- [x] Documentation complete

## Functional Requirements

- FR-1: Breakpoints oficiais: phone ≤768px; tablet 769–1024px; desktop ≥1025px
- FR-2: Em phone, o Shell Admin deve usar drawer/hamburger; sidebar desktop permanece fixa ≥1025px
- FR-3: Na Visualização mobile, o drawer inicia fechado e o iframe usa altura baseada em `dvh` menos o chrome superior
- FR-4: No phone, o BI deve empilhar KPIs, pares de gráficos e campos de detalhe que hoje usam múltiplas `st.columns`
- FR-5: Tablet (769–1024, inclusive landscape) deve usar layout intermediário: KPIs 2×2 e **gráficos Operacional empilhados** (não lado a lado)
- FR-6: Drill Operacional e seleção de dia no Histórico devem ter controle explícito (selectbox/chips) além do clique Plotly
- FR-7: ModeBar Plotly desligado na série do Histórico
- FR-8: Filtros BI no phone em coluna única, com indicação de filtros ativos quando o expander estiver fechado
- FR-9: Detalhe NF no phone em layout vertical de campo único por linha (empilhado)
- FR-10: Admin deve ser instalável como PWA: manifest + ícones derivados de `public/logos/logo.png` + metas iOS + **service worker mínimo** (só assets estáticos do Admin; sem BI/API offline)
- FR-11: Nenhuma funcionalidade de análise existente (filtros, drill, lote ativo, escopo filial) pode ser removida — apenas adaptar apresentação
- FR-12: Desktop ≥1025px deve preservar o comportamento visual atual do Admin e do BI

## Non-Goals

- Redesign visual completo da marca / novo design system
- Reescrever o BI em React nesta entrega
- Adequação completa das telas **Importação**, Users, SMTP, Destinatários, API Integration, Automações (próximo PRD) — apenas garantir que o **menu** as alcança no drawer
- Bottom navigation bar (avaliar depois se necessário)
- Offline completo de dados do BI / sync em background
- App nas stores (App Store / Play Store)
- Mudança de regras de negócio, lote ativo, macros ou API TMS Elite
- Quebrar ou “mobile-only” o layout desktop

## Design Considerations

- Reutilizar tokens CSS existentes (`styles.css` / Shell) — navy/laranja TMB
- Drawer: overlay escuro semitransparente; fechar no link e no overlay
- Alvos de toque ≥44px nos controles novos (hamburger, Limpar drill, chips)
- Plotly: preferir barras horizontais / altura controlada no phone; pizza pode permanecer no tablet/desktop
- Plano de referência: `.atlas/plans/2026-08-03-responsividade-mobile.md`
- Análise prévia: Admin desktop-first com 1 `@media`; BI sem media queries

## Technical Considerations

- Admin: React + CSS (sem Tailwind/MUI) — estado open/close do drawer em `Shell.tsx`
- BI: Streamlit + Plotly — CSS `@media` em `estilo.py`/`embed.py`; layouts condicionais se detecção de viewport for necessária (evitar depender só de seletores frágeis do DOM Streamlit)
- Embed: `VisualizacaoPage` + `biEmbedUrl()` (`embed=true` + token) — não alterar contrato de auth
- Testar iframe + `100dvh` no Safari iOS (rubber-banding / barra de endereço)
- PWA: arquivos estáticos no `frontend/public/` (Vite); `start_url` com `basename` `/admin/`; ícones a partir de `public/logos/logo.png`
- Service worker: precache do shell Admin apenas; versionar cache para invalidar no deploy (`npm run build`)
- Ordem de implementação sugerida: US-001 → US-002 → US-003 → US-004…US-009 → US-010 → US-011

## Success Metrics

- Em phone (≤768): Visualização abre com BI legível sem precisar rolar past um menu longo permanente
- Operacional: KPIs e pelo menos um gráfico principal legíveis sem zoom; drill possível só com toque em controles nativos
- Histórico: escolher um dia e ver detalhe sem depender exclusivamente do tap no gráfico
- Desktop: zero regressão perceptível no shell e nos dashboards wide
- PWA: “Adicionar à tela inicial” funciona em Android Chrome; iOS Safari mostra Add to Home Screen com nome/ícone corretos
- Smoke checklist US-001 100% marcado em phone + tablet + desktop

## Open Questions

_(Nenhuma em aberto — decisões 2026-08-03)_

- Ícone PWA: **usar** `frontend/public/logos/logo.png` (e `logo_full.png` se precisar de arte maior) para gerar 192/512.
- Service worker: **mínimo nesta entrega** (cache estático do Admin; sem BI/API offline).
- Tablet (incl. landscape): gráficos Operacional **empilhados**.
