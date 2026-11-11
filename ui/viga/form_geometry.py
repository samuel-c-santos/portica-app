"""Formulario de geometria (h, bw, bf, hf), validadores e montagem da sidebar.

EP-04.3: extraido de ui/viga.py; funcoes recebem `ctx` (ViewContext) explicito.
"""

from functools import partial

import flet as ft

from ui.entrada import (
    ftool_visivel,
)
from ui.theme import (
    Palette,
    Spacing,
    section_header,
    surface_card,
    tonal_button,
)
from ui.viga.widgets import (
    _open_b1,
    _open_geometria,
    _open_viga_t,
    _styled_dropdown,
    _styled_textfield,
)


# Validation helpers (logica pura: texto -> mensagem de erro | None)
def erro_numero_positivo(texto):
    """Erro de validacao para um campo numerico > 0 (None = valido)."""
    val_str = texto.strip()
    if not val_str:
        return "Campo obrigatório"
    try:
        val_float = float(val_str.replace(",", "."))
    except ValueError:
        return "Use número com vírgula (ex: 50,0)"
    return "Deve ser maior que 0" if val_float <= 0 else None


def erro_numero_nao_negativo(texto):
    """Erro de validacao para um campo numerico >= 0 (None = valido)."""
    val_str = texto.strip()
    if not val_str:
        return "Campo obrigatório"
    try:
        val_float = float(val_str.replace(",", "."))
    except ValueError:
        return "Use número com vírgula (ex: 50,0)"
    return "Não pode ser negativo" if val_float < 0 else None


def erro_campo_trecho(texto):
    """Campo de trecho: vazio e valido; se preenchido, deve ser numero."""
    val_str = texto.strip()
    if not val_str:
        return None
    try:
        float(val_str.replace(",", "."))
    except ValueError:
        return "Inválido"
    return None


def validate_positive_number(ctx, e):
    e.control.error_text = erro_numero_positivo(e.control.value)
    ctx.page.update()


def validate_non_negative_number(ctx, e):
    e.control.error_text = erro_numero_nao_negativo(e.control.value)
    ctx.page.update()


def validate_trecho_field(ctx, e):
    e.control.error_text = erro_campo_trecho(e.control.value)
    ctx.page.update()


def setup_validadores(ctx):
    """Passo de construcao: setup_validadores."""
    ctx.validate_positive_number = partial(validate_positive_number, ctx)

    ctx.validate_non_negative_number = partial(validate_non_negative_number, ctx)

    ctx.validate_trecho_field = partial(validate_trecho_field, ctx)


def _on_geom_change(ctx, original_callback):
    def wrapper(e):
        original_callback(e)
        ctx._check_ftool_pronto()

    return wrapper


def run_manual_validations(ctx):
    ok = True

    # Validar h
    h_val = ctx.h_tf.control.value.strip()
    if not h_val:
        ctx.h_tf.control.error_text = "Campo obrigatório"
        ok = False
    else:
        try:
            if float(h_val.replace(",", ".")) <= 0:
                ctx.h_tf.control.error_text = "Deve ser maior que 0"
                ok = False
            else:
                ctx.h_tf.control.error_text = None
        except ValueError:
            ctx.h_tf.control.error_text = "Use número (ex: 50,0)"
            ok = False

    # Validar bw
    bw_val = ctx.bw_tf.control.value.strip()
    if not bw_val:
        ctx.bw_tf.control.error_text = "Campo obrigatório"
        ok = False
    else:
        try:
            if float(bw_val.replace(",", ".")) <= 0:
                ctx.bw_tf.control.error_text = "Deve ser maior que 0"
                ok = False
            else:
                ctx.bw_tf.control.error_text = None
        except ValueError:
            ctx.bw_tf.control.error_text = "Use número (ex: 20,0)"

            ok = False

    if ctx.is_t:
        for tf_ctrl, _ in [(ctx.bf_tf, "bf"), (ctx.hf_tf, "hf")]:
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
    for tf in ctx.md_rows + ctx.vk_rows:
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

    ctx.page.update()
    return ok


