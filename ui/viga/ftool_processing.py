"""Processamento da importacao FTOOL (parser -> secoes criticas -> dimensionamento -> ELS).

EP-04.3: extraido de ui/viga.py; funcoes recebem `ctx` (ViewContext) explicito.
"""

import logging
import os
from functools import partial

import flet as ft

from core.calculos import (
    GAMMA_F_TABLE,
)
from core.format import fmt_diam, fmt_num
from ui.ftool.dimensionamento import (
    dimensionar_trechos_ftool,
)
from ui.ftool.secoes_criticas import detectar_todas_secoes
from ui.theme import (
    Palette,
    Radius,
    Spacing,
    caption,
    numeric_text,
    outlined_button,
    pad_all,
    pad_sym,
    polarity_badge,
    primary_button,
    result_card,
    results_table,
    section_header,
    spacer,
    status_chip,
    surface_card,
    themed_dialog,
    title_medium,
    title_small,
)

logger = logging.getLogger(__name__)


def processar_ftool(ctx):
    # Validar geometria antes de processar
    try:
        h_val = (
            float(ctx.h_tf.control.value.replace(",", ".")) if ctx.h_tf.control.value.strip() else 0
        )
        bw_val = (
            float(ctx.bw_tf.control.value.replace(",", "."))
            if ctx.bw_tf.control.value.strip()
            else 0
        )
        phi_val = float(ctx.phi_bar_dd.control.value) if ctx.phi_bar_dd.control.value else 0
    except (ValueError, AttributeError):
        h_val = bw_val = phi_val = 0
    if h_val <= 0 or bw_val <= 0 or phi_val <= 0:
        ctx.show_msg(
            "Preencha h, bw e o diâmetro da armadura antes de importar o FTOOL", Palette.WARNING
        )
        return

    # Loading spinner
    loading = ft.AlertDialog(
        modal=True,
        content=ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(width=48, height=48, color=Palette.PRIMARY),
                    ft.Container(height=Spacing.MD),
                    ft.Text("Processando dados do FTOOL...", size=14, color=Palette.TEXT_SECONDARY),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=pad_all(Spacing.XL),
        ),
        bgcolor=ft.Colors.TRANSPARENT,
    )
    ctx.page.show_dialog(loading)
    ctx.page.update()

    try:
        # Verifica se os arquivos físicos existem localmente na máquina
        arquivos_existem = False
        try:
            arquivos_existem = all(
                ctx.state.get(k) and os.path.exists(ctx.state[k])
                for k in ("ftool_momento_path", "ftool_cortante_path", "ftool_deformacao_path")
            )
        except (OSError, TypeError, ValueError) as err:
            logger.debug("Falha ao checar arquivos FTOOL no disco: %s", err)
            arquivos_existem = False

        if arquivos_existem:
            # Força a re-leitura do disco para garantir sincronia com os arquivos mais recentes
            from ui.ftool.parser import parse_cortante, parse_deformacao, parse_momento

            momentos = parse_momento(ctx.state["ftool_momento_path"])
            cortantes = parse_cortante(ctx.state["ftool_cortante_path"])
            deformacoes = parse_deformacao(ctx.state["ftool_deformacao_path"])
            secoes = detectar_todas_secoes(momentos, cortantes)
            ctx.state["ftool_momentos"] = momentos
            ctx.state["ftool_cortantes"] = cortantes
            ctx.state["ftool_deformacoes"] = deformacoes
            ctx.state["ftool_secoes_criticas"] = secoes
        elif ctx.state.get("ftool_momentos") and ctx.state.get("ftool_cortantes"):
            # Fallback: se os arquivos não existem localmente, reutiliza os dados restaurados do JSON
            momentos = ctx.state["ftool_momentos"]
            cortantes = ctx.state["ftool_cortantes"]
            secoes = ctx.state.get("ftool_secoes_criticas") or detectar_todas_secoes(
                momentos, cortantes
            )
            deformacoes = ctx.state.get("ftool_deformacoes")
            if not deformacoes:
                try:
                    from ui.ftool.parser import parse_deformacao

                    # Primeiro tenta do path salvo
                    path = ctx.state.get("ftool_deformacao_path")
                    if path and os.path.exists(path):
                        deformacoes = parse_deformacao(path)
                    # Fallback: tenta samples/
                    else:
                        path = ctx.state.get("ftool_path", "")
                        base = os.path.dirname(path) if path else "samples"
                        candidates = [
                            f
                            for f in os.listdir(base)
                            if "deformac" in f.lower() and f.endswith(".txt")
                        ]
                        if candidates:
                            deformacoes = parse_deformacao(os.path.join(base, candidates[0]))
                    if deformacoes:
                        ctx.state["ftool_deformacoes"] = deformacoes
                except (OSError, ValueError, KeyError, IndexError) as err:
                    logger.debug("Falha ao carregar deformacoes de fallback: %s", err)
                    deformacoes = []
            if not deformacoes:
                deformacoes = []
        else:
            # Se não existem arquivos e não há esforços pré-carregados no state, tenta ler dos paths salvos (deve falhar)
            from ui.ftool.parser import parse_cortante, parse_deformacao, parse_momento

            momentos = parse_momento(ctx.state["ftool_momento_path"])
            cortantes = parse_cortante(ctx.state["ftool_cortante_path"])
            deformacoes = parse_deformacao(ctx.state["ftool_deformacao_path"])
            secoes = detectar_todas_secoes(momentos, cortantes)
            ctx.state["ftool_momentos"] = momentos
            ctx.state["ftool_cortantes"] = cortantes
            ctx.state["ftool_deformacoes"] = deformacoes
            ctx.state["ftool_secoes_criticas"] = secoes
        ctx.page.update()
        ctx._atualizar_viewer()

        rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(numeric_text(fmt_num(s.x, 2, unidade="m"), size=12)),
                    ft.DataCell(numeric_text(fmt_num(s.momento, 2), size=12)),
                    ft.DataCell(numeric_text(fmt_num(s.cortante, 2), size=12)),
                    ft.DataCell(ft.Text(s.tipo)),
                    ft.DataCell(
                        ft.Text(s.descricao[:25] + ".." if len(s.descricao) > 25 else s.descricao)
                    ),
                ]
            )
            for s in secoes
        ]
        table_container = results_table(
            columns=[
                ft.DataColumn(ft.Text("x (m)"), numeric=True),
                ft.DataColumn(ft.Text("Mk (kN·m)"), numeric=True),
                ft.DataColumn(ft.Text("Vk (kN)"), numeric=True),
                ft.DataColumn(ft.Text("Tipo")),
                ft.DataColumn(ft.Text("Descrição")),
            ],
            rows=rows,
            scroll_height=300,
        )

        def _build_resultados_controls(state, dados_viga, secoes, page, show_msg):
            """Monta a lista de controles do modal de resultados (flexão, cisalhamento, ELS)."""
            resultado_els = state.get("ftool_resultado_els")
            detalhamento = state.get("ftool_detalhamento")

            flex_cards = ft.Row(
                spacing=Spacing.MD,
                scroll=ft.ScrollMode.AUTO,
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            sec_results = []
            for i, secao in enumerate(secoes):
                rf = state["resultados_flex"][i] if i < len(state["resultados_flex"]) else None
                rc = state["resultados_cis"][i] if i < len(state["resultados_cis"]) else None
                sec_results.append(
                    {
                        "x": secao.x,
                        "momento": secao.momento,
                        "cortante": secao.cortante,
                        "resultado_flexao": rf,
                        "resultado_cisalhamento": rc,
                        "tipo": secao.tipo,
                        "descricao": secao.descricao,
                    }
                )

            # Deduplica seções adjacentes de platô com mesmo momento/armadura (ex.: x=3,70 e x=3,80 m)
            flex_groups = []
            for item in sec_results:
                r = item["resultado_flexao"]
                if r is None:
                    continue
                if flex_groups:
                    prev = flex_groups[-1]
                    pr = prev["resultado_flexao"]
                    if (
                        item["tipo"] == prev["tipo"]
                        and item["descricao"] == prev["descricao"]
                        and abs(item["momento"] - prev["momento"]) < 1e-6
                        and abs(r.as_req_cm2 - pr.as_req_cm2) < 1e-6
                        and r.qtd_barras == pr.qtd_barras
                        and r.diametro_mm == pr.diametro_mm
                        and r.bx_passa == pr.bx_passa
                    ):
                        prev["x_fim"] = item["x"]
                        continue
                flex_groups.append({**item, "x_fim": item["x"]})

            for item in flex_groups:
                r = item["resultado_flexao"]
                passa_flex = r.bx_passa == "SIM"
                sinal_tipo = getattr(r, "tipo", "POSITIVO" if item["momento"] >= 0 else "NEGATIVO")
                x_label = (
                    f"x = {fmt_num(item['x'], 2, unidade='m')}"
                    if abs(item["x_fim"] - item["x"]) < 1e-6
                    else f"x = {fmt_num(item['x'], 2)}–{fmt_num(item['x_fim'], 2, unidade='m')}"
                )
                card = result_card(
                    controls=[
                        ft.Row(
                            [
                                ft.Text(
                                    f"{item['descricao']}",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=Palette.PRIMARY,
                                    expand=True,
                                ),
                                polarity_badge(sinal_tipo),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text(
                            x_label,
                            size=10,
                            color=Palette.TEXT_SECONDARY,
                        ),
                        spacer(height=Spacing.XS),
                        ft.Row(
                            [
                                ft.Text("Md:", size=10, color=Palette.TEXT_SECONDARY),
                                numeric_text(
                                    fmt_num(
                                        r.momento_kNm * dados_viga.get("gamma_f", 1.4),
                                        1,
                                        unidade="kN·m",
                                    ),
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("As:", size=10, color=Palette.TEXT_SECONDARY),
                                numeric_text(
                                    fmt_num(r.as_req_cm2, 2, unidade="cm²"),
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("Adotado:", size=10, color=Palette.TEXT_SECONDARY),
                                numeric_text(
                                    f"{r.qtd_barras}φ{fmt_diam(r.diametro_mm)} ({fmt_num(r.as_necessaria_cm2, 2, unidade='cm²')})",
                                    size=10,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("Status:", size=10, color=Palette.TEXT_SECONDARY),
                                status_chip(
                                    "OK" if passa_flex else "NÃO PASSA",
                                    "ok" if passa_flex else "error",
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    width=220,
                    padding=Spacing.SM,
                    spacing=3,
                    shadow=False,
                )
                flex_cards.controls.append(card)

            rows_cis = []
            for item in sec_results:
                r = item["resultado_cisalhamento"]
                if r is None:
                    continue
                label = f"x={fmt_num(item['x'], 2)} m"
                status_label = "OK" if r.passa_vrd2 == "SIM" else "NAO"
                rows_cis.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(title_small(label, color=Palette.TEXT_PRIMARY)),
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
                                status_chip(
                                    status_label, "ok" if r.passa_vrd2 == "SIM" else "error"
                                )
                            ),
                        ]
                    )
                )

            controls_resultados = [
                section_header(
                    "Flexão (Dimensionamento por seção crítica)",
                    icon=ft.Icon(ft.Icons.SQUARE_OUTLINED, size=16, color=Palette.PRIMARY),
                ),
                spacer(height=Spacing.SM),
                flex_cards,
                spacer(height=Spacing.LG),
                section_header(
                    "Cisalhamento",
                    icon=ft.Icon(ft.Icons.SWAP_VERT, size=16, color=Palette.PRIMARY),
                ),
                spacer(height=Spacing.SM),
                results_table(
                    columns=[
                        ft.DataColumn(title_small("Seção")),
                        ft.DataColumn(title_small("Vsolic (kN)"), numeric=True),
                        ft.DataColumn(title_small("Vrd2 (kN)"), numeric=True),
                        ft.DataColumn(title_small("Vsw (kN)"), numeric=True),
                        ft.DataColumn(title_small("Espaçamento"), numeric=True),
                        ft.DataColumn(title_small("Status")),
                    ],
                    rows=rows_cis,
                    vertical_lines=True,
                )
                if rows_cis
                else caption("Nenhum trecho calculado.", color=Palette.TEXT_DISABLED),
            ]

            if detalhamento:
                controls_resultados.extend(
                    [
                        spacer(height=Spacing.LG),
                        section_header(
                            "Detalhamento de Estribos",
                            icon=ft.Icon(ft.Icons.SWAP_VERT, size=16, color=Palette.PRIMARY),
                        ),
                        spacer(height=Spacing.SM),
                        results_table(
                            columns=[
                                ft.DataColumn(title_small("Trecho")),
                                ft.DataColumn(title_small("φ"), numeric=True),
                                ft.DataColumn(title_small("Esp."), numeric=True),
                                ft.DataColumn(title_small("Asw/s"), numeric=True),
                            ],
                            rows=[
                                ft.DataRow(
                                    cells=[
                                        ft.DataCell(
                                            numeric_text(
                                                f"{fmt_num(r['x_inicio'], 1)}–{fmt_num(r['x_fim'], 1, unidade='m')}",
                                                size=12,
                                                text_align=ft.TextAlign.LEFT,
                                            )
                                        ),
                                        ft.DataCell(
                                            numeric_text(
                                                fmt_diam(r["phi_mm"], unidade="mm"), size=12
                                            )
                                        ),
                                        ft.DataCell(
                                            numeric_text(
                                                fmt_num(r["espacamento_cm"], 0, unidade="cm"),
                                                size=12,
                                            )
                                        ),
                                        ft.DataCell(
                                            numeric_text(fmt_num(r["asw_s_cm2m"], 2), size=12)
                                        ),
                                    ]
                                )
                                for r in detalhamento
                            ],
                            heading_row_height=Spacing.XL + 4,
                            data_row_min_height=Spacing.XL + 2,
                        ),
                    ]
                )

            erro_els = (resultado_els or {}).get("flecha", {}).get("erro")
            if erro_els:
                # Modelo fora do escopo do ELS (ex.: viga continua/engastada): mostrar o
                # motivo em vez de quebrar o modal inteiro com KeyError.
                controls_resultados.extend(
                    [
                        spacer(height=Spacing.LG),
                        section_header(
                            "ELS — Flecha e Fissuração",
                            icon=ft.Icon(ft.Icons.STRAIGHTEN, size=16, color=Palette.PRIMARY),
                        ),
                        ft.Text(erro_els, size=11, color=Palette.ERROR),
                    ]
                )
            elif resultado_els:
                controls_resultados.extend(
                    [
                        spacer(height=Spacing.LG),
                        section_header(
                            "ELS — Flecha e Fissuração",
                            icon=ft.Icon(ft.Icons.STRAIGHTEN, size=16, color=Palette.PRIMARY),
                        ),
                        spacer(height=Spacing.SM),
                        ft.Text(
                            "Flecha",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=Palette.TEXT_PRIMARY,
                        ),
                        ft.Row(
                            [
                                ft.Text("Total:", size=11, color=Palette.TEXT_SECONDARY),
                                numeric_text(
                                    fmt_num(
                                        resultado_els["flecha"]["flecha_total_cm"],
                                        2,
                                        unidade="cm",
                                    ),
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("Limite L/250:", size=11, color=Palette.TEXT_SECONDARY),
                                numeric_text(
                                    fmt_num(
                                        resultado_els["flecha"]["limite_total_cm"],
                                        2,
                                        unidade="cm",
                                    ),
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=Palette.SUCCESS
                                    if resultado_els["flecha"]["passa_total"]
                                    else Palette.ERROR,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ]
                )

                if not resultado_els["flecha"]["passa_total"] and resultado_els["flecha"].get(
                    "dica"
                ):
                    controls_resultados.extend(
                        [
                            spacer(height=Spacing.XS),
                            ft.Text(
                                resultado_els["flecha"].get("dica", ""),
                                size=9,
                                color=Palette.ERROR,
                                italic=True,
                            ),
                        ]
                    )

                controls_resultados.extend(
                    [
                        spacer(height=Spacing.SM),
                        ft.Text(
                            "Fissuração",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=Palette.TEXT_PRIMARY,
                        ),
                        ft.Row(
                            [
                                ft.Text("w_k:", size=11, color=Palette.TEXT_SECONDARY),
                                numeric_text(
                                    fmt_num(resultado_els["fissuracao"]["wk_mm"], 2, unidade="mm"),
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("w_lim:", size=11, color=Palette.TEXT_SECONDARY),
                                numeric_text(
                                    fmt_num(
                                        resultado_els["fissuracao"]["wk_limite_mm"],
                                        1,
                                        unidade="mm",
                                    ),
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color=Palette.SUCCESS
                                    if resultado_els["fissuracao"]["passa"]
                                    else Palette.ERROR,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                status_chip("OK", "ok")
                                if resultado_els["fissuracao"]["passa"]
                                else status_chip("NÃO PASSA", "error"),
                                spacer(width=Spacing.SM),
                                status_chip("OK", "ok")
                                if resultado_els["flecha"]["passa_total"]
                                else status_chip("NÃO PASSA", "error"),
                            ]
                        ),
                    ]
                )

                if not resultado_els["fissuracao"]["passa"] and resultado_els["fissuracao"].get(
                    "dica"
                ):
                    controls_resultados.extend(
                        [
                            spacer(height=Spacing.XS),
                            ft.Text(
                                resultado_els["fissuracao"].get("dica", ""),
                                size=9,
                                color=Palette.ERROR,
                                italic=True,
                            ),
                        ]
                    )

                if (
                    not resultado_els["flecha"]["passa_total"]
                    or not resultado_els["fissuracao"]["passa"]
                ):
                    controles_ajustes = _criar_painel_ajustes_els(
                        resultado_els,
                        state,
                        dados_viga,
                        secoes,
                        state.get("ftool_momentos"),
                        state.get("ftool_cortantes"),
                        state.get("ftool_deformacoes"),
                        page,
                        show_msg,
                    )
                    controls_resultados.extend(controles_ajustes)
            else:
                controls_resultados.append(
                    ft.Text(
                        "ELS não disponível (sem dados de deformação)",
                        size=11,
                        color=Palette.TEXT_DISABLED,
                    )
                )

            return controls_resultados

        def _mostrar_modal_resultados(
            state, dados_viga, secoes, momentos, cortantes, deformacoes, page, show_msg
        ):
            """Constrói e exibe o modal de resultados do dimensionamento."""
            controls_resultados = _build_resultados_controls(
                state, dados_viga, secoes, page, show_msg
            )

            results_content = ft.Column(
                controls=controls_resultados,
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
            )

            state["_modal_results_content"] = results_content

            page.show_dialog(
                themed_dialog(
                    title=ft.Row(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=Palette.PRIMARY),
                            spacer(width=Spacing.SM),
                            title_medium(
                                "Resultados do dimensionamento FTOOL", color=Palette.TEXT_PRIMARY
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    content=results_content,
                    width=800,
                    height=540,
                    actions=[outlined_button("Fechar", on_click=lambda ev: page.pop_dialog())],
                )
            )

        def _criar_painel_ajustes_els(
            resultado_els,
            state,
            dados_viga,
            secoes,
            momentos,
            cortantes,
            deformacoes,
            page,
            show_msg,
        ):
            """Cria painel de ajustes manuais para ELS quando não passa."""
            from ui.ftool.dimensionamento import dimensionar_trechos_ftool
            from ui.ftool.els import AjustesELS

            # Controles do painel
            chk_barras = ft.Checkbox(label="Adicionar barras extras", value=False)
            spn_barras = ft.TextField(value="2", width=80, text_size=13, disabled=True)

            chk_phi = ft.Checkbox(label="Forçar diâmetro mínimo", value=False)
            dd_phi = ft.Dropdown(
                options=[ft.dropdown.Option(str(d)) for d in [10, 12.5, 16, 20, 25]],
                value="16",
                width=100,
                disabled=True,
            )

            chk_h = ft.Checkbox(label="Aumentar h para", value=False)
            tf_h = ft.TextField(
                value="", width=100, disabled=True, hint_text=fmt_num(dados_viga["h_cm"], 0)
            )

            chk_fck = ft.Checkbox(label="Aumentar fck para", value=False)
            dd_fck = ft.Dropdown(
                options=[ft.dropdown.Option(str(f)) for f in [25, 30, 35, 40, 45, 50]],
                value="35",
                width=100,
                disabled=True,
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
                        dados_viga,
                        secoes,
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
                        novos_controles = _build_resultados_controls(
                            state, dados_viga, secoes, page, show_msg
                        )
                        results_content.controls = novos_controles
                        results_content.update()
                    else:
                        _mostrar_modal_resultados(
                            state,
                            dados_viga,
                            secoes,
                            state.get("ftool_momentos"),
                            state.get("ftool_cortantes"),
                            state.get("ftool_deformacoes"),
                            page,
                            show_msg,
                        )

                except (ValueError, KeyError, TypeError, ZeroDivisionError, RuntimeError) as ex:
                    logger.error("Erro ao recalcular ajustes manuais ELS: %s", ex, exc_info=True)
                    show_msg(f"Erro ao recalcular: {ex}", Palette.ERROR)

            # Retornar controles do painel
            return [
                spacer(height=Spacing.LG),
                surface_card(
                    ft.Column(
                        [
                            ft.Text(
                                "Ajustes Manuais para ELS",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=Palette.PRIMARY,
                            ),
                            spacer(height=Spacing.SM),
                            ft.Row(
                                [
                                    chk_barras,
                                    spn_barras,
                                    ft.Text("barras", size=11, color=Palette.TEXT_PRIMARY),
                                ]
                            ),
                            ft.Row([chk_phi, dd_phi]),
                            ft.Row(
                                [
                                    chk_h,
                                    tf_h,
                                    ft.Text("cm", size=11, color=Palette.TEXT_PRIMARY),
                                ]
                            ),
                            ft.Row(
                                [
                                    chk_fck,
                                    dd_fck,
                                    ft.Text("MPa", size=11, color=Palette.TEXT_PRIMARY),
                                ]
                            ),
                            spacer(height=Spacing.SM),
                            primary_button(
                                "Recalcular com Ajustes",
                                icon=ft.Icons.REFRESH,
                                on_click=on_recalcular,
                            ),
                        ]
                    ),
                    padding=Spacing.MD,
                    radius=Radius.SM,
                    bgcolor=ft.Colors.with_opacity(0.05, Palette.PRIMARY),
                ),
            ]

        def on_calcular_ftool(ev):
            ctx.page.pop_dialog()
            # Spinner de calculo
            calc_loading = ft.AlertDialog(
                modal=True,
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.ProgressRing(width=48, height=48, color=Palette.PRIMARY),
                            ft.Container(height=Spacing.MD),
                            ft.Text(
                                "Calculando dimensionamento...",
                                size=14,
                                color=Palette.TEXT_SECONDARY,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=pad_all(Spacing.XL),
                ),
                bgcolor=ft.Colors.TRANSPARENT,
            )
            ctx.page.show_dialog(calc_loading)
            ctx.page.update()
            try:
                h = float(ctx.h_tf.control.value or 0)
                bw = float(ctx.bw_tf.control.value or 0)
                fck = float(ctx.fck_dd.control.value or 0)
                fyk = float(ctx.fyk_dd.control.value or 0)
                fyke = float(ctx.fyke_dd.control.value or 0)
                caa = int(ctx.caa_dd.control.value)
                diam_est = float(ctx.phi_est_dd.control.value)
                diam_bar = float(ctx.phi_bar_dd.control.value)
                gamma_f = GAMMA_F_TABLE.get(ctx.gamma_f_dd.control.value, {}).get("gamma_f", 1.4)
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
                if ctx.is_t:
                    bf = float(ctx.bf_tf.control.value or 0)
                    hf = float(ctx.hf_tf.control.value or 0)
                    dados_viga["bf_cm"] = bf
                    dados_viga["hf_cm"] = hf
                    # EP-02.3: b1 ausente = 0,0 (bf,ef = bw; conservador)
                    b1e_str = ctx.b1esq_tf.control.value.strip().replace(",", ".")
                    b1d_str = ctx.b1dir_tf.control.value.strip().replace(",", ".")
                    dados_viga["b1esq_cm"] = float(b1e_str) if b1e_str else 0.0
                    dados_viga["b1dir_cm"] = float(b1d_str) if b1d_str else 0.0
                resultados = dimensionar_trechos_ftool(
                    dados_viga,
                    secoes,
                    momentos=ctx.state.get("ftool_momentos"),
                    cortantes=ctx.state.get("ftool_cortantes"),
                    deformacoes=ctx.state.get("ftool_deformacoes"),
                )
                sec_results = resultados["secoes"]
                ctx.state["resultados_flex"] = [r["resultado_flexao"] for r in sec_results]
                ctx.state["resultados_cis"] = [r["resultado_cisalhamento"] for r in sec_results]
                ctx.state["ftool_detalhamento"] = resultados.get("detalhamento")
                ctx.state["ftool_resultado_els"] = resultados.get("els")
                ctx.btn_gerar_pdf.disabled = False
                ctx.btn_exportar_dxf.disabled = False
                ctx.page.update()

                ctx.page.pop_dialog()  # Fecha loading

                # Mostrar modal de resultados
                _mostrar_modal_resultados(
                    ctx.state,
                    dados_viga,
                    secoes,
                    momentos,
                    cortantes,
                    deformacoes,
                    ctx.page,
                    ctx.show_msg,
                )
            except (ValueError, KeyError, TypeError, ZeroDivisionError, RuntimeError) as ex:
                logger.error("Erro no dimensionamento FTOOL: %s", ex, exc_info=True)
                ctx.page.pop_dialog()  # Fecha loading
                ctx.show_msg(f"Erro no dimensionamento: {ex}", Palette.ERROR)

        ctx.page.pop_dialog()  # Fecha loading
        ctx.page.show_dialog(
            themed_dialog(
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.AUTO_GRAPH, color=Palette.PRIMARY),
                        ft.Container(width=Spacing.SM),
                        title_medium("FTOOL - Seções Detectadas", color=Palette.TEXT_PRIMARY),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"{len(secoes)} seções críticas encontradas.",
                                size=14,
                                color=Palette.TEXT_SECONDARY,
                            ),
                            ft.Container(height=Spacing.SM),
                            table_container,
                        ],
                        tight=True,
                    ),
                    width=700,
                    padding=pad_sym(horizontal=Spacing.MD, vertical=Spacing.SM),
                ),
                actions=[
                    outlined_button("Cancelar", on_click=lambda ev: ctx.page.pop_dialog()),
                    primary_button(
                        "Calcular", icon=ft.Icons.PLAY_ARROW, on_click=on_calcular_ftool
                    ),
                ],
            )
        )
    except (ValueError, KeyError, TypeError, OSError, IndexError, RuntimeError) as ex:
        logger.error("Erro ao processar FTOOL: %s", ex, exc_info=True)
        try:
            ctx.page.pop_dialog()  # Fecha loading se ainda estiver aberto
        except (IndexError, RuntimeError, AttributeError):
            pass
        ctx.show_msg(f"Erro ao processar FTOOL: {ex}", Palette.ERROR)


def setup_processamento(ctx):
    """Passo de construcao: setup_processamento."""
    ctx.processar_ftool = partial(processar_ftool, ctx)
