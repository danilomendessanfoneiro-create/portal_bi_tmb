"""
gerar_senha.py
---------------
Utilitario para gerar o hash de uma senha, para colocar no usuarios.csv.

Uso:
    python gerar_senha.py MinhaSenha123

Copie o hash gerado e cole na coluna 'senha_hash' da linha do usuario,
em usuarios.csv.
"""
import sys
from auth import hash_senha

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python gerar_senha.py <senha>")
        sys.exit(1)

    senha = sys.argv[1]
    print(hash_senha(senha))
