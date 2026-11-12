"""Acoes do usuario: calcular, salvar/carregar .ptc, gerar PDF e exportar DXF.

EP-04.3: extraido de ui/viga.py; funcoes recebem `ctx` (ViewContext) explicito.
"""

import json
import logging
import os
import platform
import subprocess
from copy import deepcopy
from datetime import datetime
from functools import partial

import flet as ft

from core.calculos import (
    CAA_DATA,
    GAMMA_F_TABLE,
    calcular_cisalhamento_viga_comum,
    calcular_flexao_viga_comum,
    calcular_flexao_viga_t,
)
from core.calculos.secao import d_linha_cm
from core.format import fmt_num
from core.relatorio_base import gerar_relatorio_viga_comum, gerar_relatorio_viga_t
from ui.entrada import (
    EDICAO_ATUAL,
    aplicar_entrada_projeto,
    aviso_edicao,
    entrada_para_salvar,
    ftool_visivel,
)
from ui.ftool.dimensionamento import (
    gerar_relatorio_viga_comum_com_diagramas,
    gerar_relatorio_viga_t_com_diagramas,
)
from ui.recent_projects import add_recent
from ui.theme import (
    Palette,
    Spacing,
    is_dark,
    outlined_button,
    primary_button,
    section_header,
    surface_card,
)
from ui.viga.form_trechos import ler_sinais

logger = logging.getLogger(__name__)


# ── Status e mensagens ───────────────────────────────────────────────
def show_msg(ctx, msg, color=Palette.PRIMARY):
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
        ctx.page.update()

    sb.on_action = close_sb
    ctx.page.overlay.append(sb)
    ctx.page.update()


# ── Calcular ──────────────────────────────────────────────────────────
def on_calculate(ctx, e):
    if not ctx.run_manual_validations():
        ctx.show_msg(
            "Por favor, corrija os erros de validação nos campos em vermelho.", Palette.ERROR
        )
        return

    ctx.state["tipo_viga"] = ctx.viga_nome_tf.control.value or (
        "V1" if ctx.modo == "comum" else "VT1"
    )
    try:
        # Validar d (altura util) > 0 antes de calcular
        cob_mm_est = CAA_DATA.get(int(ctx.caa_dd.control.value or 2), {}).get("cobrimento", 30)
        d_lin_est = d_linha_cm(
            cob_mm_est,
            float(ctx.phi_est_dd.control.value or 5),
            float(ctx.phi_bar_dd.control.value or 16),
        )
        h = float(ctx.h_tf.control.value or 0)
        bw = float(ctx.bw_tf.control.value or 0)
        if h <= d_lin_est:
            ctx.h_tf.control.error_text = f"Deve ser > d' ({fmt_num(d_lin_est, 1, unidade='cm')})"
            ctx.page.update()
            ctx.show_msg(
                f"Altura h={fmt_num(h, 1, unidade='cm')} incorreta. d'={fmt_num(d_lin_est, 1, unidade='cm')}. h deve ser maior.",
                Palette.ERROR,
            )
            return
        if bw <= 5:
            ctx.bw_tf.control.error_text = "Mínimo 5,0 cm"
            ctx.page.update()
            ctx.show_msg(f"Largura bw={bw} cm muito pequena (min 5 cm).", Palette.ERROR)
            return
        fck = float(ctx.fck_dd.control.value or 0)
        fyk = float(ctx.fyk_dd.control.value or 0)
        fyke = float(ctx.fyke_dd.control.value or 0)
        caa = int(ctx.caa_dd.control.value)
        diam_est = float(ctx.phi_est_dd.control.value)
        diam_bar = float(ctx.phi_bar_dd.control.value)
        gamma_f = GAMMA_F_TABLE[ctx.gamma_f_dd.control.value]["gamma_f"]
    except (ValueError, KeyError, TypeError) as ex:
        ctx.show_msg(f"Verifique os campos de entrada: {ex}", Palette.WARNING)
        return

    momentos = ler_sinais(ctx.md_rows)
    cortantes = ler_sinais(ctx.vk_rows)

    # ── Flexao ──
    try:
        if ctx.is_t:
            bf = float(ctx.bf_tf.control.value or 0)
            hf = float(ctx.hf_tf.control.value or 0)
            # EP-02.3: b1 ausente = 0,0 (bf,ef = bw; conservador)
            b1e_str = ctx.b1esq_tf.control.value.strip().replace(",", ".")
            b1d_str = ctx.b1dir_tf.control.value.strip().replace(",", ".")
            b1e = float(b1e_str) if b1e_str else 0.0
            b1d = float(b1d_str) if b1d_str else 0.0
            res_flex = calcular_flexao_viga_t(
                h_cm=h,
                bw_cm=bw,
                bf_cm=bf,
                hf_cm=hf,
                caa=caa,
                fck_mpa=fck,
                diam_estribo_mm=diam_est,
                diam_barra_mm=diam_bar,
                # fyk entra em kN/cm² (dropdown "fyk aço (kN/cm²)")
                fyk_kn_cm2=fyk,
                momentos=momentos,
                b1esq_cm=b1e,
                b1dir_cm=b1d,
                gamma_f=gamma_f,
            )
        else:
            res_flex = calcular_flexao_viga_comum(
                h_cm=h,
                bw_cm=bw,
                caa=caa,
                fck_mpa=fck,
                diam_estribo_mm=diam_est,
                diam_barra_mm=diam_bar,
                # fyk entra em kN/cm² (dropdown "fyk aço (kN/cm²)")
                fyk_kn_cm2=fyk,
                momentos=momentos,
                gamma_f=gamma_f,
            )
    except (ValueError, TypeError, ZeroDivisionError, ArithmeticError) as ex:
        err_msg = str(ex)
        if ctx.is_t:
            if "bf" in err_msg:
                ctx.bf_tf.control.error_text = err_msg
                ctx.page.update()
            elif "hf" in err_msg:
                ctx.hf_tf.control.error_text = err_msg
                ctx.page.update()
        ctx.show_msg(f"Falha no cálculo de flexão: {ex}", Palette.ERROR)
        return

    # ── Cisalhamento (viga comum e viga T - usa largura da alma bw) ──
    res_cis = None
    try:
        res_cis = calcular_cisalhamento_viga_comum(
            h_cm=h,
            bw_cm=bw,
            fck_mpa=fck,
            diam_estribo_mm=diam_est,
            diam_barra_mm=diam_bar,
            fyk_estribo_kn_cm2=fyke,
            fyk_barra_kn_cm2=fyk,
            caa=caa,
            forcas_cortantes=cortantes,
            gamma_f=gamma_f,
        )
    except (ValueError, TypeError, ZeroDivisionError, ArithmeticError) as ex:
        ctx.show_msg(f"Falha no cálculo de cisalhamento: {ex}", Palette.ERROR)
        res_cis = None

    ctx.state["resultados_flex"] = deepcopy(res_flex)
    ctx.state["resultados_cis"] = deepcopy(res_cis) if res_cis else None
    # Habilita Gerar PDF apos calculo bem-sucedido
    ctx.btn_gerar_pdf.disabled = False
    ctx.btn_exportar_dxf.disabled = False
    ctx.page.update()
    ctx.show_msg("Cálculos concluídos com sucesso", Palette.PRIMARY)
    ctx.open_resultados_modal()


