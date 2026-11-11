"""Visualizacao de resultados: modal, viewer de flexao/cisalhamento e abas.

EP-04.3: extraido de ui/viga.py; funcoes recebem `ctx` (ViewContext) explicito.
"""

from functools import partial

import flet as ft

from core.calculos import (
    CAA_DATA,
    area_barra,
)
from core.format import fmt_diam, fmt_num
from ui.theme import (
    SHADOW_SM,
    Palette,
    Radius,
    Spacing,
    br_all,
    caption,
    numeric_text,
    pad_all,
    pad_only,
    pad_sym,
    primary_button,
    section_header,
    status_chip,
    surface_card,
    title_medium,
    title_small,
)
from ui.viga.widgets import (
    _build_illustrations_panel,
)


# ── Modal de resultados ──────────────────────────────────────────────
def open_resultados_modal(ctx):
    import math

    res_flex = ctx.state["resultados_flex"]
    res_cis = ctx.state["resultados_cis"]

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
                bw = float(ctx.bw_tf.control.value or 12.0)
                caa = int(ctx.caa_dd.control.value)
                diam_est = float(ctx.phi_est_dd.control.value or 5.0)
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
                eh_passa_1 = eh_1 >= eh_tol

            if eh_passa_1:
                eh_status = "CABE"
                status_type = "ok"
                eh_val = eh_1
                r.eh_passa = "SIM"
                r.barras_suportadas = r.qtd_barras
                r.barras_cima = 0
                obs_det = ""
                eh_tooltip = f"As barras cabem em 1 única camada. Espaçamento horizontal livre eh = {fmt_num(eh_val, 2, unidade='cm')} (mínimo {fmt_num(eh_min, 1, unidade='cm')})."
            else:
                n_max_layer = math.ceil(r.qtd_barras / 2)
                if n_max_layer <= 1:
                    eh_2 = espaco_disp - phi_cm
                    eh_passa_2 = True
                else:
                    eh_2 = (espaco_disp - n_max_layer * phi_cm) / (n_max_layer - 1)
                    eh_passa_2 = eh_2 >= eh_tol

                if eh_passa_2:
                    eh_status = "2 CAMADAS"
                    status_type = "warn"
                    eh_val = eh_2
                    r.eh_passa = "SIM"
                    r.barras_suportadas = n_max_layer
                    r.barras_cima = r.qtd_barras - n_max_layer
                    obs_det = "Requer cavaletes transversais (ex: φ12,5 a cada 1 m) para separar as camadas"
                    if n_max_layer >= 4 and bw >= 30:
                        obs_det += (
                            " | Adotar grampos de travamento φ5,0 conectando as barras centrais"
                        )
                    eh_tooltip = f"As barras não cabem em 1 camada, mas cabem em 2 camadas. Espaçamento horizontal livre eh = {fmt_num(eh_val, 2, unidade='cm')} (mínimo {fmt_num(eh_min, 1, unidade='cm')}). {obs_det}"
                else:
                    eh_status = "NÃO CABE"
                    status_type = "error"
                    eh_val = eh_1
                    r.eh_passa = "NÃO"
                    r.barras_suportadas = r.qtd_barras
                    r.barras_cima = 0
                    obs_det = ""
                    eh_tooltip = f"O espaçamento horizontal livre ({fmt_num(eh_val, 2, unidade='cm')}) é inferior ao mínimo regulamentar de {fmt_num(eh_min, 1, unidade='cm')}, mesmo em 2 camadas."

            if hasattr(r, "eh_suportado"):
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
                n_bars = math.ceil(r.as_necessaria_cm2 / a_bar) if a_bar > 0 else 0
                is_chosen = d == r.diametro_mm
                text_color = Palette.PRIMARY if is_chosen else Palette.TEXT_PRIMARY
                text_weight = ft.FontWeight.BOLD if is_chosen else ft.FontWeight.NORMAL
                diam_rows.append(
                    ft.Row(
                        controls=[
                            ft.Text(
                                fmt_diam(d, prefixo="Ø ") + (" (atual)" if is_chosen else ""),
                                size=11,
                                color=text_color,
                                weight=text_weight,
                            ),
                            ft.Text(
                                f"{n_bars}",
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=text_color,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )
                )

            def make_bitola_change_handler(r_obj):
                def on_change(e):
                    val = float(e.control.value)
                    r_obj.diametro_mm = val
                    a_bar = area_barra(val)
                    r_obj.qtd_barras = (
                        math.ceil(r_obj.as_necessaria_cm2 / a_bar) if a_bar > 0 else 0
                    )
                    rebuild_results_ui()
                    ctx.page.update()

                return on_change

            diam_dd = ft.Dropdown(
                value=str(r.diametro_mm),
                options=[
                    ft.dropdown.Option(str(d))
                    for d in [5.0, 6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0, 32.0]
                ],
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
                                ft.Text(
                                    f"M{i + 1}",
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color=Palette.PRIMARY,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        r.tipo,
                                        size=9,
                                        weight=ft.FontWeight.BOLD,
                                        color=Palette.ON_PRIMARY,
                                    ),
                                    bgcolor=Palette.PRIMARY
                                    if r.tipo == "POSITIVO"
                                    else Palette.SECONDARY,
                                    padding=pad_sym(horizontal=4, vertical=1),
                                    border_radius=br_all(3),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(color=Palette.OUTLINE_VARIANT, height=1),
                        ft.Row(
                            [
                                ft.Text("KC:", size=10, color=Palette.TEXT_SECONDARY),
                                numeric_text(fmt_num(r.kc, 2), size=10, weight=ft.FontWeight.BOLD),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("Bx:", size=10, color=Palette.TEXT_SECONDARY),
                                numeric_text(fmt_num(r.bx, 3), size=10, weight=ft.FontWeight.BOLD),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("PASSA?", size=10, color=Palette.TEXT_SECONDARY),
                                ft.Text(
                                    bx_status,
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                    color=bx_color,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("KS:", size=10, color=Palette.TEXT_SECONDARY),
                                numeric_text(fmt_num(r.ks, 3), size=10, weight=ft.FontWeight.BOLD),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("As:", size=10, color=Palette.TEXT_SECONDARY),
                                numeric_text(
                                    fmt_num(r.as_req_cm2, 2), size=10, weight=ft.FontWeight.BOLD
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("Asmin:", size=10, color=Palette.TEXT_SECONDARY),
                                numeric_text(
                                    fmt_num(r.asmin_cm2, 2), size=10, weight=ft.FontWeight.BOLD
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("AsUSADO:", size=10, color=Palette.TEXT_SECONDARY),
                                numeric_text(
                                    fmt_num(r.as_necessaria_cm2, 2),
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(color=Palette.OUTLINE_VARIANT, height=1),
                        ft.Text(
                            "BARRAS",
                            size=10,
                            weight=ft.FontWeight.BOLD,
                            color=Palette.TEXT_SECONDARY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        *diam_rows,
                        ft.Divider(color=Palette.OUTLINE_VARIANT, height=1),
                        ft.Text(
                            "Ø ESCOLHIDO:",
                            size=10,
                            weight=ft.FontWeight.BOLD,
                            color=Palette.TEXT_SECONDARY,
                        ),
                        diam_dd,
                        ft.Container(height=2),
                        ft.Row(
                            controls=[
                                ft.Text(
                                    f"Qtd: {r.qtd_barras}", size=11, weight=ft.FontWeight.W_500
                                ),
                                chip,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text(
                            f"eh: {fmt_num(eh_val, 1, unidade='cm')} (mín 2 cm)",
                            size=10,
                            color=Palette.TEXT_SECONDARY,
                        ),
                    ],
                    spacing=5,
                ),
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
                    ft.Text(
                        "ARMADURA DE PELE",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=Palette.SECONDARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        f"As,min/face: {fmt_num(r.as_pele_min_face_cm2, 2, unidade='cm²')} | s,máx: {fmt_num(r.s_pele_max_cm, 0, unidade='cm')}",
                        size=9,
                        color=Palette.TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER,
                    ),
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
                                    ft.Text(
                                        fmt_diam(phi, prefixo="Ø "),
                                        size=10,
                                        color=Palette.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        f"{n}x  s={fmt_num(s, 0, unidade='cm')}  {fmt_num(as_val, 2, unidade='cm²')}",
                                        size=10,
                                        color=Palette.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        "OK" if cabe else "NÃO",
                                        size=10,
                                        weight=ft.FontWeight.BOLD,
                                        color=Palette.SUCCESS if cabe else Palette.ERROR,
                                    ),
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
                        ctx.page.update()

                    return on_change

                pele_dd = ft.Dropdown(
                    value=str(r.phi_pele_mm),
                    options=[
                        ft.dropdown.Option(str(item["phi_mm"])) for item in (r.tabela_pele or [])
                    ],
                    border_radius=br_all(Radius.SM),
                    dense=True,
                    text_size=11,
                    filled=True,
                    bgcolor=Palette.SURFACE_VARIANT,
                    border_color=Palette.OUTLINE_VARIANT,
                    on_select=make_pele_bitola_handler(r),
                )
                pele_controls.append(
                    ft.Text(
                        "Ø PELE:",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=Palette.TEXT_SECONDARY,
                    )
                )
                pele_controls.append(pele_dd)
                pele_controls.append(ft.Container(height=2))
                pele_controls.append(
                    ft.Row(
                        controls=[
                            ft.Text(
                                f"Qtd/face: {r.n_barras_pele_face}",
                                size=11,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Text(
                                f"s: {fmt_num(r.s_pele_cm, 0, unidade='cm')}",
                                size=11,
                                color=Palette.TEXT_SECONDARY,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )
                )
                pele_controls.append(
                    ft.Text(
                        f"As/face: {fmt_num(r.as_pele_face_cm2, 2, unidade='cm²')}",
                        size=10,
                        color=Palette.TEXT_SECONDARY,
                    )
                )

            # Adicionar controles de pele ao card
            if pele_controls:
                card.content.controls.extend(pele_controls)

            flex_cards.controls.append(card)

    # Initial build
    rebuild_results_ui()

    flex_section = ft.Column(
        controls=[
            section_header(
                "Flexão (Dimensionamento de Armaduras)",
                icon=ft.Icon(ft.Icons.SQUARE_OUTLINED, size=16, color=Palette.PRIMARY),
            ),
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
        rows_cis.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(title_small(f"V{i + 1}", color=Palette.TEXT_PRIMARY)),
                    ft.DataCell(
                        numeric_text(
                            fmt_num(r.vsd_verdadeiro_kn, 1, unidade="kN"),
                            size=12,
                            color=Palette.TEXT_PRIMARY,
                        )
                    ),
                    ft.DataCell(
                        numeric_text(
                            fmt_num(r.vrd2_kn, 1, unidade="kN"),
                            size=12,
                            color=Palette.TEXT_PRIMARY,
                        )
                    ),
                    ft.DataCell(
                        numeric_text(
                            fmt_num(r.vsw_kn, 1, unidade="kN"),
                            size=12,
                            color=Palette.TEXT_PRIMARY,
                        )
                    ),
                    ft.DataCell(
                        numeric_text(
                            fmt_num(r.dist_estribos_cm, 1, unidade="cm"),
                            size=12,
                            color=Palette.TEXT_PRIMARY,
                        )
                    ),
                    ft.DataCell(
                        status_chip(status_label, "ok" if r.passa_vrd2 == "SIM" else "error")
                    ),
                ],
            )
        )

    cis_section = ft.Column(
        controls=[
            ft.Container(height=Spacing.LG),
            section_header(
                "Cisalhamento", icon=ft.Icon(ft.Icons.SWAP_VERT, size=16, color=Palette.PRIMARY)
            ),
            ft.Container(height=Spacing.SM),
            ft.DataTable(
                columns=[
                    ft.DataColumn(title_small("Trecho")),
                    ft.DataColumn(title_small("Vsolic (kN)"), numeric=True),
                    ft.DataColumn(title_small("Vrd2 (kN)"), numeric=True),
                    ft.DataColumn(title_small("Vsw (kN)"), numeric=True),
                    ft.DataColumn(title_small("Espaçamento"), numeric=True),
                    ft.DataColumn(title_small("Status")),
                ],
                rows=rows_cis,
                heading_row_height=Spacing.XL + 8,
                data_row_min_height=Spacing.XL + 4,
                border=ft.Border.all(1, Palette.OUTLINE_VARIANT),
                border_radius=br_all(Radius.SM),
                vertical_lines=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
                horizontal_lines=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
            )
            if rows_cis
            else caption("Nenhum trecho calculado.", color=Palette.TEXT_DISABLED),
        ],
        spacing=0,
    )

    results_content = ft.Column(
        controls=[flex_section, cis_section],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )

    async def on_gerar_pdf_click(e):
        ctx.page.pop_dialog()
        await ctx.on_gerar_pdf(e)

    results_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=Palette.PRIMARY),
                ft.Container(width=Spacing.SM),
                title_medium("Resultados do cálculo"),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(
            content=results_content,
            width=800,
            height=540,
            padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.SM),
        ),
        actions=[
            ft.OutlinedButton(
                "Fechar",
                on_click=lambda e: ctx.page.pop_dialog(),
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
    ctx.page.show_dialog(results_dialog)


def setup_modal_resultados(ctx):
    """Passo de construcao: setup_modal_resultados."""
    ctx.open_resultados_modal = partial(open_resultados_modal, ctx)


def _atualizar_viewer(ctx):
    ctx.viewer_flexao.controls.clear()
    ctx.viewer_cisalhamento.controls.clear()
    momentos = ctx.state.get("ftool_momentos")
    cortantes = ctx.state.get("ftool_cortantes")
    secoes = ctx.state.get("ftool_secoes_criticas")

    if not momentos or not cortantes:
        msg = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.CLOUD_UPLOAD, size=48, color=Palette.TEXT_DISABLED),
                    ft.Container(height=Spacing.SM),
                    ft.Text(
                        "Importe os arquivos .txt do FTOOL pela barra lateral",
                        size=14,
                        color=Palette.TEXT_DISABLED,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=pad_all(Spacing.XL),
            expand=True,
            alignment=ft.Alignment(0, 0),
        )
        ctx.viewer_flexao.controls.append(msg)
        ctx.viewer_cisalhamento.controls.append(msg)
        return

    n_mom = len(momentos)
    n_cort = len(cortantes)
    L = max(p[0] for p in momentos)
    m_max = max(p[1] for p in momentos)
    m_min = min(p[1] for p in momentos)
    v_max = max(p[1] for p in cortantes)
    v_min = min(p[1] for p in cortantes)

    info = surface_card(
        ft.Column(
            [
                ft.Text(
                    "Dados importados do FTOOL",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=Palette.PRIMARY,
                ),
                ft.Divider(color=Palette.OUTLINE_VARIANT, height=1),
                ft.Row(
                    [
                        ft.Text("Vão total:", size=12, color=Palette.TEXT_SECONDARY),
                        numeric_text(fmt_num(L, 2, unidade="m"), size=12),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        ft.Text("Pontos de momento:", size=12, color=Palette.TEXT_SECONDARY),
                        numeric_text(f"{n_mom}", size=12),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        ft.Text("M máx:", size=12, color=Palette.TEXT_SECONDARY),
                        numeric_text(
                            fmt_num(m_max, 1, sinal=True, unidade="kN·m"),
                            size=12,
                            color=Palette.PRIMARY,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        ft.Text("M mín:", size=12, color=Palette.TEXT_SECONDARY),
                        numeric_text(
                            fmt_num(m_min, 1, sinal=True, unidade="kN·m"),
                            size=12,
                            color=Palette.SECONDARY,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        ft.Text("Pontos de cortante:", size=12, color=Palette.TEXT_SECONDARY),
                        numeric_text(f"{n_cort}", size=12),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        ft.Text("V máx:", size=12, color=Palette.TEXT_SECONDARY),
                        numeric_text(
                            fmt_num(v_max, 1, sinal=True, unidade="kN"),
                            size=12,
                            color=Palette.PRIMARY,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(
                    [
                        ft.Text("V mín:", size=12, color=Palette.TEXT_SECONDARY),
                        numeric_text(
                            fmt_num(v_min, 1, sinal=True, unidade="kN"),
                            size=12,
                            color=Palette.SECONDARY,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ]
        ),
        padding=Spacing.LG,
    )
    ctx.viewer_flexao.controls.append(info)

    if secoes:
        rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(numeric_text(fmt_num(s.x, 2), size=11)),
                    ft.DataCell(numeric_text(fmt_num(s.momento, 1), size=11)),
                    ft.DataCell(numeric_text(fmt_num(s.cortante, 1), size=11)),
                    ft.DataCell(status_chip(s.tipo, "info")),
                    ft.DataCell(
                        ft.Container(
                            ft.Text(
                                s.descricao[:20] + ".." if len(s.descricao) > 20 else s.descricao,
                                size=10,
                                color=Palette.TEXT_SECONDARY,
                            ),
                            width=80,
                        )
                    ),
                ]
            )
            for s in secoes
        ]
        tabela = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("x (m)", size=11), numeric=True),
                ft.DataColumn(ft.Text("Mk", size=11), numeric=True),
                ft.DataColumn(ft.Text("Vk", size=11), numeric=True),
                ft.DataColumn(ft.Text("Tipo", size=11)),
                ft.DataColumn(ft.Text("Descrição", size=11)),
            ],
            rows=rows,
            column_spacing=8,
            heading_row_height=Spacing.XL,
            data_row_min_height=Spacing.XL,
            border=ft.Border.all(1, Palette.OUTLINE_VARIANT),
            border_radius=br_all(Radius.SM),
            horizontal_lines=ft.BorderSide(1, Palette.OUTLINE_VARIANT),
        )
        ctx.viewer_flexao.controls.append(ft.Container(height=Spacing.SM))
        ctx.viewer_flexao.controls.append(
            ft.Text(f"{len(secoes)} seções críticas detectadas", size=12, weight=ft.FontWeight.BOLD)
        )
        ctx.viewer_flexao.controls.append(tabela)

    # Viewer de cisalhamento: mesma info básica
    ctx.viewer_cisalhamento.controls.append(info)


def setup_viewer(ctx):
    """Passo de construcao: setup_viewer."""

    # ── Visualizador de dados FTOOL (centro) ──────────────────────────────
    ctx.viewer_flexao = ft.Column(spacing=Spacing.SM)

    ctx.viewer_cisalhamento = ft.Column(spacing=Spacing.SM)

    ctx._atualizar_viewer = partial(_atualizar_viewer, ctx)

    ctx._atualizar_viewer()

    # ── Tab de trechos (centro) ──────────────────────────────────────────
    if ctx.is_t:
        ctx.flex_specs = [
            ("viga_t_secao.png", "Geometria e nomenclatura da seção transversal T colaborante")
        ]
        ctx.flex_title = "Seção Transversal T"
        ctx.flex_sub = "Dimensões da seção de viga T"
    else:
        ctx.flex_specs = [
            ("momento_fletor.jpg", "Diagrama de momento fletor e deformação sob flexão"),
            (
                "partes_armadura_viga.png",
                "Gaiola de armadura 3D típica (longitudinal e transversal)",
            ),
        ]
        ctx.flex_title = "Flexão em Viga Comum"
        ctx.flex_sub = "Comportamento e distribuição de armadura"

    ctx.cis_specs = [
        ("bielas_tirantes.jpg", "Modelo de Bielas e Tirantes (Treliça de Mörsch)"),
        ("cisalhamento.png", "Fissuração inclinada a 45° típica do ensaio ao cisalhamento"),
    ]

    ctx.flex_illustrations = _build_illustrations_panel(
        ctx.page, ctx.flex_title, ctx.flex_sub, ctx.flex_specs
    )

    ctx.cis_illustrations = _build_illustrations_panel(
        ctx.page,
        "Cisalhamento em Viga",
        "Analogia de treliça e padrão de fissuração",
        ctx.cis_specs,
    )

    ctx.page_flex_content = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ctx.viewer_flexao,
                    expand=3,
                ),
                ft.Container(
                    content=ctx.flex_illustrations,
                    expand=2,
                ),
            ],
            spacing=Spacing.MD,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=pad_all(Spacing.MD),
    )

    ctx.page_cis_content = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ctx.viewer_cisalhamento,
                    expand=3,
                ),
                ft.Container(
                    content=ctx.cis_illustrations,
                    expand=2,
                ),
            ],
            spacing=Spacing.MD,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=pad_all(Spacing.MD),
    )

    ctx.tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label="Flexão", icon=ft.Icons.SQUARE_OUTLINED),
            ft.Tab(label="Cisalhamento", icon=ft.Icons.SWAP_VERT),
        ],
        indicator_color=Palette.PRIMARY,
        label_color=Palette.PRIMARY,
    )

    ctx.tab_view = ft.TabBarView(
        controls=[ctx.page_flex_content, ctx.page_cis_content],
        clip_behavior=ft.ClipBehavior.NONE,
        expand=True,
    )

    ctx.tabs_control = ft.Tabs(
        content=ft.Column(controls=[ctx.tab_bar, ctx.tab_view], spacing=0, expand=True),
        length=2,
        expand=True,
    )