def setup_geometria(ctx):
    """Passo de construcao: setup_geometria."""

    # ── Builder da sidebar de geometria ──────────────────────────────────
    ctx.viga_nome_tf = _styled_textfield(
        "Identificacao da Viga",
        "V1" if ctx.modo == "comum" else "VT1",
        keyboard_type=ft.KeyboardType.TEXT,
        max_length=30,
    )

    ctx._on_geom_change = partial(_on_geom_change, ctx)

    ctx.h_tf = _styled_textfield(
        "d (cm)",
        "",
        on_change=ctx._on_geom_change(ctx.validate_positive_number),
        info_on_click=lambda e: _open_geometria(ctx.page),
    )

    ctx.bw_tf = _styled_textfield(
        "tw (cm)",
        "",
        on_change=ctx._on_geom_change(ctx.validate_positive_number),
        info_on_click=lambda e: _open_geometria(ctx.page),
    )

    ctx.bf_tf = _styled_textfield(
        "b (cm)",
        "60",
        on_change=ctx.validate_positive_number,
        info_on_click=lambda e: _open_viga_t(ctx.page),
    )

    ctx.hf_tf = _styled_textfield(
        "tf (cm)",
        "12",
        on_change=ctx.validate_positive_number,
        info_on_click=lambda e: _open_viga_t(ctx.page),
    )

    ctx.b1esq_tf = _styled_textfield(
        "b1 esquerdo (cm)",
        "40",
        on_change=ctx.validate_non_negative_number,
        info_on_click=lambda e: _open_b1(ctx.page),
    )

    ctx.b1dir_tf = _styled_textfield(
        "b1 direito (cm)",
        "40",
        on_change=ctx.validate_non_negative_number,
        info_on_click=lambda e: _open_b1(ctx.page),
    )

    # RT inputs
    ctx.PROFISSOES = [
        "Engenheiro Civil",
        "Projetista / Calculista",
        "Arquiteto",
        "Técnico em Edificações",
        "Engenheiro (outras áreas)",
    ]

    ctx.prof_dd = _styled_dropdown(
        "Profissão", "Engenheiro Civil", [ft.dropdown.Option(p) for p in ctx.PROFISSOES]
    )

    ctx.resp_nome_tf = _styled_textfield(
        "Nome do Responsável", "", keyboard_type=ft.KeyboardType.TEXT, max_length=40
    )

    ctx.resp_registro_tf = _styled_textfield(
        "CREA/UF", "", keyboard_type=ft.KeyboardType.TEXT, max_length=20
    )

    ctx.is_t = ctx.modo == "t"

    ctx.geom_widgets = [
        ctx.h_tf,
        ctx.bw_tf,
    ]

    if ctx.is_t:
        ctx.geom_widgets += [ctx.bf_tf, ctx.hf_tf, ctx.b1esq_tf, ctx.b1dir_tf]

    ctx.run_manual_validations = partial(run_manual_validations, ctx)


