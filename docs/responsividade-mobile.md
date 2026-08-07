# Responsividade mobile — Portal BI TMB

Plano de referência: [`.atlas/plans/2026-08-03-responsividade-mobile.md`](../.atlas/plans/2026-08-03-responsividade-mobile.md)  
PRD: [`tasks/prd-responsividade-mobile-menu-dashboards.md`](../tasks/prd-responsividade-mobile-menu-dashboards.md)

## Breakpoints

| Nome | Largura | Comportamento |
|------|---------|----------------|
| **Phone** | ≤ 768px | Drawer Admin; BI empilhado; KPIs 2×2; gráficos empilhados |
| **Tablet** | 769–1024px | Drawer Admin; layout intermediário; KPIs 2×2; **gráficos Operacional empilhados** (também landscape) |
| **Desktop** | ≥ 1025px | Sidebar fixa 250px; BI wide (colunas/gráficos lado a lado) |

Constantes CSS alinhadas: `--bp-phone: 768px`, `--bp-tablet: 1024px` (Admin `Shell.css` / BI `estilo.py`).

## Checklist de aceite (smoke)

### Phone (≤768) e tablet (≤1024)
- [ ] Hamburger abre/fecha drawer; overlay fecha o menu
- [ ] Links do drawer navegam e fecham o menu
- [ ] Rota **Visualização**: drawer inicia fechado; iframe usa altura `dvh` menos a barra superior
- [ ] **Operacional**: KPIs legíveis; gráficos empilhados; drill por selectbox + gráfico; detalhe NF empilhado
- [ ] **Histórico**: selectbox de dia; ModeBar oculto; detalhe do dia usável
- [ ] Filtros em coluna única (via CSS); resumo de filtros ativos com expander fechado

### Desktop (≥1025)
- [ ] Sidebar fixa à esquerda (sem hamburger)
- [ ] Operacional: 4 KPIs + gráficos lado a lado
- [ ] Histórico: layout wide preservado
- [ ] Iframe Visualização em altura cheia como antes

### PWA
- [ ] Manifest + ícones 192/512 a partir de `logos/logo.png`
- [ ] Android Chrome: “Instalar app” / Adicionar à tela inicial
- [ ] iOS Safari: Compartilhar → Adicionar à Tela de Início
- [ ] Service worker cacheia apenas assets estáticos do Admin (não API / não BI)

## Entregue nesta onda (Fases 1–2)

- Shell drawer + iframe `dvh`
- CSS responsivo Streamlit (`estilo.py` / `embed.py`)
- Controles de drill touch-friendly; ModeBar off no Histórico
- PWA (manifest + SW mínimo)

## Próximo PRD (fora desta entrega)

- Importação de planilhas (tabela 11 cols, toolbars)
- CRUDs admin (Users, SMTP, Destinatários, API Integration) em card-list / tabelas mobile

## PWA — instalar na tela inicial

### Android (Chrome / Edge)
1. Abra `https://SEU_DOMINIO/admin/` (ou IP) e faça login.
2. Menu do navegador → **Instalar app** ou **Adicionar à tela inicial**.

### iOS (Safari)
1. Abra `/admin/` no Safari.
2. Compartilhar → **Adicionar à Tela de Início**.
3. Confirme o nome **Portal BI**.

O service worker (`/admin/sw.js`) cacheia apenas o shell estático do Admin. **Não** funciona offline para API nem para o BI embutido.

## iOS / Safari — iframe e scroll

No embed, a altura usa `100dvh` menos a barra do Admin (~52px). A barra de endereço do Safari pode alterar `dvh` dinamicamente; o scroll principal deve ficar **dentro do iframe do BI**. Evitar sidebar empilhada acima do iframe (drawer off-canvas).