def setup_calculo(ctx):
    """Passo de construcao: setup_calculo."""
    ctx.show_msg = partial(show_msg, ctx)

    ctx.on_calculate = partial(on_calculate, ctx)


# ── Serialização de Ajustes ELS ──────────────────────────────────────
def serializar_ajustes_els(ajustes):
    """Serializa AjustesELS para dict JSON."""
    if ajustes is None:
        return None
    return {
        "barras_extras": ajustes.barras_extras,
        "phi_minimo_mm": ajustes.phi_minimo_mm,
        "h_override_cm": ajustes.h_override_cm,
        "fck_override_mpa": ajustes.fck_override_mpa,
    }


def desserializar_ajustes_els(data):
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
async def on_save_project_click(ctx, e):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    import re

    sanitized_viga = re.sub(r'[\\/*?:"<>|]', "_", ctx.viga_nome_tf.control.value)
    sanitized_viga = re.sub(r"\s+", " ", sanitized_viga).strip()
    if not sanitized_viga:
        sanitized_viga = "V1" if ctx.modo == "comum" else "VT1"
    default_filename = f"Projeto_{sanitized_viga}_{ts}.ptc"

    out_path = await ctx.fp_save_project.save_file(
        dialog_title="Salvar Projeto (.ptc)",
        file_name=default_filename,
        allowed_extensions=["ptc"],
        file_type=ft.FilePickerFileType.CUSTOM,
    )
    if not out_path:
        return

    # Coletar dados
    proj_data = {
        "edicao": EDICAO_ATUAL,
        "viga_nome": ctx.viga_nome_tf.control.value,
        "modo": ctx.modo,
        "entrada": entrada_para_salvar(ctx.state),
        "geometria": {
            "h_cm": ctx.h_tf.control.value,
            "bw_cm": ctx.bw_tf.control.value,
            "bf_cm": ctx.bf_tf.control.value if ctx.is_t else "",
            "hf_cm": ctx.hf_tf.control.value if ctx.is_t else "",
            "b1esq_cm": ctx.b1esq_tf.control.value if ctx.is_t else "",
            "b1dir_cm": ctx.b1dir_tf.control.value if ctx.is_t else "",
        },
        "materiais": {
            "caa": ctx.caa_dd.control.value,
            "fck_mpa": ctx.fck_dd.control.value,
            "fyk_mpa": ctx.fyk_dd.control.value,
            "fyk_estribo_mpa": ctx.fyke_dd.control.value,
            "gamma_f": ctx.gamma_f_dd.control.value,
            "diam_estribo_mm": ctx.phi_est_dd.control.value,
            "diam_barra_mm": ctx.phi_bar_dd.control.value,
        },
        "esforcos": {
            "momentos_kNm": [tf.value for tf in ctx.md_rows],
            "cortantes_kN": [tf.value for tf in ctx.vk_rows],
        },
        "ftool": {
            "ftool_path": ctx.state.get("ftool_path"),
            "ftool_filename": ctx.state.get("ftool_filename"),
            "ftool_momento_path": ctx.state.get("ftool_momento_path"),
            "ftool_cortante_path": ctx.state.get("ftool_cortante_path"),
            "ftool_deformacao_path": ctx.state.get("ftool_deformacao_path"),
            "ftool_momentos": ctx.state.get("ftool_momentos"),
            "ftool_cortantes": ctx.state.get("ftool_cortantes"),
            "ftool_deformacoes": ctx.state.get("ftool_deformacoes"),
            "ftool_secoes_criticas": [
                {
                    "x": s.x,
                    "momento": s.momento,
                    "cortante": s.cortante,
                    "tipo": s.tipo,
                    "descricao": s.descricao,
                }
                for s in (ctx.state.get("ftool_secoes_criticas") or [])
            ],
            "ajustes_els": serializar_ajustes_els(ctx.state.get("ftool_ajustes_els")),
        },
        "profissao": ctx.prof_dd.control.value,
        "nome_engenheiro": ctx.resp_nome_tf.control.value,
        "crea_uf": ctx.resp_registro_tf.control.value,
    }

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(proj_data, f, indent=2, ensure_ascii=False)
        add_recent(out_path, modo=ctx.modo)
        ctx.show_msg("Projeto salvo com sucesso", Palette.PRIMARY)
    except (OSError, TypeError, ValueError) as ex:
        logger.error("Erro ao salvar projeto em '%s': %s", out_path, ex, exc_info=True)
        ctx.show_msg(f"Erro ao salvar projeto: {ex}", Palette.ERROR)


