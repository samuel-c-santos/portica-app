"""
Pórtica App - Tela principal de calculo.
Layout: sidebar de inputs (esquerda) + tabs Flexao/Cisalhamento (centro) + sidebar de imagem/PDF (direita).
"""

import os
import platform
import subprocess
import tempfile
import json
import math
from copy import deepcopy
from datetime import datetime

from core.utils_tempfile import temp_path
from ui.recent_projects import add_recent
from ui.entrada import (
    ENTRADA_FTOOL,
    ENTRADA_MANUAL,
    aplicar_entrada_projeto,
    aviso_edicao,
    entrada_para_salvar,
    ftool_visivel,
)
from ui.ftool.parser import parse_tudo, validate_file_type
from ui.ftool.secoes_criticas import detectar_todas_secoes
from ui.ftool.dimensionamento import (
    dimensionar_trechos_ftool,
    gerar_relatorio_premium,
    gerar_relatorio_viga_comum_premium,
    gerar_relatorio_viga_t_premium
)

import flet as ft

from core.calculos import (
    CAA_DATA, DIAM_BARRAS, DIAM_BARRAS_LONG, area_barra, GAMMA_F_TABLE,
    calcular_flexao_viga_comum, calcular_cisalhamento_viga_comum,
    calcular_flexao_viga_t,
)
from core.relatorio_base import gerar_relatorio_viga_comum, gerar_relatorio_viga_t
from ui.theme import (
    Palette, Spacing, Radius, pad_sym, pad_only, pad_all, br_all,
    surface_card, primary_button, tonal_button, outlined_button, success_button,
    display_large, headline_large, headline_medium, headline_small,
    title_large, title_medium, title_small, body_large, body_medium, body_small,
    label_medium, label_small, caption, overline, icon_pill, icon,
    section_header, field, info_button, status_chip,
    is_dark, border_all,
    SHADOW_SM, SHADOW_MD, SHADOW_LG,
)


MAX_TRECHOS = 20
DEFAULT_TRECHOS = 3


# ── Componentes de input reutilizáveis ─────────────────────────────────────

