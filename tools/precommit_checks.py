"""Checagens de higiene executadas pelo pre-commit (EP-00.2 / EP-00.6).

Uso pelo `.pre-commit-config.yaml`; o pre-commit chama:

    python tools/precommit_checks.py <arquivo-stageado> ...

Regras:
1. Nenhum arquivo sob `docs/nbr/` e nenhum `*.pdf` pode ser commitado
   (os PDFs da ABNT nunca podem entrar no repositório nem no bundle);
2. Todo `.py`/`.md` stageado precisa decodificar como UTF-8 e não pode ter
   BOM.

Exit code 0 = limpo; 1 = bloqueia o commit.
"""

from __future__ import annotations

import sys
from pathlib import Path

PASTAS_PROIBIDAS = ("docs/nbr/",)
EXTENSOES_PROIBIDAS = (".pdf",)
EXTENSOES_UTF8 = (".py", ".md")


def _erros_para(path: Path) -> list[str]:
    erros: list[str] = []
    relativo = path.as_posix().lower()

    if any(relativo.startswith(p) for p in PASTAS_PROIBIDAS):
        erros.append(f"proibido no repositório (norma ABNT): {path}")

    if path.suffix.lower() in EXTENSOES_PROIBIDAS:
        erros.append(f"proibido commitar PDF: {path}")

    if path.suffix.lower() in EXTENSOES_UTF8 and path.exists():
        dados = path.read_bytes()
        try:
            dados.decode("utf-8")
        except UnicodeDecodeError as exc:
            erros.append(f"não é UTF-8 válido: {path} ({exc})")
        else:
            if dados.startswith(b"\xef\xbb\xbf"):
                erros.append(f"tem BOM (o repo usa UTF-8 sem BOM): {path}")

    return erros


def main(argv: list[str]) -> int:
    erros: list[str] = []
    for arg in argv:
        erros.extend(_erros_para(Path(arg)))

    if erros:
        print("pre-commit: commit bloqueado.\n", file=sys.stderr)
        for erro in erros:
            print(f"  - {erro}", file=sys.stderr)
        print(
            "\nPDFs normativos (docs/nbr/) nunca entram no repo; textos devem ser UTF-8 sem BOM.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
