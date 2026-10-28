"""
Detalhamento de estribos por zona ao longo da viga.
Usa a curva V(x) completa + decalagem NBR 6118:17.4.2.2.
Divide cada vao em 3 zonas: Apoio Esq / Vao / Apoio Dir.
"""

from typing import List, Tuple, Dict
import math
from core.calculos.engenharia import calcular_cisalhamento_viga_comum


def _calc_asw_s(vk_kn, gamma_f, h_cm, bw_cm, fck_mpa, fyk_mpa, fyk_estribo_mpa, caa):
    res = calcular_cisalhamento_viga_comum(
        h_cm=h_cm, bw_cm=bw_cm, fck_mpa=fck_mpa,
        diam_estribo_mm=5.0, diam_barra_mm=16.0,
        fyk_estribo_mpa=fyk_estribo_mpa, fyk_barra_mpa=fyk_mpa,
        caa=caa, forcas_cortantes=[vk_kn], gamma_f=gamma_f,
    )
    return res[0].asw_usado_cm2_m if (res and res[0]) else 0.0


def _calc_espacamento(asw_s_cm2m, phi_mm):
    area = math.pi * (phi_mm / 10) ** 2 / 4
    if asw_s_cm2m <= 0:
        return 30.0
    s = (2 * area) / asw_s_cm2m * 100
    return max(5.0, min(s, 30.0))


def _encontrar_apoios(cortantes: List[Tuple[float, float]]) -> List[float]:
    """Detecta apoios por descontinuidade em x."""
    apoios = []
    for i in range(1, len(cortantes)):
        if abs(cortantes[i][0] - cortantes[i - 1][0]) < 0.001:
            apoios.append(cortantes[i][0])
    return sorted(set(apoios))


def detalhar_estribos(h_cm, bw_cm, fck_mpa, fyk_mpa, fyk_estribo_mpa, caa,
                      cortantes: List[Tuple[float, float]],
                      phi_estribo_mm=5.0, gamma_f=1.4) -> List[Dict]:
    """
    Divide a viga em zonas de estribos usando decalagem al = d.
    Para cada vao, gera 3 zonas: Apoio Esq / Vao / Apoio Dir.
    """
    if not cortantes:
        return []

    pontos = sorted(cortantes, key=lambda p: p[0])
    L = max(p[0] for p in pontos)
    d_cm = h_cm - 3.0 - 0.5 - 0.8
    al_m = d_cm / 100

    apoios = _encontrar_apoios(pontos)
    if not apoios:
        apoios = [0.0, L]

    # Limites dos vaos entre apoios
    limites = [0.0] + apoios + [L]
    limites = sorted(set(limites))

    zonas = []
    for i in range(len(limites) - 1):
        xi, xf = limites[i], limites[i + 1]
        if xf - xi < 0.1:
            continue

        # Zona de apoio esquerdo do vao: xi ate xi + al
        ze_fim = min(xi + al_m, xf)
        if ze_fim > xi:
            pts = [p for p in pontos if xi <= p[0] <= ze_fim]
            vk = max(abs(p[1]) for p in pts) if pts else 0
            asw = _calc_asw_s(vk, gamma_f, h_cm, bw_cm, fck_mpa, fyk_mpa, fyk_estribo_mpa, caa)
            zonas.append({"x_inicio": round(xi, 2), "x_fim": round(ze_fim, 2),
                          "phi_mm": phi_estribo_mm,
                          "espacamento_cm": round(_calc_espacamento(asw, phi_estribo_mm), 1),
                          "asw_s_cm2m": round(asw, 2), "zona": "Apoio"})

        # Zona de meio de vao: xi + al ate xf - al
        zv_ini = ze_fim
        zv_fim = max(xf - al_m, zv_ini)
        if zv_fim > zv_ini + 0.1:
            pts = [p for p in pontos if zv_ini <= p[0] <= zv_fim]
            vk = max(abs(p[1]) for p in pts) if pts else 0
            asw = _calc_asw_s(vk, gamma_f, h_cm, bw_cm, fck_mpa, fyk_mpa, fyk_estribo_mpa, caa)
            zonas.append({"x_inicio": round(zv_ini, 2), "x_fim": round(zv_fim, 2),
                          "phi_mm": phi_estribo_mm,
                          "espacamento_cm": round(_calc_espacamento(asw, phi_estribo_mm), 1),
                          "asw_s_cm2m": round(asw, 2), "zona": "Vao"})
            zd_ini = zv_fim
        else:
            zd_ini = ze_fim

        # Zona de apoio direito do vao: xf - al ate xf
        if xf - zd_ini > 0.1:
            pts = [p for p in pontos if zd_ini <= p[0] <= xf]
            vk = max(abs(p[1]) for p in pts) if pts else 0
            asw = _calc_asw_s(vk, gamma_f, h_cm, bw_cm, fck_mpa, fyk_mpa, fyk_estribo_mpa, caa)
            zonas.append({"x_inicio": round(zd_ini, 2), "x_fim": round(xf, 2),
                          "phi_mm": phi_estribo_mm,
                          "espacamento_cm": round(_calc_espacamento(asw, phi_estribo_mm), 1),
                          "asw_s_cm2m": round(asw, 2), "zona": "Apoio"})

    # Mesclar zonas adjacentes com mesmo espacamento (tolerancia 2cm)
    if len(zonas) > 1:
        merged = [zonas[0]]
        for z in zonas[1:]:
            if abs(z["espacamento_cm"] - merged[-1]["espacamento_cm"]) <= 2 and z["phi_mm"] == merged[-1]["phi_mm"]:
                merged[-1]["x_fim"] = z["x_fim"]
                merged[-1]["zona"] = "Apoio+Vao" if merged[-1]["zona"] != z["zona"] else merged[-1]["zona"]
            else:
                merged.append(z)
        zonas = merged

    return zonas


def calcular_qtd_estribos(regioes: List[Dict]) -> List[Dict]:
    """Calcula quantidade de estribos por zona."""
    for r in regioes:
        comprimento_cm = (r["x_fim"] - r["x_inicio"]) * 100
        if r["espacamento_cm"] > 0:
            r["qtd_estribos"] = math.ceil(comprimento_cm / r["espacamento_cm"])
        else:
            r["qtd_estribos"] = 0
    return regioes


def gerar_tabela_detailing(regioes: List[Dict]) -> str:
    if not regioes:
        return "Nenhuma regiao calculada."
    linhas = ["-" * 60, "  DETALHAMENTO DE ESTRIBOS", "-" * 60,
              f"  {'Trecho (m)':<18} {'Esp.':<7} {'Asw/s':<8} {'Zona':<14}", "-" * 60]
    for r in regioes:
        trecho = f"{r['x_inicio']:.2f} a {r['x_fim']:.2f}"
        linhas.append(f"  {trecho:<18} {r['espacamento_cm']:<5}cm {r['asw_s_cm2m']:<6.2f}cm2/m {r['zona']:<14}")
    linhas.append("-" * 60)
    return "\n".join(linhas)