async def on_load_project_click(ctx, e):
    pick_res = await ctx.fp_load_project.pick_files(
        dialog_title="Selecionar Projeto (.ptc)",
        allowed_extensions=["ptc"],
        file_type=ft.FilePickerFileType.CUSTOM,
        allow_multiple=False,
    )
    if not pick_res or not pick_res.files:
        return
    file_path = pick_res.files[0].path

    try:
        with open(file_path, encoding="utf-8") as f:
            proj_data = json.load(f)

        # Verificar modo (eixo retangular x T) — inalterado
        saved_modo = proj_data.get("modo", "comum")
        if saved_modo != ctx.modo:
            ctx.show_msg(
                f"Este projeto foi criado no modo de Viga {'T' if saved_modo == 't' else 'Retangular'}. Altere o modo na tela inicial para importar.",
                Palette.WARNING,
            )
            return

        # Edição de origem (legado): qualquer valor é aceito, com nota informativa
        edicao = proj_data.get("edicao", "")
        msg_aviso = aviso_edicao(edicao)

        # Fonte de entrada (manual | FTOOL) — retrocompatível
        aplicar_entrada_projeto(ctx.state, proj_data)

        # Restaurar dados
        ctx.viga_nome_tf.control.value = proj_data.get("viga_nome", "")
        ctx.h_tf.control.value = proj_data.get("geometria", {}).get("h_cm", "")
        ctx.bw_tf.control.value = proj_data.get("geometria", {}).get("bw_cm", "")
        if ctx.is_t:
            ctx.bf_tf.control.value = proj_data.get("geometria", {}).get("bf_cm", "")
            ctx.hf_tf.control.value = proj_data.get("geometria", {}).get("hf_cm", "")
            ctx.b1esq_tf.control.value = proj_data.get("geometria", {}).get("b1esq_cm", "")
            ctx.b1dir_tf.control.value = proj_data.get("geometria", {}).get("b1dir_cm", "")

        # Materiais
        ctx.caa_dd.control.value = str(proj_data.get("materiais", {}).get("caa", "2"))
        ctx.fck_dd.control.value = str(proj_data.get("materiais", {}).get("fck_mpa", "25"))
        ctx.fyk_dd.control.value = str(proj_data.get("materiais", {}).get("fyk_mpa", "50"))
        ctx.fyke_dd.control.value = str(proj_data.get("materiais", {}).get("fyk_estribo_mpa", "60"))
        ctx.gamma_f_dd.control.value = str(proj_data.get("materiais", {}).get("gamma_f", "normais"))
        ctx.phi_est_dd.control.value = str(
            proj_data.get("materiais", {}).get("diam_estribo_mm", "5")
        )
        ctx.phi_bar_dd.control.value = str(
            proj_data.get("materiais", {}).get("diam_barra_mm", "12.5")
        )

        # Nome/CREA
        ctx.prof_dd.control.value = str(proj_data.get("profissao", "Engenheiro Civil"))
        ctx.resp_nome_tf.control.value = proj_data.get("nome_engenheiro", "")
        ctx.resp_registro_tf.control.value = proj_data.get("crea_uf", "")

        # Esforços
        saved_momentos = proj_data.get("esforcos", {}).get("momentos_kNm", [])
        saved_cortantes = proj_data.get("esforcos", {}).get("cortantes_kN", [])

        # Limpar e reconstruir trechos de flexão
        ctx.md_rows.clear()
        for idx, val in enumerate(saved_momentos):
            ctx.md_rows.append(ctx._make_trecho_field("M", idx + 1, str(val)))
        if "M" in ctx.panel_rebuilds:
            ctx.panel_rebuilds["M"]()

        # Limpar e reconstruir trechos de cisalhamento
        ctx.vk_rows.clear()
        for idx, val in enumerate(saved_cortantes):
            ctx.vk_rows.append(ctx._make_trecho_field("V", idx + 1, str(val)))
        if "V" in ctx.panel_rebuilds:
            ctx.panel_rebuilds["V"]()

        # Ftool Image Preview
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
            ctx.state["ftool_cortantes"] = [tuple(pt) for pt in ctx.state["ftool_cortantes"]]
        if ctx.state.get("ftool_deformacoes"):
            ctx.state["ftool_deformacoes"] = [tuple(pt) for pt in ctx.state["ftool_deformacoes"]]

        raw_secoes = saved_ftool.get("ftool_secoes_criticas", [])
        if raw_secoes:
            from ui.ftool.secoes_criticas import SecaoCritica

            ctx.state["ftool_secoes_criticas"] = [SecaoCritica(**s) for s in raw_secoes]
        else:
            ctx.state["ftool_secoes_criticas"] = None

        # Carregar ajustes ELS
        ajustes_data = saved_ftool.get("ajustes_els")
        ctx.state["ftool_ajustes_els"] = desserializar_ajustes_els(ajustes_data)

        # Reconstroi o painel conforme a entrada do projeto ANTES de tocar
        # nos controles do painel FTOOL (eles so existem na pagina quando a
        # fonte de entrada e FTOOL; caso contrario, update() falharia).
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

        # Reset resultados e desabilita PDF
        ctx.state["resultados_flex"] = None
        ctx.state["resultados_cis"] = None
        ctx.btn_gerar_pdf.disabled = True
        ctx.btn_exportar_dxf.disabled = True

        add_recent(file_path, modo=saved_modo)
        ctx.page.update()
        if msg_aviso:
            ctx.show_msg(msg_aviso, Palette.WARNING)
        else:
            ctx.show_msg("Projeto importado com sucesso", Palette.PRIMARY)
    except (json.JSONDecodeError, OSError, KeyError, ValueError, TypeError) as ex:
        logger.error("Erro ao carregar projeto de '%s': %s", file_path, ex, exc_info=True)
        ctx.show_msg(f"Erro ao carregar projeto: {ex}", Palette.ERROR)


