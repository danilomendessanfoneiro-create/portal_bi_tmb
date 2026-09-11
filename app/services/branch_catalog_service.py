"""Branch catalog for manual import validation (from prb_users)."""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from app.repositories.base import get_connection
from app.utils.password import hash_password

logger = logging.getLogger(__name__)

DEFAULT_FILIAL_PASSWORD = "tmb123"


@dataclass(frozen=True)
class EnsureFilialResult:
    branch: str
    login: str
    user_id: int
    created: bool


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

    @staticmethod
    def slug_from_branch(branch: str) -> str:
        text = unicodedata.normalize("NFKD", branch or "")
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.upper()
        text = re.sub(r"^TMB\s+", "", text.strip())
        text = re.sub(r"[^A-Za-z0-9]+", "", text.lower())
        return text or "filial"

    @staticmethod
    def display_from_branch(branch: str) -> str:
        raw = (branch or "").strip()
        if not raw:
            return "Filial"
        parts = raw.split()
        out: list[str] = []
        for i, part in enumerate(parts):
            if part.upper() == "TMB" and i == 0:
                out.append("TMB")
            elif len(part) <= 2 and part.endswith("."):
                out.append(part.upper())
            else:
                out.append(part[:1].upper() + part[1:].lower() if part else part)
        return " ".join(out)

    def ensure_filial_user(
        self,
        branch: str,
        *,
        actor: str,
        password: str = DEFAULT_FILIAL_PASSWORD,
    ) -> EnsureFilialResult:
        """Find or create enabled filial user for exact spreadsheet branch string."""
        branch_key = (branch or "").strip()
        if not branch_key:
            raise ValueError("Filial vazia não pode ser cadastrada automaticamente.")

        with get_connection() as conn:
            existing = conn.execute(
                """
                SELECT id, login, branch
                FROM prb_users
                WHERE enabled = TRUE
                  AND lower(profile) = 'filial'
                  AND TRIM(branch) = %s
                ORDER BY id
                LIMIT 1
                """,
                [branch_key],
            ).fetchone()
            if existing:
                return EnsureFilialResult(
                    branch=branch_key,
                    login=str(existing["login"]),
                    user_id=int(existing["id"]),
                    created=False,
                )

            base_login = self.slug_from_branch(branch_key)
            login = base_login
            for attempt in range(0, 50):
                candidate = base_login if attempt == 0 else f"{base_login}{attempt}"
                taken = conn.execute(
                    "SELECT 1 FROM prb_users WHERE lower(login) = %s LIMIT 1",
                    [candidate.lower()],
                ).fetchone()
                if not taken:
                    login = candidate
                    break
            else:
                raise ValueError(
                    f"Não foi possível gerar login único para a filial ({branch_key})."
                )

            display = self.display_from_branch(branch_key)
            pwd_hash = hash_password(password)
            row = conn.execute(
                """
                INSERT INTO prb_users (
                    login, password_hash, profile, branch, display_name, name, code,
                    created_by, created_on, modified_by, modified_on, enabled
                ) VALUES (
                    %s, %s, 'filial', %s, %s, %s, %s,
                    %s, NOW(), %s, NOW(), TRUE
                )
                RETURNING id, login, branch
                """,
                [login, pwd_hash, branch_key, display, display, login, actor, actor],
            ).fetchone()

        logger.info(
            "Filial auto-criada branch=%s login=%s user_id=%s actor=%s",
            branch_key,
            login,
            int(row["id"]),
            actor,
        )
        return EnsureFilialResult(
            branch=branch_key,
            login=str(row["login"]),
            user_id=int(row["id"]),
            created=True,
        )
