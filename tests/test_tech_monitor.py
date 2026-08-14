"""Monitoramento técnico das automações visíveis."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from worker.idempotency import complete_run
from worker.runtime import JobResult

from app.services.tech_monitor_service import build_monitor_email, notify_visible_robot_run


def test_monitor_email_success_and_failure_copy(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    subject, body = build_monitor_email(
        job_id="fetch_tmselite_spreadsheet",
        status="success",
        business_date=date(2026, 8, 14),
        started_on=datetime(2026, 8, 14, 5, 0),
        finished_on=datetime(2026, 8, 14, 5, 3),
        duration_ms=192000,
        metrics={
            "total_rows": 15420,
            "rows_inserted": 10,
            "rows_updated": 5,
            "batch_id": 34,
            "file_name": "entregas.csv",
            "valid_rows": 15420,
            "import_status": "imported",
        },
        message="Importado lote #34 (15420 linhas).",
        run_id=32,
    )
    assert subject == "Portal BI [LOCAL] – Relatório de Execução das Automações – 14/08/2026"
    assert "Ambiente: local" in body
    assert "Importação de pedidos" in body
    assert "Identificador: fetch_tmselite_spreadsheet" in body
    assert "Status: SUCESSO" in body
    assert "Resultado: Importado lote #34 (15420 linhas)." in body
    assert "Run ID: 32" in body
    assert "Lote: 34" in body
    assert "Arquivo: entregas.csv" in body
    assert "Registros processados: 15420" in body
    assert "Execução geral:" in body
    assert "ATENÇÃO – EXISTEM FALHAS" not in body
    assert "Atenciosamente," in body

    monkeypatch.setenv("APP_ENV", "produção")
    fail_subject, fail = build_monitor_email(
        job_id="report_client_daily",
        status="failed",
        business_date=date(2026, 8, 14),
        started_on=datetime(2026, 8, 14, 8, 0),
        finished_on=datetime(2026, 8, 14, 8, 1),
        duration_ms=63000,
        metrics={
            "step": "smtp",
            "sent": 0,
            "errors": [{"error": "timeout no host smtp.gmail.com"}],
        },
        message="Falha na conexão SMTP.",
        error_step="smtp",
        run_id=99,
    )
    assert fail_subject.startswith("Portal BI [PRODUÇÃO] – FALHA –")
    assert "Ambiente: produção" in fail
    assert "Status: FALHA" in fail
    assert "ATENÇÃO – EXISTEM FALHAS" in fail
    assert "MOTIVO DA FALHA" in fail
    assert "Etapa: smtp" in fail
    assert "Motivo: Falha na conexão SMTP." in fail
    assert "timeout no host smtp.gmail.com" in fail
    assert "Necessidade de reprocessamento: sim" in fail


def test_notify_skips_hidden_and_skipped_jobs(monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.services.tech_monitor_service.send_tech_email",
        lambda *a, **k: called.append(a),
    )
    notify_visible_robot_run(
        job_id="import_deliveries_daily",
        status="success",
        business_date=date(2026, 8, 14),
    )
    notify_visible_robot_run(
        job_id="fetch_tmselite_spreadsheet",
        status="skipped",
        business_date=date(2026, 8, 14),
    )
    assert called == []
    notify_visible_robot_run(
        job_id="report_branch_daily",
        status="success",
        business_date=date(2026, 8, 14),
        duration_ms=1000,
        metrics={"sent": 25},
    )
    assert len(called) == 1
    assert "Relatório das Filiais" in called[0][1]


def test_complete_run_skipped_does_not_notify(monkeypatch):
    monkeypatch.setattr(
        "app.services.tech_monitor_service.notify_visible_robot_run",
        lambda **k: (_ for _ in ()).throw(AssertionError("não deve notificar")),
    )
    result = complete_run(None, JobResult(status="skipped", message="fora da janela"))
    assert result.status == "skipped"


def test_complete_run_notifies_after_finish(monkeypatch):
    captured = {}

    class FakeRepo:
        def finish(self, run_id, **kwargs):
            return {
                "id": run_id,
                "job_id": "report_managerial",
                "business_date": date(2026, 8, 14),
                "started_on": datetime(2026, 8, 14, 8, 0, tzinfo=ZoneInfo("America/Sao_Paulo")),
                "finished_on": datetime(2026, 8, 14, 8, 4, tzinfo=ZoneInfo("America/Sao_Paulo")),
                "duration_ms": 251000,
                "error_step": None,
                "status": kwargs["status"],
            }

    def fake_notify(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("app.services.tech_monitor_service.notify_visible_robot_run", fake_notify)
    result = complete_run(
        99,
        JobResult(status="success", message="ok", metrics={"sent": 3}),
        repo=FakeRepo(),  # type: ignore[arg-type]
    )
    assert result.status == "success"
    assert captured["job_id"] == "report_managerial"
    assert captured["metrics"]["sent"] == 3
    assert captured["run_id"] == 99
