# Diagnóstico de conectividade SMTP — Portal BI × mail TMB Logística

**Data:** 15/08/2026  
**Assunto:** Timeout no envio de e-mails operacionais a partir da VPS do Portal BI  
**Destinatário:** equipe técnica / hospedagem do e-mail TMB Logística  
**Contato Portal BI:** jeverson.abreu@gmail.com  

---

## 1. Resumo executivo

O Portal BI precisa enviar relatórios operacionais pelo SMTP:

| Item | Valor |
|------|--------|
| Servidor | `mail.tmblogistica.com.br` |
| IP resolvido | `216.245.208.229` |
| Porta SMTP | **465** (SSL) — alternativa testada: **587** (STARTTLS) |
| Conta / remetente | `gestaoentregas@tmblogistica.com.br` |
| Origem dos envios (produção) | VPS do Portal BI — IP público **`179.198.101.65`** |

**Conclusão do diagnóstico:** as **credenciais e o servidor de e-mail estão corretos** (envio de teste bem-sucedido a partir de rede externa). A VPS de produção **não consegue abrir conexão TCP** com `216.245.208.229` nas portas 465, 587 e nem 443 (timeout). O mesmo servidor VPS **consegue** falar com `smtp.gmail.com` nas portas 465/587.

Solicitamos à TMB / provedor do mail **liberar (whitelist) o IP `179.198.101.65`** no firewall / antispam / regras de acesso SMTP (e, se houver, HTTPS do host de mail), ou indicar se há bloqueio a faixas de datacenter/cloud.

---

## 2. Sintoma no Portal BI

- Robôs de relatório operacional (filiais / clientes / gerencial) falham com **timeout** ao conectar no SMTP cadastrado no Admin (`prb_smtp_settings`).
- O e-mail técnico de **monitoramento** (outro SMTP, Gmail) **chega normalmente** — prova de que a VPS envia e-mail quando o destino é alcançável.

---

## 3. Evidências dos testes (15/08/2026)

### 3.1 A partir de rede externa (estação de desenvolvimento)

| Teste | Resultado |
|-------|-----------|
| TCP `mail.tmblogistica.com.br:465` | OK |
| TCP `mail.tmblogistica.com.br:587` | OK |
| Login SMTP + envio (SSL 465) para `jeverson.abreu@gmail.com` | **OK — e-mail recebido** |
| Login SMTP + envio (STARTTLS 587) para o mesmo destinatário | **OK — e-mail recebido** |

→ Credenciais válidas; servidor TMB operacional e aceitando autenticação.

### 3.2 A partir da VPS de produção (`179.198.101.65`)

| Teste | Resultado |
|-------|-----------|
| DNS `mail.tmblogistica.com.br` | OK → `216.245.208.229` |
| TCP `216.245.208.229:465` | **FAIL — Timeout** |
| TCP `216.245.208.229:587` | **FAIL — Timeout** |
| TCP `mail.tmblogistica.com.br:443` | **FAIL — Timeout** |
| Ping ICMP para `216.245.208.229` | 100% loss (ICMP pode estar filtrado; o relevante é o TCP) |
| TCP `smtp.gmail.com:465` | **OK** |
| TCP `smtp.gmail.com:587` | **OK** |
| Firewall local na VPS (UFW / iptables OUTPUT) | Sem bloqueio (policy ACCEPT / UFW inactive) |

→ O problema **não** é credencial e **não** é “SMTP desabilitado em geral na VPS”. É **inalcançabilidade do IP do mail TMB** a partir deste IP de origem.

### 3.3 Configuração cadastrada no Portal (referência)

- Nome: `tmblogistica`
- Host: `mail.tmblogistica.com.br`
- Porta: `465`
- Usuário / remetente: `gestaoentregas@tmblogistica.com.br`
- SSL/TLS: ativo
- Status: habilitado e padrão

*(Senha omitida neste documento por segurança.)*

---

## 4. Interpretação técnica

1. Se o bloqueio fosse só “porta 25/SMTP outbound” do provedor da VPS, **Gmail 465/587 também falharia** — e não falha.
2. Se o mail TMB estivesse fora do ar ou com senha errada, o teste **do PC externo** falharia — e **não falhou** (2 e-mails recebidos).
3. Timeout em **465, 587 e 443** no mesmo IP indica filtro de **destino/origem** (firewall no lado do mail, WAF, antispam, ou rota/ACL no caminho), não erro de aplicação do Portal.

Ajuste já feito no Portal (independente da rede): na porta **465** o cliente SMTP deve usar **SSL implícito (`SMTP_SSL`)**, não STARTTLS. Isso evita timeout quando a porta estiver aberta; **não resolve** o bloqueio de rede atual da VPS → TMB.

---

## 5. Pedido à TMB / hospedagem do e-mail

1. **Whitelist / liberação de firewall** para o IP de origem:  
   **`179.198.101.65`**  
   Destino: **`mail.tmblogistica.com.br` (`216.245.208.229`)**, portas **465** e/ou **587** (SMTP autenticado).
2. Confirmar se existe política que **bloqueia IPs de datacenter / VPS / cloud**.
3. Se a liberação for feita, avisar para reteste. Validação rápida esperada na VPS:

```bash
timeout 8 bash -c 'echo >/dev/tcp/216.245.208.229/465' && echo OK || echo FAIL
```

Quando retornar `OK`, o Portal BI poderá reenviar os relatórios operacionais.

---

## 6. Dados para o ticket da TMB (copiar/colar)

```
Assunto: Liberação de IP para SMTP autenticado — Portal BI

Origem (cliente SMTP): 179.198.101.65
Destino: mail.tmblogistica.com.br (216.245.208.229)
Portas necessárias: 465 (SSL) e/ou 587 (STARTTLS)
Conta: gestaoentregas@tmblogistica.com.br
Sintoma: TCP timeout da VPS; envio OK a partir de rede externa com as mesmas credenciais
Data dos testes: 15/08/2026
```

---

## 7. Histórico interno (Portal BI)

| Data | Ação |
|------|------|
| 15/08/2026 | Timeout nos relatórios operacionais; monitoramento Gmail OK |
| 15/08/2026 | Validação de credenciais OK (2 e-mails de teste recebidos) |
| 15/08/2026 | Confirmação: VPS não alcança IP do mail TMB; Gmail alcançável |
| 15/08/2026 | Correção de cliente SMTP para porta 465 (`SMTP_SSL`) no mailer |
| 17/08/2026 | Ponte temporária: relatórios autenticam no Gmail (`smtp.gmail.com:587`), From `gestaoentregas@tmblogistica.com.br`. Monitoramento técnico inalterado. Reverter com `python database/deploy/switch_smtp_gmail_bridge.py --revert` |

---

*Documento gerado para apoio à abertura de chamado com a TMB Logística / provedor de e-mail. Não contém senhas.*