def setup_projeto(ctx):
    """Passo de construcao: setup_projeto."""
    ctx.on_save_project_click = partial(on_save_project_click, ctx)

    ctx.on_load_project_click = partial(on_load_project_click, ctx)


# ── Gerar PDF ───────────────────────────────────────────────────────
async def on_gerar_pdf(ctx, e):
    ctx.state["tipo_viga"] = ctx.viga_nome_tf.control.value or (
        "V1" if ctx.modo == "comum" else "VT1"
    )
    if ctx.state["resultados_flex"] is None and ctx.state["resultados_cis"] is None:
        ctx.show_msg("Calcule primeiro antes de gerar o PDF", Palette.WARNING)
        return

    # B3: Desabilitar o botão e mostrar spinner text
    ctx.btn_gerar_pdf.disabled = True
    ctx.btn_gerar_pdf.text = "Gerando PDF..."
    ctx.btn_gerar_pdf.icon = ft.Icons.HOURGLASS_EMPTY
    ctx.page.update()

    try:
        gamma_f = GAMMA_F_TABLE[ctx.gamma_f_dd.control.value]["gamma_f"]
    except (KeyError, TypeError):
        gamma_f = 1.4
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        # B9: Validação e sanitização de filename contra caracteres ilegais
        import re

        sanitized_viga = re.sub(r'[\\/*?:"<>|]', "_", ctx.state["tipo_viga"])
        sanitized_viga = re.sub(r"\s+", " ", sanitized_viga).strip()
        if not sanitized_viga:
            sanitized_viga = "V1" if ctx.modo == "comum" else "VT1"
        default_filename = f"PorticaApp_{sanitized_viga}_{ts}.pdf"

        # Abre o diálogo para salvar arquivo
        out = await ctx.fp_pdf.save_file(
            dialog_title="Salvar Relatório PDF",
            file_name=default_filename,
            allowed_extensions=["pdf"],
            file_type=ft.FilePickerFileType.CUSTOM,
        )

        # Se o usuário cancelou o diálogo, não faz nada
        if not out:
            return

        nome_eng = ctx.resp_nome_tf.control.value or ""
        crea_val = ctx.resp_registro_tf.control.value or ""
        profissao_val = ctx.prof_dd.control.value or "Engenheiro Civil"

        ftool = (
            ctx.state["ftool_path"]
            if ctx.state.get("ftool_path") and os.path.exists(ctx.state["ftool_path"])
            else None
        )
        if ctx.is_t:
            bf = float(ctx.bf_tf.control.value or 0)
            hf = float(ctx.hf_tf.control.value or 0)
            if ctx.state.get("ftool_momentos"):
                gerar_relatorio_viga_t_com_diagramas(
                    out,
                    nome_viga=ctx.state["tipo_viga"],
                    h_cm=float(ctx.h_tf.control.value or 0),
                    bw_cm=float(ctx.bw_tf.control.value or 0),
                    bf_cm=bf,
                    hf_cm=hf,
                    caa=int(ctx.caa_dd.control.value),
                    fck_mpa=float(ctx.fck_dd.control.value or 0),
                    fyk_kn_cm2=float(ctx.fyk_dd.control.value or 0),
                    fyk_estribo_kn_cm2=float(ctx.fyke_dd.control.value or 0),
                    phi_estribo_mm=float(ctx.phi_est_dd.control.value),
                    phi_barra_mm=float(ctx.phi_bar_dd.control.value),
                    resultados_flexao=ctx.state["resultados_flex"] or [],
                    resultados_cisalhamento=ctx.state["resultados_cis"] or [],
                    imagem_ftool=ftool,
                    gamma_f=gamma_f,
                    dark_mode=is_dark(ctx.page),
                    nome_engenheiro=nome_eng,
                    crea=crea_val,
                    profissao=profissao_val,
                    momentos=ctx.state["ftool_momentos"],
                    cortantes=ctx.state["ftool_cortantes"],
                    secoes_criticas=ctx.state["ftool_secoes_criticas"],
                    detalhamento=ctx.state.get("ftool_detalhamento"),
                    resultado_els=ctx.state.get("ftool_resultado_els"),
                )
            else:
                gerar_relatorio_viga_t(
                    out,
                    nome_viga=ctx.state["tipo_viga"],
                    h_cm=float(ctx.h_tf.control.value or 0),
                    bw_cm=float(ctx.bw_tf.control.value or 0),
                    bf_cm=bf,
                    hf_cm=hf,
                    caa=int(ctx.caa_dd.control.value),
                    fck_mpa=float(ctx.fck_dd.control.value or 0),
                    fyk_kn_cm2=float(ctx.fyk_dd.control.value or 0),
                    fyk_estribo_kn_cm2=float(ctx.fyke_dd.control.value or 0),
                    phi_estribo_mm=float(ctx.phi_est_dd.control.value),
                    phi_barra_mm=float(ctx.phi_bar_dd.control.value),
                    resultados_flexao=ctx.state["resultados_flex"] or [],
                    resultados_cisalhamento=ctx.state["resultados_cis"] or [],
                    imagem_ftool=ftool,
                    gamma_f=gamma_f,
                    dark_mode=is_dark(ctx.page),
                    nome_engenheiro=nome_eng,
                    crea=crea_val,
                    profissao=profissao_val,
                )
        else:
            if ctx.state.get("ftool_momentos"):
                gerar_relatorio_viga_comum_com_diagramas(
                    out,
                    nome_viga=ctx.state["tipo_viga"],
                    h_cm=float(ctx.h_tf.control.value or 0),
                    bw_cm=float(ctx.bw_tf.control.value or 0),
                    caa=int(ctx.caa_dd.control.value),
                    fck_mpa=float(ctx.fck_dd.control.value or 0),
                    fyk_kn_cm2=float(ctx.fyk_dd.control.value or 0),
                    fyk_estribo_kn_cm2=float(ctx.fyke_dd.control.value or 0),
                    phi_estribo_mm=float(ctx.phi_est_dd.control.value),
                    phi_barra_mm=float(ctx.phi_bar_dd.control.value),
                    resultados_flexao=ctx.state["resultados_flex"] or [],
                    resultados_cisalhamento=ctx.state["resultados_cis"] or [],
                    imagem_ftool=ftool,
                    gamma_f=gamma_f,
                    dark_mode=is_dark(ctx.page),
                    nome_engenheiro=nome_eng,
                    crea=crea_val,
                    profissao=profissao_val,
                    momentos=ctx.state["ftool_momentos"],
                    cortantes=ctx.state["ftool_cortantes"],
                    secoes_criticas=ctx.state["ftool_secoes_criticas"],
                    detalhamento=ctx.state.get("ftool_detalhamento"),
                    resultado_els=ctx.state.get("ftool_resultado_els"),
                )
            else:
                gerar_relatorio_viga_comum(
                    out,
                    nome_viga=ctx.state["tipo_viga"],
                    h_cm=float(ctx.h_tf.control.value or 0),
                    bw_cm=float(ctx.bw_tf.control.value or 0),
                    caa=int(ctx.caa_dd.control.value),
                    fck_mpa=float(ctx.fck_dd.control.value or 0),
                    fyk_kn_cm2=float(ctx.fyk_dd.control.value or 0),
                    fyk_estribo_kn_cm2=float(ctx.fyke_dd.control.value or 0),
                    phi_estribo_mm=float(ctx.phi_est_dd.control.value),
                    phi_barra_mm=float(ctx.phi_bar_dd.control.value),
                    resultados_flexao=ctx.state["resultados_flex"] or [],
                    resultados_cisalhamento=ctx.state["resultados_cis"] or [],
                    imagem_ftool=ftool,
                    gamma_f=gamma_f,
                    dark_mode=is_dark(ctx.page),
                    nome_engenheiro=nome_eng,
                    crea=crea_val,
                    profissao=profissao_val,
                )
        ctx.state["pdf_path"] = out
        # Habilita Abrir ultimo PDF apos gerar com sucesso
        ctx.btn_abrir_pdf.disabled = False
        ctx.page.update()
        # B11: feedback de sucesso claro e persistente
        ctx.show_msg(f"PDF gerado com sucesso: {out}", Palette.PRIMARY)

        # Abre o PDF gerado automaticamente
        ctx.on_abrir_pdf(None)
    except (OSError, ValueError, TypeError) as ex:
        import traceback

        traceback.print_exc()
        ctx.show_msg(f"Erro ao gerar PDF: {ex}", Palette.ERROR)
    finally:
        ctx.btn_gerar_pdf.disabled = False
        ctx.btn_gerar_pdf.text = "Gerar PDF"
        ctx.btn_gerar_pdf.icon = ft.Icons.PICTURE_AS_PDF
        ctx.page.update()


