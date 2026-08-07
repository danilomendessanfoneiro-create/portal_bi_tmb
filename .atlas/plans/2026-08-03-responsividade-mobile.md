---
title: Responsividade mobile do Portal BI
created: 2026-08-03
status: active
tags: [ux, mobile, streamlit, react-admin]
related: ["tasks/prd-responsividade-mobile-menu-dashboards.md", "frontend/src/components/Shell.tsx", "app/controllers/dashboard_controller.py", "frontend/src/pages/ImportPage.tsx"]
---

# Plano: Responsividade mobile do Portal BI

## Objetivo
Tornar Admin (React) + BI (Streamlit) plenamente utilizáveis em smartphone/tablet (Android, iOS; Chrome/Edge/Safari), **sem versão separada** e **sem degradar o desktop**. Resultado observável: dashboards, navegação e importação usáveis com toque; demais telas admin consistentes.

## Contexto

### Estado atual (diagnóstico)
- **Desktop-first** nos dois frontends. Sem estratégia mobile-first.
- **Admin:** CSS global + 1 `@media (max-width: 900px)` em `Shell.css` — só empilha sidebar acima do conteúdo (sem hamburger/drawer). Tabelas com `white-space: nowrap` global. Viewport ok em `index.html`.
- **BI:** `layout="wide"`, KPIs `st.columns(4)`, gráficos `[1.3,1]`, detalhe NF até `columns(6)`, Plotly + dataframes densos. **Zero `@media`** em `estilo.py` / embed. Sidebar Streamlit oculta; filtros em expander.
- **Embed:** Visualização = iframe `?embed=true&token=` com `height: 100vh` — scroll aninhado + sidebar empilhada reduzem área útil no celular.
- Stack Admin: React + CSS custom (sem Tailwind/MUI). BI: Streamlit + Plotly.

### Restrições
- Preservar UX desktop atual.
- Não criar app/PWA separado nesta fase.
- Streamlit não tem breakpoints nativos confiáveis — CSS/@media ou layout condicional.

## Abordagem
**Progressive enhancement por breakpoints** (ex.: 768 / 900 / 1024), mantendo layouts desktop como default CSS/JSX/Streamlit e adaptando só abaixo do breakpoint.
Alternativas rejeitadas: (a) fork mobile-only — custo duplo; (b) reescrever BI em React agora — alto risco fora de escopo.

Prioridade de negócio: **Dashboards → Menu → Importação → Admin restante → Performance**.

## Passos

### Fase 0 — Baseline e critérios (pré-código)
- [x] Definir breakpoints: phone ≤768, tablet ≤1024, desktop >1024
- [x] Checklist de aceite mobile (Operacional, Histórico, nav, import)
- [ ] Smoke manual iOS Safari + Android Chrome + tablet

### Fase 1 — Menu / shell Admin (desbloqueia tudo no iframe)
- [x] Drawer/hamburger no `Shell` (sidebar oculta por padrão em ≤1024px; overlay)
- [x] Altura do iframe BI com `100dvh` / header compacto; evitar sidebar+iframe competindo
- [x] Drawer com todos os grupos (Configurações acessível no mobile)

### Fase 2 — Dashboards BI (prioridade máxima)
- [x] CSS `@media` em `estilo.py`/`embed.py`: empilhar `stHorizontalBlock` no mobile
- [x] KPIs: 2×2 no phone/tablet (CSS); tipografia legível
- [x] Gráficos Operacional: empilhar barra+pizza (≤1024); altura compacta; limitar categorias
- [ ] Pizza: considerar barras horizontais de situações no mobile (melhor tap) — mantida pizza + selectbox de drill
- [x] Drill touch: selectbox/chips de filial e situação além do clique Plotly
- [x] Tabelas: colunas essenciais; detalhe NF em 2 cols empilháveis (não `columns(6)`)
- [x] Histórico: `displayModeBar: False`; selectbox de dia como caminho primário; cols priorizadas
- [x] Filtros: widgets em coluna única via CSS; chips de filtros ativos no topo

### Fase 3 — Importação de planilhas
- [ ] Manter file picker nativo; tratar drag-drop como secondary (desktop)
- [ ] Toolbar de histórico empilhável; searches sem `min-width: 220px` rígido no mobile
- [ ] Histórico: card-list no mobile **ou** tabela com cols prioritárias + scroll horizontal explícito
- [ ] Progresso/erros: ok; revisar tipografia e tap targets dos botões

### Fase 4 — Módulos administrativos
- [ ] Users / SMTP / Recipients / API: `.table-wrap` em todas; card-list opcional ≤768
- [ ] Modais já `min(520px,100%)` — revisar teclado virtual iOS (scroll)
- [ ] Login / Settings overview / Automações: ajustes menores (já ok)

### Fase 5 — Performance e polish
- [ ] Limitar opções de multiselect (top-N / typeahead) no mobile
- [ ] Avaliar `st.fragment` (versão Streamlit) para charts/tabela
- [ ] Lazy de charts fora da viewport se aplicável
- [ ] Testes de aceitação nos 3 navegadores alvo

## Inventário de telas (complexidade / impacto)

| Tela | Complexidade | Impacto no código | Notas |
|------|--------------|-------------------|-------|
| Shell / Nav Admin | Média | Shell.tsx + Shell.css | Drawer obrigatório |
| BI Operacional | Alta | dashboard_controller, estilo, embed | Colunas + Plotly + tabela |
| BI Histórico | Alta | history_controller, estilo | Toolbar Plotly + drill + tabela 10 cols |
| Visualização iframe | Média–Alta | VisualizacaoPage.css + Shell | Viewport + scroll |
| Importação | Alta | ImportPage.tsx (+ CSS) | 11 cols + filtros |
| Users / SMTP / Recipients | Média | pages + styles.css | Tabelas nowrap |
| API Integration | Média | ApiIntegrationPage | Falta table-wrap |
| Automações / Settings / Login | Baixa | pouco | Já fluidos |

## Riscos & Mitigações
- CSS Streamlit quebra em upgrade de versão → preferir seletores estáveis + fallback layout condicional
- Clique Plotly frágil no touch → sempre oferecer selectbox/chips paralelos
- Scroll aninhado iframe+Streamlit no iOS → drawer + altura `dvh` + um scroll principal
- Regressão desktop → media queries only; QA desktop em cada fase
- Escopo “tudo de uma vez” → fases 1→2→3 obrigatórias antes de polish

## Questões em aberto
- _(fechadas 2026-08-03)_ Mobile: **todas** as funções. Tablet: layout **intermediário**. PWA: **entra**.
- Ícone: `frontend/public/logos/logo.png`. SW: **mínimo** (só shell Admin). Tablet: gráficos **empilhados**.
- PRD: `tasks/prd-responsividade-mobile-menu-dashboards.md`
