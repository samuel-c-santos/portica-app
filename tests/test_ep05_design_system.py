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


def test_ep05_2_formatacao_pt_br_unica():
    """EP-05.2: core/format.py unifica formatacao pt-BR com virgula decimal entre UI e PDF."""
    import core.relatorio_base as rb
    from core.format import _diam, _n, fmt_diam, fmt_grandeza, fmt_num
    from ui.theme import numeric_text

    assert fmt_num(10.51, 2) == "10,51"
    assert fmt_num(12345.6, 2, unidade="kN·m") == "12.345,60 kN·m"
    assert fmt_num(15.2, 1, sinal=True, unidade="kN·m") == "+15,2 kN·m"
    assert fmt_grandeza(4.567, "as") == "4,57 cm²"
    assert fmt_diam(12.5, prefixo="Ø", unidade="mm") == "Ø12,5 mm"
    assert fmt_diam(16.0, prefixo="Ø") == "Ø16"
    assert rb._n is _n
    assert rb._diam is _diam

    t = numeric_text(10.51, casas=2, unidade="cm²")
    assert t.value == "10,51 cm²"
    assert t.font_family == "Roboto Mono"


def test_ep05_3_fonte_tabular_em_campos_e_tabelas():
    """EP-05.3: Campos numericos e colunas de tabelas usam Roboto Mono tabular e alinhamento a direita."""
    import flet as ft

    from core.calculos import calcular_cisalhamento_viga_comum, calcular_flexao_viga_comum
    from ui.ftool.secoes_criticas import SecaoCritica

    page = _FakePage()
    ctx = montar_contexto(page, "comum", lambda: None, None, None, None, None, None)
    ctx.state["resultados_flex"] = calcular_flexao_viga_comum(50, 20, 2, 25, 5, 12.5, 50, [100.0])
    ctx.state["resultados_cis"] = calcular_cisalhamento_viga_comum(
        50, 20, 25, 5, 12.5, 60, 50, 2, [80.0]
    )
    ctx.open_resultados_modal()
    dlg = page.dialogs[-1]
    results_col = dlg.content.content
    cis_table = results_col.controls[1].controls[3]
    # Colunas numericas marcadas com numeric=True
    assert cis_table.columns[1].numeric is True
    assert cis_table.columns[2].numeric is True
    assert cis_table.columns[3].numeric is True
    assert cis_table.columns[4].numeric is True
    # Celulas numericas usam Roboto Mono e alinhamento a direita
    cell_ctrl = cis_table.rows[0].cells[1].content
    assert cell_ctrl.font_family == "Roboto Mono"
    assert cell_ctrl.text_align == ft.TextAlign.RIGHT

    # Viewer FTOOL tambem usa numeric_text
    ctx.state["ftool_momentos"] = [(0.0, 0.0), (2.0, 120.5)]
    ctx.state["ftool_cortantes"] = [(0.0, 80.0), (2.0, -80.0)]
    ctx.state["ftool_secoes_criticas"] = [
        SecaoCritica(x=2.0, momento=120.5, cortante=0.0, tipo="M_MAX_POS", descricao="Meio do vão")
    ]
    ctx._atualizar_viewer()
    viewer_table = ctx.viewer_flexao.controls[-1]
    assert viewer_table.columns[0].numeric is True
    assert viewer_table.rows[0].cells[0].content.font_family == "Roboto Mono"


def test_ep05_5_scroll_independente_sem_clipping():
    """EP-05.5: Coluna esquerda (geometria/materiais) e coluna direita possuem scroll independente e expand=True."""
    import flet as ft

    from ui.entrada import ENTRADA_FTOOL

    page = _FakePage()
    ctx = montar_contexto(page, "t", lambda: None, None, None, None, None, None)
    left_col = ctx.sidebar_holder.content
    assert left_col.scroll == ft.ScrollMode.AUTO
    assert left_col.expand is True
    assert ctx.sidebar_holder.alignment == ft.Alignment(-1, -1)

    # Modo FTOOL nao aninha scroll dentro do card FTOOL
    ctx.state["entrada"] = ENTRADA_FTOOL
    left_col_ftool = ctx.build_sidebar()
    ftool_card_col = left_col_ftool.controls[-1].content
    assert ftool_card_col.scroll is None
    assert left_col_ftool.scroll == ft.ScrollMode.AUTO
    assert left_col_ftool.expand is True
    assert ctx.right_sidebar.scroll == ft.ScrollMode.AUTO
    assert ctx.right_sidebar.expand is True


