"""Worker report job and schedule unit tests."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from app.repositories.job_schedule_repository import JobSchedule
from app.services.job_schedule_service import JobScheduleError, JobScheduleService
from app.utils.report_emails import validate_report_emails
from worker.adapters.report_html import build_report_html, build_report_subject
from worker.jobs.report_overdue_daily_impl import _filter_branch, _filter_cnpj, _write_csv
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
    assert svc.is_due("report_branch_daily", now=datetime(2026, 7, 28, 8, 0, tzinfo=tz))
    assert not svc.is_due("report_branch_daily", now=datetime(2026, 7, 28, 8, 1, tzinfo=tz))
    assert not svc.is_due("report_branch_daily", now=datetime(2026, 7, 28, 17, 45, tzinfo=tz))


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


def test_tms_schedule_rejects_credentials_on_other_jobs():
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

        def update(self, *args, **kwargs):
            raise AssertionError("não deve gravar")

    svc = JobScheduleService(repo=FakeRepo())  # type: ignore[arg-type]
    try:
        svc.update("report_branch_daily", tms_username="DANILO", actor="admin")
        assert False, "expected error"
    except JobScheduleError as exc:
        assert "TMS" in str(exc)


def test_tms_schedule_requires_password_when_enabling():
    class FakeRepo:
        def get_by_job_id(self, job_id: str):
            return JobSchedule(
                id=9,
                job_id=job_id,
                local_time="05:00",
                timezone="America/Sao_Paulo",
                enabled=False,
                frequency="daily",
                tms_login_url="https://tmblogistica.tmselite.com/login",
                tms_username="DANILO",
            )

        def update(self, *args, **kwargs):
            raise AssertionError("não deve gravar")

    svc = JobScheduleService(repo=FakeRepo())  # type: ignore[arg-type]
    try:
        svc.update("fetch_tmselite_spreadsheet", enabled=True, actor="admin")
        assert False, "expected error"
    except JobScheduleError as exc:
        assert "Senha" in str(exc)


def test_tms_schedule_encrypts_password():
    captured: dict = {}

    class FakeRepo:
        def get_by_job_id(self, job_id: str):
            return JobSchedule(
                id=9,
                job_id=job_id,
                local_time="05:00",
                timezone="America/Sao_Paulo",
                enabled=False,
                frequency="daily",
                tms_login_url="https://tmblogistica.tmselite.com/login",
                tms_username="DANILO",
            )

        def update(self, job_id, **kwargs):
            captured.update(kwargs)
            return JobSchedule(
                id=9,
                job_id=job_id,
                local_time=kwargs.get("local_time") or "05:00",
                timezone="America/Sao_Paulo",
                enabled=True,
                frequency="daily",
                tms_login_url="https://tmblogistica.tmselite.com/login",
                tms_username="DANILO",
                tms_password_encrypted=kwargs.get("tms_password_encrypted"),
            )

    svc = JobScheduleService(repo=FakeRepo())  # type: ignore[arg-type]
    updated = svc.update(
        "fetch_tmselite_spreadsheet",
        enabled=True,
        tms_password="secret-test",
        actor="admin",
    )
    assert updated.enabled
    enc = captured.get("tms_password_encrypted") or ""
    assert enc.startswith("enc:v1:")
    assert "secret-test" not in enc


def test_schedule_is_due_respects_run_weekdays_and_enabled():
    class FakeRepo:
        def get_by_job_id(self, job_id: str):
            return JobSchedule(
                id=1,
                job_id=job_id,
                local_time="08:00",
                timezone="America/Sao_Paulo",
                enabled=True,
                frequency="daily",
                run_weekdays=[1, 2, 3, 4, 5, 6],
            )

    svc = JobScheduleService(repo=FakeRepo())  # type: ignore[arg-type]
    tz = ZoneInfo("America/Sao_Paulo")
    # terça 28/07/2026
    assert svc.is_due("report_branch_daily", now=datetime(2026, 7, 28, 8, 0, tzinfo=tz))
    # domingo 16/08/2026
    assert not svc.is_due("report_branch_daily", now=datetime(2026, 8, 16, 8, 0, tzinfo=tz))

    class Disabled:
        def get_by_job_id(self, job_id: str):
            return JobSchedule(
                id=1,
                job_id=job_id,
                local_time="08:00",
                timezone="America/Sao_Paulo",
                enabled=False,
                frequency="daily",
                run_weekdays=[1, 2, 3, 4, 5, 6],
            )

    off = JobScheduleService(repo=Disabled())  # type: ignore[arg-type]
    assert not off.is_due("fetch_tmselite_spreadsheet", now=datetime(2026, 7, 28, 8, 0, tzinfo=tz))
    assert not off.is_due("report_client_daily", now=datetime(2026, 7, 28, 8, 0, tzinfo=tz))
    assert not off.is_due("report_managerial", now=datetime(2026, 7, 28, 8, 0, tzinfo=tz))


def test_update_rejects_empty_run_weekdays():
    class FakeRepo:
        def get_by_job_id(self, job_id: str):
            return JobSchedule(
                id=1,
                job_id=job_id,
                local_time="08:00",
                timezone="America/Sao_Paulo",
                enabled=False,
                frequency="daily",
                run_weekdays=[1, 2, 3, 4, 5, 6],
            )

        def update(self, *args, **kwargs):
            raise AssertionError("não deve gravar")

    svc = JobScheduleService(repo=FakeRepo())  # type: ignore[arg-type]
    try:
        svc.update("report_branch_daily", run_weekdays=[], actor="admin")
        assert False, "expected error"
    except JobScheduleError as exc:
        assert "dia" in str(exc).lower()


def test_list_shows_api_jobs_disabled_path():
    from app.services.job_schedule_service import API_AUTOMATIONS, HIDDEN_API_AUTOMATIONS

    class FakeRepo:
        def list_all(self):
            ids = [
                "fetch_tmselite_spreadsheet",
                "report_branch_daily",
                "report_client_daily",
                "report_managerial",
                "import_deliveries_daily",
                "import_deliveries_initial",
                "import_deliveries",
            ]
            return [
                JobSchedule(
                    id=i,
                    job_id=jid,
                    local_time="08:00",
                    timezone="America/Sao_Paulo",
                    enabled=False,
                )
                for i, jid in enumerate(ids, start=1)
            ]

    listed = JobScheduleService(repo=FakeRepo()).list()  # type: ignore[arg-type]
    ids = [s.job_id for s in listed]
    assert ids[0] == "fetch_tmselite_spreadsheet"
    assert "import_deliveries_daily" in ids
    assert "import_deliveries_initial" in ids
    assert "import_deliveries" not in ids
    assert set(API_AUTOMATIONS).issubset(set(ids))
    assert set(ids).isdisjoint(HIDDEN_API_AUTOMATIONS)


def test_api_job_cannot_be_enabled():
    from app.services.job_schedule_service import JobScheduleError

    class FakeRepo:
        def get_by_job_id(self, job_id: str):
            return JobSchedule(
                id=1,
                job_id=job_id,
                local_time="07:00",
                timezone="America/Sao_Paulo",
                enabled=False,
                frequency="daily",
                run_weekdays=[1, 2, 3, 4, 5, 6],
            )

        def update(self, *args, **kwargs):
            raise AssertionError("não deve gravar se tentou ativar")

    svc = JobScheduleService(repo=FakeRepo())  # type: ignore[arg-type]
    try:
        svc.update("import_deliveries_daily", enabled=True, actor="admin")
        assert False, "expected error"
    except JobScheduleError as exc:
        assert "desabilitado" in str(exc).lower()


def test_visible_robots_if_due_skip_sunday_disabled_and_before_time():
    from app.services.job_schedule_service import VISIBLE_AUTOMATIONS

    tz = ZoneInfo("America/Sao_Paulo")
    sunday = datetime(2026, 8, 16, 9, 0, tzinfo=tz)
    tuesday_early = datetime(2026, 7, 28, 4, 59, tzinfo=tz)
    tuesday_ok = datetime(2026, 7, 28, 5, 30, tzinfo=tz)
    tuesday_after_grace = datetime(2026, 7, 28, 6, 1, tzinfo=tz)

    class Repo:
        def __init__(self, *, enabled=True, days=None, time="05:00"):
            self.enabled = enabled
            self.days = days if days is not None else [1, 2, 3, 4, 5, 6]
            self.time = time

        def get_by_job_id(self, job_id: str):
            return JobSchedule(
                id=1,
                job_id=job_id,
                local_time=self.time,
                timezone="America/Sao_Paulo",
                enabled=self.enabled,
                frequency="daily",
                run_weekdays=self.days,
            )

    for job_id in VISIBLE_AUTOMATIONS:
        assert not JobScheduleService(repo=Repo()).is_due(job_id, now=sunday)  # type: ignore[arg-type]
        assert not JobScheduleService(repo=Repo(enabled=False)).is_due(job_id, now=tuesday_ok)  # type: ignore[arg-type]
        assert not JobScheduleService(repo=Repo(time="05:00")).is_due(job_id, now=tuesday_early)  # type: ignore[arg-type]
        assert JobScheduleService(repo=Repo(time="05:00")).is_due(job_id, now=tuesday_ok)  # type: ignore[arg-type]
        assert not JobScheduleService(repo=Repo(time="05:00")).is_due(job_id, now=tuesday_after_grace)  # type: ignore[arg-type]


def test_report_phases_skip_when_if_due_not_met(monkeypatch):
    from datetime import date

    from worker.jobs import report_overdue_daily_impl as impl
    from worker.runtime import JobContext

    class FakeSched:
        def is_due(self, job_id, *, now=None):
            return False

    monkeypatch.setattr(impl, "JobScheduleService", FakeSched)
    ctx = JobContext(
        job_id="report_overdue_daily",
        business_date=date(2026, 8, 16),
        if_due=True,
        dry_run=True,
    )
    assert impl._phase_due("report_branch_daily", ctx) is False
    assert impl._phase_due("report_client_daily", ctx) is False
    assert impl._phase_due("report_managerial", ctx) is False
    branch = impl._run_phase_branch(ctx, pd.DataFrame(), pd.DataFrame())
    client = impl._run_phase_client(ctx, pd.DataFrame(), pd.DataFrame())
    managerial = impl._run_phase_managerial(ctx, pd.DataFrame(), pd.DataFrame())
    assert branch.get("skipped_schedule") is True
    assert client.get("skipped_schedule") is True
    assert managerial.get("skipped_schedule") is True
    assert branch.get("sent", 0) == 0


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


def test_filter_cnpj_normalizes_digits():
    df = pd.DataFrame(
        {
            "cnpj_cliente": ["12.345.678/0001-90", "999", None],
            "nota_fiscal": ["1", "2", "3"],
        }
    )
    out = _filter_cnpj(df, "12345678000190")
    assert list(out["nota_fiscal"]) == ["1"]
    empty = _filter_cnpj(df, "")
    assert empty.empty
    missing_col = _filter_cnpj(pd.DataFrame({"nota_fiscal": ["1"]}), "123")
    assert missing_col.empty


def test_build_report_html_empty_nat_nan():
    df = pd.DataFrame(
        {
            "nota_fiscal": ["NF1"],
            "cliente": ["C"],
            "cidade_entrega": ["SP"],
            "dt_cadastro": [pd.NaT],
            "status": [float("nan")],
            "remetente": [None],
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
            "nota_fiscal": ["1173309/1"],
            "cliente": ["C"],
            "cidade_entrega": ["SP"],
            "dt_cadastro": [pd.Timestamp("2026-07-20")],
            "status": ["RECEBIDO"],
            "remetente": ["INDUSTRIA XYZ"],
            "motorista": ["João"],
            "dias_atraso": [5],
            "valor_total": [99.9],
            "dt_agendamento": [pd.Timestamp("2026-07-18")],
        }
    )
    html = build_report_html(audience_name="SPO", overdue=df, due_today=pd.DataFrame())
    assert "Valor (R$)" not in html
    assert "Dt. Agendamento" not in html
    assert "Dt. Cadastro" in html
    assert "Status" in html
    assert "Indústria" in html
    assert "Ult. Motorista" in html
    assert "20/07/2026" in html
    assert "RECEBIDO" in html
    assert "INDUSTRIA XYZ" in html
    assert "1173309" in html
    assert "1173309/1" not in html
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
    assert "Notas fiscais que vencem hoje" not in html
    assert html.count("Nenhuma nota fiscal nesta situação.") == 1
    assert build_report_subject("Maria") == "Relatório de Entregas - Maria"


def test_build_report_html_unifies_due_today_as_zero_days():
    overdue = pd.DataFrame(
        {
            "nro_entrega": ["A1"],
            "nota_fiscal": ["NF-ATRASO/1"],
            "cliente": ["C1"],
            "cidade_entrega": ["SP"],
            "dt_cadastro": [pd.Timestamp("2026-08-10")],
            "status": ["RECEBIDO"],
            "remetente": ["Industria A"],
            "motorista": ["João"],
            "dias_atraso": [5],
        }
    )
    due_today = pd.DataFrame(
        {
            "nro_entrega": ["B2"],
            "nota_fiscal": ["NF-HOJE/2"],
            "cliente": ["C2"],
            "cidade_entrega": ["RJ"],
            "dt_cadastro": [pd.Timestamp("2026-08-17")],
            "status": ["LIBERADO PARA ENTREGA"],
            "remetente": ["Industria B"],
            "motorista": ["Ana"],
            "dias_atraso": [3],
        }
    )
    html = build_report_html(audience_name="SPO", overdue=overdue, due_today=due_today)
    assert "Notas Fiscais em atraso (2)" in html
    assert "Notas fiscais que vencem hoje" not in html
    assert html.count("<table") == 1
    assert "Dias em atraso igual a 0 indica nota que vence hoje." in html
    assert "NF-ATRASO" in html
    assert "NF-HOJE" in html
    assert "NF-ATRASO/1" not in html
    assert html.index("NF-ATRASO") < html.index("NF-HOJE")
    assert ">5</td>" in html
    hoje_pos = html.index("NF-HOJE")
    assert ">0</td>" in html[hoje_pos:]
    assert html.count("Nenhuma nota fiscal nesta situação.") == 0


def test_combine_report_rows_drops_due_today_duplicate():
    from worker.adapters.report_html import combine_report_rows

    overdue = pd.DataFrame({"nro_entrega": ["A1"], "nota_fiscal": ["NF1"], "dias_atraso": [4]})
    due_today = pd.DataFrame({"nro_entrega": ["A1"], "nota_fiscal": ["NF1"], "dias_atraso": [0]})
    out = combine_report_rows(overdue, due_today)
    assert len(out) == 1
    assert int(out.iloc[0]["dias_atraso"]) == 4
