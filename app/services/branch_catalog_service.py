"""Branch catalog for manual import validation (from prb_users)."""

from __future__ import annotations

from app.repositories.base import get_connection


class BranchCatalogService:
    """Filiais válidas = branch distintas de usuários perfil filial enabled."""

    SUGGEST_MESSAGE = (
        "Cadastre a filial em Administração → Usuários "
        "(perfil Filial e campo Filial preenchido)."
    )

    def list_enabled_filial_branches(self) -> set[str]:
        sql = """
            SELECT DISTINCT TRIM(branch) AS branch
            FROM prb_users
            WHERE enabled = TRUE
              AND lower(profile) = 'filial'
              AND branch IS NOT NULL
              AND TRIM(branch) <> ''
        """
        with get_connection() as conn:
            rows = conn.execute(sql).fetchall()
        return {str(r["branch"]).strip() for r in rows if r.get("branch")}

    def is_known_branch(self, branch: str | None, known: set[str] | None = None) -> bool:
        if branch is None or not str(branch).strip():
            return False
        catalog = known if known is not None else self.list_enabled_filial_branches()
        return str(branch).strip() in catalog
