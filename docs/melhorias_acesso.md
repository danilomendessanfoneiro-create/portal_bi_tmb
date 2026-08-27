# PRD — Gestão de Usuários, Senhas e Recuperação de Acesso

## 1. Objetivo

Implementar uma evolução completa do módulo de usuários, contemplando:

1. Cadastro de e-mail de login.
2. Alteração de senha pelo administrador.
3. Geração de senha segura.
4. Recuperação de senha pelo próprio usuário.
5. Envio de link de recuperação por e-mail.
6. Link de recuperação exclusivo para o usuário e válido por 30 minutos.
7. Tela para definição de nova senha.
8. Alteração da própria senha pelo usuário autenticado.
9. Geração e envio de senha provisória pelo administrador.
10. Primeiro acesso utilizando senha provisória.
11. Obrigatoriedade de definição de senha definitiva após o primeiro acesso.
12. Criação de **novo usuário** (perfis existentes `admin` / `filial` — **não** criar perfil “Gestão de Entregas”).
13. Controle adequado de permissões com os perfis já existentes.
14. Auditoria e segurança das operações.
15. Validação por Build após cada User History.

Todas as alterações deverão respeitar a arquitetura, padrões de código, nomenclaturas, componentes e mecanismos de segurança já existentes no sistema.

---

# 2. Regras gerais de desenvolvimento

## 2.1 Branch

As alterações deverão ser realizadas **exclusivamente na branch atual**.

Não realizar:

* Criação de nova branch.
* `git commit`.
* `git push`.
* Merge.
* Rebase que altere o histórico da branch.

Não descartar alterações locais existentes que não pertençam ao escopo desta demanda.

---

## 2.2 Análise antes da implementação

Antes de iniciar qualquer alteração, analisar a implementação atual do sistema para identificar:

* Estrutura de usuários.
* Login.
* Autenticação.
* Perfis.
* Roles.
* Permissões.
* Senhas.
* Hash de senha.
* Sessões.
* E-mails.
* SMTP.
* Templates de e-mail.
* Serviços existentes.
* Repositories.
* Managers.
* Helpers.
* Auditoria.
* Estrutura de banco.
* Padrão das telas.
* Padrão dos endpoints.
* Padrão de validação.
* Padrão de segurança.

**Não criar uma arquitetura paralela se já existir uma implementação equivalente no sistema.**

Sempre que possível, reutilizar componentes existentes.

---

# 3. User History 01 — Cadastro de e-mail de login

## História

**Como administrador, quero cadastrar e gerenciar o e-mail de login de um usuário, para permitir autenticação e recuperação de senha por e-mail.**

## Requisitos

Adicionar o campo:

**E-mail de Login**

na tela de gestão de usuários.

O campo deverá permitir:

* Cadastro.
* Alteração.
* Visualização.
* Validação.
* Persistência.

## Validações

O sistema deverá:

* Validar formato de e-mail.
* Remover espaços no início e no final.
* Tratar e-mails de maneira case-insensitive.
* Impedir duplicidade quando o e-mail for identificador único.
* Informar adequadamente erros de validação.

## Permissões

Somente administradores poderão:

* Cadastrar e-mail de outro usuário.
* Alterar e-mail de outro usuário.

O usuário comum não poderá alterar o e-mail de login de outro usuário.

## Critérios de aceite

* [ ] Campo E-mail de Login disponível.
* [ ] Cadastro funcionando.
* [ ] Alteração funcionando.
* [ ] Validação funcionando.
* [ ] Duplicidade tratada.
* [ ] Persistência funcionando.

### Validação obrigatória

Ao finalizar esta User History:

**Executar Build e corrigir todos os erros antes de prosseguir.**

---

# 4. User History 02 — Alteração de senha pelo administrador

## História

**Como administrador, quero alterar a senha de um usuário, para permitir a gestão das credenciais de acesso.**

## Requisitos

Na gestão de usuários deverá existir a ação:

**Alterar senha**

Ao acioná-la:

* Identificar o usuário.
* Abrir tela/modal de alteração.
* Permitir definir uma nova senha.
* Permitir geração automática de senha segura.
* Persistir a senha utilizando o mecanismo seguro existente.

