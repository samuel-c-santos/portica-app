"""Painel FTOOL: arquivos, combinacoes, envelope e zona de arraste.

EP-04.3: extraido de ui/viga.py; funcoes recebem `ctx` (ViewContext) explicito.
"""

import os
from functools import partial

import flet as ft

from core.calculos import (
    GAMMA_F_TABLE,
)
from core.utils_tempfile import temp_path
from ui.entrada import (
    ENTRADA_FTOOL,
    ENTRADA_MANUAL,
)
from ui.ftool.parser import validate_file_type
from ui.theme import (
    Palette,
    Radius,
    Spacing,
    body_small,
    br_all,
    caption,
    pad_all,
    pad_sym,
    primary_button,
    section_header,
    surface_card,
    title_medium,
)


def update_combs_ui(ctx):
    ctx.combs_column.controls.clear()
    for idx, c in enumerate(ctx.state.get("combinacoes", [])):
        ctx.combs_column.controls.append(
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.ALT_ROUTE, size=12, color=Palette.PRIMARY),
                    ft.Text(f"{c['nome']}", size=11, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=14,
                        icon_color=Palette.ERROR,
                        tooltip="Remover",
                        on_click=lambda e, i=idx: ctx.remove_comb(i),
                    ),
                ]
            )
        )
    ctx.btn_calc_envelope.disabled = len(ctx.state.get("combinacoes", [])) < 2
    ctx.page.update()


def remove_comb(ctx, idx):
    if "combinacoes" in ctx.state and idx < len(ctx.state["combinacoes"]):
        ctx.state["combinacoes"].pop(idx)
        ctx.update_combs_ui()


def setup_controles_ftool(ctx):
    """Passo de construcao: setup_controles_ftool."""

    ctx.combs_column = ft.Column(spacing=Spacing.XS)

    ctx.btn_calc_envelope = ft.OutlinedButton(
        "Calcular",
        icon=ft.Icons.CALCULATE,
        on_click=lambda e: ctx.on_calcular_envelope_click(e),
        disabled=True,
        height=32,
        style=ft.ButtonStyle(text_style=ft.TextStyle(size=12)),
    )

    ctx.update_combs_ui = partial(update_combs_ui, ctx)

    ctx.remove_comb = partial(remove_comb, ctx)

    # Labels dos arquivos FTOOL selecionados
    ctx.lbl_ftool_momento = ft.Text("Nenhum", size=11, color=Palette.TEXT_DISABLED, expand=True)

    ctx.lbl_ftool_cortante = ft.Text("Nenhum", size=11, color=Palette.TEXT_DISABLED, expand=True)

    ctx.lbl_ftool_deformacao = ft.Text("Nenhum", size=11, color=Palette.TEXT_DISABLED, expand=True)

    ctx.btn_processar_ftool = ft.Button(
        "Processar",
        icon=ft.Icons.PLAY_ARROW,
        on_click=lambda e: ctx.processar_ftool(),
        disabled=True,
        tooltip="Selecione os 3 arquivos TXT e preencha h, bw e φ barra",
        style=ft.ButtonStyle(
            bgcolor=Palette.PRIMARY,
            color=Palette.ON_PRIMARY,
            padding=pad_sym(horizontal=Spacing.XL, vertical=Spacing.MD),
            shape=ft.RoundedRectangleBorder(radius=br_all(Radius.MD)),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        ),
    )

    ctx.panel_rebuilds = {}  # dicionario para armazenar funcoes de reconstrucao de trechos


# ── Fonte de entrada: manual (padrao) x FTOOL (opcional) ─────────────
def on_abrir_ftool(ctx, e):
    """Revela o painel FTOOL: a fonte de entrada passa a ser o FTOOL."""
    ctx.state["entrada"] = ENTRADA_FTOOL
    ctx._refresh_entrada_ui()


def on_fechar_ftool(ctx, e):
    """Fecha o painel FTOOL e volta para a entrada manual."""
    ctx.state["entrada"] = ENTRADA_MANUAL
    ctx._refresh_entrada_ui()


def setup_alternancia_entrada(ctx):
    """Passo de construcao: setup_alternancia_entrada."""
    ctx.on_abrir_ftool = partial(on_abrir_ftool, ctx)

    ctx.on_fechar_ftool = partial(on_fechar_ftool, ctx)


async def select_momento_click(ctx, e):
    await ctx.fp_momento_env.pick_files(
        dialog_title="Selecionar arquivo de momentos (.txt)", allowed_extensions=["txt"]
    )


