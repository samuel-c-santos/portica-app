"""Orquestracao da tela de viga: monta o contexto e encadeia os passos de cada modulo.

EP-04.3: extraido de ui/viga.py; funcoes recebem `ctx` (ViewContext) explicito.
"""

import json
import logging
import os
from functools import partial

import flet as ft

from ui.entrada import (
    aplicar_entrada_projeto,
    aviso_edicao,
    ftool_visivel,
)
from ui.recent_projects import add_recent
from ui.theme import (
    Palette,
    Radius,
    Spacing,
    br_all,
    label_medium,
    overline,
    pad_sym,
    title_large,
)
from ui.viga import (
    actions,
    form_geometry,
    form_materials,
    form_trechos,
    ftool_processing,
    panel_ftool,
    results_view,
)
from ui.viga.state import ViewContext

logger = logging.getLogger(__name__)


def _setup_topbar(ctx):
    """Passo de construcao: _setup_topbar."""

    # ── Top bar ──────────────────────────────────────────────────────────
    ctx.topbar = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=Palette.TEXT_PRIMARY,
                    tooltip="Voltar para o início",
                    on_click=lambda e: ctx.on_back(),
                ),
                ft.Container(width=Spacing.SM),
                ft.Column(
                    controls=[
                        overline("MODO DE CÁLCULO", color=Palette.TEXT_SECONDARY),
                        title_large(
                            "Viga Comum - Flexão e Cisalhamento"
                            if not ctx.is_t
                            else "Viga T - Flexão e Cisalhamento",
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
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.XS),
                    border_radius=br_all(Radius.PILL),
                    bgcolor=Palette.SURFACE_VARIANT,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=pad_sym(horizontal=Spacing.LG, vertical=Spacing.MD),
        bgcolor=Palette.SURFACE,
        border=ft.Border(bottom=ft.BorderSide(1, Palette.OUTLINE_VARIANT)),
    )


def _build_center_content(ctx):
    """Conteudo central conforme a fonte de entrada ativa."""
    if ftool_visivel(ctx.state["entrada"]):
        return ctx.tabs_control
    return ctx.manual_tabs_control


def _refresh_entrada_ui(ctx):
    """Reconstroi sidebar e centro para refletir a fonte de entrada."""
    try:
        ctx.sidebar_holder.content = ctx.build_sidebar()
        ctx.center_holder.content = ctx._build_center_content()
        ctx.page.update()
    except (AssertionError, RuntimeError):
        # page.update() pode falhar se a pagina foi fechada
        pass


def _setup_layout(ctx):
    """Passo de construcao: _setup_layout."""

    # ── Holders:sidebar e centro trocam de conteudo conforme a entrada ────
    ctx.sidebar_holder = ft.Container(
        content=None,
        width=300,
        padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.MD),
        bgcolor=Palette.BG,
        alignment=ft.Alignment(-1, -1),
    )

    ctx.center_holder = ft.Container(
        content=None,
        expand=True,
        bgcolor=Palette.BG,
    )

    ctx._build_center_content = partial(_build_center_content, ctx)

    ctx._refresh_entrada_ui = partial(_refresh_entrada_ui, ctx)

    ctx.sidebar_holder.content = ctx.build_sidebar()

    ctx.center_holder.content = ctx._build_center_content()

    # ── Layout final: 3 colunas ─────────────────────────────────────────
    ctx.body = ft.Row(
        controls=[
            ctx.sidebar_holder,
            ft.Container(
                content=ctx.center_holder,
                expand=True,
                bgcolor=Palette.BG,
                padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.MD),
            ),
            ft.Container(
                content=ctx.right_sidebar,
                width=300,
                padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.MD),
                bgcolor=Palette.BG,
                alignment=ft.Alignment(-1, -1),
            ),
        ],
        spacing=0,
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    # Retorna o layout principal da tela

    ctx.screen = ft.Column(
        controls=[ctx.topbar, ft.Container(content=ctx.body, expand=True)],
        spacing=0,
        expand=True,
    )