# ── Builder de sidebar (esquerda) ────────────────────────────────────
def build_sidebar(ctx):
    geom_card = surface_card(
        ft.Column(
            controls=[
                section_header(
                    "Geometria",
                    icon=ft.Icon(ft.Icons.SQUARE_OUTLINED, size=16, color=Palette.TEXT_SECONDARY),
                ),
                ctx.viga_nome_tf,
                *ctx.geom_widgets,
            ],
            spacing=Spacing.MD,
        ),
        padding=Spacing.LG,
    )

    resp_card = surface_card(
        ft.Column(
            controls=[
                section_header(
                    "Responsabilidade Técnica",
                    icon=ft.Icon(ft.Icons.PERSON_OUTLINE, size=16, color=Palette.TEXT_SECONDARY),
                ),
                ctx.prof_dd,
                ctx.resp_nome_tf,
                ctx.resp_registro_tf,
            ],
            spacing=Spacing.MD,
        ),
        padding=Spacing.LG,
    )

    mat_card = surface_card(
        ft.Column(
            controls=[
                section_header(
                    "Materiais",
                    icon=ft.Icon(ft.Icons.SCIENCE_OUTLINED, size=16, color=Palette.TEXT_SECONDARY),
                ),
                ctx.caa_dd,
                ctx.fck_dd,
                ctx.fyk_dd,
                ctx.fyke_dd,
                ctx.gamma_f_dd,
            ],
            spacing=Spacing.MD,
        ),
        padding=Spacing.LG,
    )

    arm_card = surface_card(
        ft.Column(
            controls=[
                section_header(
                    "Armaduras",
                    icon=ft.Icon(ft.Icons.CONSTRUCTION, size=16, color=Palette.TEXT_SECONDARY),
                ),
                ctx.phi_est_dd,
                ctx.phi_bar_dd,
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
                        on_click=ctx.on_fechar_ftool,
                        style=ft.ButtonStyle(text_style=ft.TextStyle(size=11)),
                    ),
                ),
                ft.Text(
                    "Arquivos .txt exportados do FTOOL:", size=11, color=Palette.TEXT_SECONDARY
                ),
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.UPLOAD_FILE, size=14, color=Palette.PRIMARY),
                        ft.Container(width=Spacing.XS),
                        ft.Text("Momentos", size=12, expand=True),
                        ft.OutlinedButton(
                            "...", icon=ft.Icons.FILE_UPLOAD, height=28, on_click=ctx._pick_momento
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ctx.lbl_ftool_momento,
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.UPLOAD_FILE, size=14, color=Palette.PRIMARY),
                        ft.Container(width=Spacing.XS),
                        ft.Text("Cortantes", size=12, expand=True),
                        ft.OutlinedButton(
                            "...", icon=ft.Icons.FILE_UPLOAD, height=28, on_click=ctx._pick_cortante
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ctx.lbl_ftool_cortante,
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.UPLOAD_FILE, size=14, color=Palette.PRIMARY),
                        ft.Container(width=Spacing.XS),
                        ft.Text("Deformações", size=12, expand=True),
                        ft.OutlinedButton(
                            "...",
                            icon=ft.Icons.FILE_UPLOAD,
                            height=28,
                            on_click=ctx._pick_deformacao,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ctx.lbl_ftool_deformacao,
                ctx.btn_processar_ftool,
                ft.Divider(height=1, color=Palette.OUTLINE_VARIANT),
                ft.Text("Envelope de Combinações", size=12, weight=ft.FontWeight.BOLD),
                ctx.combs_column,
                ft.Row(
                    controls=[
                        ft.OutlinedButton(
                            "Adicionar",
                            icon=ft.Icons.ADD,
                            icon_color=Palette.PRIMARY,
                            height=32,
                            style=ft.ButtonStyle(text_style=ft.TextStyle(size=12)),
                            on_click=ctx.on_add_comb_click,
                        ),
                        ctx.btn_calc_envelope,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                ),
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
                    "Ou calcule a viga a partir dos arquivos .txt exportados do FTOOL.",
                    size=11,
                    color=Palette.TEXT_SECONDARY,
                ),
                ft.Container(height=Spacing.SM),
                tonal_button(
                    "Importar do FTOOL",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=ctx.on_abrir_ftool,
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
            ftool_card if ftool_visivel(ctx.state["entrada"]) else ftool_entry_card,
        ],
        spacing=Spacing.MD,
        scroll=ft.ScrollMode.AUTO,
    )


def setup_sidebar(ctx):
    """Passo de construcao: setup_sidebar."""
    ctx.build_sidebar = partial(build_sidebar, ctx)
