"""Worker report job and schedule unit tests."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from app.repositories.job_schedule_repository import JobSchedule
from app.services.job_schedule_service import JobScheduleService
from app.utils.report_emails import validate_report_emails
from worker.adapters.report_html import build_report_html, build_report_subject
from worker.jobs.report_overdue_daily_impl import _filter_branch, _write_csv
from worker.runtime import parse_business_date


def test_parse_business_date_default():
    d = parse_business_date(None)
    assert isinstance(d, date)


def test_write_csv_columns(tmp_path):
    df = pd.DataFrame(
        {
            "nro_entrega": ["1"],
            "nota_fiscal": ["NF1"],
            "cliente": ["C"],
            "filial": ["SPO"],
            "prazo_considerado": [pd.Timestamp("2026-07-01")],
            "data_referencia": ["2026-07-28"],
            "dias_atraso": [27],
            "status": ["Aberto"],
            "motorista": ["M"],
            "cidade_entrega": ["SP"],
            "uf_entrega": ["SP"],
            "valor_total": [10.0],
            "motivo_atraso": [""],
        }
    )
    out = tmp_path / "atrasos_consolidado.csv"
    n = _write_csv(df, out)
    assert n == 1
    assert out.exists()
    text = out.read_text(encoding="utf-8-sig")
    assert "codigo_entrega" in text
    assert "filial" in text


def test_schedule_is_due_after_configured_time():
    class FakeRepo:
        def get_by_job_id(self, job_id: str):
            return JobSchedule(
                id=1,
                job_id=job_id,
                local_time="07:00",
                timezone="America/Sao_Paulo",
                enabled=True,
                frequency="daily",
            )

    svc = JobScheduleService(repo=FakeRepo())  # type: ignore[arg-type]
    tz = ZoneInfo("America/Sao_Paulo")
    assert svc.is_due("report_branch_daily", now=datetime(2026, 7, 28, 7, 0, tzinfo=tz))
    assert not svc.is_due("report_branch_daily", now=datetime(2026, 7, 28, 6, 59, tzinfo=tz))


def test_schedule_weekly_weekday():
    class FakeRepo:
        def get_by_job_id(self, job_id: str):
            return JobSchedule(
                id=1,
                job_id=job_id,
                local_time="07:00",
                timezone="America/Sao_Paulo",
                enabled=True,
                frequency="weekly",
                weekday=2,  # Terça (PRD: Dom=0)
            )

    svc = JobScheduleService(repo=FakeRepo())  # type: ignore[arg-type]
    tz = ZoneInfo("America/Sao_Paulo")
    # 2026-07-28 is Tuesday
    assert svc.is_due("report_managerial", now=datetime(2026, 7, 28, 8, 0, tzinfo=tz))
    assert not svc.is_due("report_managerial", now=datetime(2026, 7, 29, 8, 0, tzinfo=tz))


def test_validate_report_emails():
    assert validate_report_emails(" a@b.com ; c@d.com ") == ["a@b.com", "c@d.com"]
    try:
        validate_report_emails("a@b.com;bad")
        assert False, "expected error"
    except ValueError as exc:
        assert "inválido" in str(exc).lower() or "invalid" in str(exc).lower() or "E-mail" in str(exc)


def test_filter_branch_segregation():
    df = pd.DataFrame({"filial": ["SPO", "CWB"], "nota_fiscal": ["1", "2"]})
    spo = _filter_branch(df, "SPO")
    assert list(spo["nota_fiscal"]) == ["1"]


def test_build_report_html_empty_nat_nan():
    df = pd.DataFrame(
        {
            "nota_fiscal": ["NF1"],
            "cliente": ["C"],
            "cidade_entrega": ["SP"],
            "dt_agendamento": [pd.NaT],
            "motorista": [float("nan")],
            "dias_atraso": [5],
        }
    )
    html = build_report_html(audience_name="SPO", overdue=df, due_today=pd.DataFrame())
    assert "NaT" not in html
    assert "nan" not in html.lower()


def test_build_report_html_columns():
    df = pd.DataFrame(
        {
            "nota_fiscal": ["NF1"],
            "cliente": ["C"],
            "cidade_entrega": ["SP"],
            "dt_agendamento": [pd.Timestamp("2026-07-20")],
            "motorista": ["João"],
            "dias_atraso": [5],
            "valor_total": [99.9],
        }
    )
    html = build_report_html(audience_name="SPO", overdue=df, due_today=pd.DataFrame())
    assert "Valor (R$)" not in html
    assert "Dt. Agendamento" in html
    assert "Ult. Motorista" in html
    assert "20/07/2026" in html
    assert "João" in html
    assert "99,90" not in html


def test_build_report_html_empty_and_subject():
    html = build_report_html(
        audience_name="SPO",
        overdue=pd.DataFrame(),
        due_today=pd.DataFrame(),
    )
    assert "Nenhuma nota fiscal nesta situação." in html
    assert "Olá, bom dia!" in html
    assert "SPO" in html
    assert "canhotos" in html
    assert "até as 16h00" not in html
    assert build_report_subject("Maria") == "Relatório de Entregas - Maria"