## Permissões

Somente administrador poderá alterar a senha de outro usuário.

A autorização deverá ser validada no backend.

Não confiar somente na ocultação do botão na interface.

---

# 5. User History 03 — Geração de senha segura

## História

**Como sistema, quero gerar senhas seguras automaticamente, para reduzir o risco de credenciais fracas.**

## Requisitos

Criar/reutilizar mecanismo de geração de senha segura.

A senha deverá possuir:

* Comprimento mínimo conforme política do sistema.
* Letras maiúsculas.
* Letras minúsculas.
* Números.
* Caracteres especiais.
* Aleatoriedade criptograficamente segura.

Não utilizar:

* Nome do usuário.
* E-mail.
* Data de nascimento.
* Nome da empresa.
* Informações previsíveis.

Exemplo conceitual:

`A7#mQ92!vLx4`

A senha deverá ser gerada dinamicamente.

---

# 6. Segurança de senha

Independentemente do fluxo:

* Nunca armazenar senha em texto puro.
* Utilizar hash seguro.
* Não registrar senha em logs.
* Não colocar senha na URL.
* Não colocar senha em QueryString.
* Não retornar senha em APIs desnecessariamente.
* Não armazenar senha em cookies.
* Não expor senha no frontend após o processamento.

Antes de implementar, identificar o mecanismo de hash atualmente utilizado pelo sistema e reutilizá-lo caso esteja adequado.

---

# 7. User History 04 — Alteração da própria senha

## História

**Como usuário autenticado, quero alterar minha própria senha, para manter minha conta segura.**

## Fluxo

Usuário autenticado:

`Minha conta`

→

`Alterar senha`

→

`Senha atual`

→

`Nova senha`

→

`Confirmar nova senha`

→

`Salvar`

## Validações

O sistema deverá:

* Validar senha atual.
* Validar nova senha.
* Validar confirmação.
* Garantir que a nova senha atende à política de segurança.
* Impedir nova senha inválida.
* Atualizar o hash.

O usuário não poderá alterar a senha de outro usuário por esse fluxo.

---

# 8. User History 05 — Solicitação de recuperação de senha

## História

**Como usuário, quero solicitar a recuperação da minha senha, para recuperar meu acesso sem depender do administrador.**

## Tela de login

Adicionar:

**Esqueci minha senha**

Ao clicar:

1. Solicitar e-mail.
2. Validar formato.
3. Processar solicitação.
4. Gerar token seguro.
5. Registrar solicitação.
6. Enviar e-mail.
7. Informar o usuário que a solicitação foi processada.

## Segurança contra enumeração

O sistema não deverá informar se o e-mail existe.

Exemplo de resposta:

> Se o e-mail informado estiver cadastrado, você receberá as instruções para recuperação de senha.

A mesma resposta deverá ser utilizada para e-mails inexistentes.

---

# 9. User History 06 — Token de recuperação

## História

**Como sistema, quero gerar um token seguro e temporário, para permitir recuperação de senha com controle de acesso.**

## Requisitos

O token deverá:

* Ser aleatório.
* Ser imprevisível.
* Ser exclusivo.
* Estar vinculado ao usuário.
* Ter validade de **30 minutos**.
* Ser de utilização única.
* Ser invalidado após utilização.
* Ser invalidado quando uma nova solicitação for realizada.

## Armazenamento

Preferencialmente armazenar somente o **hash do token**.

Não armazenar o token original no banco.

## Validação

Ao acessar o link:

1. Localizar token.
2. Validar hash.
3. Validar usuário.
4. Validar expiração.
5. Validar status.
6. Validar se já foi utilizado.
7. Liberar alteração somente se válido.

---

# 10. User History 07 — Link de recuperação

## História

**Como usuário, quero receber um link seguro por e-mail, para definir uma nova senha.**

O link deverá possuir token seguro.

Exemplo conceitual:

`https://sistema/.../reset-password?token=TOKEN`

O token:

* Não poderá conter a senha.
* Não poderá conter dados sensíveis.
* Terá validade de 30 minutos.
* Será de uso único.

## Link expirado

Ao acessar um link expirado:

