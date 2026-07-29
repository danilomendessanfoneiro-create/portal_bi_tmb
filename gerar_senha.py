"""
gerar_senha.py
Utilitario para gerar o hash de uma senha.

Uso:
    python gerar_senha.py MinhaSenha123
"""
import sys

from app.utils.password import hash_password

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python gerar_senha.py <senha>")
        sys.exit(1)
    print(hash_password(sys.argv[1]))