async def select_cortante_click(ctx, e):
    await ctx.fp_cortante_env.pick_files(
        dialog_title="Selecionar arquivo de cortantes (.txt)", allowed_extensions=["txt"]
    )


def on_momento_env_result(ctx, e):
    if e.files:
        ctx.state["temp_momento_path"] = e.files[0].path
        ctx.lbl_momento.value = os.path.basename(e.files[0].path)
        ctx.lbl_momento.color = Palette.TEXT_PRIMARY
        ctx.lbl_momento.update()


def on_cortante_env_result(ctx, e):
    if e.files:
        ctx.state["temp_cortante_path"] = e.files[0].path
        ctx.lbl_cortante.value = os.path.basename(e.files[0].path)
        ctx.lbl_cortante.color = Palette.TEXT_PRIMARY
        ctx.lbl_cortante.update()


def _make_ftool_picker(ctx, tipo):
    lbl_map = {
        "momento": ctx.lbl_ftool_momento,
        "cortante": ctx.lbl_ftool_cortante,
        "deformacao": ctx.lbl_ftool_deformacao,
    }
    state_key = f"ftool_{tipo}_path"

    async def _pick(e):
        files = await ctx.fp_pick.pick_files(
            dialog_title=f"Selecionar arquivo de {tipo}s (.txt)", allowed_extensions=["txt"]
        )
        if files:
            filepath = files[0].path
            valido, msg_erro = validate_file_type(filepath, tipo)
            if not valido:
                ctx.show_msg(f"Arquivo inválido: {msg_erro}", Palette.ERROR)
                return

            ctx.state[state_key] = filepath
            ctx.state["ftool_momentos"] = None
            ctx.state["ftool_cortantes"] = None
            ctx.state["ftool_deformacoes"] = None
            ctx.state["ftool_secoes_criticas"] = None
            lbl = lbl_map[tipo]
            lbl.value = os.path.basename(filepath)
            lbl.color = Palette.TEXT_PRIMARY
            lbl.update()
            ctx._check_ftool_pronto()

    return _pick


def _check_ftool_pronto(ctx):
    arquivos_ok = all(
        ctx.state.get(k)
        for k in ("ftool_momento_path", "ftool_cortante_path", "ftool_deformacao_path")
    )
    dados_ok = (
        ctx.state.get("ftool_momentos") is not None
    )  # dados ja carregados (ex: projeto salvo)
    try:
        h_ok = float(ctx.h_tf.control.value.replace(",", ".") or 0) > 0
        bw_ok = float(ctx.bw_tf.control.value.replace(",", ".") or 0) > 0
        phi_ok = float(ctx.phi_bar_dd.control.value or 0) > 0
    except (ValueError, TypeError, AttributeError):
        h_ok = bw_ok = phi_ok = False

    faltando = []
    if not arquivos_ok and not dados_ok:
        faltando.append("3 arquivos TXT")
    if not h_ok:
        faltando.append("altura h")
    if not bw_ok:
        faltando.append("largura bw")
    if not phi_ok:
        faltando.append("φ barra")
    ctx.btn_processar_ftool.disabled = len(faltando) > 0
    ctx.btn_processar_ftool.tooltip = (
        f"Preencha: {', '.join(faltando)}" if faltando else "Processar arquivos FTOOL"
    )
    ctx.page.update()


def setup_seletores_ftool(ctx):
    """Passo de construcao: setup_seletores_ftool."""

    # ── Envelope de Combinações ──────────────────────────────────────────
    ctx.lbl_momento = ft.Text(
        "Nenhum selecionado", size=11, color=Palette.TEXT_DISABLED, expand=True
    )

    ctx.lbl_cortante = ft.Text(
        "Nenhum selecionado", size=11, color=Palette.TEXT_DISABLED, expand=True
    )

    ctx.fp_momento_env = ft.FilePicker()

    ctx.fp_cortante_env = ft.FilePicker()

    ctx.page.services.append(ctx.fp_momento_env)

    ctx.page.services.append(ctx.fp_cortante_env)

    ctx.select_momento_click = partial(select_momento_click, ctx)

    ctx.select_cortante_click = partial(select_cortante_click, ctx)

    ctx.on_momento_env_result = partial(on_momento_env_result, ctx)

    ctx.on_cortante_env_result = partial(on_cortante_env_result, ctx)

    ctx.fp_momento_env.on_result = ctx.on_momento_env_result

    ctx.fp_cortante_env.on_result = ctx.on_cortante_env_result

    # ── FTOOL File Pickers Individuais ──────────────────────────────────
    ctx.fp_pick = ft.FilePicker()

    ctx.page.services.append(ctx.fp_pick)

    ctx._make_ftool_picker = partial(_make_ftool_picker, ctx)

    ctx._pick_momento = ctx._make_ftool_picker("momento")

    ctx._pick_cortante = ctx._make_ftool_picker("cortante")

    ctx._pick_deformacao = ctx._make_ftool_picker("deformacao")

    ctx._check_ftool_pronto = partial(_check_ftool_pronto, ctx)


