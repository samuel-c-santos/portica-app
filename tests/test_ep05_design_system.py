"""Testes do EP-05: Design system, hierarquia semantica e coerencia visual."""

from ui.theme import Palette
from ui.viga import montar_contexto


class _FakePage:
    def __init__(self):
        self.services = []
        self.overlay = []
        self.dialogs = []

    def update(self, *a, **k):
        pass

    def add(self, *a, **k):
        pass

    def run_task(self, *a, **k):
        pass

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        if self.dialogs:
            self.dialogs.pop()


def test_ep05_1_botoes_exportacao_nao_usam_verde():
    """EP-05.1: 'Gerar PDF' e 'Exportar DXF' nao usam Palette.SUCCESS (verde e exclusivo para conformidade)."""
    ctx = montar_contexto(_FakePage(), "comum", lambda: None, None, None, None, None, None)
    pdf_bg = getattr(ctx.btn_gerar_pdf.style, "bgcolor", None)
    dxf_bg = getattr(ctx.btn_exportar_dxf.style, "bgcolor", None)
    assert pdf_bg != Palette.SUCCESS
    assert dxf_bg != Palette.SUCCESS
    assert pdf_bg == Palette.PRIMARY

    # Toast padrao de operacao tambem usa primario (azul), nao verde normativo
    ctx.show_msg("Operação concluída")
    assert ctx.page.overlay[-1].bgcolor == Palette.PRIMARY
