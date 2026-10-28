"""
Módulo para dimensionamento automático de múltiplos trechos/seções críticas.
Fase 2.3 — Dimensionamento Automático
"""

from typing import List, Dict, Any, Tuple, Optional
from ui.ftool.secoes_criticas import SecaoCritica, detectar_pontos_momento_nulo, calcular_lo_para_secao
from ui.ftool.els import AjustesELS
from core.calculos.engenharia import (
    calcular_flexao_viga_comum,
    calcular_flexao_viga_t,
    calcular_cisalhamento_viga_comum,
)


def dimensionar_trechos_ftool(
    dados_viga: Dict[str, Any],
    secoes_criticas: List[SecaoCritica],
    momentos: Optional[List[Tuple[float, float]]] = None,
    cortantes: Optional[List[Tuple[float, float]]] = None,
    deformacoes: Optional[List[Tuple[float, float, float, float]]] = None,
    ajustes_els: Optional[AjustesELS] = None,
) -> Dict[str, Any]:
    """
    Itera sobre as seções críticas e realiza o dimensionamento à flexão e ao cisalhamento.
    Retorna uma lista de dicionários contendo os resultados detalhados de cada seção.
    """
    # Preparação de parâmetros comuns
    h_cm = dados_viga["h_cm"]
    bw_cm = dados_viga["bw_cm"]
    caa = dados_viga["caa"]
    fck_mpa = dados_viga["fck_mpa"]
    diam_estribo_mm = dados_viga["diam_estribo_mm"]
    diam_barra_mm = dados_viga["diam_barra_mm"]
    fyk_mpa = dados_viga["fyk_mpa"]
    
    # Cisalhamento precisa do fyk do estribo e da barra
    fyk_estribo_mpa = dados_viga.get("fyk_estribo_mpa", 60.0)  # default CA-60 (60 kN/cm² / 600 MPa)
    fyk_barra_mpa = dados_viga.get("fyk_barra_mpa", fyk_mpa)
    gamma_f = dados_viga.get("gamma_f", 1.4)

    resultados = []
    
    is_t_beam = bool(dados_viga.get("bf_cm") and dados_viga.get("hf_cm") and dados_viga["bf_cm"] > bw_cm)

    # Detectar pontos de momento nulo para cálculo automático de l0 (NBR 6118:15.5.2)
    pontos_momento_nulo = []
    x_min_viga = 0.0
    x_max_viga = 0.0
    if momentos:
        pontos_momento_nulo = detectar_pontos_momento_nulo(momentos)
        sorted_momentos = sorted(momentos, key=lambda p: p[0])
        x_min_viga = sorted_momentos[0][0]
        x_max_viga = sorted_momentos[-1][0]

    for secao in secoes_criticas:
        # Calcular l0 automático para esta seção (NBR 6118:15.5.2)
        lo_esq_cm, lo_dir_cm = calcular_lo_para_secao(
            secao.x, pontos_momento_nulo, x_min_viga, x_max_viga
        )
        
        # 1. Dimensionamento à Flexão
        # O motor recebe uma lista de momentos. Enviamos [secao.momento]
        # Se for seção T, usa o motor específico com largura de mesa bf
        if is_t_beam:
            res_flexao_list = calcular_flexao_viga_t(
                h_cm=h_cm, bw_cm=bw_cm,
                bf_cm=dados_viga["bf_cm"], hf_cm=dados_viga["hf_cm"],
                caa=caa, fck_mpa=fck_mpa,
                diam_estribo_mm=diam_estribo_mm, diam_barra_mm=diam_barra_mm,
                fyk_mpa=fyk_mpa, momentos=[secao.momento],
                b1esq_cm=dados_viga.get("b1esq_cm"),
                b1dir_cm=dados_viga.get("b1dir_cm"),
                lo_esq_cm=lo_esq_cm,
                lo_dir_cm=lo_dir_cm,
                gamma_f=gamma_f,
            )
        else:
            res_flexao_list = calcular_flexao_viga_comum(
                h_cm=h_cm,
                bw_cm=bw_cm,
                caa=caa,
                fck_mpa=fck_mpa,
                diam_estribo_mm=diam_estribo_mm,
                diam_barra_mm=diam_barra_mm,
                fyk_mpa=fyk_mpa,
                momentos=[secao.momento],
                gamma_f=gamma_f,
            )
        res_flexao = res_flexao_list[0] if res_flexao_list else None
        
        # 2. Dimensionamento ao Cisalhamento
        res_cis_list = calcular_cisalhamento_viga_comum(
            h_cm=h_cm,
            bw_cm=bw_cm,
            fck_mpa=fck_mpa,
            diam_estribo_mm=diam_estribo_mm,
            diam_barra_mm=diam_barra_mm,
            fyk_estribo_mpa=fyk_estribo_mpa,
            fyk_barra_mpa=fyk_barra_mpa,
            caa=caa,
            forcas_cortantes=[secao.cortante],
            gamma_f=gamma_f,
        )
        res_cis = res_cis_list[0] if res_cis_list else None
        
        resultados.append({
            "x": secao.x,
            "Mk": secao.momento,
            "Vk": secao.cortante,
            "resultado_flexao": res_flexao,
            "resultado_cisalhamento": res_cis,
            "tipo": secao.tipo,
            "descricao": secao.descricao,
        })
        
    # Detalhamento de estribos por região
    detalhamento = None
    if cortantes:
        try:
            from ui.ftool.detailing import detalhar_estribos, calcular_qtd_estribos
            detalhamento = detalhar_estribos(
                h_cm=h_cm, bw_cm=bw_cm, fck_mpa=fck_mpa,
                fyk_mpa=fyk_mpa, fyk_estribo_mpa=fyk_estribo_mpa, caa=caa,
                cortantes=cortantes, phi_estribo_mm=diam_estribo_mm, gamma_f=gamma_f,
            )
            detalhamento = calcular_qtd_estribos(detalhamento)
        except Exception:
            detalhamento = None

    # ELS (flecha + fissuração)
    resultado_els = None
    if momentos and deformacoes:
        try:
            from ui.ftool.els import calcular_flecha, calcular_fissuracao
            as_tracao = max((r["resultado_flexao"].as_usado_cm2 for r in resultados if r["resultado_flexao"]), default=0)
            is_t = bool(dados_viga.get("bf_cm") and dados_viga.get("hf_cm") and dados_viga["bf_cm"] > bw_cm)
            cobrimento_mm = dados_viga.get("cobrimento_mm", 25.0)
            flecha = calcular_flecha(
                h_cm=h_cm, bw_cm=bw_cm, d_cm=h_cm - 3 - diam_estribo_mm/10 - diam_barra_mm/20,
                fck_mpa=fck_mpa, as_tracao_cm2=as_tracao,
                momentos=momentos, deformacoes=deformacoes, gamma_f=gamma_f,
                is_t=is_t,
                bf_cm=dados_viga.get("bf_cm"),
                hf_cm=dados_viga.get("hf_cm"),
                ajustes=ajustes_els,
                phi_barra_mm=diam_barra_mm,
                diam_estribo_mm=diam_estribo_mm,
                cobrimento_mm=cobrimento_mm,
            )
            fissuracao = calcular_fissuracao(
                h_cm=h_cm, bw_cm=bw_cm, d_cm=h_cm - 3 - diam_estribo_mm/10 - diam_barra_mm/20,
                caa=caa, fck_mpa=fck_mpa, fyk_mpa=fyk_mpa,
                as_tracao_cm2=as_tracao, phi_barra_mm=diam_barra_mm,
                momentos=momentos, gamma_f=gamma_f,
                is_t=is_t,
                bf_cm=dados_viga.get("bf_cm"),
                hf_cm=dados_viga.get("hf_cm"),
                ajustes=ajustes_els,
                diam_estribo_mm=diam_estribo_mm,
                cobrimento_mm=cobrimento_mm,
            )
            resultado_els = {"flecha": flecha, "fissuracao": fissuracao, "ajustes_aplicados": ajustes_els}
            
            # Se há ajustes manuais com barras extras, atualizar resultados de flexão
            if ajustes_els and ajustes_els.barras_extras > 0:
                import math
                for res in resultados:
                    rf = res["resultado_flexao"]
                    if rf is not None:
                        # Calcular área de uma barra
                        area_barra = math.pi * (rf.diametro_mm / 20.0) ** 2  # mm -> cm²
                        # Atualizar quantidade de barras e área usada
                        rf.qtd_barras += ajustes_els.barras_extras
                        rf.as_usado_cm2 = rf.qtd_barras * area_barra
                        
                        # Recalcular layout_convergido, camadas_adotadas, etc.
                        try:
                            from core.detailing.domain import BeamDetailer, BeamDetailingInput
                            detailer = BeamDetailer()
                            cob_mm = rf.cob_mm if rf.cob_mm > 0 else 25.0
                            is_t = bool(dados_viga.get("bf_cm") and dados_viga.get("hf_cm") and dados_viga["bf_cm"] > bw_cm)
                            
                            inp = BeamDetailingInput(
                                bw=bw_cm * 10.0,
                                h=h_cm * 10.0,
                                c_nom=cob_mm,
                                phi_estribo=diam_estribo_mm,
                                phi_barra=rf.diametro_mm,
                                d_max_agregado=19.0,
                                total_bars=rf.qtd_barras,
                                is_t=is_t,
                                bf_cm=dados_viga.get("bf_cm") if is_t else 0.0,
                                hf_cm=dados_viga.get("hf_cm") if is_t else 0.0,
                                is_superior=(rf.tipo == "NEGATIVO"),
                            )
                            layout = detailer.detail(inp)
                            if layout:
                                rf.layout_convergido = layout
                                rf.camadas_adotadas = layout.layer_count
                                if layout.layers:
                                    rf.barras_suportadas = layout.layers[0].bar_count
                                    rf.barras_cima = rf.qtd_barras - rf.barras_suportadas
                        except Exception as e:
                            # Falha silenciosa no recálculo do layout para evitar quebrar ELS
                            print(f"Erro ao recalcular layout ELS: {e}")
                            
                        # Recalcular armadura de pele se necessário
                        if hasattr(rf, 'requer_pele') and rf.requer_pele:
                            from core.calculos.engenharia import calcular_armadura_pele
                            cob_mm = rf.cob_mm if rf.cob_mm > 0 else 25.0
                            pele = calcular_armadura_pele(
                                h_cm, bw_cm, cob_mm, diam_estribo_mm, rf.diametro_mm
                            )
                            rf.n_barras_pele_face = pele["n_barras_face"]
                            rf.phi_pele_mm = pele["phi_pele_mm"]
                            rf.as_pele_face_cm2 = pele["as_pele_adotada_face_cm2"]
                            rf.s_pele_cm = pele["s_adotado_cm"]
                            rf.tabela_pele = pele["tabela_phis"]
        except Exception:
            resultado_els = None

    return {
        "secoes": resultados,
        "detalhamento": detalhamento,
        "els": resultado_els,
    }