def on_add_comb_click(ctx, e):
    ctx.state["temp_momento_path"] = None
    ctx.state["temp_cortante_path"] = None
    ctx.lbl_momento.value = "Nenhum selecionado"
    ctx.lbl_cortante.value = "Nenhum selecionado"

    name_tf = ft.TextField(
        label="Nome da Combinação",
        value=f"Combinação {len(ctx.state.get('combinacoes', [])) + 1}",
        border_color=Palette.OUTLINE_VARIANT,
        height=45,
    )

    def save_comb(ev):
        nome = name_tf.value.strip()
        if not nome:
            ctx.show_msg("Digite um nome para a combinação", Palette.WARNING)
            return
        if not ctx.state["temp_momento_path"] or not ctx.state["temp_cortante_path"]:
            ctx.show_msg("Selecione ambos os arquivos (momentos e cortantes)", Palette.WARNING)
            return

        ctx.state.setdefault("combinacoes", []).append(
            {
                "nome": nome,
                "momento_path": ctx.state["temp_momento_path"],
                "cortante_path": ctx.state["temp_cortante_path"],
            }
        )
        ctx.page.pop_dialog()
        ctx.update_combs_ui()
        ctx.show_msg(f"Combinação '{nome}' adicionada", Palette.SUCCESS)

    add_dlg = ft.AlertDialog(
        modal=True,
        title=title_medium("Adicionar Combinação FTOOL"),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    name_tf,
                    ft.Container(height=Spacing.XS),
                    ft.Text(
                        "Arquivo de Momento Fletor (x vs M):",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton("Selecionar...", on_click=ctx.select_momento_click),
                            ctx.lbl_momento,
                        ],
                        spacing=Spacing.MD,
                    ),
                    ft.Container(height=Spacing.XS),
                    ft.Text(
                        "Arquivo de Esforço Cortante (x vs V):",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton("Selecionar...", on_click=ctx.select_cortante_click),
                            ctx.lbl_cortante,
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
            ft.TextButton("Cancelar", on_click=lambda ev: ctx.page.pop_dialog()),
            ft.ElevatedButton(
                "Salvar", on_click=save_comb, bgcolor=Palette.PRIMARY, color=Palette.ON_PRIMARY
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=Palette.SURFACE,
        shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG)),
    )
    ctx.page.show_dialog(add_dlg)


