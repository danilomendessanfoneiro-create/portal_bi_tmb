"""Tests for branch catalog and manual import validation helpers."""

from __future__ import annotations

import pandas as pd

from app.services.branch_catalog_service import BranchCatalogService
from app.services.manual_import_service import MAX_FILE_BYTES, MAX_ROWS, ManualImportError, ManualImportService


def test_branch_suggest_message():
    assert "Usuários" in BranchCatalogService.SUGGEST_MESSAGE


def test_is_known_branch():
    svc = BranchCatalogService()
    known = {"TMB BETIM", "TMB MATRIZ"}
    assert svc.is_known_branch("TMB BETIM", known) is True
    assert svc.is_known_branch("  TMB BETIM  ", known) is True
    assert svc.is_known_branch("OUTRA", known) is False
    assert svc.is_known_branch("", known) is False
    assert svc.is_known_branch(None, known) is False


def test_upload_rejects_bad_extension():
    svc = ManualImportService()
    try:
        svc.upload(filename="x.pdf", content=b"abc", mtime=None, actor="admin")
        assert False, "should raise"
    except ManualImportError as exc:
        assert "Formato" in str(exc)


def test_upload_rejects_empty():
    svc = ManualImportService()
    try:
        svc.upload(filename="x.csv", content=b"", mtime=None, actor="admin")
        assert False, "should raise"
    except ManualImportError as exc:
        assert "vazio" in str(exc).lower()


def test_limits_constants():
    assert MAX_FILE_BYTES == 20 * 1024 * 1024
    assert MAX_ROWS == 100_000


def test_structure_requires_key_columns():
    svc = ManualImportService()
    df = pd.DataFrame([{"Nota Fiscal": "1"}])
    issues = svc.assert_spreadsheet_structure(df)
    assert any("obrigatórias" in i for i in issues)


def test_structure_detects_duplicate_columns():
    svc = ManualImportService()
    df = pd.DataFrame([["1", "2", "A"]], columns=["Nro. Entrega", "Nro. Entrega", "Sigla Unidade Entrega"])
    # pandas may auto-rename duplicates — force identical labels for the check
    df.columns = ["Nro. Entrega", "Nro. Entrega", "Sigla Unidade Entrega"]
    issues = svc.assert_spreadsheet_structure(df)
    assert any("duplicadas" in i for i in issues)


def test_structure_allows_extra_operational_columns():
    svc = ManualImportService()
    df = pd.DataFrame(
        [
            {
                "Nro. Entrega": "1",
                "Sigla Unidade Entrega": "TMB BETIM",
                "Nome Pessoa Visita": "Cliente X",
                "Nro. Pedido": "P1",
            }
        ]
    )
    assert svc.assert_spreadsheet_structure(df) == []


def test_start_import_wait_runs_job_inline():
    svc = ManualImportService()
    seen: list[dict] = []

    class FakeRepo:
        def get_batch(self, batch_id):
            return {"id": batch_id, "status": "validated_ok", "file_path": ""}

        def update_batch(self, batch_id, fields, *, actor):
            return {"id": batch_id, "status": fields.get("status", "importing")}

    svc._imports = FakeRepo()
    svc._run_import_job = lambda **kw: seen.append(kw)
    svc.start_import(33, actor="auto", wait=True)
    assert seen == [{"batch_id": 33, "actor": "auto"}]
