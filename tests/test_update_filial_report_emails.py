import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "database" / "deploy" / "update_filial_report_emails.py"
_SPEC = importlib.util.spec_from_file_location("update_filial_report_emails", _SCRIPT)
assert _SPEC and _SPEC.loader
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

FILIAL_EMAILS_RAW = _MOD.FILIAL_EMAILS_RAW
canonical_branch = _MOD.canonical_branch
extract_emails = _MOD.extract_emails
validate_report_emails = _MOD.validate_report_emails


def test_canonical_branch_aliases():
    assert canonical_branch("TMB D. DE CAXIAS") == "DUQUE DE CAXIAS"
    assert canonical_branch("Duque de Caxias") == "DUQUE DE CAXIAS"
    assert canonical_branch("TMB VALADARES") == "GOVERNADOR VALADARES"
    assert canonical_branch("TMB UBERLÂNDIA") == "UBERLANDIA"
    assert canonical_branch("TMB DIVINOPOLIS") == "DIVINOPOLIS"
    assert canonical_branch("TMB PATOS DE MINAS") == "PATOS DE MINAS"


def test_extract_emails_from_messy_headers():
    raw = FILIAL_EMAILS_RAW["VARGINHA"]
    assert extract_emails(raw) == [
        "preacertovga@tmblogistica.com.br",
        "maria.eduarda@tmblogistica.com.br",
    ]


def test_extract_emails_dedupes_machado_and_betim():
    machado = extract_emails(FILIAL_EMAILS_RAW["MACHADO"])
    assert machado.count("joao.henrique@tmblogistica.com.br") == 1
    betim = extract_emails(FILIAL_EMAILS_RAW["BETIM"])
    assert betim.count("expedicaobt@tmblogistica.com.br") == 1
    assert "cdbetim@tmblogistica.com.br" in betim


def test_all_filiais_validate():
    assert len(FILIAL_EMAILS_RAW) == 13
    for key, raw in FILIAL_EMAILS_RAW.items():
        emails = extract_emails(raw)
        assert emails, key
        validate_report_emails(";".join(emails))