def on_calcular_envelope_click(ctx, e):
    try:
        from ui.ftool.parser import parse_cortante, parse_momento

        combs_parsed = []
        for c in ctx.state["combinacoes"]:
            m_pts = parse_momento(c["momento_path"])
            v_pts = parse_cortante(c["cortante_path"])
            combs_parsed.append({"nome": c["nome"], "momentos": m_pts, "cortantes": v_pts})

        from ui.ftool.envelope import (
            aplicar_curvas_envelope_ao_state,
            calcular_envelope,
            detectar_secoes_envelope,
            gerar_relatorio_envelope,
        )

        env = calcular_envelope(combs_parsed)
        secoes = detectar_secoes_envelope(combs_parsed, env)

        # EP-01.5: state["ftool_momentos"/"ftool_cortantes"] são SEMPRE
        # listas de tuplas; as curvas max/min ficam em chaves próprias.
        aplicar_curvas_envelope_ao_state(ctx.state, env)
        ctx.state["ftool_secoes_criticas"] = secoes

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
            ctx.page.pop_dialog()

        def on_calcular_envelope_confirm_click(ev):
            ctx.page.pop_dialog()
            try:
                h = float(ctx.h_tf.control.value or 0)
                bw = float(ctx.bw_tf.control.value or 0)
                fck = float(ctx.fck_dd.control.value or 0)
                fyk = float(ctx.fyk_dd.control.value or 0)
                fyke = float(ctx.fyke_dd.control.value or 0)
                caa = int(ctx.caa_dd.control.value)
                diam_est = float(ctx.phi_est_dd.control.value)
                diam_bar = float(ctx.phi_bar_dd.control.value)

                try:
                    gamma_f = GAMMA_F_TABLE[ctx.gamma_f_dd.control.value]["gamma_f"]
                except (KeyError, TypeError):
                    gamma_f = 1.4
            except (ValueError, KeyError, TypeError) as ex:
                ctx.show_msg(f"Por favor, verifique os campos da viga: {ex}", Palette.WARNING)
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

                resultados = dimensionar_trechos_ftool(
                    dados_viga,
                    secoes,
                    momentos=ctx.state.get("ftool_momentos"),
                    cortantes=ctx.state.get("ftool_cortantes"),
                    deformacoes=ctx.state.get("ftool_deformacoes"),
                )
                sec_results = resultados["secoes"]

                ctx.state["resultados_flex"] = [res["resultado_flexao"] for res in sec_results]
                ctx.state["resultados_cis"] = [res["resultado_cisalhamento"] for res in sec_results]

                ctx.btn_gerar_pdf.disabled = False
                ctx.btn_exportar_dxf.disabled = False
                ctx.page.update()

                relatorio_text = gerar_relatorio_envelope(dados_viga, env, secoes)

                results_dlg = ft.AlertDialog(
                    modal=True,
                    title=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=Palette.SUCCESS),
                            ft.Container(width=Spacing.SM),
                            title_medium("Dimensionamento Automático - Envelope"),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    "Dimensionamento concluído com base no envelope de combinações.",
                                    size=14,
                                    color=Palette.TEXT_SECONDARY,
                                ),
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
                                ),
                            ],
                            expand=True,
                        ),
                        width=800,
                        height=540,
                        padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.SM),
                    ),
                    actions=[
                        ft.OutlinedButton(
                            "Fechar",
                            on_click=lambda ev2: ctx.page.pop_dialog(),
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                    bgcolor=Palette.SURFACE,
                    shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG)),
                )
                ctx.page.show_dialog(results_dlg)
            except Exception as ex:
                ctx.show_msg(f"Erro no dimensionamento do envelope: {ex}", Palette.ERROR)

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
                        ft.Text(
                            f"Identificadas {len(secoes)} seções críticas a partir do envelope das combinações.",
                            size=14,
                            color=Palette.TEXT_SECONDARY,
                        ),
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
                primary_button(
                    "Calcular Envelope",
                    icon=ft.Icons.PLAY_ARROW,
                    on_click=on_calcular_envelope_confirm_click,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=Palette.SURFACE,
            shape=ft.RoundedRectangleBorder(radius=br_all(Radius.LG)),
        )
        ctx.page.show_dialog(env_dlg)

    except Exception as ex:
        ctx.show_msg(f"Erro ao processar envelope: {ex}", Palette.ERROR)


def setup_envelope(ctx):
    """Passo de construcao: setup_envelope."""
    ctx.on_add_comb_click = partial(on_add_comb_click, ctx)

    ctx.on_calcular_envelope_click = partial(on_calcular_envelope_click, ctx)


