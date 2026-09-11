"""US-002/US-003: ensure_filial_user + validate auto-create."""

from __future__ import annotations

import uuid

from app.repositories.base import get_connection
from app.repositories.import_repository import ImportRepository
from app.services.branch_catalog_service import BranchCatalogService
from app.services.manual_import_service import ManualImportService


def _unique_branch(prefix: str = "TMB AUTOTEST") -> str:
    return f"{prefix} {uuid.uuid4().hex[:8].upper()}"


def test_ensure_filial_creates_once_and_is_idempotent():
    svc = BranchCatalogService()
    branch = _unique_branch()
    first = svc.ensure_filial_user(branch, actor="test_ensure")
    assert first.created is True
    assert first.branch == branch
    assert first.login
    assert first.user_id > 0

    second = svc.ensure_filial_user(branch, actor="test_ensure")
    assert second.created is False
    assert second.user_id == first.user_id
    assert second.login == first.login

    assert svc.is_known_branch(branch) is True


def test_ensure_filial_slug_collision_gets_suffix():
    svc = BranchCatalogService()
    base = f"TMB COLLIDE{uuid.uuid4().hex[:6].upper()}"
    first = svc.ensure_filial_user(base, actor="test_ensure")
    # force another branch that would prefer the same slug by using nearly same text
    # after first is created, second different branch with same slug base needs suffix
    # Create user with same intended slug via a branch that normalizes similarly:
    # e.g. first already took slug; insert a disabled-like situation by ensuring
    # a second brand-new branch whose slug equals first.login — use ensure with
    # a branch that slugifies to the same string by duplicating punctuation variants.
    alt = base.replace(" ", "  ")  # same slug after normalize
    # same branch key after strip — would be idempotent; use a sibling with dots
    sibling = base + "."
    # If slug of sibling equals first.login, ensure must pick suffix
    slug = BranchCatalogService.slug_from_branch(sibling)
    if slug == first.login:
        other = svc.ensure_filial_user(sibling.strip("."), actor="test_ensure")
        # sibling.strip('.') == base → idempotent path
        assert other.user_id == first.user_id
    # Explicit: create with login already taken by inserting ensure for unique branch
    # whose slug we pre-occupy — covered by ensure loop when login taken:
    occupied = f"occ{uuid.uuid4().hex[:8]}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO prb_users (
                login, password_hash, profile, branch, display_name, name, code,
                created_by, created_on, modified_by, modified_on, enabled
            ) VALUES (
                %s, 'x', 'filial', %s, %s, %s, %s,
                'test_ensure', NOW(), 'test_ensure', NOW(), TRUE
            )
            """,
            [occupied, f"TMB OCC {occupied}", occupied, occupied, occupied],
        )
    # Branch that slugifies to occupied — craft by using branch text without TMB
    crafted = occupied.upper()
    result = svc.ensure_filial_user(f"TMB {crafted}", actor="test_ensure")
    assert result.created is True
    assert result.login != occupied
    assert result.login.startswith(occupied) or occupied in result.login or result.login.startswith(
        BranchCatalogService.slug_from_branch(f"TMB {crafted}")
    )


def test_validate_auto_creates_unknown_branch_and_audits():
    branch = _unique_branch("TMB VALAUTO")
    # staging via replace_items on a fresh batch
    repo = ImportRepository()
    batch = repo.create_batch(
        file_name="val_auto.csv",
        file_ext=".csv",
        file_size_bytes=1,
        file_path="",
        file_mtime=None,
        actor="test_val_auto",
    )
    batch_id = int(batch["id"])
    nro = f"9{uuid.uuid4().hex[:8]}"
    repo.replace_items(
        batch_id,
        [
            {
                "row_number": 1,
                "remessa_numero": nro,
                "nro_entrega": nro,
                "nota_fiscal": "1",
                "cliente": "Cliente Teste",
                "cliente_conta": None,
                "cnpj_cliente": None,
                "filial": branch,
                "cidade_entrega": None,
                "uf_entrega": None,
                "status_entrega": None,
                "valor_total": None,
                "qtde_volumes": None,
                "dt_prazo_atual": None,
                "dt_agendamento": None,
                "dt_entrega": None,
                "dt_recebimento": None,
                "dt_cancelamento": None,
                "motivo_cancelamento": None,
                "motivo_atraso": None,
                "nome_recebedor": None,
                "dt_cadastro": None,
                "motorista": None,
                "remetente": None,
                "cidade_remetente": None,
                "uf_remetente": None,
                "peso_taxado": None,
                "peso_informado": None,
                "payload": {},
                "is_valid": None,
                "error_message": None,
            }
        ],
        actor="test_val_auto",
    )

    updated = ManualImportService().validate(batch_id, actor="test_val_auto")
    assert updated["status"] == "validated_ok", updated.get("error_message")
    assert updated["error_rows"] == 0

    autos = repo.list_auto_branches(batch_id)
    assert len(autos) == 1
    assert autos[0]["branch"] == branch

    # segunda validação do mesmo lote não deve duplicar (clear + recreate only if created again)
    # branch already exists → no new audit on re-validate after clear
    updated2 = ManualImportService().validate(batch_id, actor="test_val_auto")
    assert updated2["status"] == "validated_ok"
    autos2 = repo.list_auto_branches(batch_id)
    assert autos2 == []  # already known → não recria → sem auditoria neste validate