def test_ep05_4_dialogos_dark_mode():
    """EP-05.4: Todos os dialogos consomem Palette e reagem a troca de tema claro/escuro."""
    from core.calculos import calcular_cisalhamento_viga_comum, calcular_flexao_viga_comum
    from ui.dialogs import open_caa_info, open_geometria_info
    from ui.theme import DARK_COLORS, LIGHT_COLORS, apply_dark, apply_light

    page = _FakePage()
    try:
        apply_light()
        ctx = montar_contexto(page, "comum", lambda: None, None, None, None, None, None)
        ctx.state["resultados_flex"] = calcular_flexao_viga_comum(
            50, 20, 2, 25, 5, 12.5, 50, [100.0]
        )
        ctx.state["resultados_cis"] = calcular_cisalhamento_viga_comum(
            50, 20, 25, 5, 12.5, 60, 50, 2, [80.0]
        )
        ctx.open_resultados_modal()
        dlg = page.dialogs[-1]
        assert dlg.bgcolor == LIGHT_COLORS["SURFACE"]

        open_caa_info(page)
        info_dlg = page.dialogs[-1]
        assert info_dlg.bgcolor == LIGHT_COLORS["SURFACE"]

        open_geometria_info(page)
        geom_dlg = page.dialogs[-1]
        assert geom_dlg.bgcolor == LIGHT_COLORS["SURFACE"]

        # Troca em runtime atualiza dialogos ja abertos para dark mode
        apply_dark()
        assert dlg.bgcolor == DARK_COLORS["SURFACE"]
        assert info_dlg.bgcolor == DARK_COLORS["SURFACE"]
        assert geom_dlg.bgcolor == DARK_COLORS["SURFACE"]
        # Card interno do modal tambem reage
        flex_card = dlg.content.content.controls[0].controls[2].controls[0]
        assert flex_card.bgcolor == DARK_COLORS["SURFACE"]
    finally:
        apply_light()


def test_ep05_8_sem_card_duplicado_no_modal_resultados():
    """EP-05.8: Seções críticas de platô adjacentes (x=3,70 m e x=3,80 m) são fundidas num único card com badge POSITIVO/NEGATIVO."""
    import os

    from ui.entrada import ENTRADA_FTOOL

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    samples = os.path.join(base, "samples")
    page = _FakePage()
    ctx = montar_contexto(page, "t", lambda: None, None, None, None, None, None)
    ctx.state["entrada"] = ENTRADA_FTOOL
    ctx.state["ftool_momento_path"] = os.path.join(samples, "test-t-momento.txt")
    ctx.state["ftool_cortante_path"] = os.path.join(samples, "test-t-cortantes.txt")
    ctx.state["ftool_deformacao_path"] = os.path.join(samples, "test-t-deformacoes.txt")
    ctx.h_tf.control.value = "60"
    ctx.bw_tf.control.value = "20"
    ctx.bf_tf.control.value = "80"
    ctx.hf_tf.control.value = "12"
    ctx.phi_bar_dd.control.value = "16"

    ctx.processar_ftool()
    dlg_secoes = page.dialogs[-1]
    btn_calc = next(
        a
        for a in dlg_secoes.actions
        if getattr(a, "content", None) == "Calcular" or getattr(a, "text", None) == "Calcular"
    )
    btn_calc.on_click(None)

    dlg_res = page.dialogs[-1]
    flex_cards_row = dlg_res.content.content.controls[2]
    # Platô 3,70 e 3,80 m consolidado em um único card "x = 3,70–3,80 m"
    assert len(flex_cards_row.controls) == 1
    card_col = flex_cards_row.controls[0].content
    badge_txt = card_col.controls[0].controls[1].content.value
    x_txt = card_col.controls[1].value
    assert badge_txt == "POSITIVO"
    assert x_txt == "x = 3,70–3,80 m"


def test_ep05_7_padronizacao_componentes_e_zero_elevated_button():
    """EP-05.7: Zero usos de ft.ElevatedButton em ui/, e componentes absorvidos em ui/theme.py."""
    import os

    from ui import theme

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ui_dir = os.path.join(base, "ui")
    for root, _, files in os.walk(ui_dir):
        for fname in files:
            if fname.endswith(".py"):
                path = os.path.join(root, fname)
                with open(path, encoding="utf-8") as f:
                    src = f.read()
                assert "ElevatedButton" not in src, f"ElevatedButton encontrado em {path}"

    # Componentes do design system e tabelas/dialogos absorvidos em ui.theme
    for sym in (
        "result_card",
        "results_table",
        "polarity_badge",
        "alert_banner",
        "collapsible_section",
        "TABELA_CAA",
        "TABELA_FCK",
        "open_caa_info",
        "build_info_dialog",
    ):
        assert hasattr(theme, sym), f"{sym} ausente em ui.theme"


