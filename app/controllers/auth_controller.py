"""Authentication UI controller (Streamlit) — JWT unificado com o admin."""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components

from app.config import settings
from app.models import User
from app.repositories import UserRepository
from app.services.auth_service import AuthError, AuthService
from app.utils.embed import is_embedded
from app.utils.jwt_tokens import create_access_token, decode_access_token
from app.utils.style import aplicar_estilo

COOKIE_NAME = "portal_token"


def _set_session(user: User, token: Optional[str] = None) -> None:
    st.session_state["autenticado"] = True
    st.session_state["usuario"] = user.login
    st.session_state["perfil"] = user.profile
    st.session_state["filial"] = user.branch or ""
    st.session_state["nome_exibicao"] = user.display_name or user.login
    st.session_state["user_id"] = user.id
    if token:
        st.session_state["access_token"] = token
        _inject_cookie(token)


def _inject_cookie(token: str) -> None:
    safe = token.replace("\\", "\\\\").replace("'", "\\'")
    components.html(
        f"<script>document.cookie='{COOKIE_NAME}={safe}; path=/; SameSite=Lax; max-age="
        f"{settings.jwt_expire_minutes * 60}';</script>",
        height=0,
    )


def _clear_cookie() -> None:
    components.html(
        f"<script>document.cookie='{COOKIE_NAME}=; path=/; max-age=0';</script>",
        height=0,
    )


def _user_from_token(token: str) -> Optional[User]:
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None
    return UserRepository().get_by_login(str(payload["sub"]), include_disabled=False)


def _token_from_request() -> Optional[str]:
    qp = st.query_params.get("token")
    if qp:
        return qp if isinstance(qp, str) else qp[0]
    try:
        cookies = getattr(st.context, "cookies", None)
        if cookies:
            return cookies.get(COOKIE_NAME)
    except Exception:
        pass
    return None


def try_jwt_login() -> bool:
    if st.session_state.get("autenticado"):
        return True
    token = _token_from_request()
    if not token:
        return False
    try:
        user = _user_from_token(token)
    except Exception:
        return False
    if user is None:
        return False
    _set_session(user, token)
    if "token" in st.query_params:
        del st.query_params["token"]
    return True


def render_embed_gate() -> None:
    admin = settings.admin_public_url.rstrip("/")
    st.markdown(
        "<div style='padding:2rem;max-width:420px;margin:10vh auto;text-align:center;'>"
        "<h3 style='color:#1E3056;'>Visualização</h3>"
        "<p style='color:#64748B;'>Abra o portal pelo Admin para carregar o BI autenticado.</p>"
        f"<p><a href='{admin}/visualizacao'>Ir para o Admin</a></p>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_login() -> None:
    if is_embedded():
        render_embed_gate()
        return

    aplicar_estilo()
    auth = AuthService()

    st.markdown("<div style='padding-top: 4vh;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.15, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        if settings.logo_full_path.exists():
            st.image(str(settings.logo_full_path), use_container_width=True)
        elif settings.logo_path.exists():
            st.image(str(settings.logo_path), use_container_width=True)
        st.markdown(
            "<h3 style='color:#1E3056;margin-top:0.8rem;margin-bottom:0.2rem;'>Portal BI de Entregas</h3>"
            "<p style='color:#64748B;font-size:0.9rem;margin-bottom:1.2rem;'>"
            "Entre com seu usuário e senha para continuar</p>",
            unsafe_allow_html=True,
        )
        with st.form("form_login"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", use_container_width=True)
        admin_url = settings.admin_public_url.rstrip("/")
        st.markdown(
            f"<p style='text-align:center;margin-top:0.8rem;font-size:0.85rem;'>"
            f"<a href='{admin_url}' target='_self'>Administração</a></p>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if entrar:
            try:
                user = auth.authenticate(usuario.strip(), senha)
            except AuthError as exc:
                st.error(exc.message)
                return
            except Exception as exc:
                st.error(f"Falha ao autenticar (banco indisponível?): {exc}")
                return
            token = create_access_token(user)
            _set_session(user, token)
            st.rerun()


def require_login() -> None:
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if st.session_state["autenticado"]:
        return
    if try_jwt_login():
        return
    render_login()
    st.stop()


def logout() -> None:
    _clear_cookie()
    for chave in [
        "autenticado",
        "usuario",
        "perfil",
        "filial",
        "nome_exibicao",
        "user_id",
        "access_token",
        "nav_group",
        "nav_item",
        "embed_mode",
    ]:
        st.session_state.pop(chave, None)
    st.rerun()


def admin_url_with_token() -> str:
    base = settings.admin_public_url.rstrip("/")
    token = st.session_state.get("access_token")
    if token:
        return f"{base}/visualizacao?token={quote(token)}"
    return f"{base}/visualizacao"