Não permitir alteração da senha.

Exibir mensagem amigável:

> Este link de recuperação expirou. Solicite uma nova recuperação de senha.

---

# 11. User History 08 — E-mail de recuperação

## História

**Como usuário, quero receber por e-mail as instruções para recuperação, para conseguir redefinir minha senha.**

Criar/reutilizar template de e-mail.

O e-mail deverá conter:

* Nome do usuário, quando aplicável.
* Identificação do sistema.
* Orientação.
* Link de recuperação.
* Informação de que o link expira em 30 minutos.
* Aviso de segurança.

Não enviar:

* Senha atual.
* Senha definitiva.
* Informações internas.
* Token em formato diferente do link necessário.

---

# 12. User History 09 — Tela de recuperação de senha

## História

**Como usuário que recebeu um link válido, quero cadastrar uma nova senha, para recuperar meu acesso.**

## Tela

Criar tela específica contendo:

* Nova senha.
* Confirmar nova senha.

Exibir requisitos da senha.

## Regras

O sistema deverá:

1. Validar token.
2. Permitir alteração somente com token válido.
3. Validar nova senha.
4. Atualizar hash.
5. Invalidar token.
6. Registrar alteração.
7. Finalizar processo.

Após conclusão, redirecionar para login ou fluxo padrão da aplicação.

---

# 13. User History 10 — Senha provisória enviada pelo administrador

## História

**Como administrador, quero enviar uma senha provisória para o e-mail cadastrado de um usuário, para permitir que ele obtenha acesso inicial ou tenha seu acesso restaurado.**

## Nova ação

Na gestão de usuários adicionar:

**Enviar senha provisória**

## Fluxo

Administrador:

`Usuários`

→

`Selecionar usuário`

→

`Enviar senha provisória`

→

`Confirmar`

→

`Gerar senha segura`

→

`Enviar e-mail`

→

`Usuário recebe credencial`

---

# 14. Validação do e-mail para senha provisória

Antes de enviar:

* Verificar se o usuário possui e-mail cadastrado.
* Validar e-mail.
* Caso não possua, impedir operação.

Mensagem:

> O usuário não possui e-mail de login cadastrado. Cadastre um e-mail antes de enviar a senha provisória.

---

# 15. Senha provisória

A senha provisória deverá:

* Ser gerada automaticamente.
* Ser segura.
* Ser armazenada somente como hash.
* Não ser registrada em logs.
* Não ser incluída na URL.
* Não ser reutilizável após definição da senha definitiva.

A senha provisória deverá possuir validade.

### Validade sugerida

**24 horas.**

Esse período deve ser configurável caso o sistema possua estrutura de configuração.

---

# 16. E-mail da senha provisória

Criar/reutilizar template de e-mail.

O e-mail deverá conter:

* Nome do usuário.
* Identificação do sistema.
* Senha provisória.
* Link de acesso ao sistema.
* Orientação de primeiro acesso.
* Aviso de que a senha é provisória.

Exemplo:

> Uma senha provisória foi gerada para sua conta.
>
> Utilize a senha abaixo para realizar seu primeiro acesso:
>
> **Senha provisória:** XXXXXXXX
>
> No primeiro acesso, você deverá cadastrar uma nova senha definitiva.

A senha deverá ser enviada somente para o e-mail cadastrado.

---

# 17. User History 11 — Primeiro acesso com senha provisória

## História

**Como usuário que recebeu uma senha provisória, quero acessar o sistema e cadastrar uma senha definitiva, para começar a utilizar minha conta normalmente.**

## Fluxo

`E-mail`

↓

`Senha provisória`

↓

`Login`

↓

`Sistema identifica senha provisória`

↓

`Tela obrigatória de nova senha`

↓

`Senha definitiva`

↓

`Acesso normal`

---

# 18. Bloqueio durante senha provisória

Enquanto o usuário estiver marcado como necessitando alterar a senha:

`MustChangePassword = true`

não deverá acessar as funcionalidades normais do sistema.

O sistema deverá permitir somente:

* Tela de alteração de senha.
* Logout.
* Recursos estritamente necessários para conclusão do processo.

Não permitir acesso normal antes da definição da senha definitiva.