# ── Drop zone (imagem do Ftool) ─────────────────────────────────────
def _build_drop_placeholder(ctx):
    return ft.Column(
        controls=[
            ft.Container(
                content=ft.Icon(
                    ft.Icons.CLOUD_UPLOAD_OUTLINED, size=42, color=Palette.TEXT_DISABLED
                ),
                alignment=ft.Alignment.CENTER,
            ),
            ft.Container(height=Spacing.SM),
            body_small(
                "Clique para selecionar",
                color=Palette.TEXT_PRIMARY,
                text_align=ft.TextAlign.CENTER,
            ),
            caption(
                "PNG / JPG / SVG do Ftool",
                color=Palette.TEXT_DISABLED,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=Spacing.XS,
    )


async def on_drop_zone_click(ctx, e):
    """Abre file picker para escolher imagem."""
    files = await ctx.fp_image.pick_files(
        allow_multiple=False, allowed_extensions=["png", "jpg", "jpeg", "svg"]
    )
    if files:
        f = files[0]
        ctx.state["ftool_path"] = f.path
        ctx.state["ftool_filename"] = f.name
        ctx.update_ftool_preview()
        ctx.page.update()


def update_ftool_preview(ctx):
    """Substitui o placeholder pelo preview quando ha imagem."""
    if ctx.state.get("ftool_path") and os.path.exists(ctx.state["ftool_path"]):
        img_path = ctx.state["ftool_path"]
        # SVG: converter para PNG temporario para preview (Flet desktop nao renderiza SVG)
        if img_path.lower().endswith(".svg"):
            try:
                import re

                from reportlab.graphics import renderPM
                from svglib.svglib import svg2rlg

                # Sanitizar dash arrays invalidos do FTOOL
                with open(img_path, encoding="utf-8", errors="ignore") as f:
                    svg_content = f.read()
                svg_clean = re.sub(
                    r'stroke-dasharray\s*=\s*"[^"]*"', 'stroke-dasharray="1"', svg_content
                )
                svg_clean = re.sub(
                    r"stroke-dasharray\s*=\s*'[^']*'", "stroke-dasharray='1'", svg_clean
                )
                svg_clean = re.sub(
                    r'stroke-dasharray\s*:\s*[^;"\']+', "stroke-dasharray:1", svg_clean
                )
                temp_svg = temp_path(suffix=".svg")
                with open(temp_svg, "w", encoding="utf-8") as f:
                    f.write(svg_clean)
                drawing = svg2rlg(temp_svg)
                if drawing is not None:
                    png_temp = temp_path(suffix=".png")
                    renderPM.drawToFile(drawing, png_temp, fmt="PNG", dpi=150)
                    ctx.state["_png_preview_temp"] = png_temp
                    img_path = png_temp
                try:
                    os.remove(temp_svg)
                except OSError:
                    pass
            except (ImportError, AttributeError, RuntimeError, OSError):
                # Faltam libs (svglib/reportlab) ou erro de render
                pass

        ctx.drop_zone_content.content = ft.Image(
            src=img_path,
            width=280,
            height=140,
            fit=ft.BoxFit.CONTAIN,
        )
        ctx.drop_zone_content.border = ft.Border.all(2, Palette.SUCCESS)
        ctx.drop_zone_content.bgcolor = Palette.SURFACE
        ctx.ftool_filename_text.value = ctx.state["ftool_filename"]
        ctx.ftool_filename_text.color = Palette.TEXT_SECONDARY
    else:
        # Limpar PNG temporario anterior se houver
        old_png = ctx.state.pop("_png_preview_temp", None)
        if old_png and os.path.exists(old_png):
            try:
                os.remove(old_png)
            except OSError:
                pass
        ctx.drop_zone_content.content = ctx._build_drop_placeholder()
        ctx.drop_zone_content.border = ft.Border.all(2, Palette.OUTLINE_VARIANT)
        ctx.drop_zone_content.bgcolor = Palette.SURFACE_VARIANT
        ctx.ftool_filename_text.value = "Nenhuma imagem selecionada"
        ctx.ftool_filename_text.color = Palette.TEXT_DISABLED


def setup_dropzone(ctx):
    """Passo de construcao: setup_dropzone."""
    ctx._build_drop_placeholder = partial(_build_drop_placeholder, ctx)

    ctx.drop_zone_content = ft.Container(
        content=ctx._build_drop_placeholder(),
        width=280,
        height=140,
        border=ft.Border.all(2, Palette.OUTLINE_VARIANT),
        border_radius=br_all(Radius.MD),
        bgcolor=Palette.SURFACE_VARIANT,
        alignment=ft.Alignment.CENTER,
        padding=Spacing.MD,
        ink=True,
    )

    ctx.on_drop_zone_click = partial(on_drop_zone_click, ctx)

    ctx.drop_zone_content.on_click = ctx.on_drop_zone_click

    # Texto de nome do arquivo (atualizado dinamicamente apos selecao)
    ctx.ftool_filename_text = ft.Text(
        ctx.state.get("ftool_filename") or "Nenhuma imagem selecionada",
        size=11,
        color=Palette.TEXT_DISABLED,
        text_align=ft.TextAlign.CENTER,
    )

    ctx.update_ftool_preview = partial(update_ftool_preview, ctx)

    # ── Sidebar direita (imagem + acoes) ─────────────────────────────────
    ctx.ftool_card = surface_card(  # noqa: F841  # card construído e não renderizado (backlog EP-04/EP-05)
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
                    content=ctx.drop_zone_content,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(height=Spacing.XS),
                ctx.ftool_filename_text,
            ],
            spacing=Spacing.XS,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=Spacing.LG,
    )
