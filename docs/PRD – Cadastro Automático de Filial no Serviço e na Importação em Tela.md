# PRD – Cadastro Automático de Filial na Importação

## 1. Objetivo

Realizar um ajuste no processo de **importação de dados**, permitindo que o sistema identifique automaticamente quando uma filial informada no arquivo de importação ainda não está cadastrada.

A ausência da filial **não deve interromper ou bloquear o processamento da importação**.

Quando uma filial não existir, o sistema deverá realizar automaticamente seu cadastro utilizando os **dados básicos disponíveis na importação**, seguindo como referência o comportamento utilizado no cadastro da **TMB Barra Mansa**.

Essa funcionalidade deverá ser implementada de forma **genérica**, contemplando tanto:

- **Serviço de Importação**;
- **Importação realizada diretamente pela tela do sistema**.

A implementação deverá ser realizada inicialmente em ambiente **local**, seguida de testes e validação. Somente após a validação completa deverá ser realizada a publicação na **VPS**.

---

# 2. Problema atual

Durante o processamento de uma importação, pode ocorrer de o arquivo possuir uma filial que ainda não existe na base de dados.

Atualmente, essa situação pode gerar um erro e impedir o processamento da importação.

Esse comportamento não é desejado.

A inexistência da filial deve ser tratada como um cenário válido de importação, permitindo que o sistema realize seu cadastro automaticamente e continue o processamento.

---

# 3. Comportamento esperado

Ao processar um registro de importação, o sistema deverá:

1. Identificar a filial informada no registro.
2. Verificar se a filial já existe na base de dados.
3. Caso exista:
   - manter o comportamento atual;
   - continuar o processamento normalmente.
4. Caso não exista:
   - realizar automaticamente o cadastro da filial;
   - utilizar os dados básicos disponíveis na importação;
   - obter o identificador da nova filial;
   - associar o registro importado à filial recém-criada;
   - continuar normalmente o processamento da importação.
5. Registrar a criação da filial para fins de rastreabilidade.

A criação automática **não deverá gerar duplicidade** caso a mesma filial seja processada novamente.

---

# 4. Aplicação da regra nos dois tipos de importação

A mesma regra de negócio deverá ser aplicada nos dois mecanismos existentes:

### 4.1. Serviço de Importação

Quando o serviço identificar uma filial inexistente:

- não deverá interromper o lote;
- deverá criar a filial automaticamente;
- deverá utilizar os dados básicos disponíveis;
- deverá continuar o processamento dos registros;
- deverá registrar a ocorrência em log;
- deverá disponibilizar a informação para que a interface consiga identificar que houve criação automática da filial, caso essa informação seja apresentada no grid de importação.

### 4.2. Importação realizada pela tela

A importação executada diretamente pela interface deverá utilizar **a mesma regra de negócio**.

Quando uma filial inexistente for identificada:

- criar automaticamente a filial;
- continuar o processamento;
- informar ao usuário que a filial foi criada;
- disponibilizar essa informação no resultado da importação.

**Importante:** evitar implementar duas regras independentes. Sempre que possível, a lógica de identificação e criação da filial deverá ser centralizada/reutilizada para garantir que o serviço e a importação em tela tenham exatamente o mesmo comportamento.

---

# 5. Dados para criação da filial

A criação deverá utilizar os **dados básicos disponíveis no arquivo/processo de importação**.

Utilizar como referência o cadastro realizado atualmente para a **TMB Barra Mansa**.

Entretanto, a implementação não deverá conter tratamento específico ou fixo para essa filial.

A solução deverá ser genérica, permitindo que qualquer nova filial recebida futuramente seja cadastrada automaticamente.

Antes da implementação, analisar:

- quais campos foram utilizados no cadastro da TMB Barra Mansa;
- quais informações estão disponíveis na importação;
- quais campos são obrigatórios para criação da filial;
- quais campos podem ser preenchidos com valores padrão;
- quais campos precisam ser obtidos diretamente dos dados importados.

Caso algum dado obrigatório não esteja disponível, a solução deverá definir um comportamento seguro para esse cenário, evitando criação de registros inconsistentes.

---

# 6. Identificação visual no Grid de Importação

Além da alteração no processamento, deverá ser realizada uma alteração visual no **Grid de Importação**.

Atualmente existem, entre outras, as colunas:

**Lote | Ação**

Deverá ser adicionada uma nova coluna entre **Lote** e **Ação**.

### Nova coluna

**Informação**

Essa coluna deverá apresentar um **ícone de informação** quando houver alguma informação relevante relacionada à importação, especificamente quando uma filial tiver sido criada automaticamente.

Exemplo visual:

**Lote | ℹ | Ação**

Quando não houver nenhuma filial criada automaticamente, avaliar a melhor forma de manter a apresentação do grid sem gerar informação desnecessária ao usuário.

---

# 7. Modal de informação da filial criada

Ao clicar no ícone de informação, deverá ser aberto um **modal** apresentando ao usuário que uma filial foi criada automaticamente durante a importação.

O modal deverá apresentar uma mensagem clara, por exemplo:

> **Filial criada automaticamente**
>
> Durante o processamento da importação, foi identificada uma filial que ainda não estava cadastrada no sistema.  
> A filial foi cadastrada automaticamente utilizando os dados disponíveis na importação e o processamento continuou normalmente.

Sempre que possível, apresentar também as informações da filial criada, como:

- Nome da filial;
- Código/identificador da filial, quando disponível;
- Data/hora da criação;
- Lote da importação;
- Quantidade de filiais criadas, caso tenha sido criada mais de uma.

Exemplo:

> **Filial criada automaticamente**
>
> **Filial:** TMB Barra Mansa  
> **Código:** 123  
> **Lote:** 456  
> **Data:** 11/09/2026 06:30
>
> A filial não estava cadastrada e foi criada automaticamente durante o processamento da importação.

A mensagem deverá deixar claro que **a criação automática não representa erro na importação**.

---

# 8. Múltiplas filiais criadas

O processo deverá considerar que um único lote/arquivo pode conter **mais de uma filial inexistente**.

Nesse cenário:

- todas as filiais deverão ser criadas automaticamente;
- o processamento deverá continuar normalmente;
- o sistema não deverá criar registros duplicados;
- o ícone de informação deverá indicar que existem informações disponíveis;
- o modal deverá apresentar todas as filiais criadas naquele processamento.

Exemplo:

> **3 filiais foram criadas automaticamente**
>
> - Filial A
> - Filial B
> - Filial C

---

# 9. Controle para evitar duplicidade

É fundamental garantir que a criação automática não gere filiais duplicadas.

Antes de criar uma filial, o sistema deverá realizar uma validação utilizando os critérios de identificação da filial já existentes na aplicação.

Também deverá ser considerada a possibilidade de dois registros do mesmo lote referenciarem a mesma filial inexistente.

Nesse caso:

1. A filial deverá ser criada apenas uma vez.
2. Os demais registros deverão utilizar a filial já criada.
3. O sistema deverá informar a criação apenas uma vez no contexto daquele lote/importação.

---

# 10. Persistência da informação

A implementação deverá avaliar a necessidade de persistir a informação de que determinada filial foi criada automaticamente durante uma importação.

Essa informação deverá estar disponível para o Grid de Importação e para o modal.

Não utilizar apenas uma informação temporária em memória se isso fizer com que o ícone/modal deixe de funcionar após uma atualização da página ou nova consulta do grid.

Definir no desenvolvimento a melhor estratégia de persistência de acordo com a estrutura atual do projeto.

---

# 11. Logs

Sempre que uma filial for criada automaticamente, o processo deverá registrar a ocorrência em log.

O log deverá permitir identificar, quando possível:

- lote da importação;
- filial criada;
- identificador gerado;
- data/hora;
- origem da importação;
- serviço ou usuário responsável pelo processamento;
- eventual erro ocorrido durante o cadastro.

Isso permitirá realizar auditoria e diagnóstico posteriormente.

---

# 12. Tratamento de erros

Caso ocorra algum problema durante o cadastro automático da filial, o sistema deverá:

- registrar o erro detalhadamente;
- evitar criar registros incompletos;
- não gerar duplicidade;
- informar adequadamente o status do processamento;
- preservar o comportamento atual de tratamento de erros para situações realmente impeditivas.

A simples inexistência da filial **não deverá ser considerada erro**.

---

# 13. Critérios de aceite

### Cenário 1 – Filial existente

Dado que a filial já existe:

- o sistema deve localizar a filial;
- não deve criar uma nova;
- a importação deve continuar normalmente;
- não deve aparecer informação de "filial criada".

### Cenário 2 – Filial inexistente

Dado que a filial não existe:

- o sistema deve criar automaticamente a filial;
- deve utilizar os dados básicos disponíveis;
- deve continuar o processamento;
- deve registrar a ocorrência;
- o Grid deverá apresentar o ícone de informação;
- ao clicar no ícone, o modal deverá informar a criação.

### Cenário 3 – Mesmo arquivo com vários registros da mesma filial inexistente

- a filial deve ser criada somente uma vez;
- todos os registros devem utilizar a mesma filial;
- não pode haver duplicidade.

### Cenário 4 – Arquivo com várias filiais inexistentes

- todas as filiais devem ser criadas;
- a importação deve continuar;
- o modal deve apresentar as filiais criadas.

### Cenário 5 – Importação pelo serviço

- o comportamento deverá funcionar sem intervenção do usuário;
- a filial deverá ser criada automaticamente;
- o processamento não deverá ser bloqueado.

### Cenário 6 – Importação pela tela

- a filial deverá ser criada automaticamente;
- o processamento deverá continuar;
- o Grid deverá apresentar o ícone;
- o modal deverá apresentar a informação da criação.

### Cenário 7 – Nova importação após criação

Ao realizar uma nova importação contendo a mesma filial:

- a filial deverá ser encontrada;
- não deverá ser criada novamente;
- não deverá gerar nova ocorrência de criação automática.

---

# 14. Estratégia de implementação

Antes de iniciar o desenvolvimento:

1. Analisar o fluxo atual do serviço de importação.
2. Analisar o fluxo da importação realizada pela tela.
3. Identificar onde ocorre atualmente a validação da filial.
4. Analisar como foi realizado o cadastro da TMB Barra Mansa.
5. Identificar os campos necessários para criação.
6. Avaliar a possibilidade de centralizar a regra em um único componente/método/serviço.
7. Implementar a criação automática.
8. Implementar o registro da ocorrência.
9. Implementar a nova coluna no Grid.
10. Implementar o ícone de informação.
11. Implementar o modal.
12. Realizar os testes no ambiente local.
13. Corrigir eventuais inconsistências.
14. Validar todos os critérios de aceite.
15. Somente após aprovação, publicar na VPS.

---

# 15. Regra principal

A regra fundamental desta alteração é:

> **Filial inexistente não deve bloquear a importação.**

O sistema deverá reconhecer a situação, criar a filial automaticamente com os dados básicos disponíveis, registrar a ocorrência e continuar o processamento normalmente.

A funcionalidade deverá ser **única e consistente**, contemplando tanto o **serviço de importação** quanto a **importação realizada pela tela**, evitando comportamentos diferentes entre os dois fluxos.