---

# 19. User History 12 — Definição da senha definitiva

## História

**Como usuário que está utilizando uma senha provisória, quero definir minha senha definitiva, para continuar utilizando o sistema normalmente.**

## Tela

Campos:

* Nova senha.
* Confirmar nova senha.

## Regras

A nova senha deverá:

* Atender à política de segurança.
* Ser diferente da senha provisória.
* Ser confirmada corretamente.

Após salvar:

1. Atualizar hash.
2. Invalidar senha provisória.
3. Definir `MustChangePassword = false`.
4. Registrar alteração.
5. Liberar acesso.
6. Manter o usuário autenticado, quando compatível com o mecanismo atual.
7. Redirecionar para a página inicial.

O usuário não deverá precisar realizar um segundo login após definir a senha definitiva, salvo limitação técnica do mecanismo atual.

---

# 20. Expiração da senha provisória

A senha provisória deverá expirar após o período definido.

Sugestão:

**24 horas.**

Após expirar:

* Não permitir login com a senha provisória.
* Informar que a credencial expirou.
* Permitir recuperação de senha ou nova geração pelo administrador.

---

# 21. Nova senha provisória

Se o administrador enviar novamente uma senha provisória:

* Invalidar a senha provisória anterior.
* Gerar nova senha.
* Atualizar hash.
* Atualizar expiração.
* Manter `MustChangePassword = true`.
* Enviar novo e-mail.

Somente a senha provisória mais recente deverá permanecer válida.

---

# 22. Diferença entre recuperação e senha provisória

Os dois fluxos deverão ser tratados separadamente.

## Recuperação de senha

Iniciada pelo usuário:

`Login`

→

`Esqueci minha senha`

→

`E-mail`

→

`Link`

→

`30 minutos`

→

`Nova senha`

→

`Login`

## Senha provisória

Iniciada pelo administrador:

`Admin`

→

`Usuário`

→

`Enviar senha provisória`

→

`E-mail`

→

`Senha provisória`

→

`Login`

→

`Obrigatório alterar senha`

→

`Senha definitiva`

→

`Sistema`

---

# 23. User History 13 — Criação de novo usuário

## História

**Como administrador, quero criar um novo usuário no sistema, para conceder acesso com e-mail de login e, quando necessário, senha provisória — sem criar um novo perfil “Gestão de Entregas”.**

## Requisitos

Analisar como o sistema atual trabalha com:

* Usuários.
* Perfis existentes (`admin`, `filial`).
* Menus e módulos por perfil.

**Não criar** um novo perfil/role chamado “Gestão de Entregas”.

A UH13 é a **criação de um novo usuário** usando os perfis já existentes, integrando:

* E-mail de login (UH01).
* Geração/envio de senha provisória (UH10), quando aplicável.
* Fluxo de primeiro acesso (UH11–UH12).

O formulário de criação deverá seguir o padrão atual da tela de usuários (login, nome, perfil `admin`|`filial`, filial quando `filial`, e-mail de login, etc.).

---

# 24. Permissões — perfis existentes

O novo usuário recebe as permissões do **perfil escolhido** (`admin` ou `filial`), já implementadas no sistema.

* Usuário com perfil `filial` não deve obter privilégios administrativos.
* Usuário com perfil `admin` mantém o acesso administrativo atual.
* Não introduzir matriz de permissões granular nova nesta demanda.
* Autorização continua validada no backend conforme o perfil existente.

---

# 25. Banco de dados

Antes de criar qualquer estrutura:

1. Analisar tabela atual de usuários.
2. Analisar estrutura de autenticação.
3. Analisar estrutura de senha.
4. Analisar perfis.
5. Analisar permissões.
6. Verificar se já existe estrutura para tokens.
7. Verificar se já existe estrutura para recuperação de senha.

Reutilizar estruturas existentes quando forem adequadas.

---

# 26. Estrutura conceitual de recuperação

Caso não exista estrutura equivalente, criar uma tabela seguindo o padrão de nomenclatura do projeto.

Exemplo conceitual:

### UserPasswordRecovery