def gerar_relatorio_premium(dados_viga: Dict[str, Any], resultados: List[Dict[str, Any]]) -> str:
    """
    Gera um resumo em formato de texto estruturado detalhando os resultados
    das seções calculadas para apresentação na UI ou exportação rápida.
    """
    gamma_f = dados_viga.get("gamma_f", 1.4)
    lines = []
    lines.append("=== PÓRTICA APP: RESUMO DE DIMENSIONAMENTO AUTOMÁTICO (FTOOL) ===")
    lines.append(f"Geometria: bw={dados_viga['bw_cm']} cm | h={dados_viga['h_cm']} cm")
    lines.append(f"Materiais: fck={dados_viga['fck_mpa']} MPa | CAA={dados_viga['caa']}")
    lines.append(f"Aços: fyk={dados_viga['fyk_mpa']} kN/cm² | fyk_est={dados_viga.get('fyk_estribo_mpa', 60.0)} kN/cm²")
    lines.append(f"Majorador de esforços: gamma_f = {gamma_f}")
    lines.append("-" * 75)
    
    for res in resultados:
        x = res["x"]
        mk = res["Mk"]
        vk = res["Vk"]
        tipo = res["tipo"]
        desc = res["descricao"]
        
        lines.append(f"Seção em x = {x:.2f} m | Tipo: {tipo} ({desc})")
        lines.append(f"  Esforços Característicos: Mk = {mk:+.2f} kN·m | Vk = {vk:+.2f} kN")
        
        rf = res["resultado_flexao"]
        if rf:
            md = rf.momento_kNm * gamma_f
            lines.append(f"  FLEXÃO (As):")
            lines.append(f"    Md = {md:+.2f} kN·m | Limite Domínio (Passa): {rf.bx_passa}")
            lines.append(f"    As necessário = {rf.as_req_cm2:.2f} cm² | As mínimo = {rf.asmin_cm2:.2f} cm²")
            lines.append(f"    Armadura Adotada: {rf.qtd_barras} Φ {rf.diametro_mm:.1f} mm (As_adotado = {rf.as_usado_cm2:.2f} cm²)")
            if rf.alerta:
                lines.append(f"    ⚠️ ALERTA: {rf.alerta}")
        else:
            lines.append("  FLEXÃO (As): Momento nulo. Nenhuma armadura de tração necessária.")
            
        rc = res["resultado_cisalhamento"]
        if rc:
            vsd = rc.vsd_kn
            lines.append(f"  CISALHAMENTO (Asw/s):")
            lines.append(f"    Vsd = {vsd:.2f} kN | VRd2 (Bielas) = {rc.vrd2_kn:.2f} kN (Passa VRd2: {rc.passa_vrd2})")
            lines.append(f"    Asw/s necessário = {rc.asw_usado_cm2_m:.2f} cm²/m")
            lines.append(f"    Estribos Adotados: Φ {rc.diam_estribo_mm:.1f} mm c/ {rc.dist_estribos_cm:.1f} cm")
        else:
            lines.append("  CISALHAMENTO (Asw/s): Esforço nulo.")
            
        lines.append("-" * 75)
        
    return "\n".join(lines)