def _setup_carga_inicial(ctx):
    """Passo de construcao: _setup_carga_inicial."""

    # Carrega arquivo inicial (aberto pela lista de recentes)
    if ctx.initial_file:

        async def _auto_load():
            try:
                with open(ctx.initial_file, encoding="utf-8") as f:
                    proj_data = json.load(f)
                saved_modo = proj_data.get("modo", "comum")
                if saved_modo != ctx.modo:
                    ctx.show_msg(
                        f"Este projeto foi criado no modo de Viga "
                        f"{'T' if saved_modo == 't' else 'Retangular'}. "
                        "Altere o modo na tela inicial para importar.",
                        Palette.WARNING,
                    )
                    return

                edicao = proj_data.get("edicao", "")
                msg_aviso = aviso_edicao(edicao)

                # Fonte de entrada (manual | FTOOL) — retrocompatível
                aplicar_entrada_projeto(ctx.state, proj_data)

                ctx.viga_nome_tf.control.value = proj_data.get("viga_nome", "")
                ctx.h_tf.control.value = proj_data.get("geometria", {}).get("h_cm", "")
                ctx.bw_tf.control.value = proj_data.get("geometria", {}).get("bw_cm", "")
                if ctx.is_t:
                    ctx.bf_tf.control.value = proj_data.get("geometria", {}).get("bf_cm", "")
                    ctx.hf_tf.control.value = proj_data.get("geometria", {}).get("hf_cm", "")
                    ctx.b1esq_tf.control.value = proj_data.get("geometria", {}).get("b1esq_cm", "")
                    ctx.b1dir_tf.control.value = proj_data.get("geometria", {}).get("b1dir_cm", "")

                ctx.caa_dd.control.value = str(proj_data.get("materiais", {}).get("caa", "2"))
                ctx.fck_dd.control.value = str(proj_data.get("materiais", {}).get("fck_mpa", "25"))
                ctx.fyk_dd.control.value = str(proj_data.get("materiais", {}).get("fyk_mpa", "50"))
                ctx.fyke_dd.control.value = str(
                    proj_data.get("materiais", {}).get("fyk_estribo_mpa", "60")
                )
                ctx.gamma_f_dd.control.value = str(
                    proj_data.get("materiais", {}).get("gamma_f", "normais")
                )
                ctx.phi_est_dd.control.value = str(
                    proj_data.get("materiais", {}).get("diam_estribo_mm", "5")
                )
                ctx.phi_bar_dd.control.value = str(
                    proj_data.get("materiais", {}).get("diam_barra_mm", "12.5")
                )

                ctx.resp_nome_tf.control.value = proj_data.get("nome_engenheiro", "")
                ctx.resp_registro_tf.control.value = proj_data.get("crea_uf", "")
                ctx.prof_dd.control.value = str(proj_data.get("profissao", "Engenheiro Civil"))

                saved_momentos = proj_data.get("esforcos", {}).get("momentos_kNm", [])
                saved_cortantes = proj_data.get("esforcos", {}).get("cortantes_kN", [])

                ctx.md_rows.clear()
                for idx, val in enumerate(saved_momentos):
                    ctx.md_rows.append(ctx._make_trecho_field("M", idx + 1, str(val)))
                if "M" in ctx.panel_rebuilds:
                    ctx.panel_rebuilds["M"]()

                ctx.vk_rows.clear()
                for idx, val in enumerate(saved_cortantes):
                    ctx.vk_rows.append(ctx._make_trecho_field("V", idx + 1, str(val)))
                if "V" in ctx.panel_rebuilds:
                    ctx.panel_rebuilds["V"]()

                saved_ftool = proj_data.get("ftool", {})
                ctx.state["ftool_path"] = saved_ftool.get("ftool_path")
                ctx.state["ftool_filename"] = saved_ftool.get("ftool_filename")
                ctx.state["ftool_momento_path"] = saved_ftool.get("ftool_momento_path")
                ctx.state["ftool_cortante_path"] = saved_ftool.get("ftool_cortante_path")
                ctx.state["ftool_deformacao_path"] = saved_ftool.get("ftool_deformacao_path")
                ctx.state["ftool_momentos"] = saved_ftool.get("ftool_momentos")
                ctx.state["ftool_cortantes"] = saved_ftool.get("ftool_cortantes")
                ctx.state["ftool_deformacoes"] = saved_ftool.get("ftool_deformacoes")

                # Conversão explícita para tuplas para garantir imutabilidade nos dados de esforços
                if ctx.state.get("ftool_momentos"):
                    ctx.state["ftool_momentos"] = [tuple(pt) for pt in ctx.state["ftool_momentos"]]
                if ctx.state.get("ftool_cortantes"):
                    ctx.state["ftool_cortantes"] = [
                        tuple(pt) for pt in ctx.state["ftool_cortantes"]
                    ]
                if ctx.state.get("ftool_deformacoes"):
                    ctx.state["ftool_deformacoes"] = [
                        tuple(pt) for pt in ctx.state["ftool_deformacoes"]
                    ]

                raw_secoes = saved_ftool.get("ftool_secoes_criticas", [])
                if raw_secoes:
                    from ui.ftool.secoes_criticas import SecaoCritica

                    ctx.state["ftool_secoes_criticas"] = [SecaoCritica(**s) for s in raw_secoes]
                else:
                    ctx.state["ftool_secoes_criticas"] = None
                # Reconstroi o painel conforme a entrada do projeto ANTES de
                # tocar nos controles do painel FTOOL.
                ctx._refresh_entrada_ui()

                if ftool_visivel(ctx.state["entrada"]):
                    ctx.update_ftool_preview()

                    # Sincroniza os rótulos de UI correspondentes
                    for lbl, key in [
                        (ctx.lbl_ftool_momento, "ftool_momento_path"),
                        (ctx.lbl_ftool_cortante, "ftool_cortante_path"),
                        (ctx.lbl_ftool_deformacao, "ftool_deformacao_path"),
                    ]:
                        path_val = ctx.state.get(key)
                        if path_val:
                            lbl.value = os.path.basename(path_val)
                            lbl.color = Palette.TEXT_PRIMARY
                        else:
                            lbl.value = "Nenhum"
                            lbl.color = Palette.TEXT_DISABLED
                        lbl.update()

                    ctx._atualizar_viewer()
                    ctx._check_ftool_pronto()

                ctx.state["resultados_flex"] = None
                ctx.state["resultados_cis"] = None
                ctx.btn_gerar_pdf.disabled = True
                ctx.btn_exportar_dxf.disabled = True

                add_recent(ctx.initial_file, modo=ctx.modo)
                ctx.page.update()
                if msg_aviso:
                    ctx.show_msg(msg_aviso, Palette.WARNING)
                else:
                    ctx.show_msg("Projeto importado com sucesso", Palette.PRIMARY)
            except (json.JSONDecodeError, OSError, KeyError, ValueError, TypeError) as ex:
                logger.error(
                    "Erro ao carregar projeto inicial '%s': %s",
                    ctx.initial_file,
                    ex,
                    exc_info=True,
                )
                ctx.show_msg(f"Erro ao carregar projeto: {ex}", Palette.ERROR)

        ctx.page.run_task(_auto_load)


