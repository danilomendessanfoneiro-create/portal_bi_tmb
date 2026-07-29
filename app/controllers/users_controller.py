"""User administration CRUD (Administração > Usuários)."""

from __future__ import annotations

import math

import streamlit as st

from app.schemas import UserCreate, UserFilter, UserUpdate
from app.services import UserService, UserServiceError


def render_users() -> None:
    if st.session_state.get("perfil") != "admin":
        st.error("Acesso restrito a administradores.")
        return

    service = UserService()
    actor = st.session_state.get("usuario", "system")

    st.markdown('<p class="brand-title">Usuários</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="brand-sub">Administração · cada usuário representa uma filial</p>',
        unsafe_allow_html=True,
    )

    if "users_page" not in st.session_state:
        st.session_state["users_page"] = 1
    if "users_edit_id" not in st.session_state:
        st.session_state["users_edit_id"] = None
    if "users_show_disabled" not in st.session_state:
        st.session_state["users_show_disabled"] = False

    # ---- filters ----
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Pesquisa</div>', unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns([2.2, 1.2, 1.2, 1])
    with f1:
        search = st.text_input("Buscar", placeholder="Login, nome, filial ou código", key="users_search")
    with f2:
        profile = st.selectbox("Perfil", ["Todos", "admin", "filial"], key="users_profile_filter")
    with f3:
        sort_by = st.selectbox(
            "Ordenar por",
            ["login", "display_name", "branch", "profile", "created_on"],
            key="users_sort_by",
        )
    with f4:
        sort_dir = st.selectbox("Direção", ["asc", "desc"], key="users_sort_dir")

    c1, c2 = st.columns([1, 3])
    with c1:
        show_disabled = st.checkbox("Exibir desativados", key="users_show_disabled")
    with c2:
        page_size = st.selectbox("Por página", [5, 10, 20, 50], index=1, key="users_page_size")

    filters = UserFilter(
        search=search or None,
        profile=None if profile == "Todos" else profile,
        enabled=None if show_disabled else True,
        page=int(st.session_state["users_page"]),
        page_size=int(page_size),
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    try:
        users, total = service.list(filters)
    except Exception as exc:
        st.error(f"Erro ao listar usuários: {exc}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    total_pages = max(1, math.ceil(total / filters.page_size))
    if filters.page > total_pages:
        st.session_state["users_page"] = total_pages
        st.rerun()

    st.caption(f"{total} usuário(s) encontrado(s)")
    st.markdown("</div>", unsafe_allow_html=True)

    # ---- list ----
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Listagem</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">Inclusão, alteração e exclusão lógica (desativar)</div>',
        unsafe_allow_html=True,
    )

    if not users:
        st.info("Nenhum usuário encontrado.")
    else:
        header = st.columns([1.2, 1.6, 1.0, 1.8, 0.8, 1.4])
        header[0].markdown("**Login**")
        header[1].markdown("**Nome**")
        header[2].markdown("**Perfil**")
        header[3].markdown("**Filial**")
        header[4].markdown("**Status**")
        header[5].markdown("**Ações**")

        for u in users:
            cols = st.columns([1.2, 1.6, 1.0, 1.8, 0.8, 1.4])
            cols[0].write(u.login)
            cols[1].write(u.display_name or u.name or "-")
            cols[2].write(u.profile)
            cols[3].write(u.branch or "-")
            cols[4].write("Ativo" if u.enabled else "Inativo")
            b1, b2 = cols[5].columns(2)
            if b1.button("Editar", key=f"edit_{u.id}", use_container_width=True):
                st.session_state["users_edit_id"] = u.id
                st.rerun()
            if u.enabled:
                if b2.button("Desativar", key=f"del_{u.id}", use_container_width=True):
                    try:
                        service.soft_delete(u.id, actor)
                        st.success(f"Usuário {u.login} desativado.")
                        st.rerun()
                    except UserServiceError as exc:
                        st.error(str(exc))

    p1, p2, p3 = st.columns([1, 2, 1])
    with p1:
        if st.button("Anterior", disabled=filters.page <= 1, use_container_width=True):
            st.session_state["users_page"] = filters.page - 1
            st.rerun()
    with p2:
        st.markdown(
            f"<div style='text-align:center;padding-top:0.4rem;'>Página {filters.page} de {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with p3:
        if st.button("Próxima", disabled=filters.page >= total_pages, use_container_width=True):
            st.session_state["users_page"] = filters.page + 1
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ---- create / edit forms ----
    edit_id = st.session_state.get("users_edit_id")
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    if edit_id:
        st.markdown('<div class="section-title">Alterar usuário</div>', unsafe_allow_html=True)
        current = service.get(edit_id)
        if current is None:
            st.warning("Usuário não encontrado.")
            st.session_state["users_edit_id"] = None
        else:
            with st.form("form_edit_user"):
                login = st.text_input("Login", value=current.login)
                name = st.text_input("Nome", value=current.name or "")
                display_name = st.text_input("Nome de exibição", value=current.display_name or "")
                code = st.text_input("Código", value=current.code or "")
                profile = st.selectbox(
                    "Perfil",
                    ["admin", "filial"],
                    index=0 if current.profile == "admin" else 1,
                )
                branch = st.text_input("Filial", value=current.branch or "")
                password = st.text_input("Nova senha (opcional)", type="password")
                enabled = st.checkbox("Ativo", value=current.enabled)
                c_save, c_cancel = st.columns(2)
                save = c_save.form_submit_button("Salvar", use_container_width=True)
                cancel = c_cancel.form_submit_button("Cancelar", use_container_width=True)
            if cancel:
                st.session_state["users_edit_id"] = None
                st.rerun()
            if save:
                try:
                    service.update(
                        edit_id,
                        UserUpdate(
                            login=login,
                            password=password or None,
                            profile=profile,
                            branch=branch,
                            display_name=display_name,
                            name=name,
                            code=code,
                            enabled=enabled,
                        ),
                        actor,
                    )
                    st.session_state["users_edit_id"] = None
                    st.success("Usuário atualizado.")
                    st.rerun()
                except UserServiceError as exc:
                    st.error(str(exc))
    else:
        st.markdown('<div class="section-title">Incluir usuário</div>', unsafe_allow_html=True)
        with st.form("form_create_user"):
            login = st.text_input("Login")
            name = st.text_input("Nome")
            display_name = st.text_input("Nome de exibição")
            code = st.text_input("Código", help="Opcional; se vazio, usa o login")
            profile = st.selectbox("Perfil", ["filial", "admin"])
            branch = st.text_input("Filial", help="Obrigatório para perfil filial (igual à planilha)")
            password = st.text_input("Senha", type="password")
            enabled = st.checkbox("Ativo", value=True)
            create = st.form_submit_button("Incluir", use_container_width=True)
        if create:
            try:
                service.create(
                    UserCreate(
                        login=login,
                        password=password,
                        profile=profile,
                        branch=branch,
                        display_name=display_name or name,
                        name=name or display_name,
                        code=code or None,
                        enabled=enabled,
                    ),
                    actor,
                )
                st.success("Usuário incluído.")
                st.rerun()
            except UserServiceError as exc:
                st.error(str(exc))
    st.markdown("</div>", unsafe_allow_html=True)
