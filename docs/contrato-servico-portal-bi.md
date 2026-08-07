# Portal BI de Entregas — Funcionamento básico e estrutura de Contrato de Serviço

**Público:** apresentação ao cliente (TMB Logística)  
**Natureza:** minuta de estrutura comercial/técnica — **não substitui assessoria jurídica**  
**Relacionado:** detalhes técnicos da API em [`integracao-api-tmselite.md`](integracao-api-tmselite.md)

Status: rascunho para alinhamento comercial. Preencher campos entre `[colchetes]` antes da versão final.

---

## Parte A — Funcionamento básico da solução

### A.1 O que é

Solução de **Business Intelligence (BI)** para acompanhamento visual do desempenho das entregas da transportadora, com foco em:

- Identificar entregas **atrasadas**
- Monitorar entregas **vencendo no dia**
- Analisar volume, valor e distribuição por unidade/cliente
- Permitir drill-down (detalhe) de cada entrega

### A.2 Como funciona (visão do usuário)

1. O usuário acessa o **portal web** com login e senha.
2. Conforme o perfil:
   - **Administrador:** visualiza todas as unidades.
   - **Unidade/filial:** visualiza apenas o recorte da sua unidade (quando aplicável).
3. O painel exibe indicadores (KPIs), gráficos e tabela filtrável.
4. Filtros típicos: período, unidade, cliente, busca por nota/entrega.
5. Clique em uma entrega abre o detalhe (datas, valor, status, motivo de atraso quando disponível).
6. Aba **Histórico:** evolução diária de atrasos (snapshots). Clique em um dia (ou use **Dia para detalhar**) abre o **Detalhe do dia** — KPIs, breakdown e registros só das entregas em atraso daquela fotografia (não reconstrói “vence hoje”/“em dia”). Ver `tasks/prd-drilldown-dashboard-historico.md`.

### A.3 Regra de negócio central (atraso)

Definida com o cliente e implementada no sistema (**paridade `calcConsolidada.vb`**):

| Conceito | Regra atual (código) |
|---|---|
| Prazo considerado | Igual a **Dt. Prazo Atual** (`dt_prazo_atual`) — **não** usa mais `max(prazo, agendamento)` |
| Fonte do campo | Planilha/API → coluna `Dt. Prazo Atual` / `dt_prazo_atual` |
| Onde é calculado | Pipeline `limpeza.processar_entregas` → `calcular_atraso` → `macro_delivery_rules.aplicar_regras_macros` |
| STATUS PRAZO | Classificação só com `dt_prazo_atual` vs data de referência (hoje BR) |
| Atrasada (macros) | `status_prazo == 01_ATRASO` (prazo &lt; hoje) |
| Vencendo hoje (macros) | `status_prazo == 02_VENCENDO HOJE` |
| No Dashboard Operacional | Mesma regra das macros; filtro **Prazo considerado** = atrasados com data do prazo no intervalo (após normalização) |

> Nota: a regra antiga documentada como `max(dt_prazo_atual, dt_agendamento)` foi substituída pela paridade Excel (somente prazo atual).

### A.4 Origem dos dados (hoje e evolução)

| Fase | Fonte | Observação |
|---|---|---|
| **Atual** | Arquivo/relatório CSV exportado do TMS | Atualização manual ou rotina combinada |
| **Evolução** | API do TMS (TMS Elite) + **persistência local** | Sync periódico; portal lê a base própria |

A persistência local existe para garantir histórico, performance do dashboard e
recalculo estável dos indicadores, independentemente da paginação da API.

```
TMS (CSV ou API)  →  base do portal  →  regras de atraso  →  dashboards / acesso
```

### A.5 Componentes da solução

| Componente | Função |
|---|---|
| Portal BI (web) | Indicadores, filtros, gráficos, detalhe |
| Controle de acesso | Usuários, perfis admin / unidade |
| Camada de dados | Carga CSV e/ou sync API → armazenamento local |
| Regras de BI | Limpeza, deduplicação, cálculo de atraso |
| Ambiente de publicação | Hosting do portal (ex.: Streamlit Cloud ou infra acordada) |

### A.6 O que a solução **não** é (limites claros)

- Não substitui o TMS operacional (criação/alteração de pedidos).
- Não é WMS, roteirização nem app de motorista.
- Não garante a qualidade dos dados de origem (responsabilidade do TMS / operação).
- Não inclui, salvo acordo explícito: app mobile nativo, BI corporativo Power BI/Tableau, integração financeira/fiscal completa.

---

## Parte B — Estrutura do Contrato de Serviço (minuta)

> Use as seções abaixo como esqueleto do documento a apresentar ao cliente.
> Valores, prazos e cláusulas legais devem ser revisados pelo jurídico das partes.

### 1. Identificação das partes

| Campo | Conteúdo |
|---|---|
| **Contratada** | [Razão social / CNPJ / endereço] |
| **Contratante (Cliente)** | TMB Logística — [razão social / CNPJ / endereço] |
| **Objeto resumido** | Prestação de serviços de desenvolvimento, disponibilização e [manutenção/suporte] do Portal BI de Entregas |
| **Vigência** | [Início] a [Fim], renovável por [período] |
| **Local de execução** | Remoto / [cidade], com entregáveis digitais |

