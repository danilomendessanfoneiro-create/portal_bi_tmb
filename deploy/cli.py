"""CLI de deploy do Portal BI TMB.

Uso (na VPS, raiz do repo):
  python -m deploy update
  python -m deploy update --branch master --with-units
  python -m deploy update --skip-pull --dry-run

No Windows (dev) executa pull/pip/migrate/build e ignora systemd.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, cwd: Path | None = None, dry_run: bool = False) -> None:
    printable = " ".join(cmd)
    print(f"==> {printable}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)


def _python() -> str:
    venv_py = ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / (
        "python.exe" if os.name == "nt" else "python"
    )
    if venv_py.is_file():
        return str(venv_py)
    return sys.executable


def _npm() -> str:
    return shutil.which("npm") or "npm"


def _systemctl_available() -> bool:
    return os.name != "nt" and shutil.which("systemctl") is not None


def cmd_update(args: argparse.Namespace) -> int:
    py = _python()
    dry = bool(args.dry_run)

    if not (ROOT / ".venv").is_dir() and not dry:
        print("Erro: .venv não encontrado. Crie o venv antes do deploy.", file=sys.stderr)
        return 1

    if args.restart and _systemctl_available():
        print("==> systemctl stop portal-bi portal-api")
        if not dry:
            subprocess.run(
                ["sudo", "systemctl", "stop", "portal-bi", "portal-api"],
                check=False,
            )

    if not args.skip_pull:
        _run(["git", "fetch", "origin"], dry_run=dry)
        _run(["git", "checkout", args.branch], dry_run=dry)
        _run(["git", "pull", "--ff-only", "origin", args.branch], dry_run=dry)

    if not args.skip_pip:
        _run([py, "-m", "pip", "install", "-r", "requirements.txt"], dry_run=dry)

    if not args.skip_migrate:
        _run([py, "database/deploy/run_migrations.py"], dry_run=dry)

    if not args.skip_frontend:
        npm = _npm()
        frontend = ROOT / "frontend"
        _run([npm, "ci"], cwd=frontend, dry_run=dry)
        _run([npm, "run", "build"], cwd=frontend, dry_run=dry)

    if args.with_units and _systemctl_available():
        units = list((ROOT / "deploy" / "systemd").glob("*.service"))
        timers = list((ROOT / "deploy" / "systemd").glob("*.timer"))
        for path in units + timers:
            _run(["sudo", "cp", str(path), "/etc/systemd/system/"], dry_run=dry)
        nginx_src = ROOT / "deploy" / "nginx" / "portal-bi-tmb.conf"
        if nginx_src.is_file():
            _run(
                ["sudo", "cp", str(nginx_src), "/etc/nginx/sites-available/portal-bi-tmb"],
                dry_run=dry,
            )
        _run(["sudo", "systemctl", "daemon-reload"], dry_run=dry)
        if shutil.which("nginx"):
            _run(["sudo", "nginx", "-t"], dry_run=dry)
            _run(["sudo", "systemctl", "reload", "nginx"], dry_run=dry)
    elif args.with_units and not _systemctl_available():
        print("(aviso) --with-units ignorado: systemd indisponível neste SO")

    if args.restart and _systemctl_available():
        _run(["sudo", "systemctl", "start", "portal-api", "portal-bi"], dry_run=dry)
        _run(["sudo", "systemctl", "restart", "portal-api", "portal-bi"], dry_run=dry)
        if not dry:
            subprocess.run(
                ["sudo", "systemctl", "status", "portal-api", "portal-bi", "--no-pager"],
                check=False,
            )
    elif args.restart and not _systemctl_available():
        print("(aviso) restart systemd ignorado neste SO")

    if args.health_url and shutil.which("curl"):
        print(f"==> curl {args.health_url}")
        if not dry:
            rc = subprocess.run(["curl", "-sfS", args.health_url], check=False)
            if rc.returncode != 0:
                print(
                    "(health falhou — journalctl -u portal-api -n 80)",
                    file=sys.stderr,
                )
                return 1
    elif args.health_url:
        print("(aviso) curl ausente; smoke check pulado")

    print("Deploy concluído.")
    print(
        "Pós-deploy: smoke /admin /api/health /bi; "
        "upload planilha (Progressão); seed clientes opcional."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m deploy", description="Deploy Portal BI TMB")
    sub = parser.add_subparsers(dest="command", required=True)

    update = sub.add_parser("update", help="Atualização rotineira (pull + migrate + build + restart)")
    update.add_argument("--branch", default="master", help="Branch para pull (default: master)")
    update.add_argument("--skip-pull", action="store_true")
    update.add_argument("--skip-pip", action="store_true")
    update.add_argument("--skip-migrate", action="store_true")
    update.add_argument("--skip-frontend", action="store_true")
    update.add_argument(
        "--no-restart",
        dest="restart",
        action="store_false",
        help="Não reinicia portal-api/portal-bi",
    )
    update.add_argument(
        "--with-units",
        action="store_true",
        help="Copia units systemd/nginx e recarrega",
    )
    update.add_argument(
        "--health-url",
        default="http://127.0.0.1:8000/api/health",
        help="URL do smoke check",
    )
    update.add_argument(
        "--no-health",
        action="store_true",
        help="Não executa smoke check HTTP",
    )
    update.add_argument("--dry-run", action="store_true", help="Só imprime os comandos")
    update.set_defaults(func=cmd_update, restart=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "no_health", False):
        args.health_url = ""
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
