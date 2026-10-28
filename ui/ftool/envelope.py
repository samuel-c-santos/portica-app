"""
Módulo para cálculo e processamento de envelope de combinações de esforços (FTOOL).
Fase 2.5 — Envelope de Combinações
"""

from typing import List, Dict, Tuple, Any
from ui.ftool.secoes_criticas import SecaoCritica, interpolar_y


def calcular_envelope(combinacoes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Recebe uma lista de dicionários, cada um com "momentos" e "cortantes" (listas de (x, valor)).
    Retorna um dicionário com as curvas envolventes máximas e mínimas:
    {
        "momentos_max": List[Tuple[float, float]],
        "momentos_min": List[Tuple[float, float]],
        "cortantes_max": List[Tuple[float, float]],
        "cortantes_min": List[Tuple[float, float]],
    }
    """
    if not combinacoes:
        return {
            "momentos_max": [],
            "momentos_min": [],
            "cortantes_max": [],
            "cortantes_min": [],
        }

    # 1. Coletar todos os pontos x de todas as combinações
    all_xs = []
    for comb in combinacoes:
        all_xs.extend([p[0] for p in comb.get("momentos", [])])
        all_xs.extend([p[0] for p in comb.get("cortantes", [])])

    # 2. Fundir e obter pontos x únicos com tolerância de 1 cm (0.01 m)
    all_xs.sort()
    unique_xs = []
    for x in all_xs:
        if not any(abs(x - ux) < 0.01 for ux in unique_xs):
            unique_xs.append(x)

    momentos_max = []
    momentos_min = []
    cortantes_max = []
    cortantes_min = []

    def get_valores_no_x(curva: List[Tuple[float, float]], x_target: float) -> List[float]:
        # Se houver pontos correspondentes exatos na curva (dentro de uma tolerância pequena de 1e-5),
        # retornamos todos eles (pode ser mais de um no caso de descontinuidade)
        matches = [pt[1] for pt in curva if abs(pt[0] - x_target) < 1e-5]
        if matches:
            return matches
        # Senão, interpolamos linearmente
        return [interpolar_y(curva, x_target)]

    # 3. Mapear os valores máximos e mínimos para cada x único
    for ux in unique_xs:
        m_vals = []
        v_vals = []
        for comb in combinacoes:
            m_vals.extend(get_valores_no_x(comb.get("momentos", []), ux))
            v_vals.extend(get_valores_no_x(comb.get("cortantes", []), ux))

        if m_vals:
            momentos_max.append((ux, max(m_vals)))
            momentos_min.append((ux, min(m_vals)))
        if v_vals:
            cortantes_max.append((ux, max(v_vals)))
            cortantes_min.append((ux, min(v_vals)))

    return {
        "momentos_max": momentos_max,
        "momentos_min": momentos_min,
        "cortantes_max": cortantes_max,
        "cortantes_min": cortantes_min,
    }


def detectar_secoes_envelope(combinacoes: List[Dict[str, Any]], envelope: Dict[str, Any]) -> List[SecaoCritica]:
    """
    Detecta as seções críticas no envelope de esforços, identificando a origem (combinação)
    de cada esforço crítico.
    """
    m_max_curve = envelope["momentos_max"]
    m_min_curve = envelope["momentos_min"]
    v_max_curve = envelope["cortantes_max"]
    v_min_curve = envelope["cortantes_min"]

    if not m_max_curve:
        return []

    from ui.ftool.secoes_criticas import (
        detectar_maximos_locais,
        detectar_minimos_locais,
        detectar_apoios,
        detectar_pontos_momento_nulo,
    )

    L = max(p[0] for p in m_max_curve)
    x_min = m_max_curve[0][0]

    # Detectar candidatos x críticos
    x_maximos = [p[0] for p in detectar_maximos_locais(m_max_curve)]
    x_minimos = [p[0] for p in detectar_minimos_locais(m_min_curve)]
    x_apoios = detectar_apoios(m_max_curve, v_max_curve) + detectar_apoios(m_min_curve, v_min_curve)
    x_nulos = [p[0] for p in detectar_pontos_momento_nulo(m_max_curve)] + [p[0] for p in detectar_pontos_momento_nulo(m_min_curve)]
    x_extremos = [x_min, L]

    # Fundir
    todos_x = sorted(x_maximos + x_minimos + x_apoios + x_nulos + x_extremos)
    unique_x = []
    for x in todos_x:
        if not any(abs(x - ux) < 1e-5 for ux in unique_x):
            unique_x.append(x)

    def encontrar_origem_momento(x_val: float, m_val: float) -> str:
        for idx, comb in enumerate(combinacoes):
            nome = comb.get("nome", f"Combinação {idx + 1}")
            m_comb = interpolar_y(comb["momentos"], x_val)
            if abs(m_comb - m_val) < 1e-2:
                return nome
        return "Desconhecida"

    def encontrar_origem_cortante(x_val: float, v_val: float) -> str:
        for idx, comb in enumerate(combinacoes):
            nome = comb.get("nome", f"Combinação {idx + 1}")
            matches = [pt[1] for pt in comb["cortantes"] if abs(pt[0] - x_val) < 1e-5]
            if matches:
                for v in matches:
                    if abs(v - v_val) < 1e-2:
                        return nome
            else:
                v_comb = interpolar_y(comb["cortantes"], x_val)
                if abs(v_comb - v_val) < 1e-2:
                    return nome
        return "Desconhecida"

    secoes = []
    for x in unique_x:
        is_max = any(abs(x - xm) < 1e-5 for xm in x_maximos)
        is_min = any(abs(x - xm) < 1e-5 for xm in x_minimos)
        is_apoio = any(abs(x - xa) < 1e-5 for xa in x_apoios)
        is_extremo = any(abs(x - xe) < 1e-5 for xe in x_extremos)
        is_nulo = any(abs(x - xn) < 1e-5 for xn in x_nulos)

        # Interpolar esforços do envelope
        m_max = interpolar_y(m_max_curve, x)
        m_min = interpolar_y(m_min_curve, x)
        v_max = interpolar_y(v_max_curve, x)
        v_min = interpolar_y(v_min_curve, x)

        # Cortante crítico (maior em módulo)
        v_pior = max([v_max, v_min], key=abs)
        origem_v = encontrar_origem_cortante(x, v_pior)

        if is_apoio:
            origem_m = encontrar_origem_momento(x, m_min)
            secoes.append(SecaoCritica(
                x=round(x, 4),
                momento=round(m_min, 2),
                cortante=round(v_pior, 2),
                tipo="APOIO",
                descricao="Apoio detectado (mínimo de envelope)" if x != x_min and x != L else ("Apoio esquerdo" if x == x_min else "Apoio direito"),
                origem=f"M: {origem_m} | V: {origem_v}"
            ))
        elif is_max or (is_extremo and abs(m_max) >= abs(m_min)):
            origem_m = encontrar_origem_momento(x, m_max)
            secoes.append(SecaoCritica(
                x=round(x, 4),
                momento=round(m_max, 2),
                cortante=round(v_pior, 2),
                tipo="MÁX" if is_max else "EXTREMO",
                descricao="Momento máximo de envelope" if is_max else "Extremo de envelope (máximo)",
                origem=f"M: {origem_m} | V: {origem_v}"
            ))
        elif is_min or (is_extremo and abs(m_min) > abs(m_max)):
            origem_m = encontrar_origem_momento(x, m_min)
            secoes.append(SecaoCritica(
                x=round(x, 4),
                momento=round(m_min, 2),
                cortante=round(v_pior, 2),
                tipo="MÍN" if is_min else "EXTREMO",
                descricao="Momento mínimo de envelope" if is_min else "Extremo de envelope (mínimo)",
                origem=f"M: {origem_m} | V: {origem_v}"
            ))
        elif is_nulo:
            secoes.append(SecaoCritica(
                x=round(x, 4),
                momento=0.0,
                cortante=round(v_pior, 2),
                tipo="M_NULO",
                descricao="Momento nulo de envelope",
                origem=f"V: {origem_v}"
            ))

    return secoes


def gerar_relatorio_envelope(dados_viga: Dict[str, Any], envelope: Dict[str, Any], secoes: List[SecaoCritica]) -> str:
    """
    Gera um relatório textual completo detalhando os resultados do dimensionamento
    com base nas seções críticas do envelope.
    """
    from ui.ftool.dimensionamento import dimensionar_trechos_ftool
    resultados = dimensionar_trechos_ftool(dados_viga, secoes)["secoes"]

    lines = []
    lines.append("=== PÓRTICA APP: RELATÓRIO DO ENVELOPE DE COMBINAÇÕES ===")
    lines.append(f"Geometria: bw={dados_viga['bw_cm']} cm | h={dados_viga['h_cm']} cm")
    lines.append(f"Materiais: fck={dados_viga['fck_mpa']} MPa | CAA={dados_viga['caa']}")
    lines.append("-" * 85)
    lines.append("Resumo das Seções Críticas Dimensionadas pelo Envelope:")
    lines.append("-" * 85)

    for res in resultados:
        x = res["x"]
        mk = res["Mk"]
        vk = res["Vk"]
        tipo = res["tipo"]
        desc = res["descricao"]
        
        # Encontra a seção correspondente para obter origem
        sec = next((s for s in secoes if abs(s.x - x) < 1e-4), None)
        origem_str = f" | Origem: {sec.origem}" if sec else ""

        lines.append(f"Seção em x = {x:.2f} m | Tipo: {tipo} ({desc}){origem_str}")
        lines.append(f"  Esforço de Dimensionamento: Mk = {mk:+.2f} kN·m | Vk = {vk:+.2f} kN")

        rf = res["resultado_flexao"]
        if rf:
            lines.append(f"  FLEXÃO (As): As_req = {rf.as_req_cm2:.2f} cm² | Adotado: {rf.qtd_barras} Φ {rf.diametro_mm:.1f} mm (As = {rf.as_usado_cm2:.2f} cm²)")
            if rf.alerta:
                lines.append(f"    ⚠️ ALERTA: {rf.alerta}")
        else:
            lines.append("  FLEXÃO (As): Armadura de tração não necessária.")

        rc = res["resultado_cisalhamento"]
        if rc:
            lines.append(f"  CISALHAMENTO (Asw/s): Asw/s_req = {rc.asw_usado_cm2_m:.2f} cm²/m | Adotado: Φ {rc.diam_estribo_mm:.1f} mm c/ {rc.dist_estribos_cm:.1f} cm")
        else:
            lines.append("  CISALHAMENTO (Asw/s): Esforço nulo.")

        lines.append("-" * 85)

    return "\n".join(lines)