### 2. Objeto do contrato

A Contratada obriga-se a fornecer ao Cliente:

1. Portal BI de acompanhamento de atrasos e desempenho de entregas, conforme Parte A.
2. [Implantação inicial / evolução CSV→API / ambos — especificar].
3. Serviços de [suporte / evolução / treinamento] descritos neste contrato.
4. Documentação operacional mínima (acesso, perfis, atualização de dados).

### 3. Escopo incluído (entregáveis)

Marcar o que entra nesta contratação:

| # | Entregável | Incluído? |
|---|---|---|
| 3.1 | Portal web com login e perfis | [Sim] |
| 3.2 | KPIs de atraso, vencendo hoje, valor em atraso, % atraso | [Sim] |
| 3.3 | Gráficos e tabela com filtros | [Sim] |
| 3.4 | Simulador de tolerância | [Sim] |
| 3.5 | Carga a partir de CSV / relatório do TMS | [Sim / Não] |
| 3.6 | Integração com API TMS Elite + persistência local | [Sim / Fase 2] |
| 3.7 | Cadastro inicial de usuários | [Sim — até N usuários] |
| 3.8 | Publicação em ambiente [Cloud X / servidor Cliente] | [Definir] |
| 3.9 | Treinamento (até [N] horas / [N] participantes) | [Definir] |
| 3.10 | Manual curto de uso | [Sim] |
| 3.11 | Período de estabilização pós go-live ([N] dias) | [Definir] |

### 4. Fora de escopo (salvo aditivo)

- Customizações não listadas na seção 3.
- Correção de inconsistências nos dados do TMS de origem.
- Desenvolvimento ou manutenção da API do fornecedor TMS Elite.
- Disponibilidade da API de terceiros, tokens, VPN e allowlist de IP do Cliente/fornecedor.
- Novos módulos (financeiro, SLA contratual por cliente final, app mobile, etc.).
- Conformidade LGPD além das medidas razoáveis descritas na seção 10 (detalhar com jurídico).
- Suporte 24×7, salvo pacote contratado.

### 5. Premissas e obrigações do Cliente

O Cliente se compromete a:

1. Indicar um **ponto focal** técnico/negócio ([nome / e-mail / telefone]).
2. Fornecer acesso à fonte de dados (arquivo periódico e/ou **credenciais da API**, ambientes, IPs).
3. Validar regras de atraso e glossário (unidade, status, data de entrega).
4. Informar lista de usuários e perfil (admin / unidade) e manter siglas alinhadas aos dados.
5. Responder dúvidas e homologações em até **[N] dias úteis**.
6. Garantir que o uso do portal esteja autorizado perante fornecedores de TMS/API.
7. Não compartilhar logins; solicitar revogação imediata de acessos desligados.

Atrasos do Cliente em premissas **prorrogam** prazos da Contratada em igual período.

### 6. Obrigações da Contratada

1. Entregar o escopo da seção 3 com qualidade profissional.
2. Comunicar impedimentos (ex.: API inacessível) em até **[N] dias úteis**.
3. Manter confidencialidade das informações do Cliente (seção 10).
4. Corrigir defeitos do software entregue, conforme SLA da seção 8.
5. Não utilizar dados do Cliente para outros fins sem autorização.

### 7. Fases e cronograma (modelo)

| Fase | Descrição | Prazo alvo | Critério de conclusão |
|---|---|---|---|
| F0 | Kickoff + alinhamento de regras | [Semana 0] | Ata com regras de atraso assinadas |
| F1 | Portal em produção com fonte CSV | [Semanas _] | Homologação Cliente OK |
| F2 | Análise contrato API + persistência | [Semanas _] | Documento técnico aprovado |
| F3 | Sync API + período paralelo CSV∥API | [Semanas _] | Paridade de KPIs na amostra |
| F4 | Cutover API como fonte primária | [Semanas _] | Go-live + estabilização |

Datas são **estimativas** condicionadas às premissas da seção 5.

### 8. Níveis de serviço (SLA) — suporte

Aplicável após go-live da fase contratada.

| Severidade | Definição | Tempo de 1ª resposta | Meta de solução |
|---|---|---|---|
| S1 — Crítico | Portal inacessível para todos | [ex.: 4h úteis] | [ex.: 1 dia útil] |
| S2 — Alto | KPI principal incorreto / login quebrado | [ex.: 1 dia útil] | [ex.: 3 dias úteis] |
| S3 — Médio | Filtro/tela com falha parcial | [ex.: 2 dias úteis] | [ex.: 5 dias úteis] |
| S4 — Baixo | Melhoria / dúvida de uso | [ex.: 3 dias úteis] | Backlog acordado |

- Canal de abertura: **[e-mail / portal / WhatsApp corporativo]**  
- Horário: **[dias úteis, 9h–18h, fuso _]**  
- Exclusões de SLA: indisponibilidade da API/TMS de terceiros, falta de premissa do Cliente, força maior, mudanças não autorizadas no ambiente.

