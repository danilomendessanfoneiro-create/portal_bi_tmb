# Automação TMB (Python) — substitui o robô do Power Automate

Este pacote refaz em Python (Selenium) o fluxo que o robô do Power Automate
fazia:

1. Login no portal **tmblogistica.tmselite.com**, geração e download do
   *Relatório Geral de Entregas* em Excel.
2. Login no painel admin **179.198.101.65/admin**, upload do arquivo
   baixado na tela de *Importação de Dados* e clique em
   *Validar planilha* → *Importar dados*.

## Correções feitas em relação ao fluxo original

- **Login**: o gravador do Power Automate não capturava a digitação de
  usuário/senha (provavelmente autofill do navegador). Aqui o login é
  explícito, via variáveis de ambiente — mais confiável e sem depender
  de sessão salva no Chrome da máquina.
- **Esperas fixas (`WAIT 2`)** foram trocadas por esperas explícitas
  (`WebDriverWait`), que só avançam quando o elemento realmente aparece —
  evita falhas por lentidão da rede e não perde tempo quando a página
  responde rápido.
- **Seleção de arquivo**: em vez de simular o diálogo nativo do Windows
  (clicar em "Selecionar arquivo", digitar o nome, clicar "Abrir"), o
  script envia o caminho do arquivo diretamente para o campo
  `<input type="file">` via Selenium. Isso elimina a parte mais frágil da
  automação original (ela quebra fácil se a janela do diálogo muda de
  posição, idioma do SO, etc.).
- **Nome do arquivo baixado**: o link de download gera um nome com hash
  dinâmico (ex.: `entregas_relatorio-00360-e6cec064....csv`). O script
  detecta automaticamente o arquivo mais recente na pasta de downloads,
  em vez de usar um nome fixo.
- **Logs**: cada execução grava um log diário em `logs/`, com todos os
  passos e erros — útil para diagnosticar quando rodar sem tela (modo
  headless/agendado).

## 1. Instalação

Requer Python 3.10+ e Google Chrome instalado.

```bat
cd tmb_automation
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configuração

```bat
copy .env.example .env
notepad .env
```

Preencha `TMB_USER`, `TMB_PASS`, `ADMIN_USER`, `ADMIN_PASS` e confirme os
caminhos de `DOWNLOAD_DIR` / `LOG_DIR`.

Deixe `HEADLESS=false` na primeira execução para ver o navegador e
confirmar que tudo funciona.

## 3. Ajustar os seletores de login (passo obrigatório)

Como o robô original nunca preencheu os campos de login manualmente, os
seletores em `tmb_automation.py` são **placeholders**:

```python
USER_FIELD_SELECTOR = (By.NAME, "Email")        # ajustar
PASS_FIELD_SELECTOR = (By.NAME, "Password")      # ajustar
ADMIN_USER_SELECTOR = (By.NAME, "username")      # ajustar
ADMIN_PASS_SELECTOR = (By.NAME, "password")      # ajustar
```

Para descobrir os valores corretos:

1. Abra a página de login no Chrome.
2. Clique com o botão direito no campo de usuário → **Inspecionar**.
3. Veja o atributo `name` ou `id` do `<input>` no HTML.
4. Troque `By.NAME, "Email"` por, por exemplo, `By.ID, "txtUsuario"`,
   conforme o que você encontrar.
5. Repita para o campo de senha e para os dois logins (TMB e admin).

## 4. Testar manualmente

```bat
python tmb_automation.py
```

Acompanhe o log em `logs\tmb_automation_AAAA-MM-DD.log`. Se algo falhar,
o log mostra em qual etapa (login TMB, download, login admin, upload,
validação, importação).

Quando estiver funcionando de ponta a ponta, mude `HEADLESS=true` no
`.env` para rodar sem abrir janela visível.

## 5. Agendar para rodar quando o computador ligar

### Opção A — pelo Agendador de Tarefas (interface gráfica)

1. Abra **Agendador de Tarefas** (Win + R → `taskschd.msc`).
2. **Ação → Criar Tarefa...**
3. Aba **Geral**:
   - Nome: `TMB Automation`
   - Marque **Executar estando o usuário conectado ou não** (ou "Executar
     com privilégios mais altos", se necessário).
4. Aba **Gatilhos → Novo...**:
   - Iniciar a tarefa: **Ao iniciar o computador** (ou **Ao fazer logon**,
     se preferir que rode só quando você loga).
5. Aba **Ações → Nova...**:
   - Ação: **Iniciar um programa**
   - Programa/script: caminho completo para `run_tmb_automation.bat`
     (ex.: `C:\TMB_Automation\run_tmb_automation.bat`)
   - Iniciar em: a pasta onde está o `.bat` (ex.: `C:\TMB_Automation`)
6. Aba **Condições**: desmarque "Iniciar a tarefa somente se o computador
   estiver com energia CA", se for notebook.
7. Salve. Pode pedir a senha do usuário do Windows.

### Opção B — via linha de comando (`schtasks`)

Abra o *Prompt de Comando* como administrador:

```bat
schtasks /create /tn "TMB Automation" /tr "C:\TMB_Automation\run_tmb_automation.bat" /sc onstart /ru SYSTEM
```

Ou para rodar apenas quando o usuário atual faz logon:

```bat
schtasks /create /tn "TMB Automation" /tr "C:\TMB_Automation\run_tmb_automation.bat" /sc onlogon
```

Para testar a tarefa sem esperar reiniciar:

```bat
schtasks /run /tn "TMB Automation"
```

## 6. Estrutura de arquivos

```
tmb_automation/
├── tmb_automation.py       # script principal
├── requirements.txt
├── .env.example            # copie para .env e preencha
├── run_tmb_automation.bat  # launcher para o Agendador de Tarefas
├── logs/                   # criado automaticamente
└── README.md
```

## Observações finais

- Se o relatório do portal TMB exigir filtros de data obrigatórios
  (o fluxo original não mostrava isso claramente), você precisa
  adicionar o preenchimento desses campos na função `download_report()`,
  antes do clique em "Buscar".
- Se o painel admin usa autenticação por sessão/cookie (sem tela de
  login repetida), a função `login_admin()` já trata isso: se não achar
  os campos de login em 10s, assume que a sessão já está ativa e segue
  em frente.
- Rodar com `HEADLESS=true` é recomendado para a execução agendada (mais
  rápido e não abre janela na tela), mas deixe `false` sempre que for
  testar ajustes de seletor.