def test_ep05_9_acessibilidade_contraste_tooltips_e_erros_por_campo():
    """EP-05.9: Contraste WCAG AA >= 4.5, tooltips contextuais, rotulos acessiveis e erros associados ao campo."""
    import flet as ft

    from ui.theme import DARK_COLORS, LIGHT_COLORS, contrast_ratio, field

    # 1. Contraste WCAG AA (>= 4.5:1) para texto primario/secundario e chips de status em claro e escuro
    for pal_name, pal in (("LIGHT", LIGHT_COLORS), ("DARK", DARK_COLORS)):
        for bg_key in ("BG", "SURFACE", "SURFACE_VARIANT"):
            assert contrast_ratio(pal["TEXT_PRIMARY"], pal[bg_key]) >= 4.5, (
                f"{pal_name}: TEXT_PRIMARY em {bg_key} abaixo de 4.5"
            )
            assert contrast_ratio(pal["TEXT_SECONDARY"], pal[bg_key]) >= 4.5, (
                f"{pal_name}: TEXT_SECONDARY em {bg_key} abaixo de 4.5"
            )
        for fg_key, bg_key in (
            ("SUCCESS", "SUCCESS_BG"),
            ("WARNING", "WARNING_BG"),
            ("ERROR", "ERROR_BG"),
            ("INFO", "INFO_BG"),
        ):
            ratio = contrast_ratio(pal[fg_key], pal[bg_key])
            assert ratio >= 4.5, f"{pal_name}: {fg_key}/{bg_key} = {ratio:.2f} < 4.5"

    # 2. field() injeta label acessivel, tooltip e foco visivel quando ausentes
    raw_tf = ft.TextField(value="10")
    field("Largura útil", raw_tf, hint="em cm")
    assert raw_tf.label == "Largura útil"
    assert "Largura útil" in raw_tf.tooltip
    assert raw_tf.focused_border_color == Palette.PRIMARY

    # 3. Todos os inputs com info_button possuem tooltip contextual e foco visivel
    page = _FakePage()
    ctx = montar_contexto(page, "t", lambda: None, None, None, None, None, None)
    for wrapped in (
        ctx.h_tf,
        ctx.bw_tf,
        ctx.bf_tf,
        ctx.hf_tf,
        ctx.b1esq_tf,
        ctx.b1dir_tf,
        ctx.caa_dd,
        ctx.fck_dd,
        ctx.fyk_dd,
        ctx.fyke_dd,
        ctx.gamma_f_dd,
        ctx.phi_est_dd,
        ctx.phi_bar_dd,
    ):
        assert wrapped.control.focused_border_color == Palette.PRIMARY
        info_btn = wrapped.content.controls[1]
        assert info_btn.tooltip and "NBR" in info_btn.tooltip

    # 4. Erros de validacao associados diretamente ao campo que os originou
    ctx.h_tf.control.value = ""
    ctx.bw_tf.control.value = ""
    ctx.phi_bar_dd.control.value = ""
    assert ctx.run_manual_validations() is False
    assert ctx.h_tf.control.error_text == "Campo obrigatório"
    assert ctx.bw_tf.control.error_text == "Campo obrigatório"
    assert ctx.phi_bar_dd.control.error_text == "Selecione a bitola"

    # Altura menor ou igual a d' associa erro ao campo h_tf
    ctx.h_tf.control.value = "3"
    ctx.bw_tf.control.value = "20"
    ctx.phi_bar_dd.control.value = "16"
    ctx.on_calculate(None)
    assert ctx.h_tf.control.error_text and "d'" in ctx.h_tf.control.error_text

    # Largura bw <= 5 associa erro ao campo bw_tf
    ctx.h_tf.control.value = "50"
    ctx.bw_tf.control.value = "4"
    ctx.on_calculate(None)
    assert ctx.bw_tf.control.error_text == "Mínimo 5,0 cm"


def test_result_card_traduz_bool_para_boxshadow():
    """`result_card(shadow=...)` deve produzir BoxShadow/None, nunca bool.

    Regressao: o Flet nao deserializa `shadow=False`; o Flutter desenha o
    ErrorWidget (retangulo cinza) no lugar do card no modal de resultados.
    """
    import flet as ft

    from ui.theme import SHADOW_SM, result_card

    com_sombra = result_card([])
    sem_sombra = result_card([], shadow=False)

    assert isinstance(com_sombra.shadow, ft.BoxShadow)
    assert com_sombra.shadow is SHADOW_SM
    assert sem_sombra.shadow is None