def montar_contexto(
    page,
    modo,
    on_back,
    fp_image,
    fp_pdf,
    fp_load_project,
    fp_save_project,
    fp_dxf,
    initial_file=None,
):
    """
    Constroi o ``ViewContext`` completo da tela de calculo (testavel com ``page`` falso).

    Constroi a tela completa de calculo.
    modo: "comum" | "t"
    on_back: callable() -> None (volta para home)
    initial_file: str | None  -- caminho .ptc para carregar ao abrir

    Orquestracao: cria o ``ViewContext`` (estado tipado + controles) e encadeia
    os passos de cada modulo na ordem original de construcao dos controles.
    """
    ctx = ViewContext(
        page,
        modo,
        on_back,
        fp_image,
        fp_pdf,
        fp_load_project,
        fp_save_project,
        fp_dxf,
        initial_file,
    )
    form_trechos.setup_armazenamento_trechos(ctx)
    panel_ftool.setup_controles_ftool(ctx)
    form_geometry.setup_validadores(ctx)
    form_geometry.setup_geometria(ctx)
    form_materials.setup_materiais(ctx)
    panel_ftool.setup_alternancia_entrada(ctx)
    form_geometry.setup_sidebar(ctx)
    form_trechos.setup_trechos(ctx)
    actions.setup_calculo(ctx)
    panel_ftool.setup_seletores_ftool(ctx)
    ftool_processing.setup_processamento(ctx)
    panel_ftool.setup_envelope(ctx)
    actions.setup_projeto(ctx)
    results_view.setup_modal_resultados(ctx)
    actions.setup_exportacao(ctx)
    _setup_topbar(ctx)
    panel_ftool.setup_dropzone(ctx)
    actions.setup_card_acoes(ctx)
    results_view.setup_viewer(ctx)
    form_trechos.setup_calculo_manual(ctx)
    _setup_layout(ctx)
    _setup_carga_inicial(ctx)
    return ctx


def build_viga_screen(
    page,
    modo,
    on_back,
    fp_image,
    fp_pdf,
    fp_load_project,
    fp_save_project,
    fp_dxf,
    initial_file=None,
):
    """Constroi a tela completa de calculo (``ft.Control`` raiz).

    modo: "comum" | "t"; on_back: callable() -> None (volta para home);
    initial_file: caminho .ptc para carregar ao abrir.
    """
    return montar_contexto(
        page,
        modo,
        on_back,
        fp_image,
        fp_pdf,
        fp_load_project,
        fp_save_project,
        fp_dxf,
        initial_file,
    ).screen
