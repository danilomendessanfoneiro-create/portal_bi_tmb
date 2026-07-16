"""
auth.py
--------
Autenticacao simples do portal, baseada num arquivo usuarios.csv.

Cada usuario tem: usuario, senha (hash), perfil (admin ou filial), filial.
- perfil = "admin"  -> enxerga todos os dados, de todas as filiais
- perfil = "filial" -> enxerga apenas os dados da coluna "filial" correspondente

As senhas NUNCA sao guardadas em texto puro - so o hash (SHA-256 + sal fixo
do projeto). Use o script gerar_senha.py para criar o hash de uma senha nova.
"""

import hashlib
import os
import pandas as pd
import streamlit as st

SAL_PROJETO = "tmb-logistica-bi"  # trocar por algo proprio do seu projeto

# logo_tmb.png fica na mesma pasta deste arquivo (auth.py)
CAMINHO_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_tmb.png")


def hash_senha(senha: str) -> str:
    return hashlib.sha256(f"{SAL_PROJETO}:{senha}".encode("utf-8")).hexdigest()


def carregar_usuarios(caminho: str = "usuarios.csv") -> pd.DataFrame:
    return pd.read_csv(caminho, sep=";", encoding="utf-8", dtype=str)


def verificar_login(usuario: str, senha: str, usuarios: pd.DataFrame):
    """Retorna a linha do usuario se usuario+senha conferem, senao None."""
    linha = usuarios[usuarios["usuario"] == usuario]
    if linha.empty:
        return None

    linha = linha.iloc[0]
    if linha["senha_hash"] == hash_senha(senha):
        return linha
    return None


def tela_login(usuarios: pd.DataFrame):
    """Mostra o formulario de login. Preenche st.session_state quando ok."""
    from estilo import aplicar_estilo
    aplicar_estilo()

    st.markdown("<div style='padding-top: 4vh;'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.15, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.image(CAMINHO_LOGO, use_container_width=True)
        st.markdown(
            "<h3 style='color:#1E3056;margin-top:0.8rem;margin-bottom:0.2rem;'>Portal BI de Entregas</h3>"
            "<p style='color:#64748B;font-size:0.9rem;margin-bottom:1.2rem;'>Entre com seu usuário e senha para continuar</p>",
            unsafe_allow_html=True,
        )

        with st.form("form_login"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

        if entrar:
            linha = verificar_login(usuario.strip(), senha, usuarios)
            if linha is not None:
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = linha["usuario"]
                st.session_state["perfil"] = linha["perfil"]
                st.session_state["filial"] = linha["filial"]
                st.session_state["nome_exibicao"] = linha.get("nome_exibicao", linha["usuario"])
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")


def exigir_login(caminho_usuarios: str = "usuarios.csv"):
    """
    Chame no topo do app.py. Se o usuario ainda nao esta logado, mostra a
    tela de login e interrompe a execucao do resto da pagina.
    """
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        usuarios = carregar_usuarios(caminho_usuarios)
        tela_login(usuarios)
        st.stop()


def logout():
    for chave in ["autenticado", "usuario", "perfil", "filial", "nome_exibicao"]:
        st.session_state.pop(chave, None)
    st.rerun()
