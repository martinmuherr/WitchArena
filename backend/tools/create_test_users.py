"""Crea usuarios de prueba con contraseñas aleatorias y las guarda en test_users.txt.

Uso: python tools/create_test_users.py
No subas test_users.txt a ningún repositorio público.
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app import auth, db  # noqa: E402

USERS = ["prueba_cuervo", "prueba_lobo", "prueba_bruja", "prueba_calabaza"]


def main():
    db.init_schema()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_users.txt")
    lines = []
    for name in USERS:
        pw = secrets.token_urlsafe(9)
        if auth.create_user(name, pw, is_test=True) is None:
            print("ya existe:", name)
            continue
        lines.append("%s  %s" % (name, pw))
        print("creado:", name)
    if lines:
        with open(out, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("contraseñas guardadas en", os.path.normpath(out))


if __name__ == "__main__":
    main()