* `Id`
* `UserId`
* `TokenHash`
* `CreatedAt`
* `ExpiresAt`
* `UsedAt`
* `RevokedAt`
* `Status`

Possíveis status:

* `Pending`
* `Used`
* `Expired`
* `Revoked`

Os nomes reais deverão seguir o padrão do banco existente.

---

# 27. Estrutura conceitual para senha provisória

Reutilizar os campos existentes sempre que possível.

Caso necessário, utilizar conceito equivalente a:

* `MustChangePassword`
* `TemporaryPasswordExpiresAt`
* `PasswordChangedAt`

Não criar estruturas duplicadas se o banco já possuir campos equivalentes.

---

# 28. Auditoria

Quando existir mecanismo de auditoria no sistema, registrar operações relevantes:

* Alteração de senha pelo administrador.
* Solicitação de recuperação.
* Geração de senha provisória.
* Alteração de senha pelo usuário.
* Conclusão do primeiro acesso.
* Revogação de credencial.
* Expiração de token.

Nunca registrar:

* Senha.
* Token original.
* Dados sensíveis desnecessários.

---

# 29. Segurança de autorização

Toda operação administrativa deverá ser protegida no backend.

Isso inclui:

* Alterar senha de usuário.
* Gerar senha provisória.
* Enviar senha provisória.
* Alterar e-mail de usuário.
* Gerenciar permissões.

Não considerar suficiente:

* Esconder botão.
* Desabilitar botão.
* Ocultar menu.
* Validar somente no JavaScript.

---

# 30. Tratamento de erros

As mensagens apresentadas ao usuário devem ser amigáveis e não revelar detalhes internos.

Não exibir:

* Stack trace.
* SQL.
* Nome de tabela.
* Exception interna.
* Hash.
* Token.
* Informações de existência de usuário em recuperação.

Registrar detalhes técnicos somente nos mecanismos apropriados de log.

---

# 31. Testes funcionais

## Cadastro de e-mail

* [ ] Criar usuário com e-mail.
* [ ] Editar e-mail.
* [ ] E-mail inválido.
* [ ] E-mail duplicado.
* [ ] E-mail com espaços.
* [ ] Usuário sem e-mail.

## Alteração administrativa

* [ ] Admin altera senha.
* [ ] Usuário comum não altera senha de terceiros.
* [ ] Nova senha é salva corretamente.
* [ ] Senha antiga deixa de funcionar.

## Alteração pelo próprio usuário

* [ ] Senha atual correta.
* [ ] Senha atual incorreta.
* [ ] Nova senha válida.
* [ ] Confirmação diferente.
* [ ] Senha fora do padrão.

## Recuperação

* [ ] Solicitar recuperação.
* [ ] E-mail válido.
* [ ] E-mail inexistente.
* [ ] Resposta não revela existência.
* [ ] E-mail recebido.
* [ ] Link válido.
* [ ] Link expirado.
* [ ] Link utilizado novamente.
* [ ] Nova solicitação.
* [ ] Token anterior invalidado.

## Senha provisória

* [ ] Admin gera senha provisória.
* [ ] Usuário possui e-mail.
* [ ] Usuário sem e-mail.
* [ ] E-mail recebido.
* [ ] Login com senha provisória.
* [ ] Sistema força alteração.
* [ ] Usuário não acessa sistema antes da troca.
* [ ] Nova senha é salva.
* [ ] Senha provisória deixa de funcionar.
* [ ] `MustChangePassword` é desativado.
* [ ] Usuário continua autenticado.
* [ ] Nova senha provisória invalida a anterior.
* [ ] Senha provisória expirada não funciona.

## Permissões

* [ ] Admin possui todas as funcionalidades previstas.
* [ ] Usuário comum não possui funções administrativas.
* [ ] Novo usuário criado com perfil existente (`admin` ou `filial`).
* [ ] Backend valida permissões do perfil.

---

# 32. Ordem obrigatória de implementação

As User Histories deverão ser executadas na seguinte ordem:

### UH01

Cadastro de e-mail de login.

**Executar Build.**

### UH02

Alteração de senha pelo administrador.

**Executar Build.**

### UH03

Geração de senha segura.

**Executar Build.**

### UH04

Alteração da própria senha.

