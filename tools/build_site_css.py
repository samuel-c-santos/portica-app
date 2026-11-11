"""Gera site/bundle.css a partir das folhas de estilo do site (EP-06.9).

O site carrega um unico arquivo (`bundle.css`) para eliminar round-trips.
As fontes continuam versionadas e editaveis; este script apenas as concatena
na ordem em que devem cascatear:

    vendor/aipim/aipim.css
    vendor/aipim/aipim-components.css
    theme.css          (tokens do Portica sobre o Aipim)
    base.css           (layout, tipografia e componentes proprios)

Sempre que editar qualquer uma delas, rode:

    python tools/build_site_css.py

O teste `tests/test_site_css.py` falha se o bundle estiver desatualizado, para
que a edicao de `theme.css` nunca fique silenciosamente sem efeito.
"""

from __future__ import annotations

from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"

FONTES = (
    "vendor/aipim/aipim.css",
    "vendor/aipim/aipim-components.css",
    "theme.css",
    "base.css",
)

DESTINO = SITE / "bundle.css"


def gerar(fontes: tuple[str, ...] = FONTES, destino: Path = DESTINO) -> str:
    """Devolve o conteudo do bundle (sem gravar em disco)."""
    partes = [(SITE / nome).read_text(encoding="utf-8").strip() for nome in fontes]
    return "\n\n".join(partes) + "\n"


def escrever(conteudo: str | None = None, destino: Path = DESTINO) -> Path:
    """Grava o bundle e devolve o caminho."""
    # Sem `newline=`: o Windows grava CRLF (como o bundle versionado) e o
    # Linux/CI grava LF. A comparacao do teste normaliza as quebras.
    destino.write_text(
        conteudo if conteudo is not None else gerar(),
        encoding="utf-8",
    )
    return destino


def main() -> int:
    destino = escrever()
    tamanho = destino.stat().st_size
    print(f"[OK] {destino.relative_to(SITE.parent)} regenerado ({tamanho:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