def on_abrir_pdf(ctx, e):
    path = ctx.state.get("pdf_path")
    if not path or not os.path.exists(path):
        ctx.show_msg("Gere o PDF primeiro", Palette.WARNING)
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
        ctx.show_msg(f"Erro ao abrir PDF (instale um visualizador): {ex}", Palette.ERROR)


# ── Exportar DXF ─────────────────────────────────────────────────────
async def on_exportar_dxf(ctx, e):
    ctx.state["tipo_viga"] = ctx.viga_nome_tf.control.value or (
        "V1" if ctx.modo == "comum" else "VT1"
    )
    if not ctx.state["resultados_flex"]:
        ctx.show_msg("Calcule primeiro antes de exportar o DXF", Palette.WARNING)
        return

    # Encontrar a primeira seção com detalhamento convergido
    resultado_valido = None
    for r in ctx.state["resultados_flex"]:
        if r and getattr(r, "layout_convergido", None):
            resultado_valido = r
            break

    is_t = ctx.modo == "t"
    if not resultado_valido:
        if is_t:
            from core.calculos.engenharia import ResultadoFlexaoT

            resultado_valido = next(
                (r for r in ctx.state["resultados_flex"] or [] if r is not None), None
            )
            if resultado_valido is None:
                resultado_valido = ResultadoFlexaoT(
                    momento_kNm=0,
                    tipo="POSITIVO",
                    kc=0,
                    a=0,
                    b=0,
                    x1=0,
                    x2=0,
                    bx=0,
                    bx_passa="SIM",
                    x_cm=0,
                    linha_neutra_condiz="SIM",
                    bf_efetivo_cm=float(ctx.bf_tf.control.value.replace(",", "."))
                    if is_t and ctx.bf_tf.control.value
                    else 0,
                    ks=0,
                    as_req_cm2=0,
                    asmin_cm2=0,
                    as_necessaria_cm2=0,
                    diametro_mm=float(ctx.phi_bar_dd.control.value)
                    if ctx.phi_bar_dd.control.value
                    else 10.0,
                    qtd_barras=3,
                    eh_min_real=0.0,
                    eh_passa="SIM",
                )
        else:
            ctx.show_msg(
                "Nenhum detalhamento geométrico disponível para exportação. Verifique se a viga passa no dimensionamento.",
                Palette.WARNING,
            )
            return

    ctx.btn_exportar_dxf.disabled = True
    ctx.btn_exportar_dxf.text = "Exportando DXF..."
    ctx.btn_exportar_dxf.icon = ft.Icons.HOURGLASS_EMPTY
    ctx.page.update()

    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        import re

        sanitized_viga = re.sub(r'[\\/*?:"<>|]', "_", ctx.state["tipo_viga"])
        sanitized_viga = re.sub(r"\s+", " ", sanitized_viga).strip()
        if not sanitized_viga:
            sanitized_viga = "V1" if ctx.modo == "comum" else "VT1"
        default_filename = f"PorticaApp_{sanitized_viga}_{ts}.dxf"

        out = await ctx.fp_dxf.save_file(
            dialog_title="Salvar Detalhamento DXF",
            file_name=default_filename,
            allowed_extensions=["dxf"],
            file_type=ft.FilePickerFileType.CUSTOM,
        )

        if not out:
            return

        # Chamar a função de exportação DXF
        from core.detailing import BeamDetailer, BeamDetailingInput
        from core.detailing.dxf_export import exportar_secao_dxf

        layout = resultado_valido.layout_convergido

        # Coletar dados da seção
        if layout:
            bw_cm = layout.bw / 10.0
            h_cm = layout.h / 10.0
            cob_cm = layout.c_nom / 10.0
            phi_estribo_mm = layout.phi_estribo
            d_max_agregado_mm = layout.d_max_agregado
        else:
            bw_cm = (
                float(ctx.bw_tf.control.value.replace(",", "."))
                if ctx.bw_tf.control.value
                else 15.0
            )
            h_cm = (
                float(ctx.h_tf.control.value.replace(",", ".")) if ctx.h_tf.control.value else 40.0
            )
            caa = int(ctx.caa_dd.control.value) if ctx.caa_dd.control.value else 2
            cob_mm = CAA_DATA.get(caa, {}).get("cobrimento", 30)
            cob_cm = cob_mm / 10.0
            phi_estribo_mm = (
                float(ctx.phi_est_dd.control.value) if ctx.phi_est_dd.control.value else 5.0
            )
            d_max_agregado_mm = 19.0

        if is_t:
            bw_cm = (
                float(ctx.bw_tf.control.value.replace(",", "."))
                if ctx.bw_tf.control.value
                else bw_cm
            )

        # Encontrar armadura máxima para o desenho da seção transversal representativa
        max_bars_inf = 0
        max_bars_sup = 0
        phi_inf_adot = (
            layout.phi_barra
            if layout
            else (float(ctx.phi_bar_dd.control.value) if ctx.phi_bar_dd.control.value else 10.0)
        )
        phi_sup_adot = (
            layout.phi_barra
            if layout
            else (float(ctx.phi_bar_dd.control.value) if ctx.phi_bar_dd.control.value else 10.0)
        )

        for r in ctx.state["resultados_flex"] or []:
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

        # Seção T: o detalhador precisa da mesa para posicionar as barras.
        is_t = ctx.modo == "t"
        bf_cm = None
        hf_cm = None
        if is_t:
            bf_cm = (
                float(ctx.bf_tf.control.value.replace(",", "."))
                if ctx.bf_tf.control.value
                else None
            )
            hf_cm = (
                float(ctx.hf_tf.control.value.replace(",", "."))
                if ctx.hf_tf.control.value
                else None
            )

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
                is_t=is_t,
                bf_cm=bf_cm or 0.0,
                hf_cm=hf_cm or 0.0,
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
                is_t=is_t,
                bf_cm=bf_cm or 0.0,
                hf_cm=hf_cm or 0.0,
            )
            layout_sup = detailer.detail(inp_sup)

            # Adiciona barras inferiores
            for bar in layout_inf.bar_positions:
                if not bar.is_corner_bar:
                    combined_bar_positions.append(
                        {
                            "x": bar.x,
                            "y": bar.y,
                            "layer": bar.layer,
                            "is_corner_bar": False,
                            "phi_mm": phi_inf_adot,
                        }
                    )

            # Adiciona barras superiores (espelhadas em Y)
            h_mm = h_cm * 10.0
            for bar in layout_sup.bar_positions:
                if not bar.is_corner_bar:
                    y_mirrored = h_mm - bar.y
                    combined_bar_positions.append(
                        {
                            "x": bar.x,
                            "y": y_mirrored,
                            "layer": -(bar.layer + 1),
                            "is_corner_bar": False,
                            "phi_mm": phi_sup_adot,
                        }
                    )
        else:
            # Posições calculadas manualmente
            e_off_mm = cob_cm * 10.0 + phi_estribo_mm

            # Inferiores
            y_inf = e_off_mm + phi_inf_adot / 2.0
            avail_w_inf = bw_cm * 10.0 - 2.0 * e_off_mm - phi_inf_adot
            if n_inf_dxf == 1 or avail_w_inf <= 0:
                xs_inf = [bw_cm * 10.0 / 2.0]
            else:
                xs_inf = [
                    e_off_mm + phi_inf_adot / 2.0 + i * avail_w_inf / (n_inf_dxf - 1)
                    for i in range(n_inf_dxf)
                ]
            for x in xs_inf:
                combined_bar_positions.append(
                    {
                        "x": x,
                        "y": y_inf,
                        "layer": 0,
                        "is_corner_bar": False,
                        "phi_mm": phi_inf_adot,
                    }
                )

            # Superiores
            h_mm = h_cm * 10.0
            y_sup = h_mm - e_off_mm - phi_sup_adot / 2.0
            avail_w_sup = bw_cm * 10.0 - 2.0 * e_off_mm - phi_sup_adot
            if n_sup_dxf == 1 or avail_w_sup <= 0:
                xs_sup = [bw_cm * 10.0 / 2.0]
            else:
                xs_sup = [
                    e_off_mm + phi_sup_adot / 2.0 + i * avail_w_sup / (n_sup_dxf - 1)
                    for i in range(n_sup_dxf)
                ]
            for x in xs_sup:
                combined_bar_positions.append(
                    {
                        "x": x,
                        "y": y_sup,
                        "layer": -1,
                        "is_corner_bar": False,
                        "phi_mm": phi_sup_adot,
                    }
                )

        # Dados de armadura de pele
        n_barras_pele = getattr(resultado_valido, "n_barras_pele_face", 0)
        phi_pele_mm = getattr(resultado_valido, "phi_pele_mm", 0.0)

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
            d_max_agregado_mm=ctx.state.get("d_max_agregado_mm", 19.0),
            nome_arquivo=out,
        )

        ctx.show_msg(f"Arquivo DXF exportado com sucesso: {out}", Palette.PRIMARY)

    except (OSError, ValueError, TypeError, RuntimeError, AttributeError) as ex:
        logger.error("Erro ao exportar DXF: %s", ex, exc_info=True)
        ctx.show_msg(f"Erro ao exportar DXF: {ex}", Palette.ERROR)
    finally:
        ctx.btn_exportar_dxf.disabled = False
        ctx.btn_exportar_dxf.text = "Exportar DXF"
        ctx.btn_exportar_dxf.icon = ft.Icons.DOWNLOAD
        ctx.page.update()


