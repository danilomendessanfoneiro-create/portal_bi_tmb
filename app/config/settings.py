"""Application settings (env + paths)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    root_dir: Path = ROOT_DIR
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://portal_bi:147258369@127.0.0.1:5433/portal_bi_tmb",
    )
    password_salt: str = os.getenv("PASSWORD_SALT", "tmb-logistica-bi")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me-min-32-chars!!")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    public_origin: str = os.getenv("PUBLIC_ORIGIN", "http://localhost:5173")
    api_public_url: str = os.getenv("API_PUBLIC_URL", "http://localhost:8000/api")
    admin_public_url: str = os.getenv("ADMIN_PUBLIC_URL", "http://localhost:5173")
    bi_public_url: str = os.getenv("BI_PUBLIC_URL", "http://localhost:8501")
    data_csv: Path = ROOT_DIR / "dados" / "entregas_relatorio.csv"
    users_csv_seed: Path = ROOT_DIR / "usuarios.csv"
    logo_path: Path = ROOT_DIR / "assets" / "logos" / "logo.png"
    logo_full_path: Path = ROOT_DIR / "assets" / "logos" / "logo_full.png"
    migrations_dir: Path = ROOT_DIR / "database" / "migrations"


settings = Settings()
