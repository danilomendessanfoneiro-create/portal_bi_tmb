"""
auth.py — compatibility shim for legacy scripts (gerar_senha.py).
Prefer app.services.AuthService and app.utils.password in new code.
"""

from app.controllers.auth_controller import logout, require_login
from app.utils.password import hash_password as hash_senha

exigir_login = require_login

__all__ = ["hash_senha", "exigir_login", "logout"]
