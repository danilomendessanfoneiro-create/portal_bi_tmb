# Portal BI de Entregas — TMB Logística

## Estrutura de arquivos

```
portal/
├── app.py                  -> tela principal do portal
├── auth.py                 -> controla login e permissões
├── estilo.py                -> visual do portal (cores, cards, tipografia)
├── limpeza.py               -> trata a planilha (mesmo do e-mail diário)
├── gerar_senha.py            -> gera o hash de uma senha nova
├── usuarios.csv              -> cadastro de logins (usuário/senha/perfil)
├── requirements.txt          -> lista de bibliotecas necessárias
├── logo_tmb.png               -> logo usada no portal
├── assets/icons/               -> ícones usados nos cards de indicador
├── .streamlit/config.toml      -> cores do portal (tema TMB)
└── dados/entregas_relatorio.csv -> planilha usada pelo portal (trocar quando tiver dados novos)
```

## Sobre o visual (v2)

O portal foi redesenhado com cards de indicador, gráficos com mais acabamento
(barra de atrasos + rosca de situação) e uma tabela de dados interativa no
lugar da lista de cards expansíveis. Também tem um **simulador de tolerância**
na barra lateral: um controle deslizante que recalcula, em tempo real, quantas
entregas ficariam atrasadas se a empresa desse alguns dias a mais de prazo —
útil para testar cenários sem mexer nos dados reais.

## Antes de publicar

1. **Trocar as senhas de exemplo.** Hoje `usuarios.csv` está com senhas
   provisórias (`admin123` para o admin, `filial123` para as filiais — todas
   iguais, só para teste). Para gerar uma senha nova de verdade:

   ```
   python gerar_senha.py NovaSenhaForte
   ```

   Isso imprime um código (hash). Copie e cole esse código na coluna
   `senha_hash` da linha do usuário correspondente, dentro do `usuarios.csv`.
   **Nunca coloque a senha em texto puro no arquivo — sempre o hash gerado.**

2. **Conferir os nomes de usuário.** Cada linha do `usuarios.csv` representa
   um login. A coluna `filial` precisa ser IGUAL ao valor que aparece na
   planilha (ex: `TMB VIANA`), senão o filtro não vai casar. A linha do
   admin tem `perfil = admin` e enxerga tudo, independente da coluna filial.

3. **Atualizar a planilha.** Sempre que tiver uma planilha nova do sistema
   de gestão, substitua o arquivo em `dados/entregas_relatorio.csv` (mesmo
   nome) e suba para o GitHub. O portal atualiza sozinho (os dados ficam em
   cache por 10 minutos, para não reprocessar a cada clique).

## Publicando (mesmo fluxo do portal contábil)

1. Suba a pasta `portal/` inteira para um repositório no GitHub.
2. Acesse [share.streamlit.io](https://share.streamlit.io), conecte esse
   repositório e aponte o arquivo principal como `app.py`.
3. O Streamlit Cloud instala automaticamente o que está em
   `requirements.txt` e publica um link público.

## Como funciona o acesso

- **Login admin:** vê todas as filiais, com gráfico comparativo entre elas.
- **Login de filial:** vê só os próprios dados (o filtro de filial some da
  tela, porque não faz sentido para esse usuário).
- Qualquer usuário pode clicar em cada entrega para expandir e ver os
  detalhes: cliente, cidade, valor, volumes, status, datas de prazo e
  motivo do atraso (quando houver).