**Executar Build.**

### UH05

Solicitação de recuperação.

**Executar Build.**

### UH06

Token de recuperação.

**Executar Build.**

### UH07

Link de recuperação.

**Executar Build.**

### UH08

E-mail de recuperação.

**Executar Build.**

### UH09

Tela de recuperação.

**Executar Build.**

### UH10

Senha provisória administrativa.

**Executar Build.**

### UH11

Primeiro acesso com senha provisória.

**Executar Build.**

### UH12

Definição da senha definitiva.

**Executar Build.**

### UH13

Criação de novo usuário (perfis existentes; sem perfil “Gestão de Entregas”).

**Executar Build.**

---

# 33. Regra obrigatória de Build

Após **cada User History finalizada**, obrigatoriamente:

1. Salvar alterações.
2. Revisar código.
3. Executar Build.
4. Verificar resultado.
5. Corrigir erros.
6. Executar Build novamente.
7. Confirmar que não existem erros.
8. Somente então iniciar a próxima User History.

Não acumular várias User Histories antes de executar o Build.

---

# 34. Critérios gerais de aceite

A implementação será considerada concluída quando:

* [ ] E-mail de login estiver disponível na gestão de usuários.
* [ ] E-mail possuir validação.
* [ ] E-mail duplicado for tratado.
* [ ] Administrador puder alterar senha.
* [ ] Usuário puder alterar sua própria senha.
* [ ] Senhas forem armazenadas de forma segura.
* [ ] Existir geração de senha segura.
* [ ] Usuário puder solicitar recuperação.
* [ ] E-mail de recuperação for enviado.
* [ ] Link de recuperação possuir validade de 30 minutos.
* [ ] Token for seguro.
* [ ] Token for de uso único.
* [ ] Token anterior for invalidado quando necessário.
* [ ] Usuário puder definir nova senha pelo link.
* [ ] Administrador puder enviar senha provisória.
* [ ] Senha provisória for enviada para o e-mail cadastrado.
* [ ] Senha provisória possuir validade.
* [ ] Usuário puder realizar primeiro acesso.
* [ ] Sistema obrigar troca da senha provisória.
* [ ] Usuário puder definir senha definitiva.
* [ ] Senha provisória for invalidada após a troca.
* [ ] Usuário puder continuar autenticado após definir senha definitiva.
* [ ] Administrador puder criar novo usuário com e-mail de login.
* [ ] Novo usuário usar somente perfis existentes (`admin` / `filial`).
* [ ] Autorizações forem validadas no backend conforme o perfil.
* [ ] Auditoria for aplicada conforme o padrão existente.
* [ ] Cada User History tiver passado pelo Build.
* [ ] Build final estiver sem erros.
* [ ] Nenhum commit tiver sido realizado.
* [ ] Nenhum push tiver sido realizado.
* [ ] Todas as alterações permanecerem na branch atual.

---

# 35. Entrega final

Ao terminar a implementação, apresentar um resumo contendo:

## User Histories

Para cada UH:

* Status.
* Descrição.
* Arquivos alterados.
* Banco alterado.
* Principais mudanças.

## Build

Apresentar:

* Build da UH01.
* Build da UH02.
* Build da UH03.
* ...
* Build da UH13.
* Resultado final.

Caso algum Build apresente erro:

* Informar o erro.
* Informar a correção.
* Executar novamente.
* Registrar o resultado final.

## Banco

Informar:

* Tabelas criadas.
* Tabelas alteradas.
* Campos adicionados.
* Procedures alteradas.
* Scripts necessários.

## Segurança

Informar:

* Mecanismo de hash utilizado.
* Estratégia de geração de senha.
* Estratégia de geração do token.
* Armazenamento do token.
* Validade do token: **30 minutos**.
* Validade da senha provisória: **24 horas**, caso não exista configuração diferente no sistema.
* Controle de utilização única.
* Controle de permissões.

## Git

Confirmar explicitamente:

**Branch atual utilizada:** manter a branch em que o trabalho foi iniciado.

**Commit:** nenhum.

**Push:** nenhum.

**Estado:** alterações permanecem somente no ambiente de trabalho para posterior revisão.