def gerar_relatorio_viga_comum_premium(
    filepath: str,
    *,
    momentos: List[Tuple[float, float]] = None,
    cortantes: List[Tuple[float, float]] = None,
    secoes_criticas: List[SecaoCritica] = None,
    detalhamento: List[Dict] = None,
    resultado_els: Dict = None,
    **kwargs
) -> str:
    from ui.ftool.diagrama import gerar_diagrama_esforcos
    from core.relatorio_base import gerar_relatorio_viga_comum

    def on_add_diagrams(pdf, sec_num_inicial=3):
        sec_diag = sec_num_inicial
        sec_det = sec_num_inicial + 1
        sec_els = sec_num_inicial + 2
        if momentos and cortantes and secoes_criticas:
            pdf.add_page()
            pdf.section_title(sec_diag, "Diagramas de Esforcos")
            gerar_diagrama_esforcos(pdf, momentos, cortantes, secoes_criticas)
        if detalhamento:
            pdf.ln(4)
            pdf.section_title(sec_det, "Detalhamento de Estribos")
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 4, "Tabela pratica para execucao em obra. Calculo detalhado em Anexo.", border=0)
            pdf.ln(7)
            col_w = [55, 39, 26, 25, 25]
            cab = ["Trecho (m)", "Regiao", "fi (mm)", "Esp. (cm)", "Qtd."]
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(0, 0, 205)
            pdf.set_text_color(255, 255, 255)
            for i, c in enumerate(cab):
                pdf.cell(col_w[i], 7, c, border=1, align="C", fill=True)
            pdf.ln()
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(31, 41, 55)
            for j, r in enumerate(detalhamento):
                bg = (243, 244, 246) if j % 2 == 0 else (255, 255, 255)
                pdf.set_fill_color(*bg)
                vals = [f"{r['x_inicio']:.1f}-{r['x_fim']:.1f}", r['zona'], f"{r['phi_mm']:.0f}", f"{r['espacamento_cm']:.0f}", str(r.get('qtd_estribos', '-'))]
                for i, v in enumerate(vals):
                    pdf.cell(col_w[i], 6, v, border=1, align="C", fill=True)
                pdf.ln()
            pdf.set_text_color(31, 41, 55)
            pdf.ln(4)
        if resultado_els and "erro" not in resultado_els.get("flecha", {}):
            pdf.ln(4)
            pdf.section_title(sec_els, "ELS - Flecha e Fissuracao")
            flecha = resultado_els["flecha"]
            fiss = resultado_els.get("fissuracao", {})
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(0, 0, 205)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 8, "  FLECHA (NBR 6118:17.3.2)", border=0, fill=True)
            pdf.ln(10)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(31, 41, 55)
            for label, val, cor_override in [
                ("I_eq:", f"{flecha['ieq_cm4']:.0f} cm4", None),
                ("Mr:", f"{flecha['mr_kncm']:.1f} kN.cm", None),
                ("Flecha imediata:", f"{flecha['flecha_imediata_cm']:.2f} cm", None),
                ("Flecha diferida:", f"{flecha['flecha_diferida_cm']:.2f} cm", None),
                ("Flecha total:", f"{flecha['flecha_total_cm']:.2f} cm", None),
                ("Limite L/250:", f"{flecha['limite_total_cm']:.2f} cm", None),
                ("Status total:", "OK" if flecha['passa_total'] else "NAO PASSA", (22,101,52) if flecha['passa_total'] else (185,28,28)),
                ("Limite L/350:", f"{flecha['limite_ativo_cm']:.2f} cm", None),
                ("Status diferida:", "OK" if flecha['passa_ativo'] else "NAO PASSA", (22,101,52) if flecha['passa_ativo'] else (185,28,28)),
            ]:
                pdf.cell(90, 6, label, border=0)
                cor = cor_override or (31, 41, 55)
                pdf.set_text_color(*cor)
                pdf.cell(80, 6, val, border=0, align="R")
                pdf.set_text_color(31, 41, 55)
                pdf.ln(6)
            # Exibir dica de correção se não passar
            if not flecha['passa_total'] and flecha.get('dica'):
                pdf.ln(2)
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(185, 28, 28)
                pdf.multi_cell(0, 5, f"Sugestao: {flecha['dica']}", border=0)
                pdf.set_text_color(31, 41, 55)
                pdf.ln(2)
            if fiss:
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_fill_color(0, 0, 205)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 8, "  FISSURACAO (NBR 6118:17.3.3)", border=0, fill=True)
                pdf.ln(10)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(31, 41, 55)
                st = "OK" if fiss.get('passa') else "NAO PASSA"
                cr = (22, 101, 52) if fiss.get('passa') else (185, 28, 28)
                for label, val, cor_override in [
                    ("wk:", f"{fiss['wk_mm']:.2f} mm", cr),
                    ("w_lim (CAA):", f"{fiss['wk_limite_mm']:.1f} mm", None),
                    ("Status:", st, cr),
                ]:
                    pdf.cell(90, 6, label, border=0)
                    cor_f = cor_override or (31, 41, 55)
                    pdf.set_text_color(*cor_f)
                    pdf.cell(80, 6, val, border=0, align="R")
                    pdf.set_text_color(31, 41, 55)
                    pdf.ln(6)
                # Exibir dica de correção se não passar
                if not fiss.get('passa') and fiss.get('dica'):
                    pdf.ln(2)
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.set_text_color(185, 28, 28)
                    pdf.multi_cell(0, 5, f"Sugestao: {fiss['dica']}", border=0)
                    pdf.set_text_color(31, 41, 55)
            
            # Exibir ajustes aplicados se houver
            ajustes = resultado_els.get("ajustes_aplicados")
            if ajustes and (ajustes.barras_extras > 0 or ajustes.phi_minimo_mm or ajustes.h_override_cm or ajustes.fck_override_mpa):
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_fill_color(0, 128, 0)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 8, "  AJUSTES MANUAIS APLICADOS", border=0, fill=True)
                pdf.ln(10)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(31, 41, 55)
                
                if ajustes.barras_extras > 0:
                    pdf.cell(90, 6, "Barras extras:", border=0)
                    pdf.cell(80, 6, f"{ajustes.barras_extras}", border=0, align="R")
                    pdf.ln(6)
                
                if ajustes.phi_minimo_mm:
                    pdf.cell(90, 6, "Diametro minimo:", border=0)
                    pdf.cell(80, 6, f"{ajustes.phi_minimo_mm:.1f} mm", border=0, align="R")
                    pdf.ln(6)
                
                if ajustes.h_override_cm:
                    pdf.cell(90, 6, "Altura ajustada:", border=0)
                    pdf.cell(80, 6, f"{ajustes.h_override_cm:.1f} cm", border=0, align="R")
                    pdf.ln(6)
                
                if ajustes.fck_override_mpa:
                    pdf.cell(90, 6, "fck ajustado:", border=0)
                    pdf.cell(80, 6, f"{ajustes.fck_override_mpa:.0f} MPa", border=0, align="R")
                    pdf.ln(6)

    return gerar_relatorio_viga_comum(
        filepath,
        on_add_diagrams=on_add_diagrams if (momentos and cortantes) else None,
        **kwargs
    )


