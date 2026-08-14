"""Orquestração da coleta TMS Elite → upload manual."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.integrations.tmselite_rpa.exceptions import TmsRpaError
from app.services.job_schedule_service import AUTOMATION_TMS_SPREADSHEET
from app.services.manual_import_service import ManualImportError
from app.services.tms_spreadsheet_fetch_service import (
    TmsSpreadsheetFetchError,
    TmsSpreadsheetFetchService,
)
from worker.registry import get, load_builtin_jobs


class _Sched:
    tms_login_url = "https://tmblogistica.tmselite.com/login"
    tms_username = "DANILO"


class FakeSchedules:
    def __init__(self, *, sched=_Sched(), password: str | None = "secret"):
        self._sched = sched
        self._password = password

    def get(self, job_id: str):
        assert job_id == AUTOMATION_TMS_SPREADSHEET
        return self._sched

    def get_tms_password(self, job_id: str = AUTOMATION_TMS_SPREADSHEET):
        return self._password


def _download(**kwargs):
    return SimpleNamespace(
        file_name="entregas_relatorio-00360-abc.csv",
        content=b"nro_entrega;filial\n1;TMB VIANA\n",
        sha256="abc",
        size_bytes=32,
    )


class FakeImports:
    def __init__(self, *, validate_status="validated_ok", import_status="imported"):
        self.validate_status = validate_status
        self.import_status = import_status
        self.started = False
        self.calls: list[str] = []

    def upload(self, **kwargs):
        self.calls.append("upload")
        assert kwargs["filename"].endswith(".csv")
        assert kwargs["content"]
        return {"id": 11, "total_rows": 1, "status": "uploaded"}

    def validate(self, batch_id, *, actor):
        self.calls.append("validate")
        return {
            "id": batch_id,
            "status": self.validate_status,
            "valid_rows": 1 if self.validate_status == "validated_ok" else 0,
            "error_rows": 0 if self.validate_status == "validated_ok" else 1,
            "error_message": None if self.validate_status == "validated_ok" else "filial inválida",
        }

    def start_import(self, batch_id, *, actor, wait=False):
        self.calls.append("start_import")
        self.actor = actor
        self.wait = wait
        self.started = True
        return {"id": batch_id, "status": "importing"}

    def get_batch(self, batch_id):
        status = self.import_status if self.started else "uploaded"
        return {
            "id": batch_id,
            "status": status,
            "rows_inserted": 1,
            "rows_updated": 0,
        }


def test_job_is_registered():
    load_builtin_jobs()
    spec = get(AUTOMATION_TMS_SPREADSHEET)
    assert spec is not None
    assert "planilha" in spec.description.lower() or "TMS" in spec.description


def test_missing_password():
    svc = TmsSpreadsheetFetchService(
        schedules=FakeSchedules(password=None),
        imports=FakeImports(),
        downloader=_download,
    )
    with pytest.raises(TmsSpreadsheetFetchError) as exc:
        svc.run()
    assert exc.value.step == "config"


def test_dry_run_skips_import():
    imports = FakeImports()
    svc = TmsSpreadsheetFetchService(
        schedules=FakeSchedules(),
        imports=imports,
        downloader=_download,
    )
    metrics = svc.run(dry_run=True)
    assert metrics["file_name"].endswith(".csv")
    assert imports.calls == []


def test_validate_error_does_not_import():
    imports = FakeImports(validate_status="validated_error")
    svc = TmsSpreadsheetFetchService(
        schedules=FakeSchedules(),
        imports=imports,
        downloader=_download,
    )
    with pytest.raises(TmsSpreadsheetFetchError) as exc:
        svc.run()
    assert exc.value.step == "validate"
    assert "start_import" not in imports.calls


def test_happy_path_reuses_manual_import():
    imports = FakeImports()
    svc = TmsSpreadsheetFetchService(
        schedules=FakeSchedules(),
        imports=imports,
        downloader=_download,
    )
    metrics = svc.run()
    assert imports.calls == ["upload", "validate", "start_import"]
    assert imports.actor == "auto"
    assert imports.wait is True
    assert metrics["batch_id"] == 11
    assert metrics["import_status"] == "imported"


def test_rpa_error_maps_step():
    def boom(**kwargs):
        raise TmsRpaError("Login recusado", step="login")

    svc = TmsSpreadsheetFetchService(
        schedules=FakeSchedules(),
        imports=FakeImports(),
        downloader=boom,
    )
    with pytest.raises(TmsSpreadsheetFetchError) as exc:
        svc.run()
    assert exc.value.step == "login"


def test_manual_import_error_becomes_fetch_error():
    class Boom(FakeImports):
        def upload(self, **kwargs):
            raise ManualImportError("Arquivo vazio.")

    svc = TmsSpreadsheetFetchService(
        schedules=FakeSchedules(),
        imports=Boom(),
        downloader=_download,
    )
    with pytest.raises(TmsSpreadsheetFetchError) as exc:
        svc.run()
    assert exc.value.step == "import"


def test_fetch_job_if_due_skips_without_download(monkeypatch):
    from datetime import date

    from worker.jobs import fetch_tmselite_spreadsheet as job
    from worker.runtime import JobContext

    class FakeSched:
        def is_due(self, job_id, *, now=None):
            assert job_id == AUTOMATION_TMS_SPREADSHEET
            return False

    monkeypatch.setattr(job, "JobScheduleService", FakeSched)

    def boom(**kwargs):
        raise AssertionError("não deve coletar")

    monkeypatch.setattr(
        "app.services.tms_spreadsheet_fetch_service.TmsSpreadsheetFetchService.run",
        boom,
    )
    ctx = JobContext(
        job_id=AUTOMATION_TMS_SPREADSHEET,
        business_date=date(2026, 8, 16),
        if_due=True,
        dry_run=True,
    )
    result = job.run(ctx)
    assert result.status == "skipped"
    assert result.metrics.get("if_due") is True