### 9. Aceite e critérios de homologação

O Cliente homologa cada fase mediante:

1. Acesso funcional com os perfis combinados.
2. Conferência dos KPIs em **amostra fechada** (lista de entregas acordada).
3. Confirmação de que a regra de atraso (Parte A.3) está refletida na tela.
4. Na fase API: paridade aceitável CSV × API conforme critérios técnicos anexos
   (ver `integracao-api-tmselite.md`).

Silêncio do Cliente superior a **[N] dias úteis** após comunicação de “pronto para aceite”
poderá ser considerado **aceite tácito** [a validar com jurídico].

### 10. Dados, confidencialidade e LGPD (esqueleto)

1. Dados de entregas e usuários são de titularidade / responsabilidade do **Cliente**.
2. A Contratada trata os dados apenas para execução deste contrato.
3. Medidas mínimas: acesso autenticado, senhas com hash, [HTTPS], restrição de acesso à base.
4. Local de hospedagem dos dados: **[definir — Cloud X / Brasil / exterior]**.
5. Retenção: dados mantidos por **[N] meses** após o término, salvo obrigação legal ou exportação solicitada pelo Cliente.
6. Incidente de segurança: comunicação em até **[N] horas/dias** após ciência.

*(Completar com DPA/aditivo LGPD se necessário.)*

### 11. Propriedade intelectual

1. Código e artefatos desenvolvidos sob este contrato: **[licença / cessão / uso vitalício — definir]**.
2. Componentes de terceiros (bibliotecas open source, Streamlit, etc.) mantêm suas licenças.
3. Marca e logo TMB: uso apenas no portal, autorização do Cliente.
4. Ao término: entrega de **[código-fonte / dump / export CSV]** conforme pacote contratado.

### 12. Condições comerciais (preencher)

| Item | Valor |
|---|---|
| Modelo | [Projeto fechado / mensalidade / híbrido] |
| Implantação (F1) | R$ [_] |
| Evolução API (F2–F4) | R$ [_] ou incluso |
| Mensalidade de suporte/hospedagem | R$ [_]/mês |
| Usuários inclusos | Até [N]; adicional R$ [_]/usuário |
| Forma de pagamento | [50% início / 50% aceite] ou [mensal] |
| Reajuste | [IPCA anual / índice _] |
| Horas de evolução além do escopo | R$ [_]/hora ou pacote |

### 13. Alterações de escopo (change request)

Pedidos fora da seção 3 serão orçados por escrito (escopo, prazo, valor).
Só entram em vigor após aprovação formal do Cliente ([e-mail / aditivo].

### 14. Rescisão (esqueleto)

1. Rescisão imotivada: aviso prévio de **[N] dias**, com pagamento do devido até a data.
2. Rescisão por inadimplemento: notificação e prazo de cura de **[N] dias**.
3. Efeitos: cessação de acessos; entrega de exportação dos dados em até **[N] dias**;
   apuração de valores proporcionais.

### 15. Disposições gerais (esqueleto)

- Foro: **[comarca]**  
- Comunicações: e-mails dos pontos focais  
- Integralidade: este contrato + anexos supersedem entendimentos anteriores sobre o objeto  
- Anexos sugeridos:
  - **Anexo I** — Parte A (funcionamento e regras de atraso)  
  - **Anexo II** — Escopo detalhado / cronograma  
  - **Anexo III** — Documento técnico API (`integracao-api-tmselite.md`)  
  - **Anexo IV** — Lista de usuários iniciais  
  - **Anexo V** — Comercial / proposta financeira  

---

## Parte C — Roteiro de apresentação ao cliente (sugestão)

| Bloco | Tempo | Conteúdo |
|---|---|---|
| 1 | 5 min | Problema: atrasos visíveis, decisão rápida |
| 2 | 10 min | Demo / telas: KPIs, filtros, detalhe, simulador |
| 3 | 5 min | Regra de atraso (transparência) |
| 4 | 5 min | Fonte de dados: CSV hoje → API + base própria |
| 5 | 10 min | O que está no contrato (escopo / fora / SLA / papéis) |
| 6 | 5 min | Próximos passos e o que o Cliente precisa fornecer |

### Pedidos imediatos ao Cliente (checklist)

- [ ] Validar regra de atraso (Parte A.3) por escrito  
- [ ] Confirmar se haverá recorte por **unidade** ou visão única TMB  
- [ ] Indicar ponto focal e lista de usuários  
- [ ] Disponibilizar acesso API (ou manter CSV até lá)  
- [ ] Definir hosting e política de dados  
- [ ] Escolher fases contratadas (F1 apenas vs F1+API)  

---

## Controle do documento

| Versão | Data | Autor | Nota |
|---|---|---|---|
| 0.1 | 2026-07-27 | Equipe projeto | Estrutura inicial para alinhamento comercial |

**Aviso:** este texto é base de trabalho comercial/técnica. A versão assinável
deve ser revisada por assessoria jurídica das partes antes de qualquer
comprometimento formal.