def gerar_relatorio_viga_t_premium(
    filepath: str,
    *,
    momentos: List[Tuple[float, float]] = None,
    cortantes: List[Tuple[float, float]] = None,
    secoes_criticas: List[SecaoCritica] = None,
    detalhamento: List[Dict] = None,
    resultado_els: Dict = None,
    **kwargs
) -> str:
    from ui.ftool.diagrama import gerar_diagrama_esforcos
    from core.relatorio_base import gerar_relatorio_viga_t

    def on_add_diagrams(pdf, sec_num_inicial=3):
        sec_diag = sec_num_inicial
        sec_det = sec_num_inicial + 1
        sec_els = sec_num_inicial + 2
        if momentos and cortantes and secoes_criticas:
            pdf.add_page()
            pdf.section_title(sec_diag, "Diagramas de Esforcos")
            gerar_diagrama_esforcos(pdf, momentos, cortantes, secoes_criticas)
        if detalhamento:
            pdf.ln(4)
            pdf.section_title(sec_det, "Detalhamento de Estribos")
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 4, "Tabela pratica para execucao em obra. Calculo detalhado em Anexo.", border=0)
            pdf.ln(7)
            col_w = [55, 39, 26, 25, 25]
            cab = ["Trecho (m)", "Regiao", "fi (mm)", "Esp. (cm)", "Qtd."]
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(0, 0, 205)
            pdf.set_text_color(255, 255, 255)
            for i, c in enumerate(cab):
                pdf.cell(col_w[i], 7, c, border=1, align="C", fill=True)
            pdf.ln()
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(31, 41, 55)
            for j, r in enumerate(detalhamento):
                bg = (243, 244, 246) if j % 2 == 0 else (255, 255, 255)
                pdf.set_fill_color(*bg)
                vals = [f"{r['x_inicio']:.1f}-{r['x_fim']:.1f}", r['zona'], f"{r['phi_mm']:.0f}", f"{r['espacamento_cm']:.0f}", str(r.get('qtd_estribos', '-'))]
                for i, v in enumerate(vals):
                    pdf.cell(col_w[i], 6, v, border=1, align="C", fill=True)
                pdf.ln()
            pdf.set_text_color(31, 41, 55)
            pdf.ln(4)
        if resultado_els and "erro" not in resultado_els.get("flecha", {}):
            pdf.ln(4)
            pdf.section_title(sec_els, "ELS - Flecha e Fissuracao")
            flecha = resultado_els["flecha"]
            fiss = resultado_els.get("fissuracao", {})
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(0, 0, 205)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 8, "  FLECHA (NBR 6118:17.3.2)", border=0, fill=True)
            pdf.ln(10)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(31, 41, 55)
            for label, val, cor_override in [
                ("I_eq:", f"{flecha['ieq_cm4']:.0f} cm4", None),
                ("Mr:", f"{flecha['mr_kncm']:.1f} kN.cm", None),
                ("Flecha imediata:", f"{flecha['flecha_imediata_cm']:.2f} cm", None),
                ("Flecha diferida:", f"{flecha['flecha_diferida_cm']:.2f} cm", None),
                ("Flecha total:", f"{flecha['flecha_total_cm']:.2f} cm", None),
                ("Limite L/250:", f"{flecha['limite_total_cm']:.2f} cm", None),
                ("Status total:", "OK" if flecha['passa_total'] else "NAO PASSA", (22,101,52) if flecha['passa_total'] else (185,28,28)),
                ("Limite L/350:", f"{flecha['limite_ativo_cm']:.2f} cm", None),
                ("Status diferida:", "OK" if flecha['passa_ativo'] else "NAO PASSA", (22,101,52) if flecha['passa_ativo'] else (185,28,28)),
            ]:
                pdf.cell(90, 6, label, border=0)
                cor = cor_override or (31, 41, 55)
                pdf.set_text_color(*cor)
                pdf.cell(80, 6, val, border=0, align="R")
                pdf.set_text_color(31, 41, 55)
                pdf.ln(6)
            if fiss:
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_fill_color(0, 0, 205)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 8, "  FISSURACAO (NBR 6118:17.3.3)", border=0, fill=True)
                pdf.ln(10)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(31, 41, 55)
                st = "OK" if fiss.get('passa') else "NAO PASSA"
                cr = (22, 101, 52) if fiss.get('passa') else (185, 28, 28)
                for label, val, cor_override in [
                    ("wk:", f"{fiss['wk_mm']:.2f} mm", cr),
                    ("w_lim (CAA):", f"{fiss['wk_limite_mm']:.1f} mm", None),
                    ("Status:", st, cr),
                ]:
                    pdf.cell(90, 6, label, border=0)
                    cor_f = cor_override or (31, 41, 55)
                    pdf.set_text_color(*cor_f)
                    pdf.cell(80, 6, val, border=0, align="R")
                    pdf.set_text_color(31, 41, 55)
                    pdf.ln(6)
            
            # Exibir ajustes aplicados se houver
            ajustes = resultado_els.get("ajustes_aplicados")
            if ajustes and (ajustes.barras_extras > 0 or ajustes.phi_minimo_mm or ajustes.h_override_cm or ajustes.fck_override_mpa):
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_fill_color(0, 128, 0)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(0, 8, "  AJUSTES MANUAIS APLICADOS", border=0, fill=True)
                pdf.ln(10)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(31, 41, 55)
                
                if ajustes.barras_extras > 0:
                    pdf.cell(90, 6, "Barras extras:", border=0)
                    pdf.cell(80, 6, f"{ajustes.barras_extras}", border=0, align="R")
                    pdf.ln(6)
                
                if ajustes.phi_minimo_mm:
                    pdf.cell(90, 6, "Diametro minimo:", border=0)
                    pdf.cell(80, 6, f"{ajustes.phi_minimo_mm:.1f} mm", border=0, align="R")
                    pdf.ln(6)
                
                if ajustes.h_override_cm:
                    pdf.cell(90, 6, "Altura ajustada:", border=0)
                    pdf.cell(80, 6, f"{ajustes.h_override_cm:.1f} cm", border=0, align="R")
                    pdf.ln(6)
                
                if ajustes.fck_override_mpa:
                    pdf.cell(90, 6, "fck ajustado:", border=0)
                    pdf.cell(80, 6, f"{ajustes.fck_override_mpa:.0f} MPa", border=0, align="R")
                    pdf.ln(6)

    return gerar_relatorio_viga_t(
        filepath,
        on_add_diagrams=on_add_diagrams if (momentos and cortantes) else None,
        **kwargs
    )