def setup_exportacao(ctx):
    """Passo de construcao: setup_exportacao."""
    ctx.on_gerar_pdf = partial(on_gerar_pdf, ctx)

    ctx.on_abrir_pdf = partial(on_abrir_pdf, ctx)

    ctx.on_exportar_dxf = partial(on_exportar_dxf, ctx)


def setup_card_acoes(ctx):
    """Passo de construcao: setup_card_acoes."""

    # Botao Gerar PDF - inicia desabilitado, so habilita apos calcular
    ctx.btn_gerar_pdf = primary_button(
        "Gerar PDF",
        icon=ft.Icons.PICTURE_AS_PDF,
        on_click=ctx.on_gerar_pdf,
        expand=True,
        disabled=True,
    )

    # Botao Exportar DXF - inicia desabilitado, so habilita apos calcular
    ctx.btn_exportar_dxf = outlined_button(
        "Exportar DXF",
        icon=ft.Icons.DOWNLOAD,
        on_click=ctx.on_exportar_dxf,
        expand=True,
        disabled=True,
    )

    # Botao Abrir PDF - inicia desabilitado, so habilita apos gerar PDF
    ctx.btn_abrir_pdf = outlined_button(
        "Abrir último PDF",
        icon=ft.Icons.OPEN_IN_NEW,
        on_click=ctx.on_abrir_pdf,
        expand=True,
        disabled=True,
    )

    ctx.actions_card = surface_card(
        ft.Column(
            controls=[
                section_header(
                    "Ações",
                    icon=ft.Icon(ft.Icons.PLAY_ARROW, size=16, color=Palette.TEXT_SECONDARY),
                ),
                ft.Container(height=Spacing.XS),
                ctx.btn_gerar_pdf,
                ft.Container(height=Spacing.XS),
                ctx.btn_exportar_dxf,
                ft.Container(height=Spacing.XS),
                ctx.btn_abrir_pdf,
                ft.Container(height=Spacing.SM),
                ft.Divider(color=Palette.OUTLINE_VARIANT, height=1),
                ft.Container(height=Spacing.SM),
                outlined_button(
                    "Salvar Projeto",
                    icon=ft.Icons.SAVE_ALT,
                    on_click=ctx.on_save_project_click,
                    expand=True,
                ),
                ft.Container(height=Spacing.XS),
                outlined_button(
                    "Carregar Projeto",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=ctx.on_load_project_click,
                    expand=True,
                ),
            ],
            spacing=0,
        ),
        padding=Spacing.LG,
    )

    ctx.right_sidebar = ft.Column(
        controls=[
            ctx.actions_card,
        ],
        spacing=Spacing.MD,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
