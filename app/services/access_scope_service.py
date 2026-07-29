"""Business rules for dashboard data visibility by user profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class ViewerContext:
    profile: str
    branch: Optional[str]
    login: str

    @property
    def is_admin(self) -> bool:
        return (self.profile or "").lower() == "admin"

    @property
    def is_filial(self) -> bool:
        return (self.profile or "").lower() == "filial"


class AccessScopeError(Exception):
    pass


class AccessScopeService:
    """Enforce filial scope in the service layer (not only in the UI)."""

    def from_session(self, *, profile: str, branch: Optional[str], login: str) -> ViewerContext:
        ctx = ViewerContext(profile=(profile or "").strip().lower(), branch=(branch or "").strip() or None, login=login)
        if ctx.is_filial and not ctx.branch:
            raise AccessScopeError("Usuário filial sem filial vinculada.")
        return ctx

    def apply_dataframe_scope(self, df: pd.DataFrame, viewer: ViewerContext) -> pd.DataFrame:
        if viewer.is_admin:
            return df
        if not viewer.is_filial:
            raise AccessScopeError("Perfil sem permissão de visualização.")
        branch = viewer.branch or ""
        return df[df["filial"].astype(str) == branch].copy()

    def resolve_branch_filter(
        self,
        viewer: ViewerContext,
        requested_branches: Optional[list] = None,
    ) -> list:
        """
        Admin: returns requested selection (or empty = all).
        Filial: always forces own branch; ignores client requests.
        """
        if viewer.is_admin:
            return list(requested_branches or [])
        if viewer.is_filial:
            return [viewer.branch] if viewer.branch else []
        raise AccessScopeError("Perfil sem permissão de visualização.")
