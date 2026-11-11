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


def test_ep05_6_coerencia_marca_e_nomenclatura():
    """EP-05.6: CTA primario azul na home, 'Início' acentuado na sidebar, chip NBR neutro e APP_TITLE unificado."""
    from core import APP_NAME, APP_TITLE
    from edicoes.main import APP_TITLE as MAIN_TITLE
    from ui.home import _mode_card, build_home
    from ui.sidebar import ROUTE_HOME, build_sidebar

    assert APP_TITLE == "Pórtica App"
    assert APP_NAME == "Pórtica"
    assert MAIN_TITLE == APP_TITLE

    page = _FakePage()
    sb = build_sidebar(page, ROUTE_HOME, lambda r: None)
    items_col = sb.content.controls[1]
    home_item = items_col.controls[0]
    viga_item = items_col.controls[2]
    # Label "Início" com acento e tamanho >= 12
    lbl_home = home_item.content.controls[1].content
    assert lbl_home.value == "Início"
    assert lbl_home.size >= 12
    # Ripple apenas no item ativo
    assert home_item.ink is True
    assert viga_item.ink is False

    # Card CTA Iniciar em primario azul e ilustracoes com mesma altura
    c1 = _mode_card(page, "T1", "D1", "M1", Palette.PRIMARY, "a.png", "i1.png", lambda e: None)
    c2 = _mode_card(page, "T2", "D2", "M2", Palette.SECONDARY, "b.png", "i2.png", lambda e: None)
    img1 = c1.content.controls[0].content
    img2 = c2.content.controls[0].content
    assert img1.height == img2.height == 180
    btn1 = c1.content.controls[2].content.controls[2].controls[2].controls[1]
    assert btn1.bgcolor == Palette.PRIMARY

    # Chip NBR 6118:2023 neutro na home e na tela de viga
    home_ctrl = build_home(page, lambda m: None)
    hero_badge = home_ctrl.content.controls[0].content.controls[2]
    assert hero_badge.bgcolor == Palette.SURFACE_VARIANT

    ctx = montar_contexto(page, "comum", lambda: None, None, None, None, None, None)
    top_badge = ctx.topbar.content.controls[-1]
    assert top_badge.bgcolor == Palette.SURFACE_VARIANT