class _StyledContainer(ft.Container):
    """Container que envolve um TextField/Dropdown com botao de info opcional.
    Expoe o controle via .control para acesso direto a .value."""
    def __init__(self, control, info_btn=None):
        self.control = control
        controls = []
        # O input ocupa todo o espaco disponivel
        control.expand = True
        controls.append(control)
        if info_btn is not None:
            controls.append(info_btn)
        super().__init__(
            content=ft.Row(
                controls, spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=0,
        )


def _on_change_br(original_on_change):
    """Wrapper que substitui ponto por vírgula antes de chamar o on_change original.

    Permite que o usuário digite 135.9 ou 135,9 — ambos são interpretados como 135.9.
    """
    def wrapper(e):
        # Substitui ponto por vírgula no valor digitado
        e.control.value = e.control.value.replace(".", ",")
        if original_on_change:
            original_on_change(e)
    return wrapper


def _styled_textfield(label_text, value, *, hint="", on_change=None,
                      info_on_click=None, keyboard_type=ft.KeyboardType.NUMBER, max_length=None):
    """TextField com label, valor default e opcional botao de info.
    Retorna Container que expoe .control (o TextField) para acesso a .value."""
    info_btn = None
    if info_on_click is not None:
        info_btn = ft.IconButton(
            icon=ft.Icons.INFO_OUTLINE,
            icon_color=Palette.PRIMARY,
            icon_size=16, tooltip="Ver tabela",
            on_click=info_on_click,
        )

    # Campos numéricos: substitui ponto por vírgula automaticamente
    wrapped_on_change = _on_change_br(on_change) if keyboard_type == ft.KeyboardType.NUMBER else on_change

    tf = ft.TextField(
        label=label_text,
        value=str(value),
        border_radius=br_all(Radius.SM),
        text_size=14, filled=True, dense=True,
        bgcolor=Palette.SURFACE_VARIANT,
        border_color=Palette.OUTLINE_VARIANT,
        focused_border_color=Palette.PRIMARY,
        cursor_color=Palette.PRIMARY,
        keyboard_type=keyboard_type,
        hint_text=hint,
        on_change=wrapped_on_change,
        expand=True,
        max_length=max_length,
    )
    return _StyledContainer(tf, info_btn)


def _styled_dropdown(label_text, value, options, *, on_change=None,
                     info_on_click=None):
    """Dropdown com label e opcional botao de info.
    Retorna Container que expoe .control (o Dropdown) para acesso a .value."""
    info_btn = None
    if info_on_click is not None:
        info_btn = ft.IconButton(
            icon=ft.Icons.INFO_OUTLINE,
            icon_color=Palette.PRIMARY,
            icon_size=16, tooltip="Ver tabela",
            on_click=info_on_click,
        )
    dd = ft.Dropdown(
        label=label_text,
        value=value,
        options=options,
        border_radius=br_all(Radius.SM),
        filled=True, dense=True,
        bgcolor=Palette.SURFACE_VARIANT,
        border_color=Palette.OUTLINE_VARIANT,
        focused_border_color=Palette.PRIMARY,
        text_size=14,
        on_select=on_change,
        expand=True,
    )
    return _StyledContainer(dd, info_btn)


def _make_options(values, formatter=None):
    return [ft.dropdown.Option(str(v), formatter(v) if formatter else str(v)) for v in values]


def _make_caa_options():
    return [
        ft.dropdown.Option(str(k), f"CAA {k} - {v['nome']}")
        for k, v in CAA_DATA.items()
    ]


def _make_gamma_f_options():
    return [
        ft.dropdown.Option(k, f"{v['nome']} (gf = {v['gamma_f']})")
        for k, v in GAMMA_F_TABLE.items()
    ]


def _build_illustrations_panel(page, title, subtitle, image_specs):
    """Cria um card contendo ilustrações técnicas com legendas clicáveis para ampliar."""
    from ui.dialogs import open_image_preview
    from core.utils_tempfile import resource_path
    assets_root = resource_path("core/assets/info")

    controls = [
        section_header(title, icon=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=16, color=Palette.TEXT_SECONDARY)),
        caption(subtitle, color=Palette.TEXT_SECONDARY),
        ft.Container(height=Spacing.SM),
    ]

    for i, spec in enumerate(image_specs):
        filename, label = spec
        img_path = os.path.join(assets_root, filename)
        if os.path.exists(img_path):
            if i > 0:
                controls.append(ft.Container(height=Spacing.SM))
                controls.append(ft.Divider(color=Palette.OUTLINE_VARIANT, height=1))
                controls.append(ft.Container(height=Spacing.SM))
            
            # Local click handler helper
            def make_click_handler(path, title_text):
                return lambda e: open_image_preview(page, path, title_text)
                
            controls.append(
                ft.Container(
                    content=ft.Image(
                        src=img_path,
                        fit=ft.BoxFit.CONTAIN,
                        border_radius=br_all(Radius.SM),
                        height=160 if len(image_specs) > 1 else 320,
                    ),
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=make_click_handler(img_path, label),
                    tooltip="Clique para ampliar",
                )
            )
            controls.append(ft.Container(height=Spacing.XXS))
            controls.append(
                caption(label, color=Palette.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER)
            )
            
    return surface_card(
        ft.Column(
            controls=controls,
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=Spacing.LG,
    )


# ── Tela de calculo: entrada + calculo + PDF ──────────────────────────────

def build_viga_screen(page, modo, on_back, fp_image, fp_pdf, fp_load_project, fp_save_project, fp_dxf, initial_file=None):
    """
    Constroi a tela completa de calculo.
    modo: "comum" | "t"
    on_back: callable() -> None (volta para home)
    initial_file: str | None  -- caminho .ptc para carregar ao abrir
    """
    # ── Estado (mutavel entre callbacks) ────────────────────────────────
    state = {
        "tipo_viga": "V1" if modo == "comum" else "VT1",
        "entrada": ENTRADA_MANUAL,
        "ftool_path": None,
        "ftool_filename": None,
        "resultados_flex": None,
        "resultados_cis": None,
        "pdf_path": None,
        "ftool_momentos": None,
        "ftool_cortantes": None,
        "ftool_deformacoes": None,
        "ftool_secoes_criticas": None,
        "combinacoes": [],
        "temp_momento_path": None,
        "temp_cortante_path": None,
        "ftool_momento_path": None,
        "ftool_cortante_path": None,
        "ftool_deformacao_path": None,
    }
    md_rows = []      # lista de TextField para momentos
    vk_rows = []      # lista de TextField para cortantes
    
    combs_column = ft.Column(spacing=Spacing.XS)
    btn_calc_envelope = ft.OutlinedButton(
        "Calcular", icon=ft.Icons.CALCULATE,
        on_click=lambda e: on_calcular_envelope_click(e),
        disabled=True, height=32,
        style=ft.ButtonStyle(text_style=ft.TextStyle(size=12)),
    )
    
    def update_combs_ui():
        combs_column.controls.clear()
        for idx, c in enumerate(state.get("combinacoes", [])):
            combs_column.controls.append(
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.ALT_ROUTE, size=12, color=Palette.PRIMARY),
                        ft.Text(f"{c['nome']}", size=11, weight=ft.FontWeight.BOLD, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_size=14,
                            icon_color=Palette.ERROR,
                            tooltip="Remover",
                            on_click=lambda e, i=idx: remove_comb(i),
                        )
                    ]
                )
            )
        btn_calc_envelope.disabled = len(state.get("combinacoes", [])) < 2
        page.update()

    def remove_comb(idx):
        if "combinacoes" in state and idx < len(state["combinacoes"]):
            state["combinacoes"].pop(idx)
            update_combs_ui()

    # Labels dos arquivos FTOOL selecionados
    lbl_ftool_momento = ft.Text("Nenhum", size=11, color=Palette.TEXT_DISABLED, expand=True)
    lbl_ftool_cortante = ft.Text("Nenhum", size=11, color=Palette.TEXT_DISABLED, expand=True)
    lbl_ftool_deformacao = ft.Text("Nenhum", size=11, color=Palette.TEXT_DISABLED, expand=True)
    btn_processar_ftool = ft.Button(
        "Processar", icon=ft.Icons.PLAY_ARROW,
        on_click=lambda e: processar_ftool(),
        disabled=True,
        tooltip="Selecione os 3 arquivos TXT e preencha h, bw e φ barra",
        style=ft.ButtonStyle(
            bgcolor=Palette.PRIMARY, color=Palette.ON_PRIMARY,
            padding=pad_sym(horizontal=Spacing.XL, vertical=Spacing.MD),
            shape=ft.RoundedRectangleBorder(radius=br_all(Radius.MD)),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        ),
    )
    panel_rebuilds = {}  # dicionario para armazenar funcoes de reconstrucao de trechos
    ftool_status_text = None
    pdf_status_text = None

    # Validation helpers
    def validate_positive_number(e):
        tf = e.control
        val_str = tf.value.strip()
        if not val_str:
            tf.error_text = "Campo obrigatório"
        else:
            try:
                val_float = float(val_str.replace(",", "."))
                if val_float <= 0:
                    tf.error_text = "Deve ser maior que 0"
                else:
                    tf.error_text = None
            except ValueError:
                tf.error_text = "Use número com vírgula (ex: 50,0)"

    
        page.update()

    def validate_non_negative_number(e):
        tf = e.control
        val_str = tf.value.strip()
        if not val_str:
            tf.error_text = "Campo obrigatório"
        else:
            try:
                val_float = float(val_str.replace(",", "."))
                if val_float < 0:
                    tf.error_text = "Não pode ser negativo"
                else:
                    tf.error_text = None
            except ValueError:
                tf.error_text = "Use número com vírgula (ex: 50,0)"

    
        page.update()

    def validate_trecho_field(e):
        tf = e.control
        val_str = tf.value.strip()
        if not val_str:
            tf.error_text = None
        else:
            try:
                float(val_str.replace(",", "."))
                tf.error_text = None
            except ValueError:
                tf.error_text = "Inválido"
        page.update()

    # ── Builder da sidebar de geometria ──────────────────────────────────
    viga_nome_tf = _styled_textfield("Identificacao da Viga", "V1" if modo == "comum" else "VT1", keyboard_type=ft.KeyboardType.TEXT, max_length=30)
    def _on_geom_change(original_callback):
        def wrapper(e):
            original_callback(e)
            _check_ftool_pronto()
        return wrapper

    h_tf  = _styled_textfield("d (cm)", "", on_change=_on_geom_change(validate_positive_number), info_on_click=lambda e: _open_geometria(page))
    bw_tf = _styled_textfield("tw (cm)", "", on_change=_on_geom_change(validate_positive_number), info_on_click=lambda e: _open_geometria(page))
    bf_tf = _styled_textfield("b (cm)", "60", on_change=validate_positive_number, info_on_click=lambda e: _open_viga_t(page))
    hf_tf = _styled_textfield("tf (cm)", "12", on_change=validate_positive_number, info_on_click=lambda e: _open_viga_t(page))
    b1esq_tf = _styled_textfield("b1 esquerdo (cm)", "40", on_change=validate_non_negative_number, info_on_click=lambda e: _open_b1(page))
    b1dir_tf = _styled_textfield("b1 direito (cm)", "40", on_change=validate_non_negative_number, info_on_click=lambda e: _open_b1(page))

    # RT inputs
    PROFISSOES = [
        "Engenheiro Civil",
        "Projetista / Calculista",
        "Arquiteto",
        "Técnico em Edificações",
        "Engenheiro (outras áreas)",
    ]
    prof_dd = _styled_dropdown("Profissão", "Engenheiro Civil", [ft.dropdown.Option(p) for p in PROFISSOES])
    resp_nome_tf = _styled_textfield("Nome do Responsável", "", keyboard_type=ft.KeyboardType.TEXT, max_length=40)
    resp_registro_tf = _styled_textfield("CREA/UF", "", keyboard_type=ft.KeyboardType.TEXT, max_length=20)

    is_t = (modo == "t")
    geom_widgets = [
        h_tf, bw_tf,
    ]
    if is_t:
        geom_widgets += [bf_tf, hf_tf, b1esq_tf, b1dir_tf]

    def run_manual_validations():
        ok = True
        
        # Validar h
        h_val = h_tf.control.value.strip()
        if not h_val:
            h_tf.control.error_text = "Campo obrigatório"
            ok = False
        else:
            try:
                if float(h_val.replace(",", ".")) <= 0:
                    h_tf.control.error_text = "Deve ser maior que 0"
                    ok = False
                else:
                    h_tf.control.error_text = None
            except ValueError:
                h_tf.control.error_text = "Use número (ex: 50,0)"
                ok = False

        # Validar bw
        bw_val = bw_tf.control.value.strip()
        if not bw_val:
            bw_tf.control.error_text = "Campo obrigatório"
            ok = False
        else:
            try:
                if float(bw_val.replace(",", ".")) <= 0:
                    bw_tf.control.error_text = "Deve ser maior que 0"
                    ok = False
                else:
                    bw_tf.control.error_text = None
            except ValueError:
                bw_tf.control.error_text = "Use número (ex: 20,0)"

    
                ok = False

        if is_t:
            for tf_ctrl, label in [(bf_tf, "bf"), (hf_tf, "hf")]:
                val = tf_ctrl.control.value.strip()
                if not val:
                    tf_ctrl.control.error_text = "Campo obrigatório"
                    ok = False
                else:
                    try:
                        if float(val.replace(",", ".")) <= 0:
                            tf_ctrl.control.error_text = "Deve ser maior que 0"
                            ok = False
                        else:
                            tf_ctrl.control.error_text = None
                    except ValueError:
                        tf_ctrl.control.error_text = "Use número (ex: 50,0)"
                        ok = False

            pass

        # Validar trechos
        for tf in md_rows + vk_rows:
            val = tf.value.strip()
            if val:
                try:
                    float(val.replace(",", "."))
                    tf.error_text = None
                except ValueError:
                    tf.error_text = "Use número com vírgula (ex: 135,9)"
                    ok = False
            else:
                tf.error_text = None

        page.update()
        return ok

    # ── Sidebar de materiais ─────────────────────────────────────────────
    caa_dd = _styled_dropdown(
        "Classe CAA",
        "2",
        _make_caa_options(),
        info_on_click=lambda e: _open_caa(page),
    )
    fck_dd  = _styled_dropdown(
        "fck (MPa)",
        "30",
        _make_options([20, 25, 30, 35, 40, 45, 50, 55, 60]),
        info_on_click=lambda e: _open_fck(page),
    )
    fyk_dd  = _styled_dropdown(
        "fyk aço (kN/cm²)",
        "50",
        _make_options([25, 50, 60]),
        info_on_click=lambda e: _open_aco(page),
    )
    fyke_dd = _styled_dropdown(
        "fyk estribo (kN/cm²)",
        "60",
        _make_options([25, 50, 60]),
        info_on_click=lambda e: _open_aco(page),
    )
    gamma_f_dd = _styled_dropdown(
        "Combinacao (gf)",
        "normais",
        _make_gamma_f_options(),
        info_on_click=lambda e: _open_gamma_f(page),
    )

    # ── Sidebar de armaduras ─────────────────────────────────────────────
    def _diam_options():
        return [ft.dropdown.Option(str(d)) for d in DIAM_BARRAS]

    def _diam_options_long():
        return [ft.dropdown.Option(str(d)) for d in DIAM_BARRAS_LONG]

    def _diam_options_placeholder_long():
        return [ft.dropdown.Option("", "-- Selecione --")] + [ft.dropdown.Option(str(d)) for d in DIAM_BARRAS_LONG]

    phi_est_dd = _styled_dropdown("Estribo phi_t (mm)", "5", _diam_options(), info_on_click=lambda e: _open_diametros(page))
    phi_bar_dd = _styled_dropdown("Barra phi_l (mm)", "", _diam_options_placeholder_long(), on_change=lambda e: _check_ftool_pronto(), info_on_click=lambda e: _open_diametros(page))

    # ── Fonte de entrada: manual (padrao) x FTOOL (opcional) ─────────────
    def on_abrir_ftool(e):
        """Revela o painel FTOOL: a fonte de entrada passa a ser o FTOOL."""
        state["entrada"] = ENTRADA_FTOOL
        _refresh_entrada_ui()

    def on_fechar_ftool(e):
        """Fecha o painel FTOOL e volta para a entrada manual."""
        state["entrada"] = ENTRADA_MANUAL
        _refresh_entrada_ui()

    # ── Builder de sidebar (esquerda) ────────────────────────────────────
    def build_sidebar():
        geom_card = surface_card(
            ft.Column(
                controls=[
                    section_header("Geometria", icon=ft.Icon(ft.Icons.SQUARE_OUTLINED, size=16, color=Palette.TEXT_SECONDARY)),
                    viga_nome_tf,
                    *geom_widgets,
                ],
                spacing=Spacing.MD,
            ),
            padding=Spacing.LG,
        )

        resp_card = surface_card(
            ft.Column(
                controls=[
                    section_header("Responsabilidade Técnica", icon=ft.Icon(ft.Icons.PERSON_OUTLINE, size=16, color=Palette.TEXT_SECONDARY)),
                    prof_dd,
                    resp_nome_tf,
                    resp_registro_tf,
                ],
                spacing=Spacing.MD,
            ),
            padding=Spacing.LG,
        )

        mat_card = surface_card(
            ft.Column(
                controls=[
                    section_header("Materiais", icon=ft.Icon(ft.Icons.SCIENCE_OUTLINED, size=16, color=Palette.TEXT_SECONDARY)),
                    caa_dd, fck_dd, fyk_dd, fyke_dd, gamma_f_dd,
                ],
                spacing=Spacing.MD,
            ),
            padding=Spacing.LG,
        )

        arm_card = surface_card(
            ft.Column(
                controls=[
                    section_header("Armaduras", icon=ft.Icon(ft.Icons.CONSTRUCTION, size=16, color=Palette.TEXT_SECONDARY)),
                    phi_est_dd, phi_bar_dd,
                ],
                spacing=Spacing.MD,
            ),
            padding=Spacing.LG,
        )

        ftool_card = surface_card(
            ft.Column(
                controls=[
                    section_header(
                        "FTOOL",
                        icon=ft.Icon(ft.Icons.AUTO_GRAPH, size=16, color=Palette.TEXT_SECONDARY),
                        action=ft.TextButton(
                            "Voltar para entrada manual",
                            icon=ft.Icons.CLOSE,
                            on_click=on_fechar_ftool,
                            style=ft.ButtonStyle(text_style=ft.TextStyle(size=11)),
                        ),
                    ),
                    ft.Text("Arquivos .txt exportados do FTOOL:", size=11, color=Palette.TEXT_SECONDARY),
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.UPLOAD_FILE, size=14, color=Palette.PRIMARY),
                            ft.Container(width=Spacing.XS),
                            ft.Text("Momentos", size=12, expand=True),
                            ft.OutlinedButton("...", icon=ft.Icons.FILE_UPLOAD, height=28, on_click=_pick_momento),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    lbl_ftool_momento,
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.UPLOAD_FILE, size=14, color=Palette.PRIMARY),
                            ft.Container(width=Spacing.XS),
                            ft.Text("Cortantes", size=12, expand=True),
                            ft.OutlinedButton("...", icon=ft.Icons.FILE_UPLOAD, height=28, on_click=_pick_cortante),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    lbl_ftool_cortante,
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.UPLOAD_FILE, size=14, color=Palette.PRIMARY),
                            ft.Container(width=Spacing.XS),
                            ft.Text("Deformações", size=12, expand=True),
                            ft.OutlinedButton("...", icon=ft.Icons.FILE_UPLOAD, height=28, on_click=_pick_deformacao),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    lbl_ftool_deformacao,
                    btn_processar_ftool,
                    ft.Divider(height=1, color=Palette.OUTLINE_VARIANT),
                    ft.Text("Envelope de Combinações", size=12, weight=ft.FontWeight.BOLD),
                    combs_column,
                    ft.Row(
                        controls=[
                            ft.OutlinedButton(
                                "Adicionar", icon=ft.Icons.ADD,
                                icon_color=Palette.PRIMARY, height=32,
                                style=ft.ButtonStyle(text_style=ft.TextStyle(size=12)),
                                on_click=on_add_comb_click,
                            ),
                            btn_calc_envelope,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        wrap=True,
                    )
                ],
                spacing=Spacing.SM,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=Spacing.LG,
        )

        # Entrada alternativa: revela o painel FTOOL (fonte de entrada opcional)
        ftool_entry_card = surface_card(
            ft.Column(
                controls=[
                    section_header(
                        "Dados do FTOOL (opcional)",
                        icon=ft.Icon(ft.Icons.AUTO_GRAPH, size=16, color=Palette.TEXT_SECONDARY),
                    ),
                    ft.Text(
                        "Ou calcule a viga a partir dos arquivos .txt "
                        "exportados do FTOOL.",
                        size=11, color=Palette.TEXT_SECONDARY,
                    ),
                    ft.Container(height=Spacing.SM),
                    tonal_button(
                        "Importar do FTOOL",
                        icon=ft.Icons.UPLOAD_FILE,
                        on_click=on_abrir_ftool,
                        expand=True,
                    ),
                ],
                spacing=Spacing.SM,
            ),
            padding=Spacing.LG,
        )

        return ft.Column(
            controls=[
                geom_card,
                resp_card,
                mat_card,
                arm_card,
                ftool_card if ftool_visivel(state["entrada"]) else ftool_entry_card,
            ],
            spacing=Spacing.MD,
            scroll=ft.ScrollMode.AUTO,
        )

    # ── Builder de tab de trechos (centro, dinamico) ──────────────────────

    def _make_trecho_field(prefix, idx, value=""):
        """Cria um TextField de trecho (M1, M2, ...)."""
        hint = "Ex: 50,5" if prefix == "M" else "Ex: 80,0"

        def _on_change_trecho(e):
            if "." in e.control.value:
                e.control.value = e.control.value.replace(".", ",")
                e.control.update()
            validate_trecho_field(e)

        return ft.TextField(
            label=f"{prefix}{idx}",
            value=value,
            text_size=13, filled=True, dense=True,
            bgcolor=Palette.SURFACE_VARIANT,
            border_radius=br_all(Radius.SM),
            border_color=Palette.OUTLINE_VARIANT,
            focused_border_color=Palette.PRIMARY,
            cursor_color=Palette.PRIMARY,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            hint_text=hint,
            on_change=_on_change_trecho,
            expand=True,
        )

    def _init_rows(target_list, prefix):
        """Inicializa a lista com DEFAULT_TRECHOS campos."""
        target_list.clear()
        for i in range(DEFAULT_TRECHOS):
            target_list.append(_make_trecho_field(prefix, i + 1))

    def _read_signals(rows):
        """Le momentos com sinal: vazio = 0. Aceita vírgula ou ponto como separador decimal."""
        vals = []
        for tf in rows:
            try:
                v = float(tf.value.replace(",", ".")) if tf.value.strip() else 0.0
                vals.append(v)
            except ValueError:
                vals.append(0.0)
        return vals

    _init_rows(md_rows, "M")
    _init_rows(vk_rows, "V")

    def build_trechos_panel(page, target_list, prefix):
        """Painel dinamico de trechos com botao + e lixeira por linha."""
        rows_container = ft.Column(spacing=Spacing.XS)

        def _make_row(idx, tf):
            trash = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color=Palette.ERROR,
                icon_size=20,
                tooltip="Remover trecho",
                on_click=lambda e: _remove(idx),
            )
            return ft.Row(
                controls=[
                    ft.Container(content=tf, expand=True),
                    trash,
                ],
                spacing=Spacing.XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        def _rebuild():
            rows_container.controls.clear()
            for i, tf in enumerate(target_list):
                tf.label = f"{prefix}{i + 1}"
                rows_container.controls.append(_make_row(i, tf))
            add_btn.disabled = len(target_list) >= MAX_TRECHOS
            add_btn.text = (
                f"Maximo de {MAX_TRECHOS} trechos"
                if len(target_list) >= MAX_TRECHOS
                else "Adicionar trecho"
            )
            try:
                page.update()
            except (AssertionError, RuntimeError):
                # Flet page.update() pode falhar se a pagina foi fechada
                pass

        def _add(e):
            if len(target_list) >= MAX_TRECHOS:
                return
            target_list.append(_make_trecho_field(prefix, len(target_list) + 1))
            _rebuild()

        def _remove(idx):
            if len(target_list) <= 1:
                return
            target_list.pop(idx)
            _rebuild()

        add_btn = tonal_button(
            "Adicionar trecho",
            icon=ft.Icons.ADD,
            on_click=_add,
            expand=True,
        )

        panel_rebuilds[prefix] = _rebuild
        _rebuild()

        return surface_card(
            ft.Column(
                controls=[
                    section_header(
                        f"Trechos de {'flexão' if prefix == 'M' else 'cisalhamento'} ({prefix}1 a {prefix}{MAX_TRECHOS})",
                        icon=ft.Icon(
                            ft.Icons.LIST_ALT if prefix == "M" else ft.Icons.SWAP_VERT,
                            size=16, color=Palette.TEXT_SECONDARY,
                        ),
                    ),
                    caption(
                        "Use sinal negativo (-) para momentos negativos. " if prefix == "M"
                        else "Forcas cortantes em kN (com sinal). ",
                        color=Palette.TEXT_SECONDARY,
                    ),
                    ft.Container(height=Spacing.SM),
                    rows_container,
                    ft.Container(height=Spacing.MD),
                    add_btn,
                ],
                spacing=Spacing.SM,
            ),
            padding=Spacing.LG,
        )

    # ── Status e mensagens ───────────────────────────────────────────────
    def show_msg(msg, color=Palette.SUCCESS):
        is_error_or_warn = color in (Palette.ERROR, Palette.WARNING)
        duration = 6000 if is_error_or_warn else 3000
        action = "OK" if is_error_or_warn else None
        
        sb = ft.SnackBar(
            content=ft.Text(msg, color=Palette.ON_PRIMARY),
            bgcolor=color,
            duration=duration,
            action=action,
            open=True,
        )
        
        def close_sb(e):
            sb.open = False
            page.update()
            
        sb.on_action = close_sb
        page.overlay.append(sb)
        page.update()

    # ── Calcular ──────────────────────────────────────────────────────────
    def on_calculate(e):
        if not run_manual_validations():
            show_msg("Por favor, corrija os erros de validação nos campos em vermelho.", Palette.ERROR)
            return
            
        state["tipo_viga"] = viga_nome_tf.control.value or ("V1" if modo == "comum" else "VT1")
        try:
            # Validar d (altura util) > 0 antes de calcular
            cob_mm_est = CAA_DATA.get(int(caa_dd.control.value or 2), {}).get("cobrimento", 30)
            d_lin_est = cob_mm_est / 10 + float(phi_est_dd.control.value or 5) / 10 + float(phi_bar_dd.control.value or 16) / 20
            h = float(h_tf.control.value or 0)
            bw = float(bw_tf.control.value or 0)
            if h <= d_lin_est:
                show_msg(f"Altura h={h} cm incorreta. d'={d_lin_est:.1f} cm. h deve ser maior.", Palette.ERROR)
                return
            if bw <= 5:
                show_msg(f"Largura bw={bw} cm muito pequena (min 5 cm).", Palette.ERROR)
                return
            fck = float(fck_dd.control.value or 0)
            fyk = float(fyk_dd.control.value or 0)
            fyke = float(fyke_dd.control.value or 0)
            caa = int(caa_dd.control.value)
            diam_est = float(phi_est_dd.control.value)
            diam_bar = float(phi_bar_dd.control.value)
            gamma_f = GAMMA_F_TABLE[gamma_f_dd.control.value]["gamma_f"]
        except (ValueError, KeyError, TypeError) as ex:
            show_msg(f"Verifique os campos de entrada: {ex}", Palette.WARNING)
            return

        momentos = _read_signals(md_rows)
        cortantes = _read_signals(vk_rows)

        # ── Flexao ──
        try:
            if is_t:
                bf = float(bf_tf.control.value or 0)
                hf = float(hf_tf.control.value or 0)
                # Ler b1 dos campos ou calcular default (bf-bw)/2
                b1e_str = b1esq_tf.control.value.strip().replace(",", ".")
                b1d_str = b1dir_tf.control.value.strip().replace(",", ".")
                b1e = float(b1e_str) if b1e_str else max(0.0, (bf - bw) / 2.0)
                b1d = float(b1d_str) if b1d_str else max(0.0, (bf - bw) / 2.0)
                res_flex = calcular_flexao_viga_t(
                    h_cm=h, bw_cm=bw, bf_cm=bf, hf_cm=hf,
                    caa=caa, fck_mpa=fck,
                    diam_estribo_mm=diam_est, diam_barra_mm=diam_bar,
                    fyk_mpa=fyk, momentos=momentos,
                    b1esq_cm=b1e, b1dir_cm=b1d,
                    gamma_f=gamma_f,
                )
            else:
                res_flex = calcular_flexao_viga_comum(
                    h_cm=h, bw_cm=bw, caa=caa, fck_mpa=fck,
                    diam_estribo_mm=diam_est, diam_barra_mm=diam_bar,
                    fyk_mpa=fyk, momentos=momentos,
                    gamma_f=gamma_f,
                )
        except (ValueError, TypeError, ZeroDivisionError, ArithmeticError) as ex:
            show_msg(f"Falha no cálculo de flexão: {ex}", Palette.ERROR)
            return

        # ── Cisalhamento (viga comum e viga T - usa largura da alma bw) ──
        res_cis = None
        try:
            res_cis = calcular_cisalhamento_viga_comum(
                h_cm=h, bw_cm=bw, fck_mpa=fck,
                diam_estribo_mm=diam_est, diam_barra_mm=diam_bar,
                fyk_estribo_mpa=fyke, fyk_barra_mpa=fyk,
                caa=caa, forcas_cortantes=cortantes,
                gamma_f=gamma_f,
            )
        except (ValueError, TypeError, ZeroDivisionError, ArithmeticError) as ex:
            show_msg(f"Falha no cálculo de cisalhamento: {ex}", Palette.ERROR)
            res_cis = None

        state["resultados_flex"] = deepcopy(res_flex)
        state["resultados_cis"] = deepcopy(res_cis) if res_cis else None
        # Habilita Gerar PDF apos calculo bem-sucedido
        btn_gerar_pdf.disabled = False
        btn_exportar_dxf.disabled = False
        page.update()
        show_msg("Cálculos concluídos com sucesso", Palette.SUCCESS)
        open_resultados_modal()

    # ── Envelope de Combinações ──────────────────────────────────────────
    lbl_momento = ft.Text("Nenhum selecionado", size=11, color=Palette.TEXT_DISABLED, expand=True)
    lbl_cortante = ft.Text("Nenhum selecionado", size=11, color=Palette.TEXT_DISABLED, expand=True)
    fp_momento_env = ft.FilePicker()
    fp_cortante_env = ft.FilePicker()
    page.services.append(fp_momento_env)
    page.services.append(fp_cortante_env)

    async def select_momento_click(e):
        await fp_momento_env.pick_files(dialog_title="Selecionar arquivo de momentos (.txt)", allowed_extensions=["txt"])
    async def select_cortante_click(e):
        await fp_cortante_env.pick_files(dialog_title="Selecionar arquivo de cortantes (.txt)", allowed_extensions=["txt"])

    def on_momento_env_result(e):
        if e.files:
            state["temp_momento_path"] = e.files[0].path
            lbl_momento.value = os.path.basename(e.files[0].path)
            lbl_momento.color = Palette.TEXT_PRIMARY
            lbl_momento.update()
    def on_cortante_env_result(e):
        if e.files:
            state["temp_cortante_path"] = e.files[0].path
            lbl_cortante.value = os.path.basename(e.files[0].path)
            lbl_cortante.color = Palette.TEXT_PRIMARY
            lbl_cortante.update()
    fp_momento_env.on_result = on_momento_env_result
    fp_cortante_env.on_result = on_cortante_env_result

    # ── FTOOL File Pickers Individuais ──────────────────────────────────
    fp_pick = ft.FilePicker()
    page.services.append(fp_pick)

    def _make_ftool_picker(tipo):
        lbl_map = {"momento": lbl_ftool_momento, "cortante": lbl_ftool_cortante, "deformacao": lbl_ftool_deformacao}
        state_key = f"ftool_{tipo}_path"
        async def _pick(e):
            files = await fp_pick.pick_files(dialog_title=f"Selecionar arquivo de {tipo}s (.txt)", allowed_extensions=["txt"])
            if files:
                filepath = files[0].path
                valido, msg_erro = validate_file_type(filepath, tipo)
                if not valido:
                    show_msg(f"Arquivo inválido: {msg_erro}", Palette.ERROR)
                    return

                state[state_key] = filepath
                state["ftool_momentos"] = None
                state["ftool_cortantes"] = None
                state["ftool_deformacoes"] = None
                state["ftool_secoes_criticas"] = None
                lbl = lbl_map[tipo]
                lbl.value = os.path.basename(filepath)
                lbl.color = Palette.TEXT_PRIMARY
                lbl.update()
                _check_ftool_pronto()
        return _pick

    _pick_momento = _make_ftool_picker("momento")
    _pick_cortante = _make_ftool_picker("cortante")
    _pick_deformacao = _make_ftool_picker("deformacao")

    def _check_ftool_pronto():
        arquivos_ok = all(state.get(k) for k in ("ftool_momento_path", "ftool_cortante_path", "ftool_deformacao_path"))
        dados_ok = state.get("ftool_momentos") is not None  # dados ja carregados (ex: projeto salvo)
        try:
            h_ok = float(h_tf.control.value.replace(",", ".") or 0) > 0
            bw_ok = float(bw_tf.control.value.replace(",", ".") or 0) > 0
            phi_ok = float(phi_bar_dd.control.value or 0) > 0
        except (ValueError, TypeError, AttributeError):
            h_ok = bw_ok = phi_ok = False

        faltando = []
        if not arquivos_ok and not dados_ok: faltando.append("3 arquivos TXT")
        if not h_ok: faltando.append("altura h")
        if not bw_ok: faltando.append("largura bw")
        if not phi_ok: faltando.append("φ barra")
        btn_processar_ftool.disabled = len(faltando) > 0
        btn_processar_ftool.tooltip = f"Preencha: {', '.join(faltando)}" if faltando else "Processar arquivos FTOOL"
        page.update()

    def processar_ftool():
        # Validar geometria antes de processar
        try:
            h_val = float(h_tf.control.value.replace(",", ".")) if h_tf.control.value.strip() else 0
            bw_val = float(bw_tf.control.value.replace(",", ".")) if bw_tf.control.value.strip() else 0
            phi_val = float(phi_bar_dd.control.value) if phi_bar_dd.control.value else 0
        except (ValueError, AttributeError):
            h_val = bw_val = phi_val = 0
        if h_val <= 0 or bw_val <= 0 or phi_val <= 0:
            show_msg("Preencha h, bw e o diâmetro da armadura antes de importar o FTOOL", Palette.WARNING)
            return

        # Loading spinner
        loading = ft.AlertDialog(
            modal=True,
            content=ft.Container(
                content=ft.Column([
                    ft.ProgressRing(width=48, height=48, color=Palette.PRIMARY),
                    ft.Container(height=Spacing.MD),
                    ft.Text("Processando dados do FTOOL...", size=14, color=Palette.TEXT_SECONDARY),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=pad_all(Spacing.XL),
            ),
            bgcolor=ft.Colors.TRANSPARENT,
        )
        page.show_dialog(loading)
        page.update()

        try:
            # Verifica se os arquivos físicos existem localmente na máquina
            arquivos_existem = False
            try:
                arquivos_existem = all(
                    state.get(k) and os.path.exists(state[k])
                    for k in ("ftool_momento_path", "ftool_cortante_path", "ftool_deformacao_path")
                )
            except Exception:
                pass

            if arquivos_existem:
                # Força a re-leitura do disco para garantir sincronia com os arquivos mais recentes
                from ui.ftool.parser import parse_momento, parse_cortante, parse_deformacao
                momentos = parse_momento(state["ftool_momento_path"])
                cortantes = parse_cortante(state["ftool_cortante_path"])
                deformacoes = parse_deformacao(state["ftool_deformacao_path"])
                secoes = detectar_todas_secoes(momentos, cortantes)
                state["ftool_momentos"] = momentos
                state["ftool_cortantes"] = cortantes
                state["ftool_deformacoes"] = deformacoes
                state["ftool_secoes_criticas"] = secoes
            elif state.get("ftool_momentos") and state.get("ftool_cortantes"):
                # Fallback: se os arquivos não existem localmente, reutiliza os dados restaurados do JSON
                momentos = state["ftool_momentos"]
                cortantes = state["ftool_cortantes"]
                secoes = state.get("ftool_secoes_criticas") or detectar_todas_secoes(momentos, cortantes)
                deformacoes = state.get("ftool_deformacoes")
                if not deformacoes:
                    try:
                        from ui.ftool.parser import parse_deformacao
                        # Primeiro tenta do path salvo
                        path = state.get("ftool_deformacao_path")
                        if path and os.path.exists(path):
                            deformacoes = parse_deformacao(path)
                        # Fallback: tenta samples/
                        else:
                            path = state.get("ftool_path", "")
                            base = os.path.dirname(path) if path else "samples"
                            candidates = [f for f in os.listdir(base) if "deformac" in f.lower() and f.endswith(".txt")]
                            if candidates:
                                deformacoes = parse_deformacao(os.path.join(base, candidates[0]))
                        if deformacoes:
                            state["ftool_deformacoes"] = deformacoes
                    except Exception:
                        deformacoes = []
                if not deformacoes:
                    deformacoes = []
            else:
                # Se não existem arquivos e não há esforços pré-carregados no state, tenta ler dos paths salvos (deve falhar)
                from ui.ftool.parser import parse_momento, parse_cortante, parse_deformacao
                momentos = parse_momento(state["ftool_momento_path"])
                cortantes = parse_cortante(state["ftool_cortante_path"])
                deformacoes = parse_deformacao(state["ftool_deformacao_path"])
                secoes = detectar_todas_secoes(momentos, cortantes)
                state["ftool_momentos"] = momentos
                state["ftool_cortantes"] = cortantes
                state["ftool_deformacoes"] = deformacoes
                state["ftool_secoes_criticas"] = secoes
            page.update()
            _atualizar_viewer()

            rows = [
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(f"{s.x:.2f} m")),
                    ft.DataCell(ft.Text(f"{s.momento:.2f}")),
                    ft.DataCell(ft.Text(f"{s.cortante:.2f}")),
                    ft.DataCell(ft.Text(s.tipo)),
                    ft.DataCell(ft.Text(s.descricao[:25] + ".." if len(s.descricao) > 25 else s.descricao)),
                ]) for s in secoes
            ]
            table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("x (m)")), ft.DataColumn(ft.Text("Mk (kN·m)")),
                    ft.DataColumn(ft.Text("Vk (kN)")), ft.DataColumn(ft.Text("Tipo")),
                    ft.DataColumn(ft.Text("Descrição")),
                ], rows=rows, heading_row_color=Palette.SURFACE_VARIANT, divider_thickness=1,
            )
            table_container = ft.Container(content=ft.Column([table], scroll=ft.ScrollMode.AUTO), height=300)

            def _build_resultados_controls(state, dados_viga, secoes, page, show_msg):
                """Monta a lista de controles do modal de resultados (flexão, cisalhamento, ELS)."""
                resultado_els = state.get("ftool_resultado_els")
                detalhamento = state.get("ftool_detalhamento")
                
                flex_cards = ft.Row(spacing=Spacing.MD, scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
                sec_results = []
                for i, secao in enumerate(secoes):
                    rf = state["resultados_flex"][i] if i < len(state["resultados_flex"]) else None
                    rc = state["resultados_cis"][i] if i < len(state["resultados_cis"]) else None
                    sec_results.append({
                        "x": secao.x,
                        "momento": secao.momento,
                        "cortante": secao.cortante,
                        "resultado_flexao": rf,
                        "resultado_cisalhamento": rc,
                        "tipo": secao.tipo,
                        "descricao": secao.descricao,
                    })
                
                for item in sec_results:
                    r = item["resultado_flexao"]
                    if r is None:
                        continue
                    card = ft.Container(
                        width=220,
                        padding=pad_all(Spacing.SM),
                        border=border_all(1, Palette.OUTLINE_VARIANT),
                        border_radius=br_all(Radius.SM),
                        content=ft.Column([
                            ft.Text(f"{item['descricao']}", size=11, weight=ft.FontWeight.BOLD, color=Palette.PRIMARY),
                            ft.Text(f"x = {item['x']:.2f} m", size=10, color=Palette.TEXT_SECONDARY),
                            ft.Container(height=Spacing.XS),
                            ft.Row([ft.Text("Md:", size=10, color=Palette.TEXT_SECONDARY), ft.Text(f"{r.momento_kNm * dados_viga.get('gamma_f', 1.4):.1f} kN·m", size=10, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("As:", size=10, color=Palette.TEXT_SECONDARY), ft.Text(f"{r.as_req_cm2:.2f} cm²", size=10, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("Adotado:", size=10, color=Palette.TEXT_SECONDARY), ft.Text(f"{r.qtd_barras}φ{r.diametro_mm:.1f} ({r.as_usado_cm2:.2f} cm²)", size=10)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("Status:", size=10, color=Palette.TEXT_SECONDARY), status_chip("OK" if r.bx_passa else "NÃO PASSA", "ok" if r.bx_passa else "error")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ], spacing=3)
                    )
                    flex_cards.controls.append(card)
                
                rows_cis = []
                for item in sec_results:
                    r = item["resultado_cisalhamento"]
                    if r is None:
                        continue
                    label = f"x={item['x']:.2f}m"
                    status_label = "OK" if r.passa_vrd2 == "SIM" else "NAO"
                    rows_cis.append(ft.DataRow(cells=[
                        ft.DataCell(title_small(label, color=Palette.TEXT_PRIMARY)),
                        ft.DataCell(body_small(f"{r.vsd_verdadeiro_kn:.1f} kN", color=Palette.TEXT_PRIMARY)),
                        ft.DataCell(body_small(f"{r.vrd2_kn:.1f} kN", color=Palette.TEXT_PRIMARY)),
                        ft.DataCell(body_small(f"{r.vsw_kn:.1f} kN", color=Palette.TEXT_PRIMARY)),
                        ft.DataCell(body_small(f"{r.dist_estribos_cm:.1f} cm", color=Palette.TEXT_PRIMARY)),
                        ft.DataCell(status_chip(status_label, "ok" if r.passa_vrd2 == "SIM" else "error")),
                    ]))
                
                controls_resultados = [
                    section_header("Flexão (Dimensionamento por seção crítica)", icon=ft.Icon(ft.Icons.SQUARE_OUTLINED, size=16, color=Palette.PRIMARY)),
                    ft.Container(height=Spacing.SM), flex_cards,
                    ft.Container(height=Spacing.LG),
                    section_header("Cisalhamento", icon=ft.Icon(ft.Icons.SWAP_VERT, size=16, color=Palette.PRIMARY)),
                    ft.Container(height=Spacing.SM),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(title_small("Seção")), ft.DataColumn(title_small("Vsolic (kN)")),
                            ft.DataColumn(title_small("Vrd2 (kN)")), ft.DataColumn(title_small("Vsw (kN)")),
                            ft.DataColumn(title_small("Espaçamento")), ft.DataColumn(title_small("Status")),
                        ], rows=rows_cis,
                        heading_row_height=Spacing.XL + 8, data_row_min_height=Spacing.XL + 4,
                        border=border_all(1, Palette.OUTLINE_VARIANT), border_radius=br_all(Radius.SM),
                        vertical_lines=ft.BorderSide(1, Palette.OUTLINE_VARIANT), horizontal_lines=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
                    ) if rows_cis else caption("Nenhum trecho calculado.", color=Palette.TEXT_DISABLED),
                ]
                
                if detalhamento:
                    controls_resultados.extend([
                        ft.Container(height=Spacing.LG),
                        section_header("Detalhamento de Estribos", icon=ft.Icon(ft.Icons.SWAP_VERT, size=16, color=Palette.PRIMARY)),
                        ft.Container(height=Spacing.SM),
                        ft.DataTable(
                            columns=[
                                ft.DataColumn(title_small("Trecho")), ft.DataColumn(title_small("φ")),
                                ft.DataColumn(title_small("Esp.")), ft.DataColumn(title_small("Asw/s")),
                            ],
                            rows=[ft.DataRow(cells=[
                                ft.DataCell(body_small(f"{r['x_inicio']:.1f}–{r['x_fim']:.1f}m")),
                                ft.DataCell(body_small(f"{r['phi_mm']:.0f}mm")),
                                ft.DataCell(body_small(f"{r['espacamento_cm']:.0f}cm")),
                                ft.DataCell(body_small(f"{r['asw_s_cm2m']:.2f}")),
                            ]) for r in detalhamento],
                            heading_row_height=Spacing.XL + 4, data_row_min_height=Spacing.XL + 2,
                            border=border_all(1, Palette.OUTLINE_VARIANT), border_radius=br_all(Radius.SM),
                            horizontal_lines=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
                        ),
                    ])
                
                if resultado_els:
                    controls_resultados.extend([
                        ft.Container(height=Spacing.LG),
                        section_header("ELS — Flecha e Fissuração", icon=ft.Icon(ft.Icons.STRAIGHTEN, size=16, color=Palette.PRIMARY)),
                        ft.Container(height=Spacing.SM),
                        ft.Text("Flecha", size=12, weight=ft.FontWeight.BOLD),
                        ft.Row([ft.Text("Total:", size=11, color=Palette.TEXT_SECONDARY), ft.Text(f"{resultado_els['flecha']['flecha_total_cm']:.2f} cm", size=11, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([ft.Text("Limite L/250:", size=11, color=Palette.TEXT_SECONDARY), ft.Text(f"{resultado_els['flecha']['limite_total_cm']:.2f} cm", size=11, weight=ft.FontWeight.BOLD, color=Palette.SUCCESS if resultado_els['flecha']['passa_total'] else Palette.ERROR)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ])
                    
                    if not resultado_els['flecha']['passa_total'] and resultado_els['flecha'].get('dica'):
                        controls_resultados.extend([
                            ft.Container(height=Spacing.XS),
                            ft.Text(resultado_els['flecha'].get('dica', ''), size=9, color=Palette.ERROR, italic=True),
                        ])
                    
                    controls_resultados.extend([
                        ft.Container(height=Spacing.SM),
                        ft.Text("Fissuração", size=12, weight=ft.FontWeight.BOLD),
                        ft.Row([ft.Text("w_k:", size=11, color=Palette.TEXT_SECONDARY), ft.Text(f"{resultado_els['fissuracao']['wk_mm']:.2f} mm", size=11, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([ft.Text("w_lim:", size=11, color=Palette.TEXT_SECONDARY), ft.Text(f"{resultado_els['fissuracao']['wk_limite_mm']:.1f} mm", size=11, weight=ft.FontWeight.BOLD, color=Palette.SUCCESS if resultado_els['fissuracao']['passa'] else Palette.ERROR)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([
                            status_chip("OK", "ok") if resultado_els['fissuracao']['passa'] else status_chip("NÃO PASSA", "error"),
                            ft.Container(width=Spacing.SM),
                            status_chip("OK", "ok") if resultado_els['flecha']['passa_total'] else status_chip("NÃO PASSA", "error"),
                        ]),
                    ])
                    
                    if not resultado_els['fissuracao']['passa'] and resultado_els['fissuracao'].get('dica'):
                        controls_resultados.extend([
                            ft.Container(height=Spacing.XS),
                            ft.Text(resultado_els['fissuracao'].get('dica', ''), size=9, color=Palette.ERROR, italic=True),
                        ])
                    
                    if not resultado_els['flecha']['passa_total'] or not resultado_els['fissuracao']['passa']:
                        controles_ajustes = _criar_painel_ajustes_els(
                            resultado_els, state, dados_viga, secoes,
                            state.get("ftool_momentos"),
                            state.get("ftool_cortantes"),
                            state.get("ftool_deformacoes"),
                            page, show_msg
                        )
                        controls_resultados.extend(controles_ajustes)
                else:
                    controls_resultados.append(ft.Text("ELS não disponível (sem dados de deformação)", size=11, color=Palette.TEXT_DISABLED))
                
                return controls_resultados

            def _mostrar_modal_resultados(state, dados_viga, secoes, momentos, cortantes, deformacoes, page, show_msg):
                """Constrói e exibe o modal de resultados do dimensionamento."""
                controls_resultados = _build_resultados_controls(state, dados_viga, secoes, page, show_msg)
                
                results_content = ft.Column(
                    controls=controls_resultados,
                    spacing=0,
                    scroll=ft.ScrollMode.AUTO,
                )
                
                state["_modal_results_content"] = results_content
                
                page.show_dialog(ft.AlertDialog(
                    modal=True,
                    title=ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=Palette.SUCCESS), ft.Container(width=Spacing.SM), title_medium("Resultados do dimensionamento FTOOL")], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    content=ft.Container(content=results_content, width=800, height=540, padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.SM)),
                    actions=[ft.OutlinedButton("Fechar", on_click=lambda ev: page.pop_dialog())], actions_alignment=ft.MainAxisAlignment.END,
                    bgcolor=Palette.SURFACE, shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG))))

            def _criar_painel_ajustes_els(resultado_els, state, dados_viga, secoes, momentos, cortantes, deformacoes, page, show_msg):
                """Cria painel de ajustes manuais para ELS quando não passa."""
                from ui.ftool.els import AjustesELS
                from ui.ftool.dimensionamento import dimensionar_trechos_ftool
                
                # Controles do painel
                chk_barras = ft.Checkbox(label="Adicionar barras extras", value=False)
                spn_barras = ft.TextField(value="2", width=80, text_size=13, disabled=True)
                
                chk_phi = ft.Checkbox(label="Forçar diâmetro mínimo", value=False)
                dd_phi = ft.Dropdown(
                    options=[ft.dropdown.Option(str(d)) for d in [10, 12.5, 16, 20, 25]],
                    value="16", width=100, disabled=True
                )
                
                chk_h = ft.Checkbox(label="Aumentar h para", value=False)
                tf_h = ft.TextField(value="", width=100, disabled=True, hint_text=f"{dados_viga['h_cm']:.0f}")
                
                chk_fck = ft.Checkbox(label="Aumentar fck para", value=False)
                dd_fck = ft.Dropdown(
                    options=[ft.dropdown.Option(str(f)) for f in [25, 30, 35, 40, 45, 50]],
                    value="35", width=100, disabled=True
                )
                
                # Habilitar/desabilitar campos
                def toggle_barras(e):
                    spn_barras.disabled = not chk_barras.value
                    spn_barras.update()
                def toggle_phi(e):
                    dd_phi.disabled = not chk_phi.value
                    dd_phi.update()
                def toggle_h(e):
                    tf_h.disabled = not chk_h.value
                    tf_h.update()
                def toggle_fck(e):
                    dd_fck.disabled = not chk_fck.value
                    dd_fck.update()
                
                chk_barras.on_change = toggle_barras
                chk_phi.on_change = toggle_phi
                chk_h.on_change = toggle_h
                chk_fck.on_change = toggle_fck
                
                def on_recalcular(e):
                    """Recalcula ELS com os ajustes aplicados e atualiza o modal in-place."""
                    try:
                        ajustes = AjustesELS(
                            barras_extras=int(spn_barras.value) if chk_barras.value else 0,
                            phi_minimo_mm=float(dd_phi.value) if chk_phi.value else None,
                            h_override_cm=float(tf_h.value) if chk_h.value and tf_h.value else None,
                            fck_override_mpa=float(dd_fck.value) if chk_fck.value else None,
                        )
                        
                        resultados = dimensionar_trechos_ftool(
                            dados_viga, secoes,
                            momentos=state.get("ftool_momentos"),
                            cortantes=state.get("ftool_cortantes"),
                            deformacoes=state.get("ftool_deformacoes"),
                            ajustes_els=ajustes,
                        )
                        
                        resultado_els_novo = resultados.get("els")
                        state["ftool_resultado_els"] = resultado_els_novo
                        state["ftool_ajustes_els"] = ajustes
                        
                        sec_results = resultados["secoes"]
                        state["resultados_flex"] = [r["resultado_flexao"] for r in sec_results]
                        state["resultados_cis"] = [r["resultado_cisalhamento"] for r in sec_results]
                        state["ftool_detalhamento"] = resultados.get("detalhamento")
                        
                        # Atualizar conteúdo do modal in-place (sem fechar/reabrir)
                        results_content = state.get("_modal_results_content")
                        if results_content is not None:
                            novos_controles = _build_resultados_controls(state, dados_viga, secoes, page, show_msg)
                            results_content.controls = novos_controles
                            results_content.update()
                        else:
                            _mostrar_modal_resultados(
                                state, dados_viga, secoes,
                                state.get("ftool_momentos"),
                                state.get("ftool_cortantes"),
                                state.get("ftool_deformacoes"),
                                page, show_msg
                            )
                        
                    except Exception as ex:
                        show_msg(f"Erro ao recalcular: {ex}", Palette.ERROR)
                
                # Retornar controles do painel
                return [
                    ft.Container(height=Spacing.LG),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Ajustes Manuais para ELS", size=14, weight=ft.FontWeight.BOLD, color=Palette.PRIMARY),
                            ft.Container(height=Spacing.SM),
                            ft.Row([chk_barras, spn_barras, ft.Text("barras", size=11)]),
                            ft.Row([chk_phi, dd_phi]),
                            ft.Row([chk_h, tf_h, ft.Text("cm", size=11)]),
                            ft.Row([chk_fck, dd_fck, ft.Text("MPa", size=11)]),
                            ft.Container(height=Spacing.SM),
                            ft.ElevatedButton(
                                "Recalcular com Ajustes",
                                icon=ft.Icons.REFRESH,
                                on_click=on_recalcular,
                                bgcolor=Palette.PRIMARY,
                                color=Palette.ON_PRIMARY,
                            ),
                        ]),
                        padding=pad_all(Spacing.MD),
                        border=border_all(1, Palette.PRIMARY),
                        border_radius=br_all(Radius.SM),
                        bgcolor=ft.Colors.with_opacity(0.05, Palette.PRIMARY),
                    ),
                ]

            def on_calcular_ftool(ev):
                page.pop_dialog()
                # Spinner de calculo
                calc_loading = ft.AlertDialog(
                    modal=True,
                    content=ft.Container(
                        content=ft.Column([
                            ft.ProgressRing(width=48, height=48, color=Palette.PRIMARY),
                            ft.Container(height=Spacing.MD),
                            ft.Text("Calculando dimensionamento...", size=14, color=Palette.TEXT_SECONDARY),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=pad_all(Spacing.XL),
                    ),
                    bgcolor=ft.Colors.TRANSPARENT,
                )
                page.show_dialog(calc_loading)
                page.update()
                try:
                    h = float(h_tf.control.value or 0)
                    bw = float(bw_tf.control.value or 0)
                    fck = float(fck_dd.control.value or 0)
                    fyk = float(fyk_dd.control.value or 0)
                    fyke = float(fyke_dd.control.value or 0)
                    caa = int(caa_dd.control.value)
                    diam_est = float(phi_est_dd.control.value)
                    diam_bar = float(phi_bar_dd.control.value)
                    gamma_f = GAMMA_F_TABLE.get(gamma_f_dd.control.value, {}).get("gamma_f", 1.4)
                    dados_viga = {"h_cm": h, "bw_cm": bw, "caa": caa, "fck_mpa": fck,
                                   "diam_estribo_mm": diam_est, "diam_barra_mm": diam_bar,
                                   "fyk_mpa": fyk, "fyk_estribo_mpa": fyke, "fyk_barra_mpa": fyk, "gamma_f": gamma_f}
                    if is_t:
                        bf = float(bf_tf.control.value or 0)
                        hf = float(hf_tf.control.value or 0)
                        dados_viga["bf_cm"] = bf
                        dados_viga["hf_cm"] = hf
                        # Ler b1 dos campos ou calcular default (bf-bw)/2
                        b1e_str = b1esq_tf.control.value.strip().replace(",", ".")
                        b1d_str = b1dir_tf.control.value.strip().replace(",", ".")
                        dados_viga["b1esq_cm"] = float(b1e_str) if b1e_str else max(0.0, (bf - bw) / 2.0)
                        dados_viga["b1dir_cm"] = float(b1d_str) if b1d_str else max(0.0, (bf - bw) / 2.0)
                    resultados = dimensionar_trechos_ftool(dados_viga, secoes,
                        momentos=state.get("ftool_momentos"),
                        cortantes=state.get("ftool_cortantes"),
                        deformacoes=state.get("ftool_deformacoes"))
                    sec_results = resultados["secoes"]
                    state["resultados_flex"] = [r["resultado_flexao"] for r in sec_results]
                    state["resultados_cis"] = [r["resultado_cisalhamento"] for r in sec_results]
                    state["ftool_detalhamento"] = resultados.get("detalhamento")
                    state["ftool_resultado_els"] = resultados.get("els")
                    detalhamento = resultados.get("detalhamento")
                    resultado_els = resultados.get("els")
                    btn_gerar_pdf.disabled = False
                    btn_exportar_dxf.disabled = False
                    page.update()

                    page.pop_dialog()  # Fecha loading
                    
                    # Mostrar modal de resultados
                    _mostrar_modal_resultados(
                        state, dados_viga, secoes,
                        momentos, cortantes, deformacoes,
                        page, show_msg
                    )
                except Exception as ex:
                    page.pop_dialog()  # Fecha loading
                    show_msg(f"Erro no dimensionamento: {ex}", Palette.ERROR)

            page.pop_dialog()  # Fecha loading
            page.show_dialog(ft.AlertDialog(modal=True,
                title=ft.Row([ft.Icon(ft.Icons.AUTO_GRAPH, color=Palette.PRIMARY), ft.Container(width=Spacing.SM), title_medium("FTOOL - Seções Detectadas")], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                content=ft.Container(content=ft.Column([ft.Text(f"{len(secoes)} seções críticas encontradas.", size=14, color=Palette.TEXT_SECONDARY), ft.Container(height=Spacing.SM), table_container], tight=True), width=700, padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.SM)),
                actions=[ft.OutlinedButton("Cancelar", on_click=lambda ev: page.pop_dialog()), primary_button("Calcular", icon=ft.Icons.PLAY_ARROW, on_click=on_calcular_ftool)],
                actions_alignment=ft.MainAxisAlignment.END, bgcolor=Palette.SURFACE, shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG))))
        except Exception as ex:
            try: page.pop_dialog()  # Fecha loading se ainda estiver aberto
            except: pass
            show_msg(f"Erro ao processar FTOOL: {ex}", Palette.ERROR)

    def on_add_comb_click(e):
        state["temp_momento_path"] = None
        state["temp_cortante_path"] = None
        lbl_momento.value = "Nenhum selecionado"
        lbl_cortante.value = "Nenhum selecionado"
        
        name_tf = ft.TextField(
            label="Nome da Combinação",
            value=f"Combinação {len(state.get('combinacoes', [])) + 1}",
            border_color=Palette.OUTLINE_VARIANT,
            height=45,
        )
        
        def save_comb(ev):
            nome = name_tf.value.strip()
            if not nome:
                show_msg("Digite um nome para a combinação", Palette.WARNING)
                return
            if not state["temp_momento_path"] or not state["temp_cortante_path"]:
                show_msg("Selecione ambos os arquivos (momentos e cortantes)", Palette.WARNING)
                return
                
            state.setdefault("combinacoes", []).append({
                "nome": nome,
                "momento_path": state["temp_momento_path"],
                "cortante_path": state["temp_cortante_path"]
            })
            page.pop_dialog()
            update_combs_ui()
            show_msg(f"Combinação '{nome}' adicionada", Palette.SUCCESS)
            
        add_dlg = ft.AlertDialog(
            modal=True,
            title=title_medium("Adicionar Combinação FTOOL"),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        name_tf,
                        ft.Container(height=Spacing.XS),
                        ft.Text("Arquivo de Momento Fletor (x vs M):", size=12, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton("Selecionar...", on_click=select_momento_click),
                                lbl_momento,
                            ],
                            spacing=Spacing.MD,
                        ),
                        ft.Container(height=Spacing.XS),
                        ft.Text("Arquivo de Esforço Cortante (x vs V):", size=12, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton("Selecionar...", on_click=select_cortante_click),
                                lbl_cortante,
                            ],
                            spacing=Spacing.MD,
                        ),
                    ],
                    spacing=Spacing.SM,
                    tight=True,
                ),
                width=420,
                padding=pad_all(Spacing.MD),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda ev: page.pop_dialog()),
                ft.ElevatedButton("Salvar", on_click=save_comb, bgcolor=Palette.PRIMARY, color=Palette.ON_PRIMARY),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=Palette.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG)),
        )
        page.show_dialog(add_dlg)

    def on_calcular_envelope_click(e):
        try:
            from ui.ftool.parser import parse_momento, parse_cortante
            combs_parsed = []
            for c in state["combinacoes"]:
                m_pts = parse_momento(c["momento_path"])
                v_pts = parse_cortante(c["cortante_path"])
                combs_parsed.append({
                    "nome": c["nome"],
                    "momentos": m_pts,
                    "cortantes": v_pts
                })
                
            from ui.ftool.envelope import calcular_envelope, detectar_secoes_envelope, gerar_relatorio_envelope
            env = calcular_envelope(combs_parsed)
            secoes = detectar_secoes_envelope(combs_parsed, env)
            
            state["ftool_momentos"] = {"max": env["momentos_max"], "min": env["momentos_min"]}
            state["ftool_cortantes"] = {"max": env["cortantes_max"], "min": env["cortantes_min"]}
            state["ftool_secoes_criticas"] = secoes
            
            rows = []
            for sec in secoes:
                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(f"{sec.x:.2f} m")),
                            ft.DataCell(ft.Text(f"{sec.momento:.2f}")),
                            ft.DataCell(ft.Text(f"{sec.cortante:.2f}")),
                            ft.DataCell(ft.Text(sec.tipo)),
                            ft.DataCell(ft.Text(sec.origem)),
                        ]
                    )
                )
                
            table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("x (m)")),
                    ft.DataColumn(ft.Text("Mk (kN·m)")),
                    ft.DataColumn(ft.Text("Vk (kN)")),
                    ft.DataColumn(ft.Text("Tipo")),
                    ft.DataColumn(ft.Text("Origem")),
                ],
                rows=rows,
                heading_row_color=Palette.SURFACE_VARIANT,
                divider_thickness=1,
            )
            
            table_container = ft.Container(
                content=ft.Column([table], scroll=ft.ScrollMode.AUTO),
                height=300,
            )
            
            def close_env_dlg(ev):
                page.pop_dialog()
                
            def on_calcular_envelope_confirm_click(ev):
                page.pop_dialog()
                try:
                    h = float(h_tf.control.value or 0)
                    bw = float(bw_tf.control.value or 0)
                    fck = float(fck_dd.control.value or 0)
                    fyk = float(fyk_dd.control.value or 0)
                    fyke = float(fyke_dd.control.value or 0)
                    caa = int(caa_dd.control.value)
                    diam_est = float(phi_est_dd.control.value)
                    diam_bar = float(phi_bar_dd.control.value)
                    
                    try:
                        gamma_f = GAMMA_F_TABLE[gamma_f_dd.control.value]["gamma_f"]
                    except (KeyError, TypeError):
                        gamma_f = 1.4
                except (ValueError, KeyError, TypeError) as ex:
                    show_msg(f"Por favor, verifique os campos da viga: {ex}", Palette.WARNING)
                    return
                    
                dados_viga = {
                    "h_cm": h,
                    "bw_cm": bw,
                    "caa": caa,
                    "fck_mpa": fck,
                    "diam_estribo_mm": diam_est,
                    "diam_barra_mm": diam_bar,
                    "fyk_mpa": fyk,
                    "fyk_estribo_mpa": fyke,
                    "fyk_barra_mpa": fyk,
                    "gamma_f": gamma_f,
                }
                
                try:
                    from ui.ftool.dimensionamento import dimensionar_trechos_ftool
                    resultados = dimensionar_trechos_ftool(dados_viga, secoes,
                        momentos=state.get("ftool_momentos"),
                        cortantes=state.get("ftool_cortantes"),
                        deformacoes=state.get("ftool_deformacoes"))
                    sec_results = resultados["secoes"]
                    
                    state["resultados_flex"] = [res["resultado_flexao"] for res in sec_results]
                    state["resultados_cis"] = [res["resultado_cisalhamento"] for res in sec_results]
                    
                    btn_gerar_pdf.disabled = False
                    btn_exportar_dxf.disabled = False
                    page.update()
                    
                    relatorio_text = gerar_relatorio_envelope(dados_viga, env, secoes)
                    
                    results_dlg = ft.AlertDialog(
                        modal=True,
                        title=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.CHECK_CIRCLE, color=Palette.SUCCESS),
                                ft.Container(width=Spacing.SM),
                                title_medium("Dimensionamento Premium - Envelope"),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        content=ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text("Dimensionamento concluído com base no envelope de combinações.", size=14, color=Palette.TEXT_SECONDARY),
                                    ft.Container(height=Spacing.SM),
                                    ft.TextField(
                                        value=relatorio_text,
                                        multiline=True,
                                        read_only=True,
                                        text_size=12,
                                        text_style=ft.TextStyle(font_family="monospace"),
                                        expand=True,
                                        bgcolor=Palette.SURFACE_VARIANT,
                                        border_color=Palette.OUTLINE_VARIANT,
                                    )
                                ],
                                expand=True,
                            ),
                            width=800, height=540,
                            padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.SM),
                        ),
                        actions=[
                            ft.OutlinedButton(
                                "Fechar",
                                on_click=lambda ev2: page.pop_dialog(),
                            ),
                        ],
                        actions_alignment=ft.MainAxisAlignment.END,
                        bgcolor=Palette.SURFACE,
                        shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG)),
                    )
                    page.show_dialog(results_dlg)
                except Exception as ex:
                    show_msg(f"Erro no dimensionamento do envelope: {ex}", Palette.ERROR)
            
            env_dlg = ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.AUTO_GRAPH, color=Palette.PRIMARY),
                        ft.Container(width=Spacing.SM),
                        title_medium("Envelope - Seções Críticas"),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(f"Identificadas {len(secoes)} seções críticas a partir do envelope das combinações.", size=14, color=Palette.TEXT_SECONDARY),
                            ft.Container(height=Spacing.SM),
                            table_container,
                        ],
                        tight=True,
                    ),
                    width=750,
                    padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.SM),
                ),
                actions=[
                    ft.OutlinedButton("Cancelar", on_click=close_env_dlg),
                    primary_button("Calcular Envelope", icon=ft.Icons.PLAY_ARROW, on_click=on_calcular_envelope_confirm_click),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
                bgcolor=Palette.SURFACE,
                shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG)),
            )
            page.show_dialog(env_dlg)
            
        except Exception as ex:
            show_msg(f"Erro ao processar envelope: {ex}", Palette.ERROR)

    # ── Serialização de Ajustes ELS ──────────────────────────────────────
    def _serializar_ajustes_els(ajustes):
        """Serializa AjustesELS para dict JSON."""
        if ajustes is None:
            return None
        return {
            "barras_extras": ajustes.barras_extras,
            "phi_minimo_mm": ajustes.phi_minimo_mm,
            "h_override_cm": ajustes.h_override_cm,
            "fck_override_mpa": ajustes.fck_override_mpa,
        }
    
    def _desserializar_ajustes_els(data):
        """Desserializa dict JSON para AjustesELS."""
        if data is None:
            return None
        from ui.ftool.els import AjustesELS
        return AjustesELS(
            barras_extras=data.get("barras_extras", 0),
            phi_minimo_mm=data.get("phi_minimo_mm"),
            h_override_cm=data.get("h_override_cm"),
            fck_override_mpa=data.get("fck_override_mpa"),
        )

    # ── Salvar/Carregar Projeto ───────────────────────────────────────────
    async def on_save_project_click(e):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        import re
        sanitized_viga = re.sub(r'[\\/*?:"<>|]', "_", viga_nome_tf.control.value)
        sanitized_viga = re.sub(r'\s+', " ", sanitized_viga).strip()
        if not sanitized_viga:
            sanitized_viga = "V1" if modo == "comum" else "VT1"
        default_filename = f"Projeto_{sanitized_viga}_{ts}.ptc"

        out_path = await fp_save_project.save_file(
            dialog_title="Salvar Projeto (.ptc)",
            file_name=default_filename,
            allowed_extensions=["ptc"],
            file_type=ft.FilePickerFileType.CUSTOM,
        )
        if not out_path:
            return

        # Coletar dados
        proj_data = {
            "edicao": "premium",
            "viga_nome": viga_nome_tf.control.value,
            "modo": modo,
            "entrada": entrada_para_salvar(state),
            "geometria": {
                "h_cm": h_tf.control.value,
                "bw_cm": bw_tf.control.value,
                "bf_cm": bf_tf.control.value if is_t else "",
                "hf_cm": hf_tf.control.value if is_t else "",
                "b1esq_cm": b1esq_tf.control.value if is_t else "",
                "b1dir_cm": b1dir_tf.control.value if is_t else "",
            },
            "materiais": {
                "caa": caa_dd.control.value,
                "fck_mpa": fck_dd.control.value,
                "fyk_mpa": fyk_dd.control.value,
                "fyk_estribo_mpa": fyke_dd.control.value,
                "gamma_f": gamma_f_dd.control.value,
                "diam_estribo_mm": phi_est_dd.control.value,
                "diam_barra_mm": phi_bar_dd.control.value,
            },
            "esforcos": {
                "momentos_kNm": [tf.value for tf in md_rows],
                "cortantes_kN": [tf.value for tf in vk_rows],
            },
            "ftool": {
                "ftool_path": state.get("ftool_path"),
                "ftool_filename": state.get("ftool_filename"),
                "ftool_momento_path": state.get("ftool_momento_path"),
                "ftool_cortante_path": state.get("ftool_cortante_path"),
                "ftool_deformacao_path": state.get("ftool_deformacao_path"),
                "ftool_momentos": state.get("ftool_momentos"),
                "ftool_cortantes": state.get("ftool_cortantes"),
                "ftool_deformacoes": state.get("ftool_deformacoes"),
                "ftool_secoes_criticas": [
                    {"x": s.x, "momento": s.momento, "cortante": s.cortante, "tipo": s.tipo, "descricao": s.descricao}
                    for s in (state.get("ftool_secoes_criticas") or [])
                ],
                "ajustes_els": _serializar_ajustes_els(state.get("ftool_ajustes_els")),
            },
            "profissao": prof_dd.control.value,
            "nome_engenheiro": resp_nome_tf.control.value,
            "crea_uf": resp_registro_tf.control.value,
        }

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(proj_data, f, indent=2, ensure_ascii=False)
            add_recent(out_path, modo=modo)
            show_msg("Projeto salvo com sucesso", Palette.SUCCESS)
        except Exception as ex:
            show_msg(f"Erro ao salvar projeto: {ex}", Palette.ERROR)

    async def on_load_project_click(e):
        pick_res = await fp_load_project.pick_files(
            dialog_title="Selecionar Projeto (.ptc)",
            allowed_extensions=["ptc"],
            file_type=ft.FilePickerFileType.CUSTOM,
            allow_multiple=False,
        )
        if not pick_res or not pick_res.files:
            return
        file_path = pick_res.files[0].path

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                proj_data = json.load(f)

            # Verificar modo (eixo retangular x T) — inalterado
            saved_modo = proj_data.get("modo", "comum")
            if saved_modo != modo:
                show_msg(f"Este projeto foi criado no modo de Viga {'T' if saved_modo == 't' else 'Retangular'}. Altere o modo na tela inicial para importar.", Palette.WARNING)
                return

            # Edição de origem: standard e premium são aceitas (nota informativa)
            edicao = proj_data.get("edicao", "")
            msg_aviso = aviso_edicao(edicao)

            # Fonte de entrada (manual | FTOOL) — retrocompatível
            aplicar_entrada_projeto(state, proj_data)

            # Restaurar dados
            viga_nome_tf.control.value = proj_data.get("viga_nome", "")
            h_tf.control.value = proj_data.get("geometria", {}).get("h_cm", "")
            bw_tf.control.value = proj_data.get("geometria", {}).get("bw_cm", "")
            if is_t:
                bf_tf.control.value = proj_data.get("geometria", {}).get("bf_cm", "")
                hf_tf.control.value = proj_data.get("geometria", {}).get("hf_cm", "")
                b1esq_tf.control.value = proj_data.get("geometria", {}).get("b1esq_cm", "")
                b1dir_tf.control.value = proj_data.get("geometria", {}).get("b1dir_cm", "")

            # Materiais
            caa_dd.control.value = str(proj_data.get("materiais", {}).get("caa", "2"))
            fck_dd.control.value = str(proj_data.get("materiais", {}).get("fck_mpa", "25"))
            fyk_dd.control.value = str(proj_data.get("materiais", {}).get("fyk_mpa", "50"))
            fyke_dd.control.value = str(proj_data.get("materiais", {}).get("fyk_estribo_mpa", "60"))
            gamma_f_dd.control.value = str(proj_data.get("materiais", {}).get("gamma_f", "normais"))
            phi_est_dd.control.value = str(proj_data.get("materiais", {}).get("diam_estribo_mm", "5"))
            phi_bar_dd.control.value = str(proj_data.get("materiais", {}).get("diam_barra_mm", "12.5"))

            # Nome/CREA
            prof_dd.control.value = str(proj_data.get("profissao", "Engenheiro Civil"))
            resp_nome_tf.control.value = proj_data.get("nome_engenheiro", "")
            resp_registro_tf.control.value = proj_data.get("crea_uf", "")

            # Esforços
            saved_momentos = proj_data.get("esforcos", {}).get("momentos_kNm", [])
            saved_cortantes = proj_data.get("esforcos", {}).get("cortantes_kN", [])

            # Limpar e reconstruir trechos de flexão
            md_rows.clear()
            for idx, val in enumerate(saved_momentos):
                md_rows.append(_make_trecho_field("M", idx + 1, str(val)))
            if "M" in panel_rebuilds:
                panel_rebuilds["M"]()

            # Limpar e reconstruir trechos de cisalhamento
            vk_rows.clear()
            for idx, val in enumerate(saved_cortantes):
                vk_rows.append(_make_trecho_field("V", idx + 1, str(val)))
            if "V" in panel_rebuilds:
                panel_rebuilds["V"]()

            # Ftool Image Preview
            saved_ftool = proj_data.get("ftool", {})
            state["ftool_path"] = saved_ftool.get("ftool_path")
            state["ftool_filename"] = saved_ftool.get("ftool_filename")
            state["ftool_momento_path"] = saved_ftool.get("ftool_momento_path")
            state["ftool_cortante_path"] = saved_ftool.get("ftool_cortante_path")
            state["ftool_deformacao_path"] = saved_ftool.get("ftool_deformacao_path")
            state["ftool_momentos"] = saved_ftool.get("ftool_momentos")
            state["ftool_cortantes"] = saved_ftool.get("ftool_cortantes")
            state["ftool_deformacoes"] = saved_ftool.get("ftool_deformacoes")
            
            # Conversão explícita para tuplas para garantir imutabilidade nos dados de esforços
            if state.get("ftool_momentos"):
                state["ftool_momentos"] = [tuple(pt) for pt in state["ftool_momentos"]]
            if state.get("ftool_cortantes"):
                state["ftool_cortantes"] = [tuple(pt) for pt in state["ftool_cortantes"]]
            if state.get("ftool_deformacoes"):
                state["ftool_deformacoes"] = [tuple(pt) for pt in state["ftool_deformacoes"]]

            raw_secoes = saved_ftool.get("ftool_secoes_criticas", [])
            if raw_secoes:
                from ui.ftool.secoes_criticas import SecaoCritica
                state["ftool_secoes_criticas"] = [SecaoCritica(**s) for s in raw_secoes]
            else:
                state["ftool_secoes_criticas"] = None
            
            # Carregar ajustes ELS
            ajustes_data = saved_ftool.get("ajustes_els")
            state["ftool_ajustes_els"] = _desserializar_ajustes_els(ajustes_data)
            
            # Reconstroi o painel conforme a entrada do projeto ANTES de tocar
            # nos controles do painel FTOOL (eles so existem na pagina quando a
            # fonte de entrada e FTOOL; caso contrario, update() falharia).
            _refresh_entrada_ui()

            if ftool_visivel(state["entrada"]):
                update_ftool_preview()

                # Sincroniza os rótulos de UI correspondentes
                for lbl, key in [
                    (lbl_ftool_momento, "ftool_momento_path"),
                    (lbl_ftool_cortante, "ftool_cortante_path"),
                    (lbl_ftool_deformacao, "ftool_deformacao_path")
                ]:
                    path_val = state.get(key)
                    if path_val:
                        lbl.value = os.path.basename(path_val)
                        lbl.color = Palette.TEXT_PRIMARY
                    else:
                        lbl.value = "Nenhum"
                        lbl.color = Palette.TEXT_DISABLED
                    lbl.update()

                _atualizar_viewer()
                _check_ftool_pronto()

            # Reset resultados e desabilita PDF
            state["resultados_flex"] = None
            state["resultados_cis"] = None
            btn_gerar_pdf.disabled = True
            btn_exportar_dxf.disabled = True

            add_recent(file_path, modo=saved_modo)
            page.update()
            if msg_aviso:
                show_msg(msg_aviso, Palette.WARNING)
            else:
                show_msg("Projeto importado com sucesso", Palette.SUCCESS)
        except Exception as ex:
            show_msg(f"Erro ao carregar projeto: {ex}", Palette.ERROR)

    # ── Modal de resultados ──────────────────────────────────────────────
    def open_resultados_modal():
        import math
        res_flex = state["resultados_flex"]
        res_cis = state["resultados_cis"]

        flex_cards = ft.Row(
            spacing=Spacing.MD,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # Rebuild content function to allow dynamic updates
        def rebuild_results_ui():
            flex_cards.controls.clear()
            for i, r in enumerate(res_flex or []):
                if r is None:
                    continue
                
                bx_status = "SIM" if r.bx_passa == "SIM" else "NÃO"
                bx_color = Palette.SUCCESS if r.bx_passa == "SIM" else Palette.ERROR
                alerta_msg = getattr(r, "alerta", "")
                
                try:
                    bw = float(bw_tf.control.value or 12.0)
                    caa = int(caa_dd.control.value)
                    diam_est = float(phi_est_dd.control.value or 5.0)
                except (TypeError, ValueError, KeyError):
                    bw = 12.0
                    caa = 2
                    diam_est = 5.0
                c_cm = CAA_DATA[caa]["cobrimento"] / 10
                est_cm = diam_est / 10
                espaco_disp = bw - 2 * c_cm - 2 * est_cm

                # Spacing calculations
                D_MAX_AGREGADO = 1.9
                phi_cm = r.diametro_mm / 10
                eh_min = max(2.0, phi_cm, 1.2 * D_MAX_AGREGADO)
                eh_tol = eh_min - 0.05
                if r.qtd_barras <= 1:
                    eh_1 = espaco_disp - phi_cm
                    eh_passa_1 = True
                else:
                    eh_1 = (espaco_disp - r.qtd_barras * phi_cm) / (r.qtd_barras - 1)
                    eh_passa_1 = (eh_1 >= eh_tol)

                if eh_passa_1:
                    eh_status = "CABE"
                    status_type = "ok"
                    eh_val = eh_1
                    r.eh_passa = "SIM"
                    r.barras_suportadas = r.qtd_barras
                    r.barras_cima = 0
                    obs_det = ""
                    eh_tooltip = f"As barras cabem em 1 única camada. Espaçamento horizontal livre eh = {eh_val:.2f} cm (mínimo {eh_min:.1f} cm)."
                else:
                    n_max_layer = math.ceil(r.qtd_barras / 2)
                    if n_max_layer <= 1:
                        eh_2 = espaco_disp - phi_cm
                        eh_passa_2 = True
                    else:
                        eh_2 = (espaco_disp - n_max_layer * phi_cm) / (n_max_layer - 1)
                        eh_passa_2 = (eh_2 >= eh_tol)

                    if eh_passa_2:
                        eh_status = "2 CAMADAS"
                        status_type = "warn"
                        eh_val = eh_2
                        r.eh_passa = "SIM"
                        r.barras_suportadas = n_max_layer
                        r.barras_cima = r.qtd_barras - n_max_layer
                        obs_det = "Requer cavaletes transversais (ex: φ12.5 a cada 1m) para separar as camadas"
                        if n_max_layer >= 4 and bw >= 30:
                            obs_det += " | Adotar grampos de travamento φ5.0 conectando as barras centrais"
                        eh_tooltip = f"As barras não cabem em 1 camada, mas cabem em 2 camadas. Espaçamento horizontal livre eh = {eh_val:.2f} cm (mínimo {eh_min:.1f} cm). {obs_det}"
                    else:
                        eh_status = "NÃO CABE"
                        status_type = "error"
                        eh_val = eh_1
                        r.eh_passa = "NÃO"
                        r.barras_suportadas = r.qtd_barras
                        r.barras_cima = 0
                        obs_det = ""
                        eh_tooltip = f"O espaçamento horizontal livre ({eh_val:.2f} cm) é inferior ao mínimo regulamentar de {eh_min:.1f} cm, mesmo em 2 camadas."

                if hasattr(r, 'eh_suportado'):
                    r.eh_suportado = round(eh_val, 2)

                chip = status_chip(eh_status, status_type)
                chip.tooltip = eh_tooltip

                # Diameters table
                diam_rows = []
                displayed_diams = [6.3, 8.0, 10.0, 12.5]
                if r.diametro_mm not in displayed_diams:
                    displayed_diams.append(r.diametro_mm)
                    displayed_diams.sort()

                for d in displayed_diams:
                    a_bar = area_barra(d)
                    n_bars = math.ceil(r.as_usado_cm2 / a_bar) if a_bar > 0 else 0
                    is_chosen = (d == r.diametro_mm)
                    text_color = Palette.PRIMARY if is_chosen else Palette.TEXT_PRIMARY
                    text_weight = ft.FontWeight.BOLD if is_chosen else ft.FontWeight.NORMAL
                    diam_rows.append(
                        ft.Row(
                            controls=[
                                ft.Text(f"Ø {d:g}" + (" (atual)" if is_chosen else ""), size=11, color=text_color, weight=text_weight),
                                ft.Text(f"{n_bars}", size=11, weight=ft.FontWeight.BOLD, color=text_color),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        )
                    )

                def make_bitola_change_handler(r_obj):
                    def on_change(e):
                        val = float(e.control.value)
                        r_obj.diametro_mm = val
                        a_bar = area_barra(val)
                        r_obj.qtd_barras = math.ceil(r_obj.as_usado_cm2 / a_bar) if a_bar > 0 else 0
                        rebuild_results_ui()
                        page.update()
                    return on_change

                diam_dd = ft.Dropdown(
                    value=str(r.diametro_mm),
                    options=[ft.dropdown.Option(str(d)) for d in [5.0, 6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0, 32.0]],
                    border_radius=br_all(Radius.SM),
                    dense=True,
                    text_size=12,
                    filled=True,
                    bgcolor=Palette.SURFACE_VARIANT,
                    border_color=Palette.OUTLINE_VARIANT,
                    on_select=make_bitola_change_handler(r),
                )

                card = ft.Container(
                    width=200,
                    padding=pad_all(12),
                    border=ft.Border.all(1, Palette.OUTLINE_VARIANT),
                    border_radius=br_all(Radius.SM),
                    bgcolor=Palette.SURFACE,
                    shadow=SHADOW_SM,
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(f"M{i+1}", size=13, weight=ft.FontWeight.BOLD, color=Palette.PRIMARY),
                                    ft.Container(
                                        content=ft.Text(r.tipo, size=9, weight=ft.FontWeight.BOLD, color=Palette.ON_PRIMARY),
                                        bgcolor=Palette.PRIMARY if r.tipo == "POSITIVO" else Palette.SECONDARY,
                                        padding=pad_sym(horizontal=4, vertical=1),
                                        border_radius=br_all(3),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Divider(color=Palette.OUTLINE_VARIANT, height=1),
                            ft.Row([ft.Text("KC:", size=10, color=Palette.TEXT_SECONDARY), ft.Text(f"{r.kc:.2f}", size=10, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("Bx:", size=10, color=Palette.TEXT_SECONDARY), ft.Text(f"{r.bx:.3f}", size=10, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("PASSA?", size=10, color=Palette.TEXT_SECONDARY), ft.Text(bx_status, size=10, weight=ft.FontWeight.BOLD, color=bx_color)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("KS:", size=10, color=Palette.TEXT_SECONDARY), ft.Text(f"{r.ks:.3f}", size=10, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("As:", size=10, color=Palette.TEXT_SECONDARY), ft.Text(f"{r.as_req_cm2:.2f}", size=10, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("Asmin:", size=10, color=Palette.TEXT_SECONDARY), ft.Text(f"{r.asmin_cm2:.2f}", size=10, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([ft.Text("AsUSADO:", size=10, color=Palette.TEXT_SECONDARY), ft.Text(f"{r.as_usado_cm2:.2f}", size=10, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Divider(color=Palette.OUTLINE_VARIANT, height=1),
                            ft.Text("BARRAS", size=10, weight=ft.FontWeight.BOLD, color=Palette.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
                            *diam_rows,
                            ft.Divider(color=Palette.OUTLINE_VARIANT, height=1),
                            ft.Text("Ø ESCOLHIDO:", size=10, weight=ft.FontWeight.BOLD, color=Palette.TEXT_SECONDARY),
                            diam_dd,
                            ft.Container(height=2),
                            ft.Row(
                                controls=[
                                    ft.Text(f"Qtd: {r.qtd_barras}", size=11, weight=ft.FontWeight.W_500),
                                    chip,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(f"eh: {eh_val:.1f} cm (mín 2cm)", size=10, color=Palette.TEXT_SECONDARY),
                        ],
                        spacing=5,
                    )
                )

                # A2: caixa de alerta visivel quando bx nao passa
                if alerta_msg:
                    card.content.controls.append(
                        ft.Container(
                            content=ft.Text(
                                f"⚠ {alerta_msg}",
                                size=10,
                                color=Palette.ON_PRIMARY,
                                weight=ft.FontWeight.BOLD,
                            ),
                            bgcolor=Palette.ERROR,
                            padding=pad_all(8),
                            border_radius=br_all(Radius.SM),
                            margin=pad_only(top=6, bottom=6),
                        )
                    )

                # Seção Armadura de Pele (apenas se h >= 60cm)
                pele_controls = []
                if hasattr(r, "requer_pele") and r.requer_pele:
                    pele_controls = [
                        ft.Divider(color=Palette.OUTLINE_VARIANT, height=1),
                        ft.Text("ARMADURA DE PELE", size=10, weight=ft.FontWeight.BOLD,
                                color=Palette.SECONDARY, text_align=ft.TextAlign.CENTER),
                        ft.Text(f"As,min/face: {r.as_pele_min_face_cm2:.2f} cm² | s,máx: {r.s_pele_max_cm:.0f} cm",
                                size=9, color=Palette.TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
                        ft.Container(height=2),
                    ]

                    # Tabela de diâmetros para pele
                    pele_diam_rows = []
                    if hasattr(r, "tabela_pele") and r.tabela_pele:
                        for item in r.tabela_pele:
                            phi = item["phi_mm"]
                            n = item["n_barras_face"]
                            s = item["s_cm"]
                            as_val = item["as_cm2"]
                            cabe = item["cabe"]
                            pele_diam_rows.append(
                                ft.Row(
                                    controls=[
                                        ft.Text(f"Ø {phi:g}", size=10, color=Palette.TEXT_PRIMARY),
                                        ft.Text(f"{n}x  s={s:.0f}cm  {as_val:.2f}cm²",
                                                size=10, color=Palette.TEXT_PRIMARY),
                                        ft.Text("OK" if cabe else "NÃO",
                                                size=10, weight=ft.FontWeight.BOLD,
                                                color=Palette.SUCCESS if cabe else Palette.ERROR),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                )
                            )
                    pele_controls.extend(pele_diam_rows)

                    # Dropdown para escolher phi da pele
                    def make_pele_bitola_handler(r_obj):
                        def on_change(e):
                            val = float(e.control.value)
                            r_obj.phi_pele_mm = val
                            # Recalcular n_barras e s para o phi escolhido
                            if hasattr(r_obj, "tabela_pele") and r_obj.tabela_pele:
                                for item in r_obj.tabela_pele:
                                    if item["phi_mm"] == val:
                                        r_obj.n_barras_pele_face = item["n_barras_face"]
                                        r_obj.s_pele_cm = item["s_cm"]
                                        r_obj.as_pele_face_cm2 = item["as_cm2"]
                                        break
                            rebuild_results_ui()
                            page.update()
                        return on_change

                    pele_dd = ft.Dropdown(
                        value=str(r.phi_pele_mm),
                        options=[ft.dropdown.Option(str(item["phi_mm"]))
                                 for item in (r.tabela_pele or [])],
                        border_radius=br_all(Radius.SM),
                        dense=True,
                        text_size=11,
                        filled=True,
                        bgcolor=Palette.SURFACE_VARIANT,
                        border_color=Palette.OUTLINE_VARIANT,
                        on_select=make_pele_bitola_handler(r),
                    )
                    pele_controls.append(ft.Text("Ø PELE:", size=10, weight=ft.FontWeight.BOLD,
                                                  color=Palette.TEXT_SECONDARY))
                    pele_controls.append(pele_dd)
                    pele_controls.append(ft.Container(height=2))
                    pele_controls.append(
                        ft.Row(
                            controls=[
                                ft.Text(f"Qtd/face: {r.n_barras_pele_face}", size=11, weight=ft.FontWeight.W_500),
                                ft.Text(f"s: {r.s_pele_cm:.0f} cm", size=11, color=Palette.TEXT_SECONDARY),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        )
                    )
                    pele_controls.append(
                        ft.Text(f"As/face: {r.as_pele_face_cm2:.2f} cm²", size=10, color=Palette.TEXT_SECONDARY)
                    )

                # Adicionar controles de pele ao card
                if pele_controls:
                    card.content.controls.extend(pele_controls)

                flex_cards.controls.append(card)

        # Initial build
        rebuild_results_ui()

        flex_section = ft.Column(
            controls=[
                section_header("Flexao (Dimensionamento de Armaduras)", icon=ft.Icon(ft.Icons.SQUARE_OUTLINED, size=16, color=Palette.PRIMARY)),
                ft.Container(height=Spacing.SM),
                flex_cards,
            ],
            spacing=0,
        )

        # Resumo de cisalhamento
        rows_cis = []
        for i, r in enumerate(res_cis or []):
            if r is None:
                continue
            status_label = "OK" if r.passa_vrd2 == "SIM" else "NAO"
            rows_cis.append(ft.DataRow(
                cells=[
                    ft.DataCell(title_small(f"V{i+1}", color=Palette.TEXT_PRIMARY)),
                    ft.DataCell(body_small(f"{r.vsd_verdadeiro_kn:.1f} kN", color=Palette.TEXT_PRIMARY)),
                    ft.DataCell(body_small(f"{r.vrd2_kn:.1f} kN", color=Palette.TEXT_PRIMARY)),
                    ft.DataCell(body_small(f"{r.vsw_kn:.1f} kN", color=Palette.TEXT_PRIMARY)),
                    ft.DataCell(body_small(f"{r.dist_estribos_cm:.1f} cm", color=Palette.TEXT_PRIMARY)),
                    ft.DataCell(status_chip(status_label, "ok" if r.passa_vrd2 == "SIM" else "error")),
                ],
            ))

        cis_section = ft.Column(
            controls=[
                ft.Container(height=Spacing.LG),
                section_header("Cisalhamento", icon=ft.Icon(ft.Icons.SWAP_VERT, size=16, color=Palette.PRIMARY)),
                ft.Container(height=Spacing.SM),
                ft.DataTable(
                    columns=[
                        ft.DataColumn(title_small("Trecho")),
                        ft.DataColumn(title_small("Vsolic (kN)")),
                        ft.DataColumn(title_small("Vrd2 (kN)")),
                        ft.DataColumn(title_small("Vsw (kN)")),
                        ft.DataColumn(title_small("Espacamento")),
                        ft.DataColumn(title_small("Status")),
                    ],
                    rows=rows_cis,
                    heading_row_height=Spacing.XL + 8,
                    data_row_min_height=Spacing.XL + 4,
                    border=ft.Border.all(1, Palette.OUTLINE_VARIANT),
                    border_radius=br_all(Radius.SM),
                    vertical_lines=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
                    horizontal_lines=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
                ) if rows_cis else caption("Nenhum trecho calculado.", color=Palette.TEXT_DISABLED),
            ],
            spacing=0,
        )

        results_content = ft.Column(
            controls=[flex_section, cis_section],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        )

        async def on_gerar_pdf_click(e):
            page.pop_dialog()
            await on_gerar_pdf(e)

        results_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=Palette.SUCCESS),
                    ft.Container(width=Spacing.SM),
                    title_medium("Resultados do calculo"),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=results_content,
                width=800, height=540,
                padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.SM),
            ),
            actions=[
                ft.OutlinedButton(
                    "Fechar",
                    on_click=lambda e: page.pop_dialog(),
                ),
                primary_button(
                    "Gerar PDF",
                    icon=ft.Icons.PICTURE_AS_PDF,
                    on_click=on_gerar_pdf_click,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=Palette.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG)),
        )
        page.show_dialog(results_dialog)

    # ── Gerar PDF ───────────────────────────────────────────────────────
    async def on_gerar_pdf(e):
        state["tipo_viga"] = viga_nome_tf.control.value or ("V1" if modo == "comum" else "VT1")
        if state["resultados_flex"] is None and state["resultados_cis"] is None:
            show_msg("Calcule primeiro antes de gerar o PDF", Palette.WARNING)
            return
        
        # B3: Desabilitar o botão e mostrar spinner text
        btn_gerar_pdf.disabled = True
        btn_gerar_pdf.text = "Gerando PDF..."
        btn_gerar_pdf.icon = ft.Icons.HOURGLASS_EMPTY
        page.update()

        try:
            gamma_f = GAMMA_F_TABLE[gamma_f_dd.control.value]["gamma_f"]
        except (KeyError, TypeError):
            gamma_f = 1.4
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            # B9: Validação e sanitização de filename contra caracteres ilegais
            import re
            sanitized_viga = re.sub(r'[\\/*?:"<>|]', "_", state["tipo_viga"])
            sanitized_viga = re.sub(r'\s+', " ", sanitized_viga).strip()
            if not sanitized_viga:
                sanitized_viga = "V1" if modo == "comum" else "VT1"
            default_filename = f"PorticaApp_{sanitized_viga}_{ts}.pdf"
            
            # Abre o diálogo para salvar arquivo
            out = await fp_pdf.save_file(
                dialog_title="Salvar Relatório PDF",
                file_name=default_filename,
                allowed_extensions=["pdf"],
                file_type=ft.FilePickerFileType.CUSTOM,
            )
            
            # Se o usuário cancelou o diálogo, não faz nada
            if not out:
                return

            nome_eng = resp_nome_tf.control.value or ""
            crea_val = resp_registro_tf.control.value or ""
            profissao_val = prof_dd.control.value or "Engenheiro Civil"

            ftool = state["ftool_path"] if state.get("ftool_path") and os.path.exists(state["ftool_path"]) else None
            if is_t:
                bf = float(bf_tf.control.value or 0); hf = float(hf_tf.control.value or 0)
                if state.get("ftool_momentos"):
                    gerar_relatorio_viga_t_premium(
                        out, nome_viga=state["tipo_viga"],
                        h_cm=float(h_tf.control.value or 0), bw_cm=float(bw_tf.control.value or 0),
                        bf_cm=bf, hf_cm=hf,
                        caa=int(caa_dd.control.value), fck_mpa=float(fck_dd.control.value or 0),
                        fyk_mpa=float(fyk_dd.control.value or 0), fyk_estribo_mpa=float(fyke_dd.control.value or 0),
                        phi_estribo_mm=float(phi_est_dd.control.value),
                        phi_barra_mm=float(phi_bar_dd.control.value),
                        resultados_flexao=state["resultados_flex"] or [],
                        resultados_cisalhamento=state["resultados_cis"] or [],
                        imagem_ftool=ftool,
                        gamma_f=gamma_f,
                        dark_mode=is_dark(page),
nome_engenheiro=nome_eng,
                    crea=crea_val,
                    profissao=profissao_val,
                        momentos=state["ftool_momentos"],
                        cortantes=state["ftool_cortantes"],
                        secoes_criticas=state["ftool_secoes_criticas"],
                        detalhamento=state.get("ftool_detalhamento"),
                        resultado_els=state.get("ftool_resultado_els"),
                    )
                else:
                    gerar_relatorio_viga_t(
                        out, nome_viga=state["tipo_viga"],
                        h_cm=float(h_tf.control.value or 0), bw_cm=float(bw_tf.control.value or 0),
                        bf_cm=bf, hf_cm=hf,
                        caa=int(caa_dd.control.value), fck_mpa=float(fck_dd.control.value or 0),
                        fyk_mpa=float(fyk_dd.control.value or 0), fyk_estribo_mpa=float(fyke_dd.control.value or 0),
                        phi_estribo_mm=float(phi_est_dd.control.value),
                        phi_barra_mm=float(phi_bar_dd.control.value),
                        resultados_flexao=state["resultados_flex"] or [],
                        resultados_cisalhamento=state["resultados_cis"] or [],
                        imagem_ftool=ftool,
                        gamma_f=gamma_f,
                        dark_mode=is_dark(page),
nome_engenheiro=nome_eng,
                    crea=crea_val,
                    profissao=profissao_val,
                    )
            else:
                if state.get("ftool_momentos"):
                    gerar_relatorio_viga_comum_premium(
                        out, nome_viga=state["tipo_viga"],
                        h_cm=float(h_tf.control.value or 0), bw_cm=float(bw_tf.control.value or 0),
                        caa=int(caa_dd.control.value), fck_mpa=float(fck_dd.control.value or 0),
                        fyk_mpa=float(fyk_dd.control.value or 0), fyk_estribo_mpa=float(fyke_dd.control.value or 0),
                        phi_estribo_mm=float(phi_est_dd.control.value),
                        phi_barra_mm=float(phi_bar_dd.control.value),
                        resultados_flexao=state["resultados_flex"] or [],
                        resultados_cisalhamento=state["resultados_cis"] or [],
                        imagem_ftool=ftool,
                        gamma_f=gamma_f,
                        dark_mode=is_dark(page),
nome_engenheiro=nome_eng,
                    crea=crea_val,
                    profissao=profissao_val,
                        momentos=state["ftool_momentos"],
                        cortantes=state["ftool_cortantes"],
                        secoes_criticas=state["ftool_secoes_criticas"],
                        detalhamento=state.get("ftool_detalhamento"),
                        resultado_els=state.get("ftool_resultado_els"),
                    )
                else:
                    gerar_relatorio_viga_comum(
                        out, nome_viga=state["tipo_viga"],
                        h_cm=float(h_tf.control.value or 0), bw_cm=float(bw_tf.control.value or 0),
                        caa=int(caa_dd.control.value), fck_mpa=float(fck_dd.control.value or 0),
                        fyk_mpa=float(fyk_dd.control.value or 0), fyk_estribo_mpa=float(fyke_dd.control.value or 0),
                        phi_estribo_mm=float(phi_est_dd.control.value),
                        phi_barra_mm=float(phi_bar_dd.control.value),
                        resultados_flexao=state["resultados_flex"] or [],
                        resultados_cisalhamento=state["resultados_cis"] or [],
                        imagem_ftool=ftool,
                        gamma_f=gamma_f,
                        dark_mode=is_dark(page),
nome_engenheiro=nome_eng,
                    crea=crea_val,
                    profissao=profissao_val,
                    )
            state["pdf_path"] = out
            # Habilita Abrir ultimo PDF apos gerar com sucesso
            btn_abrir_pdf.disabled = False
            page.update()
            # B11: feedback de sucesso claro e persistente
            show_msg(f"PDF gerado com sucesso: {out}", Palette.SUCCESS)
            
            # Abre o PDF gerado automaticamente
            on_abrir_pdf(None)
        except (OSError, ValueError, TypeError) as ex:
            import traceback
            traceback.print_exc()
            show_msg(f"Erro ao gerar PDF: {ex}", Palette.ERROR)
        finally:
            btn_gerar_pdf.disabled = False
            btn_gerar_pdf.text = "Gerar PDF"
            btn_gerar_pdf.icon = ft.Icons.PICTURE_AS_PDF
            page.update()

    def on_abrir_pdf(e):
        path = state.get("pdf_path")
        if not path or not os.path.exists(path):
            show_msg("Gere o PDF primeiro", Palette.WARNING)
            return
        try:
            sysname = platform.system()
            if sysname == "Windows":
                os.startfile(path)
            elif sysname == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except (OSError, FileNotFoundError) as ex:
            show_msg(f"Erro ao abrir PDF (instale um visualizador): {ex}", Palette.ERROR)

    # ── Exportar DXF ─────────────────────────────────────────────────────
    async def on_exportar_dxf(e):
        state["tipo_viga"] = viga_nome_tf.control.value or ("V1" if modo == "comum" else "VT1")
        if not state["resultados_flex"]:
            show_msg("Calcule primeiro antes de exportar o DXF", Palette.WARNING)
            return

        # Encontrar a primeira seção com detalhamento convergido
        resultado_valido = None
        for r in state["resultados_flex"]:
            if r and getattr(r, "layout_convergido", None):
                resultado_valido = r
                break

        is_t = modo == "t"
        if not resultado_valido:
            if is_t:
                from core.calculos.engenharia import ResultadoFlexaoT
                resultado_valido = next((r for r in state["resultados_flex"] or [] if r is not None), None)
                if resultado_valido is None:
                    resultado_valido = ResultadoFlexaoT(
                        momento_kNm=0, tipo="POSITIVO", kc=0, a=0, b=0, x1=0, x2=0,
                        bx=0, bx_passa="SIM", x_cm=0, linha_neutra_condiz="SIM",
                        bf_efetivo_cm=float(bf_tf.control.value.replace(",", ".")) if is_t and bf_tf.control.value else 0,
                        ks=0, as_req_cm2=0, asmin_cm2=0, as_usado_cm2=0,
                        diametro_mm=float(phi_bar_dd.control.value) if phi_bar_dd.control.value else 10.0,
                        qtd_barras=3, eh_min_real=0.0, eh_passa="SIM",
                    )
            else:
                show_msg("Nenhum detalhamento geométrico disponível para exportação. Verifique se a viga passa no dimensionamento.", Palette.WARNING)
                return

        btn_exportar_dxf.disabled = True
        btn_exportar_dxf.text = "Exportando DXF..."
        btn_exportar_dxf.icon = ft.Icons.HOURGLASS_EMPTY
        page.update()

        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            import re
            sanitized_viga = re.sub(r'[\\/*?:"<>|]', "_", state["tipo_viga"])
            sanitized_viga = re.sub(r'\s+', " ", sanitized_viga).strip()
            if not sanitized_viga:
                sanitized_viga = "V1" if modo == "comum" else "VT1"
            default_filename = f"PorticaApp_{sanitized_viga}_{ts}.dxf"

            out = await fp_dxf.save_file(
                dialog_title="Salvar Detalhamento DXF",
                file_name=default_filename,
                allowed_extensions=["dxf"],
                file_type=ft.FilePickerFileType.CUSTOM,
            )

            if not out:
                return

            # Chamar a função de exportação DXF
            from core.detailing.dxf_export import exportar_secao_dxf
            from core.detailing import BeamDetailer, BeamDetailingInput

            layout = resultado_valido.layout_convergido
            
            # Coletar dados da seção
            if layout:
                bw_cm = layout.bw / 10.0
                h_cm = layout.h / 10.0
                cob_cm = layout.c_nom / 10.0
                phi_estribo_mm = layout.phi_estribo
                d_max_agregado_mm = layout.d_max_agregado
            else:
                bw_cm = float(bw_tf.control.value.replace(",", ".")) if bw_tf.control.value else 15.0
                h_cm = float(h_tf.control.value.replace(",", ".")) if h_tf.control.value else 40.0
                caa = int(caa_dd.control.value) if caa_dd.control.value else 2
                cob_mm = CAA_DATA.get(caa, {}).get("cobrimento", 30)
                cob_cm = cob_mm / 10.0
                phi_estribo_mm = float(phi_est_dd.control.value) if phi_est_dd.control.value else 5.0
                d_max_agregado_mm = 19.0

            if is_t:
                bw_cm = float(bw_tf.control.value.replace(",", ".")) if bw_tf.control.value else bw_cm
            
            # Encontrar armadura máxima para o desenho da seção transversal representativa
            max_bars_inf = 0
            max_bars_sup = 0
            phi_inf_adot = layout.phi_barra if layout else (float(phi_bar_dd.control.value) if phi_bar_dd.control.value else 10.0)
            phi_sup_adot = layout.phi_barra if layout else (float(phi_bar_dd.control.value) if phi_bar_dd.control.value else 10.0)

            for r in state["resultados_flex"] or []:
                if not r:
                    continue
                if r.tipo == "POSITIVO":
                    if r.qtd_barras > max_bars_inf:
                        max_bars_inf = r.qtd_barras
                        phi_inf_adot = getattr(r, "diametro_mm", phi_inf_adot)
                else:
                    if r.qtd_barras > max_bars_sup:
                        max_bars_sup = r.qtd_barras
                        phi_sup_adot = getattr(r, "diametro_mm", phi_sup_adot)

            n_inf_dxf = max_bars_inf if max_bars_inf > 0 else 3
            n_sup_dxf = max_bars_sup if max_bars_sup > 0 else 2

            detailer = BeamDetailer()
            combined_bar_positions = []

            if layout:
                # 1. Detalhar armadura inferior
                inp_inf = BeamDetailingInput(
                    bw=bw_cm * 10.0,
                    h=h_cm * 10.0,
                    c_nom=cob_cm * 10.0,
                    phi_estribo=phi_estribo_mm,
                    phi_barra=phi_inf_adot,
                    d_max_agregado=d_max_agregado_mm,
                    total_bars=n_inf_dxf,
                )
                layout_inf = detailer.detail(inp_inf)
                
                # 2. Detalhar armadura superior (como se fosse inferior, depois espelhamos)
                inp_sup = BeamDetailingInput(
                    bw=bw_cm * 10.0,
                    h=h_cm * 10.0,
                    c_nom=cob_cm * 10.0,
                    phi_estribo=phi_estribo_mm,
                    phi_barra=phi_sup_adot,
                    d_max_agregado=d_max_agregado_mm,
                    total_bars=n_sup_dxf,
                )
                layout_sup = detailer.detail(inp_sup)

                # Adiciona barras inferiores
                for bar in layout_inf.bar_positions:
                    if not bar.is_corner_bar:
                        combined_bar_positions.append({
                            "x": bar.x,
                            "y": bar.y,
                            "layer": bar.layer,
                            "is_corner_bar": False,
                            "phi_mm": phi_inf_adot
                        })
                        
                # Adiciona barras superiores (espelhadas em Y)
                h_mm = h_cm * 10.0
                for bar in layout_sup.bar_positions:
                    if not bar.is_corner_bar:
                        y_mirrored = h_mm - bar.y
                        combined_bar_positions.append({
                            "x": bar.x,
                            "y": y_mirrored,
                            "layer": -(bar.layer + 1),
                            "is_corner_bar": False,
                            "phi_mm": phi_sup_adot
                        })
            else:
                # Posições calculadas manualmente
                e_off_mm = cob_cm * 10.0 + phi_estribo_mm
                
                # Inferiores
                y_inf = e_off_mm + phi_inf_adot / 2.0
                avail_w_inf = bw_cm * 10.0 - 2.0 * e_off_mm - phi_inf_adot
                if n_inf_dxf == 1 or avail_w_inf <= 0:
                    xs_inf = [bw_cm * 10.0 / 2.0]
                else:
                    xs_inf = [e_off_mm + phi_inf_adot / 2.0 + i * avail_w_inf / (n_inf_dxf - 1) for i in range(n_inf_dxf)]
                for x in xs_inf:
                    combined_bar_positions.append({
                        "x": x,
                        "y": y_inf,
                        "layer": 0,
                        "is_corner_bar": False,
                        "phi_mm": phi_inf_adot
                    })
                    
                # Superiores
                h_mm = h_cm * 10.0
                y_sup = h_mm - e_off_mm - phi_sup_adot / 2.0
                avail_w_sup = bw_cm * 10.0 - 2.0 * e_off_mm - phi_sup_adot
                if n_sup_dxf == 1 or avail_w_sup <= 0:
                    xs_sup = [bw_cm * 10.0 / 2.0]
                else:
                    xs_sup = [e_off_mm + phi_sup_adot / 2.0 + i * avail_w_sup / (n_sup_dxf - 1) for i in range(n_sup_dxf)]
                for x in xs_sup:
                    combined_bar_positions.append({
                        "x": x,
                        "y": y_sup,
                        "layer": -1,
                        "is_corner_bar": False,
                        "phi_mm": phi_sup_adot
                    })

            # Dados de armadura de pele
            n_barras_pele = getattr(resultado_valido, "n_barras_pele_face", 0)
            phi_pele_mm = getattr(resultado_valido, "phi_pele_mm", 0.0)

            # Verificar se é seção T
            is_t = modo == "t"
            bf_cm = None
            hf_cm = None
            if is_t:
                bf_cm = float(bf_tf.control.value.replace(",", ".")) if bf_tf.control.value else None
                hf_cm = float(hf_tf.control.value.replace(",", ".")) if hf_tf.control.value else None

            exportar_secao_dxf(
                bw_cm=bw_cm,
                h_cm=h_cm,
                cob_cm=cob_cm,
                phi_estribo_mm=phi_estribo_mm,
                bar_positions=combined_bar_positions,
                phi_barra_mm=phi_inf_adot,
                n_barras_pele=n_barras_pele,
                phi_pele_mm=phi_pele_mm,
                is_t=is_t,
                bf_cm=bf_cm,
                hf_cm=hf_cm,
                nome_arquivo=out
            )

            show_msg(f"Arquivo DXF exportado com sucesso: {out}", Palette.SUCCESS)

        except Exception as ex:
            show_msg(f"Erro ao exportar DXF: {ex}", Palette.ERROR)
        finally:
            btn_exportar_dxf.disabled = False
            btn_exportar_dxf.text = "Exportar DXF"
            btn_exportar_dxf.icon = ft.Icons.DOWNLOAD
            page.update()

    # ── Top bar ──────────────────────────────────────────────────────────
    topbar = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=Palette.TEXT_PRIMARY,
                    tooltip="Voltar para o inicio",
                    on_click=lambda e: on_back(),
                ),
                ft.Container(width=Spacing.SM),
                ft.Column(
                    controls=[
                        overline("MODO DE CALCULO", color=Palette.TEXT_SECONDARY),
                        title_large(
                            "Viga Comum - Flexao e Cisalhamento" if not is_t
                            else "Viga T - Flexao e Cisalhamento",
                            color=Palette.TEXT_PRIMARY,
                        ),
                    ],
                    spacing=2,
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SCIENCE, size=16, color=Palette.PRIMARY),
                            ft.Container(width=6),
                            label_medium("NBR 6118:2023", color=Palette.TEXT_SECONDARY),
                        ],
                        tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.XS),
                    border_radius=br_all(Radius.PILL),
                    bgcolor=Palette.SUCCESS_BG,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=pad_sym(horizontal=Spacing.LG, vertical=Spacing.MD),
        bgcolor=Palette.SURFACE,
        border=ft.Border(bottom=ft.BorderSide(1, Palette.OUTLINE_VARIANT)),
    )

    # ── Drop zone (imagem do Ftool) ─────────────────────────────────────
    def _build_drop_placeholder():
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.CLOUD_UPLOAD_OUTLINED, size=42, color=Palette.TEXT_DISABLED),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(height=Spacing.SM),
                body_small("Clique para selecionar", color=Palette.TEXT_PRIMARY, text_align=ft.TextAlign.CENTER),
                caption("PNG / JPG / SVG do Ftool", color=Palette.TEXT_DISABLED, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=Spacing.XS,
        )

    drop_zone_content = ft.Container(
        content=_build_drop_placeholder(),
        width=280, height=140,
        border=ft.Border.all(2, Palette.OUTLINE_VARIANT),
        border_radius=br_all(Radius.MD),
        bgcolor=Palette.SURFACE_VARIANT,
        alignment=ft.Alignment.CENTER,
        padding=Spacing.MD,
        ink=True,
    )

    async def on_drop_zone_click(e):
        """Abre file picker para escolher imagem."""
        files = await fp_image.pick_files(allow_multiple=False, allowed_extensions=["png", "jpg", "jpeg", "svg"])
        if files:
            f = files[0]
            state["ftool_path"] = f.path
            state["ftool_filename"] = f.name
            update_ftool_preview()
            page.update()

    drop_zone_content.on_click = on_drop_zone_click

    # Texto de nome do arquivo (atualizado dinamicamente apos selecao)
    ftool_filename_text = ft.Text(
        state.get("ftool_filename") or "Nenhuma imagem selecionada",
        size=11, color=Palette.TEXT_DISABLED, text_align=ft.TextAlign.CENTER,
    )

    def update_ftool_preview():
        """Substitui o placeholder pelo preview quando ha imagem."""
        if state.get("ftool_path") and os.path.exists(state["ftool_path"]):
            img_path = state["ftool_path"]
            # SVG: converter para PNG temporario para preview (Flet desktop nao renderiza SVG)
            if img_path.lower().endswith(".svg"):
                try:
                    from svglib.svglib import svg2rlg
                    from reportlab.graphics import renderPM
                    import tempfile, re
                    # Sanitizar dash arrays invalidos do FTOOL
                    with open(img_path, "r", encoding="utf-8", errors="ignore") as f:
                        svg_content = f.read()
                    svg_clean = re.sub(r'stroke-dasharray\s*=\s*"[^"]*"', 'stroke-dasharray="1"', svg_content)
                    svg_clean = re.sub(r"stroke-dasharray\s*=\s*'[^']*'", "stroke-dasharray='1'", svg_clean)
                    svg_clean = re.sub(r'stroke-dasharray\s*:\s*[^;"\']+', 'stroke-dasharray:1', svg_clean)
                    temp_svg = temp_path(suffix=".svg")
                    with open(temp_svg, "w", encoding="utf-8") as f:
                        f.write(svg_clean)
                    drawing = svg2rlg(temp_svg)
                    if drawing is not None:
                        png_temp = temp_path(suffix=".png")
                        renderPM.drawToFile(drawing, png_temp, fmt="PNG", dpi=150)
                        state["_png_preview_temp"] = png_temp
                        img_path = png_temp
                    try:
                        os.remove(temp_svg)
                    except OSError:
                        pass
                except (ImportError, AttributeError, RuntimeError, OSError):
                    # Faltam libs (svglib/reportlab) ou erro de render
                    pass

            drop_zone_content.content = ft.Image(
                src=img_path,
                width=280, height=140,
                fit=ft.BoxFit.CONTAIN,
            )
            drop_zone_content.border = ft.Border.all(2, Palette.SUCCESS)
            drop_zone_content.bgcolor = Palette.SURFACE
            ftool_filename_text.value = state["ftool_filename"]
            ftool_filename_text.color = Palette.TEXT_SECONDARY
        else:
            # Limpar PNG temporario anterior se houver
            old_png = state.pop("_png_preview_temp", None)
            if old_png and os.path.exists(old_png):
                try:
                    os.remove(old_png)
                except OSError:
                    pass
            drop_zone_content.content = _build_drop_placeholder()
            drop_zone_content.border = ft.Border.all(2, Palette.OUTLINE_VARIANT)
            drop_zone_content.bgcolor = Palette.SURFACE_VARIANT
            ftool_filename_text.value = "Nenhuma imagem selecionada"
            ftool_filename_text.color = Palette.TEXT_DISABLED

    # ── Sidebar direita (imagem + acoes) ─────────────────────────────────
    ftool_card = surface_card(
        ft.Column(
            controls=[
                section_header(
                    "Imagem do Ftool (opcional)",
                    icon=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=16, color=Palette.TEXT_SECONDARY),
                ),
                caption(
                    "Print do Ftool para incluir no relatorio PDF.",
                    color=Palette.TEXT_SECONDARY,
                ),
                ft.Container(height=Spacing.SM),
                ft.Container(
                    content=drop_zone_content,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(height=Spacing.XS),
                ftool_filename_text,
            ],
            spacing=Spacing.XS,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=Spacing.LG,
    )

    # Botao Gerar PDF - inicia desabilitado, so habilita apos calcular
    btn_gerar_pdf = success_button(
        "Gerar PDF",
        icon=ft.Icons.PICTURE_AS_PDF,
        on_click=on_gerar_pdf,
        expand=True,
        disabled=True,
    )
    # Botao Exportar DXF - inicia desabilitado, so habilita apos calcular
    btn_exportar_dxf = success_button(
        "Exportar DXF",
        icon=ft.Icons.DOWNLOAD,
        on_click=on_exportar_dxf,
        expand=True,
        disabled=True,
    )
    # Botao Abrir PDF - inicia desabilitado, so habilita apos gerar PDF
    btn_abrir_pdf = outlined_button(
        "Abrir ultimo PDF",
        icon=ft.Icons.OPEN_IN_NEW,
        on_click=on_abrir_pdf,
        expand=True,
        disabled=True,
    )

    actions_card = surface_card(
        ft.Column(
            controls=[
                section_header(
                    "Ações",
                    icon=ft.Icon(ft.Icons.PLAY_ARROW, size=16, color=Palette.TEXT_SECONDARY),
                ),
                ft.Container(height=Spacing.XS),
                btn_gerar_pdf,
                ft.Container(height=Spacing.XS),
                btn_exportar_dxf,
                ft.Container(height=Spacing.XS),
                btn_abrir_pdf,
                ft.Container(height=Spacing.SM),
                ft.Divider(color=Palette.OUTLINE_VARIANT, height=1),
                ft.Container(height=Spacing.SM),
                outlined_button(
                    "Salvar Projeto",
                    icon=ft.Icons.SAVE_ALT,
                    on_click=on_save_project_click,
                    expand=True,
                ),
                ft.Container(height=Spacing.XS),
                outlined_button(
                    "Carregar Projeto",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=on_load_project_click,
                    expand=True,
                ),
            ],
            spacing=0,
        ),
        padding=Spacing.LG,
    )

    right_sidebar = ft.Column(
        controls=[
            actions_card,
        ],
        spacing=Spacing.MD,
        scroll=ft.ScrollMode.AUTO,
    )

    # ── Visualizador de dados FTOOL (centro) ──────────────────────────────
    viewer_flexao = ft.Column(spacing=Spacing.SM)
    viewer_cisalhamento = ft.Column(spacing=Spacing.SM)

    def _atualizar_viewer():
        viewer_flexao.controls.clear()
        viewer_cisalhamento.controls.clear()
        momentos = state.get("ftool_momentos")
        cortantes = state.get("ftool_cortantes")
        secoes = state.get("ftool_secoes_criticas")

        if not momentos or not cortantes:
            msg = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.CLOUD_UPLOAD, size=48, color=Palette.TEXT_DISABLED),
                    ft.Container(height=Spacing.SM),
                    ft.Text("Importe os arquivos .txt do FTOOL pela barra lateral", size=14, color=Palette.TEXT_DISABLED, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=pad_all(Spacing.XL), expand=True,
                alignment=ft.Alignment(0, 0),
            )
            viewer_flexao.controls.append(msg)
            viewer_cisalhamento.controls.append(msg)
            return

        n_mom = len(momentos)
        n_cort = len(cortantes)
        L = max(p[0] for p in momentos)
        m_max = max(p[1] for p in momentos)
        m_min = min(p[1] for p in momentos)
        v_max = max(p[1] for p in cortantes)
        v_min = min(p[1] for p in cortantes)

        info = surface_card(
            ft.Column([
                ft.Text("Dados importados do FTOOL", size=14, weight=ft.FontWeight.BOLD, color=Palette.PRIMARY),
                ft.Divider(color=Palette.OUTLINE_VARIANT, height=1),
                ft.Row([ft.Text("Vão total:", size=12, color=Palette.TEXT_SECONDARY), ft.Text(f"{L:.2f} m", size=12, weight=ft.FontWeight.W_500)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("Pontos de momento:", size=12, color=Palette.TEXT_SECONDARY), ft.Text(f"{n_mom}", size=12, weight=ft.FontWeight.W_500)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("M máx:", size=12, color=Palette.TEXT_SECONDARY), ft.Text(f"{m_max:+.1f} kN·m", size=12, weight=ft.FontWeight.W_500, color=Palette.SUCCESS)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("M mín:", size=12, color=Palette.TEXT_SECONDARY), ft.Text(f"{m_min:+.1f} kN·m", size=12, weight=ft.FontWeight.W_500, color=Palette.ERROR)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("Pontos de cortante:", size=12, color=Palette.TEXT_SECONDARY), ft.Text(f"{n_cort}", size=12, weight=ft.FontWeight.W_500)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("V máx:", size=12, color=Palette.TEXT_SECONDARY), ft.Text(f"{v_max:+.1f} kN", size=12, weight=ft.FontWeight.W_500, color=Palette.SUCCESS)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Row([ft.Text("V mín:", size=12, color=Palette.TEXT_SECONDARY), ft.Text(f"{v_min:+.1f} kN", size=12, weight=ft.FontWeight.W_500, color=Palette.ERROR)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ]), padding=Spacing.LG,
        )
        viewer_flexao.controls.append(info)

        if secoes:
            rows = [ft.DataRow(cells=[
                ft.DataCell(ft.Text(f"{s.x:.2f}", size=11)),
                ft.DataCell(ft.Text(f"{s.momento:.1f}", size=11)),
                ft.DataCell(ft.Text(f"{s.cortante:.1f}", size=11)),
                ft.DataCell(status_chip(s.tipo, "ok")),
                ft.DataCell(ft.Container(ft.Text(s.descricao[:20] + ".." if len(s.descricao) > 20 else s.descricao, size=10, color=Palette.TEXT_SECONDARY), width=80)),
            ]) for s in secoes]
            tabela = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("x (m)", size=11)), ft.DataColumn(ft.Text("Mk", size=11)),
                    ft.DataColumn(ft.Text("Vk", size=11)), ft.DataColumn(ft.Text("Tipo", size=11)),
                    ft.DataColumn(ft.Text("Descrição", size=11)),
                ], rows=rows,
                column_spacing=8,
                heading_row_height=Spacing.XL, data_row_min_height=Spacing.XL,
                border=ft.Border.all(1, Palette.OUTLINE_VARIANT), border_radius=br_all(Radius.SM),
                horizontal_lines=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
            )
            viewer_flexao.controls.append(ft.Container(height=Spacing.SM))
            viewer_flexao.controls.append(ft.Text(f"{len(secoes)} seções críticas detectadas", size=12, weight=ft.FontWeight.BOLD))
            viewer_flexao.controls.append(tabela)

        # Viewer de cisalhamento: mesma info básica
        viewer_cisalhamento.controls.append(info)

    _atualizar_viewer()

    # ── Tab de trechos (centro) ──────────────────────────────────────────
    if is_t:
        flex_specs = [
            ("viga_t_secao.png", "Geometria e nomenclatura da seção transversal T colaborante")
        ]
        flex_title = "Seção Transversal T"
        flex_sub = "Dimensões da seção de viga T"
    else:
        flex_specs = [
            ("momento_fletor.jpg", "Diagrama de momento fletor e deformação sob flexão"),
            ("partes_armadura_viga.png", "Gaiola de armadura 3D típica (longitudinal e transversal)")
        ]
        flex_title = "Flexão em Viga Comum"
        flex_sub = "Comportamento e distribuição de armadura"

    cis_specs = [
        ("bielas_tirantes.jpg", "Modelo de Bielas e Tirantes (Treliça de Mörsch)"),
        ("cisalhamento.png", "Fissuração inclinada a 45° típica do ensaio ao cisalhamento")
    ]

    flex_illustrations = _build_illustrations_panel(page, flex_title, flex_sub, flex_specs)
    cis_illustrations = _build_illustrations_panel(page, "Cisalhamento em Viga", "Analogia de treliça e padrão de fissuração", cis_specs)

    page_flex_content = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=viewer_flexao,
                    expand=3,
                ),
                ft.Container(
                    content=flex_illustrations,
                    expand=2,
                ),
            ],
            spacing=Spacing.MD,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=pad_all(Spacing.MD),
    )
    
    page_cis_content = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=viewer_cisalhamento,
                    expand=3,
                ),
                ft.Container(
                    content=cis_illustrations,
                    expand=2,
                ),
            ],
            spacing=Spacing.MD,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=pad_all(Spacing.MD),
    )

    tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label="Flexao", icon=ft.Icons.SQUARE_OUTLINED),
            ft.Tab(label="Cisalhamento", icon=ft.Icons.SWAP_VERT),
        ],
        indicator_color=Palette.PRIMARY,
        label_color=Palette.PRIMARY,
    )

    tab_view = ft.TabBarView(
        controls=[page_flex_content, page_cis_content],
        clip_behavior=ft.ClipBehavior.NONE,
        expand=True,
    )

    tabs_control = ft.Tabs(
        content=ft.Column(controls=[tab_bar, tab_view], spacing=0, expand=True),
        length=2,
        expand=True,
    )

    # ── Centro: entrada manual (tabela de trechos) ─────────────────────────
    manual_flex_panel = build_trechos_panel(page, md_rows, "M")
    manual_cis_panel = build_trechos_panel(page, vk_rows, "V")

    btn_calcular_manual = primary_button(
        "Calcular",
        icon=ft.Icons.CALCULATE,
        on_click=on_calculate,
        expand=True,
    )

    btn_calcular_manual_cis = primary_button(
        "Calcular",
        icon=ft.Icons.CALCULATE,
        on_click=on_calculate,
        expand=True,
    )

    manual_calc_card = surface_card(
        ft.Column(
            controls=[
                section_header(
                    "Cálculo manual",
                    icon=ft.Icon(ft.Icons.CALCULATE, size=16, color=Palette.PRIMARY),
                ),
                ft.Text(
                    "Informe os momentos e cortantes nos trechos abaixo e clique em Calcular.",
                    size=11, color=Palette.TEXT_SECONDARY,
                ),
                ft.Container(height=Spacing.SM),
                btn_calcular_manual,
            ],
            spacing=Spacing.SM,
        ),
        padding=Spacing.LG,
    )

    manual_calc_card_cis = surface_card(
        ft.Column(
            controls=[
                section_header(
                    "Cálculo manual",
                    icon=ft.Icon(ft.Icons.CALCULATE, size=16, color=Palette.PRIMARY),
                ),
                ft.Text(
                    "Informe os momentos e cortantes nos trechos abaixo e clique em Calcular.",
                    size=11, color=Palette.TEXT_SECONDARY,
                ),
                ft.Container(height=Spacing.SM),
                btn_calcular_manual_cis,
            ],
            spacing=Spacing.SM,
        ),
        padding=Spacing.LG,
    )

    manual_tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label="Flexao", icon=ft.Icons.SQUARE_OUTLINED),
            ft.Tab(label="Cisalhamento", icon=ft.Icons.SWAP_VERT),
        ],
        indicator_color=Palette.PRIMARY,
        label_color=Palette.PRIMARY,
    )

    manual_flex_content = ft.Container(
        content=ft.Column(
            controls=[manual_calc_card, manual_flex_panel],
            spacing=Spacing.MD,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=pad_all(Spacing.MD),
        expand=True,
    )

    manual_cis_content = ft.Container(
        content=ft.Column(
            controls=[manual_calc_card_cis, manual_cis_panel],
            spacing=Spacing.MD,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=pad_all(Spacing.MD),
        expand=True,
    )

    manual_tab_view = ft.TabBarView(
        controls=[manual_flex_content, manual_cis_content],
        clip_behavior=ft.ClipBehavior.NONE,
        expand=True,
    )

    manual_tabs_control = ft.Tabs(
        content=ft.Column(controls=[manual_tab_bar, manual_tab_view], spacing=0, expand=True),
        length=2,
        expand=True,
    )

    # ── Holders:sidebar e centro trocam de conteudo conforme a entrada ────
    sidebar_holder = ft.Container(
        content=None,
        width=300,
        padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.MD),
        bgcolor=Palette.BG,
    )

    center_holder = ft.Container(
        content=None,
        expand=True,
        bgcolor=Palette.BG,
    )

    def _build_center_content():
        """Conteudo central conforme a fonte de entrada ativa."""
        if ftool_visivel(state["entrada"]):
            return tabs_control
        return manual_tabs_control

    def _refresh_entrada_ui():
        """Reconstroi sidebar e centro para refletir a fonte de entrada."""
        try:
            sidebar_holder.content = build_sidebar()
            center_holder.content = _build_center_content()
            page.update()
        except (AssertionError, RuntimeError):
            # page.update() pode falhar se a pagina foi fechada
            pass

    sidebar_holder.content = build_sidebar()
    center_holder.content = _build_center_content()

    # ── Layout final: 3 colunas ─────────────────────────────────────────
    body = ft.Row(
        controls=[
            sidebar_holder,
            ft.Container(
                content=center_holder,
                expand=True,
                bgcolor=Palette.BG,
                padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.MD),
            ),
            ft.Container(
                content=right_sidebar,
                width=300,
                padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.MD),
                bgcolor=Palette.BG,
            ),
        ],
        spacing=0, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    # Retorna o layout principal da tela

    screen = ft.Column(
        controls=[topbar, ft.Container(content=body, expand=True)],
        spacing=0, expand=True,
    )

    # Carrega arquivo inicial (aberto pela lista de recentes)
    if initial_file:
        async def _auto_load():
            try:
                with open(initial_file, "r", encoding="utf-8") as f:
                    proj_data = json.load(f)
                saved_modo = proj_data.get("modo", "comum")
                if saved_modo != modo:
                    show_msg(
                        f"Este projeto foi criado no modo de Viga "
                        f"{'T' if saved_modo == 't' else 'Retangular'}. "
                        "Altere o modo na tela inicial para importar.",
                        Palette.WARNING,
                    )
                    return

                edicao = proj_data.get("edicao", "")
                msg_aviso = aviso_edicao(edicao)

                # Fonte de entrada (manual | FTOOL) — retrocompatível
                aplicar_entrada_projeto(state, proj_data)

                viga_nome_tf.control.value = proj_data.get("viga_nome", "")
                h_tf.control.value = proj_data.get("geometria", {}).get("h_cm", "")
                bw_tf.control.value = proj_data.get("geometria", {}).get("bw_cm", "")
                if is_t:
                    bf_tf.control.value = proj_data.get("geometria", {}).get("bf_cm", "")
                    hf_tf.control.value = proj_data.get("geometria", {}).get("hf_cm", "")
                    b1esq_tf.control.value = proj_data.get("geometria", {}).get("b1esq_cm", "")
                    b1dir_tf.control.value = proj_data.get("geometria", {}).get("b1dir_cm", "")

                caa_dd.control.value = str(proj_data.get("materiais", {}).get("caa", "2"))
                fck_dd.control.value = str(proj_data.get("materiais", {}).get("fck_mpa", "25"))
                fyk_dd.control.value = str(proj_data.get("materiais", {}).get("fyk_mpa", "50"))
                fyke_dd.control.value = str(proj_data.get("materiais", {}).get("fyk_estribo_mpa", "60"))
                gamma_f_dd.control.value = str(proj_data.get("materiais", {}).get("gamma_f", "normais"))
                phi_est_dd.control.value = str(proj_data.get("materiais", {}).get("diam_estribo_mm", "5"))
                phi_bar_dd.control.value = str(proj_data.get("materiais", {}).get("diam_barra_mm", "12.5"))

                resp_nome_tf.control.value = proj_data.get("nome_engenheiro", "")
                resp_registro_tf.control.value = proj_data.get("crea_uf", "")
                prof_dd.control.value = str(proj_data.get("profissao", "Engenheiro Civil"))

                saved_momentos = proj_data.get("esforcos", {}).get("momentos_kNm", [])
                saved_cortantes = proj_data.get("esforcos", {}).get("cortantes_kN", [])

                md_rows.clear()
                for idx, val in enumerate(saved_momentos):
                    md_rows.append(_make_trecho_field("M", idx + 1, str(val)))
                if "M" in panel_rebuilds:
                    panel_rebuilds["M"]()

                vk_rows.clear()
                for idx, val in enumerate(saved_cortantes):
                    vk_rows.append(_make_trecho_field("V", idx + 1, str(val)))
                if "V" in panel_rebuilds:
                    panel_rebuilds["V"]()

                saved_ftool = proj_data.get("ftool", {})
                state["ftool_path"] = saved_ftool.get("ftool_path")
                state["ftool_filename"] = saved_ftool.get("ftool_filename")
                state["ftool_momento_path"] = saved_ftool.get("ftool_momento_path")
                state["ftool_cortante_path"] = saved_ftool.get("ftool_cortante_path")
                state["ftool_deformacao_path"] = saved_ftool.get("ftool_deformacao_path")
                state["ftool_momentos"] = saved_ftool.get("ftool_momentos")
                state["ftool_cortantes"] = saved_ftool.get("ftool_cortantes")
                state["ftool_deformacoes"] = saved_ftool.get("ftool_deformacoes")
                
                # Conversão explícita para tuplas para garantir imutabilidade nos dados de esforços
                if state.get("ftool_momentos"):
                    state["ftool_momentos"] = [tuple(pt) for pt in state["ftool_momentos"]]
                if state.get("ftool_cortantes"):
                    state["ftool_cortantes"] = [tuple(pt) for pt in state["ftool_cortantes"]]
                if state.get("ftool_deformacoes"):
                    state["ftool_deformacoes"] = [tuple(pt) for pt in state["ftool_deformacoes"]]

                raw_secoes = saved_ftool.get("ftool_secoes_criticas", [])
                if raw_secoes:
                    from ui.ftool.secoes_criticas import SecaoCritica
                    state["ftool_secoes_criticas"] = [SecaoCritica(**s) for s in raw_secoes]
                else:
                    state["ftool_secoes_criticas"] = None
                # Reconstroi o painel conforme a entrada do projeto ANTES de
                # tocar nos controles do painel FTOOL.
                _refresh_entrada_ui()

                if ftool_visivel(state["entrada"]):
                    update_ftool_preview()

                    # Sincroniza os rótulos de UI correspondentes
                    for lbl, key in [
                        (lbl_ftool_momento, "ftool_momento_path"),
                        (lbl_ftool_cortante, "ftool_cortante_path"),
                        (lbl_ftool_deformacao, "ftool_deformacao_path")
                    ]:
                        path_val = state.get(key)
                        if path_val:
                            lbl.value = os.path.basename(path_val)
                            lbl.color = Palette.TEXT_PRIMARY
                        else:
                            lbl.value = "Nenhum"
                            lbl.color = Palette.TEXT_DISABLED
                        lbl.update()

                    _atualizar_viewer()
                    _check_ftool_pronto()

                state["resultados_flex"] = None
                state["resultados_cis"] = None
                btn_gerar_pdf.disabled = True
                btn_exportar_dxf.disabled = True

                add_recent(initial_file, modo=modo)
                page.update()
                if msg_aviso:
                    show_msg(msg_aviso, Palette.WARNING)
                else:
                    show_msg("Projeto importado com sucesso", Palette.SUCCESS)
            except Exception as ex:
                show_msg(f"Erro ao carregar projeto: {ex}", Palette.ERROR)

        page.run_task(_auto_load)

    return screen


# ── Helpers de dialogs NBR (locais para evitar dependencia circular) ──────

def _open_caa(page):
    from ui.dialogs import open_caa_info
    open_caa_info(page)


def _open_cobrimento(page):
    from ui.dialogs import open_cobrimento_info
    open_cobrimento_info(page)


def _open_diametros(page):
    from ui.dialogs import open_diametros_info
    open_diametros_info(page)


def _open_fck(page):
    from ui.dialogs import open_fck_info
    open_fck_info(page)


def _open_aco(page):
    from ui.dialogs import open_aco_info
    open_aco_info(page)


def _open_gamma_f(page):
    from ui.dialogs import open_gamma_f_info
    open_gamma_f_info(page)


def _open_geometria(page):
    from ui.dialogs import open_geometria_info
    open_geometria_info(page)


def _open_viga_t(page):
    from ui.dialogs import open_viga_t_info
    open_viga_t_info(page)


def _open_b1(page):
    from ui.dialogs import open_b1_info
    open_b1_info(page)
