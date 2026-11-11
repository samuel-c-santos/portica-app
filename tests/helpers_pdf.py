"""Helper para verificar CONTEÚDO de PDFs nos testes (EP-03.2).

O fpdf2 não exporta texto; aqui interceptamos `FPDF.cell`/`multi_cell` e
coletamos todo texto passado ao PDF — o mesmo padrão usado por
`tests/test_relatorio_ep019.py::CapturaPDF`.
"""

import fpdf


def _extrai_texto(args, kwargs):
    t = kwargs.get("text", "")
    if not t and len(args) >= 3:
        t = args[2]
    return t if isinstance(t, str) and t else None


def pdf_com_captura(monkeypatch, construir) -> str:
    """Patchea FPDF.cell/multi_cell, executa `construir()` e devolve o texto.

    PorticaPDF é subclasse de FPDF e não sobrescreve cell/multi_cell, então
    o patch cobre os relatórios completos e os desenhos auxiliares.
    """
    linhas: list[str] = []
    orig_cell = fpdf.FPDF.cell
    orig_multi = fpdf.FPDF.multi_cell

    def cell(self, *a, **kw):
        t = _extrai_texto(a, kw)
        if t:
            linhas.append(t)
        return orig_cell(self, *a, **kw)

    def multi_cell(self, *a, **kw):
        t = _extrai_texto(a, kw)
        if t:
            linhas.append(t)
        return orig_multi(self, *a, **kw)

    monkeypatch.setattr(fpdf.FPDF, "cell", cell)
    monkeypatch.setattr(fpdf.FPDF, "multi_cell", multi_cell)
    try:
        construir()
    finally:
        monkeypatch.undo()
    return "\n".join(linhas)
