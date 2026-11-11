"""
CALCULOS ESTRUTURAIS - Flexao e Cisalhamento
Norma: NBR 6118:2023
Autor: Samuel da Costa dos Santos (https://github.com/samuel-c-santos)
Licenca: vide LICENSE
"""

import math
from dataclasses import dataclass

from core.calculos.secao import (  # noqa: F401  (re-exporta a API publica de core.calculos)
    ALPHA_C,
    CAA_COBRIMENTO_MM,
    GAMMA_C,
    alpha_c,
    altura_util_cm,
    fcd_mpa,
    fctd_kn_cm2,
    fctm_mpa,
    lambda_f,
)
from core.calculos.secao import (
    d_linha_cm as _d_linha_estimada_cm,
)
from core.detailing import BeamDetailer, BeamDetailingInput, SectionLayoutData

# ── Constantes ────────────────────────────────────────────────────────────────
# ALPHA_C e GAMMA_C: fonte unica em core/calculos/secao.py (EP-04.1)
GAMMA_S = 1.15  # Coeficiente do aço
GAMMA_F_PP = 1.30  # Peso próprio
GAMMA_F_RESTO = 1.40  # Demais ações

# ── Limites de domínio (NBR 6118:2023) ─────────────────────────────────────
# Ductilidade em vigas: a norma (17.2.3) remete a 14.6.4.3. Para δ = 1,0:
#   x/d ≤ (1,0 − 0,44)/1,25 = 0,448 ≈ 0,45  (fck ≤ 50 MPa)
#   x/d ≤ (1,0 − 0,56)/1,25 = 0,352 ≈ 0,35  (fck > 50 MPa)
BX_LIM_DUCTILIDADE_ATE_50 = 0.45
BX_LIM_DUCTILIDADE_ACIMA_50 = 0.35

# Profundidade do diagrama retangular de tensões (17.2.2-e):
#   λ = 0,8 (fck ≤ 50) ; λ = 0,8 − (fck − 50)/400 (fck > 50)
ETA_ATE_50 = 0.80
ETA_DIVISOR_ACIMA_50 = 400.0

# Fronteiras dos domínios de deformação (CA-50, εcu = 3,5‰, εyd = 2,07‰):
#   domínio 2/3: 3,5/(3,5+10) = 0,259 ; domínio 3/4: 3,5/(3,5+2,07) = 0,628
BX_DOMINIO_2_3 = 0.259
BX_DOMINIO_4 = 0.628


# Tabela 11.1 - NBR 6118:2023 - Coeficientes γf (simplificação por combinação)
# O app recebe esforços característicos (sem majorar) e aplica γf internamente.
GAMMA_F_TABLE = {
    "normais": {"nome": "Normais", "gamma_f": 1.4},
    "especiais": {"nome": "Especiais ou de construcao", "gamma_f": 1.2},
    "excepcionais": {"nome": "Excepcionais", "gamma_f": 1.0},
}

# Diâmetros de barra disponíveis (mm)
DIAM_BARRAS = [5, 6.3, 8, 10, 12.5, 16, 20, 25, 32]  # estribos e pele
DIAM_BARRAS_LONG = [10, 12.5, 16, 20, 25, 32]  # armadura longitudinal (NBR 6118: φ≥10mm)


# ── Classes de Agressividade Ambiental ───────────────────────────────────────
CAA_DATA = {
    1: {"nome": "Fraca", "cobrimento": CAA_COBRIMENTO_MM[1], "ac_max": 0.65, "fck_min": 20},
    2: {"nome": "Moderada", "cobrimento": CAA_COBRIMENTO_MM[2], "ac_max": 0.60, "fck_min": 25},
    3: {"nome": "Forte", "cobrimento": CAA_COBRIMENTO_MM[3], "ac_max": 0.55, "fck_min": 30},
    4: {"nome": "Muito Forte", "cobrimento": CAA_COBRIMENTO_MM[4], "ac_max": 0.50, "fck_min": 35},
}

# Tabela de rho_min para flexão (fck em MPa)
RHO_MIN_TABLE = {
    20: 0.150,
    25: 0.150,
    30: 0.150,
    35: 0.164,
    40: 0.179,
    45: 0.194,
    50: 0.208,
    55: 0.211,
    60: 0.219,
    65: 0.226,
    70: 0.233,
    75: 0.239,
    80: 0.245,
    85: 0.251,
    90: 0.256,
}

# Tabela de Asw/s (cm²/m) para estribos – CA-50 e CA-60 (fywd em MPa → fywd/1.15)
ASW_S_TABLE_CA50 = {
    20: (0.1768, 0.0884, 0.0737),
    25: (0.2052, 0.1026, 0.0855),
    30: (0.2317, 0.1159, 0.0965),
    35: (0.2568, 0.1284, 0.1070),
    40: (0.2807, 0.1404, 0.1177),
    45: (0.3036, 0.1518, 0.1265),
    50: (0.3257, 0.1629, 0.1357),
    55: (0.3471, 0.1735, 0.1446),
    60: (0.3678, 0.1839, 0.1533),
    65: (0.3880, 0.1940, 0.1617),
    70: (0.4076, 0.2038, 0.1698),
    75: (0.4268, 0.2134, 0.1778),
    80: (0.4456, 0.2228, 0.1857),
    85: (0.4640, 0.2320, 0.1933),
    90: (0.4820, 0.2410, 0.2008),
}


def area_barra(d_mm: float) -> float:
    """Área da seção transversal de uma barra em cm²."""
    return (math.pi * (d_mm / 10) ** 2) / 4


def fyd_kn_cm2(fyk_kn_cm2: float) -> float:
    """Resistencia de calculo do aco em kN/cm².

    O UI passa fyk em kN/cm² (CA-50 = 50, CA-60 = 60, CA-25 = 25),
    equivalente a MPa/10. Retorna fyd em kN/cm² (nao divide por 10).
    """
    return fyk_kn_cm2 / GAMMA_S


def fck_to_kgf_cm2(fck_mpa: float) -> float:
    """Converte fck de MPa para kgf/cm2 (1 MPa = 10,1972 kgf/cm2)."""
    return fck_mpa * 10.1972


def fctkinf_mpa(fck: float) -> float:
    return 0.7 * fctm_mpa(fck)


def _tensao_aco_compressao_kn_cm2(
    fyd_kn_cm2: float, d_linha_cm: float, x_cm: float, es_kn_cm2: float = 21000.0
) -> float:
    """Tensão no aço de compressão por compatibilidade (NBR 6118:2023, 17.2.3).

    ε_s' = ε_cu·(x − d')/x, limitada a ε_yd (aço elastoplástico). Retorna 0
    quando a armadura está fora da zona comprimida (d' ≥ x).
    """
    if x_cm <= 0:
        return 0.0
    eps_cu = 0.0035
    eps_s_linha = eps_cu * (x_cm - d_linha_cm) / x_cm
    if eps_s_linha <= 0:
        return 0.0
    return min(fyd_kn_cm2, es_kn_cm2 * eps_s_linha)


def _d_linha_detalhado(
    h_cm: float,
    bw_cm: float,
    cob_mm: float,
    diam_estribo_mm: float,
    diam_barra_mm: float,
    qtd_barras_linha: int,
    is_t: bool = False,
    bf_cm: float = 0.0,
    hf_cm: float = 0.0,
    d_max_agregado_mm: float = 19.0,
) -> float:
    """d' real da armadura de compressão pelo detalhamento (EP-02.4).

    O detalhador é chamado com `is_superior=True`, então `d_efetiva` é a
    distância da face comprimida (topo) ao centroide das barras. Em caso de
    recusa geométrica, recai na estimativa de 1 camada.
    """
    estimativa = _d_linha_estimada_cm(cob_mm, diam_estribo_mm, diam_barra_mm)
    if qtd_barras_linha <= 0:
        return estimativa
    try:
        layout = BeamDetailer().detail(
            BeamDetailingInput(
                bw=bw_cm * 10.0,
                h=h_cm * 10.0,
                c_nom=cob_mm,
                phi_estribo=diam_estribo_mm,
                phi_barra=diam_barra_mm,
                d_max_agregado=d_max_agregado_mm,
                total_bars=qtd_barras_linha,
                is_t=is_t,
                bf_cm=bf_cm,
                hf_cm=hf_cm,
                is_superior=True,
            )
        )
        total = max(layout.total_bars, 1)
        y_cg_comprimido_mm = sum(lyr.y_centroid * lyr.bar_count for lyr in layout.layers) / total
        return y_cg_comprimido_mm / 10.0
    except ValueError:
        return estimativa


def _d_linha_dupla(
    h_cm: float,
    bw_cm: float,
    cob_mm: float,
    diam_estribo_mm: float,
    diam_barra_mm: float,
    md_exc_kncm: float,
    fyd_kn_cm2: float,
    d_cm: float,
    d_lin_est_cm: float,
    is_t: bool = False,
    bf_cm: float = 0.0,
    hf_cm: float = 0.0,
) -> float:
    """d' da compressão: detalha a quantidade estimada e devolve a posição real."""
    a_bar = area_barra(diam_barra_mm)
    denom = _denom_as2(d_cm, d_lin_est_cm, contexto="d' da armadura de compress?o (estimativa)")
    as2_est = md_exc_kncm / (fyd_kn_cm2 * denom) if fyd_kn_cm2 > 0 else 0.0
    # Limite de seguran?a: evita loop patol?gico do detalhador com quantidade
    # absurda de barras em se??es invi?veis (a se??o ser? recusada adiante).
    qtd = min(max(1, math.ceil(as2_est / a_bar)), 1000) if a_bar > 0 else 1
    return _d_linha_detalhado(
        h_cm,
        bw_cm,
        cob_mm,
        diam_estribo_mm,
        diam_barra_mm,
        qtd,
        is_t=is_t,
        bf_cm=bf_cm,
        hf_cm=hf_cm,
    )


def _as2_as_linha_dupla(
    md_exc_kncm: float,
    fyd_kn_cm2: float,
    d_cm: float,
    d_linha_cm: float,
    x_cm: float,
    bw_cm: float,
    h_cm: float,
    is_t: bool = False,
    bf_cm: float = 0.0,
    hf_cm: float = 0.0,
    contexto: str = "",
) -> tuple[float, float]:
    """Balanço da armadura dupla (NBR 6118:2023, 17.2.3 e 17.3.5.2.4).

    As2 = Md,exc/(fyd·(d − d'))  (tração adicional)
    As' = As2·fyd/f_s'            (compressão; f_s' por compatibilidade ≤ fyd)
    As' ≥ 0,1% da área de concreto (ρ'' mínimo).
    """
    denom = _denom_as2(d_cm, d_linha_cm, contexto=contexto)
    as2 = md_exc_kncm / (fyd_kn_cm2 * denom)
    f_s_linha = _tensao_aco_compressao_kn_cm2(fyd_kn_cm2, d_linha_cm, x_cm)
    if f_s_linha <= 0:
        raise ValueError(
            f"Seção recusada: armadura de compressão fora da zona comprimida "
            f"(d'={d_linha_cm:.2f} cm ≥ x={x_cm:.2f} cm). Contexto: {contexto}"
        )
    as_linha = as2 * fyd_kn_cm2 / f_s_linha
    area_concreto = bw_cm * h_cm
    if is_t and bf_cm > bw_cm and hf_cm > 0:
        area_concreto += (bf_cm - bw_cm) * hf_cm
    as_linha = max(as_linha, 0.001 * area_concreto)
    return as2, as_linha


def _bx_lim_ductilidade(fck_mpa: float) -> float:
    """Limite de ductilidade x/d (NBR 6118:2023, 14.6.4.3, δ=1,0)."""
    return BX_LIM_DUCTILIDADE_ATE_50 if fck_mpa <= 50 else BX_LIM_DUCTILIDADE_ACIMA_50


def ETA_ACIMA_50(fck_mpa: float) -> float:
    """λ para fck > 50 MPa (NBR 6118:2023, 17.2.2-e)."""
    return ETA_ATE_50 - (fck_mpa - 50.0) / ETA_DIVISOR_ACIMA_50


def _eta_diagrama_retangular(fck_mpa: float) -> float:
    """Profundidade do diagrama retangular λ (NBR 6118:2023, 17.2.2-e)."""
    return ETA_ATE_50 if fck_mpa <= 50 else ETA_ACIMA_50(fck_mpa)


def classificar_dominio(bx: float) -> str:
    """Classifica a posição da linha neutra nos domínios de deformação.

    Fronteiras para CA-50 (εcu = 3,5‰, εyd = 2,07‰): 2/3 em 0,259 e
    3/4 em 0,628. Domínio 4 significa aço tracionado sem escoamento —
    ruptura frágil, que o dimensionamento deve recusar.
    """
    if bx > BX_DOMINIO_4:
        return "DOMINIO_4"
    if bx > BX_DOMINIO_2_3:
        return "DOMINIO_3"
    return "DOMINIO_2"


def _resolver_ln(
    md_kncm: float, fck_mpa: float, b_cm: float, d_cm: float
) -> tuple[float | None, float, float]:
    """Resolve o equilíbrio NBR da linha neutra (NBR 6118:2023, 17.2.2).

    Md = fcd·b·x·(d − 0,4x)  →  0,4x² − d·x + Md/(fcd·b) = 0.

    Retorna (x, x1, x2) com x = menor raiz (domínio 2/3). Se o discriminante
    for negativo (momento acima da capacidade da seção com armadura simples),
    retorna (None, 0, 0) — o chamador decide entre armadura dupla e recusa.
    """
    fcd = fcd_mpa(fck_mpa) / 10.0  # kN/cm²
    if fcd <= 0 or b_cm <= 0 or d_cm <= 0:
        return None, 0.0, 0.0
    c = md_kncm / (fcd * b_cm)
    delta = d_cm**2 - 1.6 * c
    if delta < 0:
        return None, 0.0, 0.0
    raiz = math.sqrt(delta)
    x1 = (d_cm - raiz) / 0.8
    x2 = (d_cm + raiz) / 0.8
    return min(x1, x2), x1, x2


def _momento_limite_ln(
    fck_mpa: float, b_cm: float, d_cm: float, bx_lim: float
) -> tuple[float, float]:
    """Momento limite (kN·cm) e x (cm) no limite de ductilidade bx_lim.

    Md,lim = fcd·b·x_lim·(d − 0,4·x_lim), x_lim = bx_lim·d.
    """
    fcd = fcd_mpa(fck_mpa) / 10.0  # kN/cm²
    x_lim = bx_lim * d_cm
    return fcd * b_cm * x_lim * (d_cm - 0.4 * x_lim), x_lim


def _denom_as2(d_cm: float, d_lin: float, contexto: str) -> float:
    """EP-01.4: guarda `d − d' > 0` para o braço da armadura dupla.

    O fallback silencioso de denominador (0,1 cm) gerava As,req gigante ou
    negativo sem explicar a causa. A seção rasa demais para acomodar
    armadura de compressão é recusada com erro legível.
    """
    denom = d_cm - d_lin
    if denom <= 0:
        raise ValueError(
            f"Seção recusada: braço da armadura dupla não positivo "
            f"(d − d' = {denom:.2f} cm ≤ 0). A seção é rasa demais para "
            f"acomodar armadura de compressão; aumente h ou reduza "
            f"cobrimento/bitola. Contexto: {contexto}"
        )
    return denom


def validar_geometria(
    h_cm: float,
    bw_cm: float,
    cob_mm: float,
    diam_estribo_mm: float,
    diam_barra_mm: float,
    fck_mpa: float | None = None,
) -> str | None:
    """A9: valida geometria antes de calcular. Retorna mensagem de erro ou None.

    Criterios minimos:
    - h > 0, bw > 0
    - d = h - d' > 0 (altura util positiva)
    - h >= 5 cm (minimo pratico para viga)
    - bw >= 5 cm (minimo normativo)
    - diametros > 0
    - fck > 0 (EP-01.4: validado quando fornecido; fck=0 causava
      ZeroDivisionError no laço de bitola)
    """
    if fck_mpa is not None and fck_mpa <= 0:
        return f"fck={fck_mpa} MPa deve ser positivo (resistência do concreto)."
    if h_cm <= 0:
        return f"Altura h={h_cm} cm deve ser positiva."
    if h_cm < 5:
        return f"Altura h={h_cm} cm muito pequena (minimo 5 cm)."
    if bw_cm <= 0:
        return f"Largura bw={bw_cm} cm deve ser positiva."
    if bw_cm < 5:
        return f"Largura bw={bw_cm} cm muito pequena (minimo 5 cm)."
    if cob_mm <= 0:
        return f"Cobrimento cob={cob_mm} mm deve ser positivo."
    if diam_estribo_mm <= 0:
        return f"Estribo phi={diam_estribo_mm} mm deve ser positivo."
    if diam_barra_mm <= 0:
        return f"Barra phi={diam_barra_mm} mm deve ser positivo."

    d_lin = _d_linha_estimada_cm(cob_mm, diam_estribo_mm, diam_barra_mm)
    d_cm = altura_util_cm(h_cm, cob_mm, diam_estribo_mm, diam_barra_mm)
    if d_cm <= 0:
        return (
            f"Altura util d={d_cm:.1f} cm invalida. "
            f"d'={d_lin:.1f} cm (cob={cob_mm}mm + estribo={diam_estribo_mm}mm + barra/2={diam_barra_mm / 2:.1f}mm). "
            f"Aumente h ou reduza cobrimento/bitola."
        )
    return None


def rho_min(fck: float) -> float:
    """Taxa mínima de armadura de flexão."""
    fck_vals = sorted(RHO_MIN_TABLE.keys())
    closest = min(fck_vals, key=lambda x: abs(x - fck))
    return RHO_MIN_TABLE[closest]


def asw_min_cm2_m(fck: float, bw_cm: float, fyk_estribo_kn_cm2: float = 50) -> float:
    """Asw/s mínimo (cm²/m) para estribos.

    A tabela ASW_S_TABLE_CA50 armazena:
      [0] = ρ_min em % (apenas referência)
      [1] = Asw_min/s por cm de bw para CA-50 (cm²/m/cm)
      [2] = Asw_min/s por cm de bw para CA-60 (cm²/m/cm)

    EP-01.8: o fyk do estribo entra em kN/cm² (CA-50=50, CA-60=60) e o
    limiar é coerente com a unidade. Antes o limiar estava em MPa (500)
    sobre valores em kN/cm² — sempre verdadeiro, a coluna CA-60 nunca era
    usada.
    """
    fck_key = min(ASW_S_TABLE_CA50.keys(), key=lambda x: abs(x - fck))
    _, ca50, ca60 = ASW_S_TABLE_CA50[fck_key]
    rho = ca50 if fyk_estribo_kn_cm2 <= 50 else ca60
    return rho * bw_cm


def calcular_armadura_pele(
    h_cm: float,
    bw_cm: float,
    cob_mm: float,
    phi_estribo_mm: float,
    phi_barra_mm: float,
) -> dict:
    """Calcula armadura de pele para vigas com h >= 60 cm.

    Conforme NBR 6118:2023, item 17.3.5.2.3:
    - Vigas com h >= 60 cm exigem armadura lateral (de pele)
    - Taxa minima: 0,10% x A_c,alma por face (limite 5 cm²/m por face)
    - Espacamento maximo vertical: min(20 cm, d/3)

    Retorna dict com:
        requer: bool
        as_pele_min_face_cm2: area minima por face (cm²)
        as_pele_adotada_face_cm2: area adotada por face (cm²)
        n_barras_face: numero de barras por face lateral
        phi_pele_mm: diametro das barras de pele
        s_max_cm: espacamento maximo vertical
        s_adotado_cm: espacamento adotado
        tabela_phis: lista de (phi_mm, n_barras, s_cm, as_cm2, cabe) para UI
    """
    LIMIAR_PELE_CM = 60.0
    # EP-02.6: bitolas comerciais de CA-50/CA-60, em ordem crescente. O φ5 mm
    # não é barra comercial de armadura e foi removido (o fallback silencioso
    # para 5 mm foi eliminado).
    PHI_OPCOES = [6.3, 8.0, 10.0, 12.5, 16.0]

    if h_cm < LIMIAR_PELE_CM:
        return {
            "requer": False,
            "as_pele_min_face_cm2": 0.0,
            "as_pele_adotada_face_cm2": 0.0,
            "n_barras_face": 0,
            "phi_pele_mm": phi_barra_mm,
            "s_max_cm": 0.0,
            "s_adotado_cm": 0.0,
            "tabela_phis": [],
        }

    # Altura util: inclui o raio da barra longitudinal (EP-02.6)
    d_cm = altura_util_cm(h_cm, cob_mm, phi_estribo_mm, phi_barra_mm)

    # Espacamento maximo vertical entre barras de pele (NBR 6118:17.3.5.2.3)
    s_max = min(20.0, d_cm / 3)  # cm

    # Area minima de pele por face: 0,10% x A_c,alma
    # Limite: nao precisa superar 5 cm²/m por face
    ac_alma = bw_cm * h_cm  # cm²
    as_pele_min_face = min(0.001 * ac_alma, 5.0 * h_cm / 100)  # cm² por face

    # Altura interna do estribo (dentro do estribo, de face a face)
    h_interna = h_cm - 2 * (cob_mm / 10 + phi_estribo_mm / 10)  # cm
    # n por espacamento: s = h_interna / (n+1) <= s_max -> n >= h_interna/s_max - 1
    n_por_espac = max(1, math.ceil(h_interna / s_max - 1)) if h_interna > 0 else 1

    # Calcular para cada diametro da lista (para UI escolher)
    tabela_phis = []
    for phi in PHI_OPCOES:
        area_phi = area_barra(phi)  # cm²
        n_por_area = math.ceil(as_pele_min_face / area_phi) if area_phi > 0 else 1
        n = max(n_por_espac, n_por_area)
        as_adot = n * area_phi

        # Espacamento adotado: s = h_interna / (n+1) — uniforme canto-barra-barra-canto
        s_adot = h_interna / (n + 1) if n > 0 else 0

        # NBR 6118:17.3.5.2.3: espaçamento ≤ 20 cm em cada face. Não há
        # exigência normativa de φ_pele ≤ φ_estribo (essa restrição extra
        # era o que forçava o fallback para φ5). Com 1 barra, a distância
        # às bordas é h_interna/2 e o próprio n_por_espac garante ≤ s_max.
        cabe = s_adot <= s_max

        tabela_phis.append(
            {
                "phi_mm": phi,
                "n_barras_face": n,
                "s_cm": round(s_adot, 1),
                "as_cm2": round(as_adot, 3),
                "cabe": cabe,
            }
        )

    # Adotar o menor diâmetro comercial que atenda à área mínima e ao
    # espaçamento. Sem fallback silencioso: se nenhum atender, é erro.
    melhor = None
    for item in tabela_phis:
        if item["cabe"] and item["as_cm2"] >= as_pele_min_face:
            melhor = item
            break
    if not melhor:
        raise ValueError(
            "Armadura de pele: nenhuma bitola comercial "
            f"({', '.join(f'{p:g}' for p in PHI_OPCOES)} mm) atende a "
            f"As,pele,min={as_pele_min_face:.3f} cm²/face e s_max={s_max:.1f} cm "
            f"para h={h_cm:g} cm, bw={bw_cm:g} cm. Aumente a seção ou reduza o "
            "cobrimento/bitola."
        )
    phi_pele_mm = melhor["phi_mm"]
    n_barras_face = melhor["n_barras_face"]
    as_adotada_face = melhor["as_cm2"]
    s_adotado = melhor["s_cm"]

    return {
        "requer": True,
        "as_pele_min_face_cm2": round(as_pele_min_face, 3),
        "as_pele_adotada_face_cm2": round(as_adotada_face, 3),
        "n_barras_face": n_barras_face,
        "phi_pele_mm": phi_pele_mm,
        "s_max_cm": round(s_max, 1),
        "s_adotado_cm": round(s_adotado, 1),
        "tabela_phis": tabela_phis,
    }


# ── Dimensionamento à Flexão – Viga Retangular ───────────────────────────────
@dataclass
class ResultadoFlexao:
    momento_kNm: float
    tipo: str  # "POSITIVO" ou "NEGATIVO"
    kc: float
    a: float
    b: float
    x1: float
    x2: float
    bx: float
    bx_passa: str  # "SIM" ou "NÃO"
    x_cm: float | None  # None quando bx é sentinela (seção insuficiente)
    ks: float
    as_req_cm2: float
    asmin_cm2: float
    as_necessaria_cm2: float
    diametro_mm: float
    qtd_barras: int
    eh_min_real: float
    eh_passa: str
    barras_suportadas: int
    eh_suportado: float
    barras_cima: int
    cob_mm: float
    espaco_disp_cm: float
    as_lista_barras: list[float]  # área por diâmetro (cm²)
    # Armadura de pele (h >= 60 cm, NBR 6118:17.3.5.2.3)
    requer_pele: bool = False
    n_barras_pele_face: int = 0
    as_pele_face_cm2: float = 0.0
    phi_pele_mm: float = 0.0
    s_pele_cm: float = 0.0
    as_pele_min_face_cm2: float = 0.0
    s_pele_max_cm: float = 0.0
    tabela_pele: list = None  # lista de dicts com phi/n/s/as/cabe
    alerta: str = ""  # mensagem de alerta (dominio nao passa, etc)
    armadura_dupla: bool = False  # indica se usa compressão
    as_linha_cm2: float = 0.0  # armadura de compressão (As')
    as_linha_adotada: float = 0.0  # As' adotada
    md_limite_knm: float = 0.0  # momento limite sem compressão
    md_excedente_knm: float = 0.0  # momento excedente (Md - Md_lim)
    as_adotado_cm2: float = 0.0
    d_cm_real: float = 0.0
    camadas_adotadas: int = 1
    status_bitola: str = "CABE"
    # EP-01.2: convergência declarada do laço de bitola (False = recusado)
    convergiu: bool = True
    layout_convergido: object | None = None
    tabela_bitolas: list = None

    def __post_init__(self):
        if self.tabela_pele is None:
            self.tabela_pele = []
        if self.tabela_bitolas is None:
            self.tabela_bitolas = []


@dataclass
class ResultadoBitola:
    diametro_mm: float
    qtd_barras: int
    as_adotado_cm2: float
    as_req_cm2: float
    d_inicial_cm: float
    d_real_cm: float
    camadas: int
    status_bitola: str
    eh_real_mm: float
    layout: SectionLayoutData | None
    iteracoes: int
    cabe: bool
    # EP-01.2: o laço de bitola declara a própria convergência. False quando
    # esgotou max_iter sem |d₀ − d_real| < tol ou quando a sequência de d
    # oscilou (não-monótona). Resultado com convergiu=False não é adotável.
    convergiu: bool = False


def dimensionar_bitola_iterativa(
    h_cm: float,
    bw_calculo_cm: float,
    cob_mm: float,
    diam_estribo_mm: float,
    diam_barra_mm: float,
    fck_mpa: float,
    fyk_kn_cm2: float,
    Md_kNm: float,
    bw_detalhamento_cm: float | None = None,
    d_max_agregado_mm: float = 19.0,
    max_iter: int = 5,
    tol_mm: float = 1.0,
    is_t: bool = False,
    bf_cm: float = 0.0,
    hf_cm: float = 0.0,
) -> ResultadoBitola:
    """Realiza o loop de convergência iterativa para encontrar a armadura e o detalhamento geométrico."""
    if bw_detalhamento_cm is None:
        bw_detalhamento_cm = bw_calculo_cm

    detailer = BeamDetailer()
    d_lin_est = _d_linha_estimada_cm(cob_mm, diam_estribo_mm, diam_barra_mm)
    d_cm = altura_util_cm(h_cm, cob_mm, diam_estribo_mm, diam_barra_mm)
    d_inicial_cm = d_cm

    iteracoes_feitas = 0
    layout_final = None
    as_req_final = 0.0
    qtd_barras = 0
    d_real_historico: list[float] = []
    convergiu_por_tol = False

    for it in range(1, max_iter + 1):
        iteracoes_feitas = it

        Md_kNcm = abs(Md_kNm) * 100.0

        fyd = fyd_kn_cm2(fyk_kn_cm2)
        bx_min = _bx_lim_ductilidade(fck_mpa)
        md_lim_kNcm, x_lim_cm = _momento_limite_ln(fck_mpa, bw_calculo_cm, d_cm, bx_min)

        if Md_kNcm > md_lim_kNcm:
            # Armadura dupla mantém a linha neutra no limite de ductilidade.
            as1 = md_lim_kNcm / (fyd * (d_cm - 0.4 * x_lim_cm))
            d_linha_cm = _d_linha_dupla(
                h_cm,
                bw_calculo_cm,
                cob_mm,
                diam_estribo_mm,
                diam_barra_mm,
                Md_kNcm - md_lim_kNcm,
                fyd,
                d_cm,
                d_lin_est,
                is_t=is_t,
                bf_cm=bf_cm,
                hf_cm=hf_cm,
            )
            as2, _as_linha_req = _as2_as_linha_dupla(
                Md_kNcm - md_lim_kNcm,
                fyd,
                d_cm,
                d_linha_cm,
                x_lim_cm,
                bw_calculo_cm,
                h_cm,
                is_t=is_t,
                bf_cm=bf_cm,
                hf_cm=hf_cm,
                contexto=(
                    f"Md={Md_kNm:+.1f} kN·m, seção "
                    f"{bw_calculo_cm:.0f}×{h_cm:.0f} cm, Ø{diam_barra_mm:g} mm"
                ),
            )
            as_req = as1 + as2
        else:
            x_ln, _x1, _x2 = _resolver_ln(Md_kNcm, fck_mpa, bw_calculo_cm, d_cm)
            if x_ln is None or x_ln <= 0:
                as_req = 0.0
            else:
                as_req = Md_kNcm / (fyd * (d_cm - 0.4 * x_ln))

        asmin = rho_min(fck_mpa) * bw_detalhamento_cm * h_cm / 100.0
        as_necessaria = max(as_req, asmin)
        as_req_final = as_req

        a_bar = area_barra(diam_barra_mm)
        qtd_barras = math.ceil(as_necessaria / a_bar) if a_bar > 0 else 0
        # Limite de seguran?a contra loop patol?gico do detalhador; se??es com
        # milhares de barras s?o invi?veis de qualquer forma.
        qtd_barras = min(max(1, qtd_barras), 1000)

        try:
            inp = BeamDetailingInput(
                bw=bw_detalhamento_cm * 10.0,
                h=h_cm * 10.0,
                c_nom=cob_mm,
                phi_estribo=diam_estribo_mm,
                phi_barra=diam_barra_mm,
                d_max_agregado=d_max_agregado_mm,
                total_bars=qtd_barras,
            )
            layout = detailer.detail(inp)
        except ValueError:
            return ResultadoBitola(
                diametro_mm=diam_barra_mm,
                qtd_barras=qtd_barras,
                as_adotado_cm2=round(qtd_barras * a_bar, 3),
                as_req_cm2=round(as_req_final, 3),
                d_inicial_cm=round(d_inicial_cm, 2),
                d_real_cm=round(d_cm, 2),
                camadas=0,
                status_bitola="NÃO CABE",
                eh_real_mm=0.0,
                layout=None,
                iteracoes=iteracoes_feitas,
                cabe=False,
            )

        layout_final = layout
        d_real_cm = layout.d_efetiva / 10.0
        d_real_historico.append(d_real_cm)

        if abs(d_cm * 10.0 - layout.d_efetiva) < tol_mm:
            d_cm = d_real_cm
            convergiu_por_tol = True
            break
        d_cm = d_real_cm

    # EP-01.2: convergência declarada — |d₀ − d_real| < tol E sequência de d
    # sem oscilação (diferenças sucessivas nunca mudam de sinal). O laço que
    # oscila entre dois layouts aceitáveis (4↔5 barras, d 54.24↔54.59 cm)
    # esgotava max_iter e adotava a última iteração em silêncio.
    convergiu = convergiu_por_tol and _d_sem_oscilacao(d_real_historico)

    a_bar = area_barra(diam_barra_mm)
    if layout_final is None:
        return ResultadoBitola(
            diametro_mm=diam_barra_mm,
            qtd_barras=qtd_barras,
            as_adotado_cm2=round(qtd_barras * a_bar, 3),
            as_req_cm2=round(as_req_final, 3),
            d_inicial_cm=round(d_inicial_cm, 2),
            d_real_cm=round(d_cm, 2),
            camadas=0,
            status_bitola="NÃO CABE",
            eh_real_mm=0.0,
            layout=None,
            iteracoes=iteracoes_feitas,
            cabe=False,
            convergiu=False,
        )

    if not convergiu:
        # Recusar a seção: nunca devolver o último iterado como resultado.
        return ResultadoBitola(
            diametro_mm=diam_barra_mm,
            qtd_barras=qtd_barras,
            as_adotado_cm2=0.0,
            as_req_cm2=round(as_req_final, 3),
            d_inicial_cm=round(d_inicial_cm, 2),
            d_real_cm=round(d_cm, 2),
            camadas=0,
            status_bitola="NÃO CONVERGIU",
            eh_real_mm=0.0,
            layout=None,
            iteracoes=iteracoes_feitas,
            cabe=False,
            convergiu=False,
        )

    camadas = layout_final.layer_count
    eh_real_mm = min(lyr.h_spacing for lyr in layout_final.layers) if layout_final.layers else 0.0

    if camadas == 1:
        status = "CABE"
        cabe = True
    elif camadas == 2:
        status = "2 CAMADAS"
        cabe = True
    elif camadas == 3:
        status = "3 CAMADAS"
        cabe = True
    else:
        status = "NÃO CABE"
        cabe = False

    return ResultadoBitola(
        diametro_mm=diam_barra_mm,
        qtd_barras=qtd_barras,
        as_adotado_cm2=round(qtd_barras * a_bar, 3),
        as_req_cm2=round(as_req_final, 3),
        d_inicial_cm=round(d_inicial_cm, 2),
        d_real_cm=round(d_cm, 2),
        camadas=camadas,
        status_bitola=status,
        eh_real_mm=round(eh_real_mm, 2),
        layout=layout_final,
        iteracoes=iteracoes_feitas,
        cabe=cabe,
        convergiu=True,
    )


def _d_sem_oscilacao(valores: list[float]) -> bool:
    """EP-01.2: True se a sequência de d não oscila.

    Oscilação = as diferenças sucessivas mudam de sinal (ex.: d alternando
    entre dois layouts com contagem de barras diferente). Zeros são
    ignorados; sequências com menos de 2 passos são triviais.
    """
    diffs = [b - a for a, b in zip(valores, valores[1:], strict=False) if abs(b - a) > 1e-9]
    if len(diffs) < 2:
        return True
    sinais = [1 if d > 0 else -1 for d in diffs]
    return all(s == sinais[0] for s in sinais)


def _validar_invariantes_flexao(
    *,
    contexto: str,
    as_req_cm2: float,
    as_adotado_cm2: float,
    d_cm: float,
    qtd_barras: int,
    area_barra_cm2: float,
    cabe: bool,
    status_bitola: str,
) -> None:
    """EP-01.3: invariantes de integridade antes de emitir um resultado.

    Garante que as duas fontes (As,req recalculado com a d convergida e
    qtd_barras/as_adotado do laço de bitola) estão em concordância. Se
    qualquer invariante falhar em um resultado que fingiria "CABE",
    levanta ValueError com contexto — nunca um subdimensionamento
    silencioso.

    Invariantes:
      - as_req_cm2 ≥ 0
      - d_cm > 0
      - qtd_barras ≥ 1 implica as_adotado_cm2 == qtd_barras · A_φ
      - as_adotado_cm2 ≥ as_req_cm2, salvo status explícito de exceção
        ("NÃO CABE" / "NÃO CONVERGIU")
    """
    erros: list[str] = []
    if as_req_cm2 < 0:
        erros.append(f"As,req = {as_req_cm2:.3f} cm² < 0")
    if d_cm <= 0:
        erros.append(f"d = {d_cm:.2f} cm ≤ 0")
    if qtd_barras >= 1 and abs(as_adotado_cm2 - qtd_barras * area_barra_cm2) > 0.011:
        erros.append(
            f"qtd_barras: As,adotado = {as_adotado_cm2:.3f} cm² não corresponde a "
            f"{qtd_barras} barras × {area_barra_cm2:.4f} cm² = "
            f"{qtd_barras * area_barra_cm2:.3f} cm²"
        )
    status_recusado = status_bitola in ("NÃO CABE", "NÃO CONVERGIU")
    if not status_recusado and as_adotado_cm2 < as_req_cm2 - 1e-6:
        erros.append(
            f"subdimensionamento: As,adotado = {as_adotado_cm2:.3f} cm² < "
            f'As,req = {as_req_cm2:.3f} cm² com status "{status_bitola}"'
        )
    if erros:
        raise ValueError(
            "Seção recusada pelo motor (invariante de integridade violada): "
            + "; ".join(erros)
            + f". Contexto: {contexto}"
        )


def calcular_flexao_viga_comum(
    h_cm: float,
    bw_cm: float,
    caa: int,
    fck_mpa: float,
    diam_estribo_mm: float,
    diam_barra_mm: float,
    fyk_kn_cm2: float,
    momentos: list[float],
    gamma_f: float = GAMMA_F_RESTO,
    d_max_agregado_mm: float = 19.0,
) -> list[ResultadoFlexao]:
    """Calcula flexao para uma secao retangular com multiplos momentos.

    Os momentos sao recebidos como valores caracteristicos (sem majoracao).
    O coeficiente gamma_f e aplicado internamente.

    Raises:
        ValueError: se geometria invalida (h<=0, bw<5, d<=0, etc).
    """

    # A9: validacao de geometria antes de calcular
    cob_mm = CAA_DATA[caa]["cobrimento"]
    erro_geo = validar_geometria(
        h_cm, bw_cm, cob_mm, diam_estribo_mm, diam_barra_mm, fck_mpa=fck_mpa
    )
    if erro_geo:
        raise ValueError(erro_geo)

    # Parametros da CAA
    d_lin = _d_linha_estimada_cm(cob_mm, diam_estribo_mm, diam_barra_mm)
    d_cm = altura_util_cm(h_cm, cob_mm, diam_estribo_mm, diam_barra_mm)

    rho_min_val = rho_min(fck_mpa)
    as_diametros = [area_barra(d) for d in DIAM_BARRAS]

    # Armadura de pele (NBR 6118:17.3.5.2.3) — calculada uma vez (independe do momento)
    pele = calcular_armadura_pele(h_cm, bw_cm, cob_mm, diam_estribo_mm, diam_barra_mm)

    resultados = []
    for Mk_kNm in momentos:
        if Mk_kNm is None or Mk_kNm == 0:
            resultados.append(None)
            continue

        # Majoracao: entrada caracteristica, aplicamos gamma_f aqui
        Md_kNm = Mk_kNm * gamma_f
        tipo = "POSITIVO" if Mk_kNm > 0 else "NEGATIVO"

        # Loop iterativo de convergência para a bitola selecionada
        res_bitola = dimensionar_bitola_iterativa(
            h_cm=h_cm,
            bw_calculo_cm=bw_cm,
            cob_mm=cob_mm,
            diam_estribo_mm=diam_estribo_mm,
            diam_barra_mm=diam_barra_mm,
            fck_mpa=fck_mpa,
            fyk_kn_cm2=fyk_kn_cm2,
            Md_kNm=Md_kNm,
            bw_detalhamento_cm=bw_cm,
            d_max_agregado_mm=d_max_agregado_mm,
        )

        tabela_bitolas = []
        for d_cand in DIAM_BARRAS_LONG:
            if d_cand == diam_barra_mm:
                tabela_bitolas.append(res_bitola)
            else:
                res_cand = dimensionar_bitola_iterativa(
                    h_cm=h_cm,
                    bw_calculo_cm=bw_cm,
                    cob_mm=cob_mm,
                    diam_estribo_mm=diam_estribo_mm,
                    diam_barra_mm=d_cand,
                    fck_mpa=fck_mpa,
                    fyk_kn_cm2=fyk_kn_cm2,
                    Md_kNm=Md_kNm,
                    bw_detalhamento_cm=bw_cm,
                    d_max_agregado_mm=d_max_agregado_mm,
                )
                tabela_bitolas.append(res_cand)

        # Adota a altura útil convergida no cálculo final
        d_cm = res_bitola.d_real_cm
        if d_cm <= 0:
            raise ValueError(
                f"Altura útil efetiva não positiva (d={d_cm:.2f} cm) para "
                f"Mk={Mk_kNm:+.1f} kN·m (Md={Md_kNm:.1f} kN·m, γf={gamma_f}) "
                f"na seção {bw_cm:.0f}×{h_cm:.0f} cm. A seção não suporta a "
                f"armadura; aumente h ou bw."
            )

        Md_kNcm = abs(Md_kNm) * 100
        kc = (bw_cm * d_cm**2) / Md_kNcm if Md_kNcm != 0 else 0

        fyd = fyd_kn_cm2(fyk_kn_cm2)  # kN/cm² (fyk entra em kN/cm²)
        bx_min = _bx_lim_ductilidade(fck_mpa)
        md_lim_kNcm, x_lim_cm = _momento_limite_ln(fck_mpa, bw_cm, d_cm, bx_min)

        # Equilíbrio NBR em x (não em βx): 0,4·x² − d·x + Md/(fcd·b) = 0
        a_coef = 0.4
        b_coef = -d_cm
        x1 = x2 = 0.0

        armadura_dupla = False
        as_linha_cm2 = 0.0
        as_linha_adotada = 0.0
        md_limite_knm = md_lim_kNcm / 100.0
        md_excedente_knm = 0.0
        dominio_4 = False

        if Md_kNcm > md_lim_kNcm:
            armadura_dupla = True
            md_excedente_knm = (Md_kNcm - md_lim_kNcm) / 100.0
            ks = 1.0 / (fyd * (1.0 - 0.4 * bx_min))
            as1 = md_lim_kNcm / (fyd * (d_cm - 0.4 * x_lim_cm))
            contexto_dupla = (
                f"Mk={Mk_kNm:+.1f} kN·m (Md={Md_kNm:.1f} kN·m, γf={gamma_f}), "
                f"seção {bw_cm:.0f}×{h_cm:.0f} cm, Ø{diam_barra_mm:g} mm, "
                f"cob={cob_mm:.0f} mm, CAA {caa}"
            )
            d_linha_cm = _d_linha_dupla(
                h_cm,
                bw_cm,
                cob_mm,
                diam_estribo_mm,
                diam_barra_mm,
                Md_kNcm - md_lim_kNcm,
                fyd,
                d_cm,
                d_lin,
            )
            as2, as_linha_cm2 = _as2_as_linha_dupla(
                Md_kNcm - md_lim_kNcm,
                fyd,
                d_cm,
                d_linha_cm,
                x_lim_cm,
                bw_cm,
                h_cm,
                contexto=contexto_dupla,
            )
            as_req = as1 + as2
            bx = bx_min
            x_cm = x_lim_cm
            x1 = x2 = x_lim_cm
            bx_passa = "SIM"
            alerta = (
                f"Armadura dupla utilizada (bx={bx_min:.2f}). "
                f"As = {as_req:.2f} cm² | As' = {as_linha_cm2:.2f} cm²."
            )
        else:
            x_ln, x1, x2 = _resolver_ln(Md_kNcm, fck_mpa, bw_cm, d_cm)
            if x_ln is None or x_ln <= 0:
                bx = 999.0
                bx_passa = "NÃO"
                ks = 0.0
                as_req = 0.0
                x_cm = 999.0 * d_cm
                alerta = (
                    f"Seção insuficiente para o momento Mk={Mk_kNm:+.1f} kN·m "
                    f"(Md={Md_kNm:.1f} kN·m, γf={gamma_f}). "
                    f"KC={kc:.2f} abaixo do mínimo para a seção "
                    f"{bw_cm:.0f}×{h_cm:.0f} cm. "
                    f"Soluções: aumente h ou bw, aumente fck, ou reduza o momento."
                )
            else:
                bx = x_ln / d_cm
                x_cm = x_ln
                ks = 1.0 / (fyd * (1.0 - 0.4 * bx))
                as_req = Md_kNcm / (fyd * (d_cm - 0.4 * x_ln))
                if classificar_dominio(bx) == "DOMINIO_4":
                    dominio_4 = True
                    bx_passa = "NÃO"
                    alerta = (
                        f"Domínio 4 (bx={bx:.3f} > {BX_DOMINIO_4:.3f}): seção "
                        f"recusada — a armadura de tração não escoa (ruptura "
                        f"frágil). Aumente h/bw/fck ou adote armadura de "
                        f"compressão. Mk={Mk_kNm:+.1f} kN·m."
                    )
                else:
                    bx_passa = "SIM" if bx <= bx_min + 1e-9 else "NÃO"
                    alerta = ""

        asmin = rho_min_val * bw_cm * h_cm / 100  # cm²
        as_necessaria = max(as_req, asmin)

        # Número de barras pelo diâmetro escolhido (convergido)
        qtd_barras = res_bitola.qtd_barras
        area_barra_d = area_barra(diam_barra_mm)

        # Adotar armadura de compressão (As') se necessário
        if armadura_dupla:
            qtd_barras_linha = math.ceil(as_linha_cm2 / area_barra_d) if area_barra_d > 0 else 0
            as_linha_adotada = qtd_barras_linha * area_barra_d
        else:
            as_linha_adotada = 0.0

        # Verificação de espaçamento horizontal com base no detalhamento geométrico convergido
        espaco_disp = bw_cm - 2 * (cob_mm / 10) - 2 * (diam_estribo_mm / 10)
        eh_min = max(2.0, diam_barra_mm / 10, 1.2 * d_max_agregado_mm / 10)
        eh_passa = "SIM" if res_bitola.cabe else "NÃO"
        if res_bitola.layout and res_bitola.layout.layers:
            eh_real = res_bitola.eh_real_mm / 10.0
            qtd_barras_1cam = res_bitola.layout.layers[0].bar_count
            barras_cima = qtd_barras - qtd_barras_1cam
        else:
            eh_real = 0.0
            qtd_barras_1cam = qtd_barras
            barras_cima = 0

        # EP-02.2: domínio 4 é recusa explícita (nunca "CABE" com As,min)
        status_final = "NÃO CABE" if dominio_4 else res_bitola.status_bitola
        convergiu_final = res_bitola.convergiu and not dominio_4

        # Armadura de pele (NBR 6118:17.3.5.2.3) — já calculada fora do loop
        # EP-01.3: invariantes de integridade antes de emitir o resultado
        _validar_invariantes_flexao(
            contexto=(
                f"Mk={Mk_kNm:+.1f} kN·m (Md={Md_kNm:.1f} kN·m, γf={gamma_f}), "
                f"seção {bw_cm:.0f}×{h_cm:.0f} cm, Ø{diam_barra_mm:g} mm, "
                f"cob={cob_mm:.0f} mm, CAA {caa}"
            ),
            as_req_cm2=round(as_req, 3),
            as_adotado_cm2=round(res_bitola.as_adotado_cm2, 3),
            d_cm=round(res_bitola.d_real_cm, 2),
            qtd_barras=res_bitola.qtd_barras,
            area_barra_cm2=area_barra_d,
            cabe=res_bitola.cabe,
            status_bitola=status_final,
        )

        resultados.append(
            ResultadoFlexao(
                momento_kNm=abs(Md_kNm),
                tipo=tipo,
                kc=round(kc, 3),
                a=round(a_coef, 6),
                b=round(b_coef, 6),
                x1=round(x1, 4),
                x2=round(x2, 4),
                bx=round(bx, 4),
                bx_passa=bx_passa,
                x_cm=round(x_cm, 2) if x_cm < 999.0 else None,
                ks=round(ks, 3),
                as_req_cm2=round(as_req, 3),
                asmin_cm2=round(asmin, 3),
                as_necessaria_cm2=round(as_necessaria, 3),
                diametro_mm=diam_barra_mm,
                qtd_barras=qtd_barras,
                eh_min_real=round(eh_min, 2),
                eh_passa=eh_passa,
                eh_suportado=round(eh_real, 2),
                barras_suportadas=qtd_barras_1cam,
                barras_cima=barras_cima,
                cob_mm=cob_mm,
                espaco_disp_cm=round(espaco_disp, 2),
                as_lista_barras=as_diametros,
                requer_pele=pele["requer"],
                n_barras_pele_face=pele["n_barras_face"],
                as_pele_face_cm2=pele["as_pele_adotada_face_cm2"],
                phi_pele_mm=pele["phi_pele_mm"],
                s_pele_cm=pele["s_adotado_cm"],
                as_pele_min_face_cm2=pele["as_pele_min_face_cm2"],
                s_pele_max_cm=pele["s_max_cm"],
                tabela_pele=pele.get("tabela_phis", []),
                alerta=alerta,
                armadura_dupla=armadura_dupla,
                as_linha_cm2=round(as_linha_cm2, 3),
                as_linha_adotada=round(as_linha_adotada, 3),
                md_limite_knm=round(md_limite_knm, 3),
                md_excedente_knm=round(md_excedente_knm, 3),
                as_adotado_cm2=round(res_bitola.as_adotado_cm2, 3),
                d_cm_real=round(res_bitola.d_real_cm, 2),
                camadas_adotadas=res_bitola.camadas,
                status_bitola=status_final,
                convergiu=convergiu_final,
                layout_convergido=res_bitola.layout,
                tabela_bitolas=tabela_bitolas,
            )
        )

    return resultados


# ── Dimensionamento ao Cisalhamento ──────────────────────────────────────────
@dataclass
class ResultadoCisalhamento:
    vsd_kn: float
    vsd_verdadeiro_kn: float
    fcd_mpa: float
    vrd2_kn: float
    passa_vrd2: str
    fctm_mpa: float
    fctkinf_mpa: float
    fctd_kn_cm2: float
    vc_kn: float
    vsw_kn: float
    positivo_negativo: str
    verificacao: str
    asw_s_min_cm2_m: float
    asw_usado_cm2_m: float
    diam_estribo_mm: float
    dist_estribos_cm: float
    s_max_cm: float
    passa_smax: str


def calcular_cisalhamento_viga_comum(
    h_cm: float,
    bw_cm: float,
    fck_mpa: float,
    diam_estribo_mm: float,
    diam_barra_mm: float,
    fyk_estribo_kn_cm2: float,
    fyk_barra_kn_cm2: float,
    caa: int,
    forcas_cortantes: list[float],
    gamma_f: float = GAMMA_F_RESTO,
) -> list[ResultadoCisalhamento]:
    """Calcula cisalhamento para uma secao retangular (largura da alma bw).

    As forcas cortantes sao recebidas como valores caracteristicos (com sinal,
    sem majorar). O coeficiente gamma_f e aplicado internamente sobre o modulo
    |V|.

    Raises:
        ValueError: se geometria invalida.
    """

    # A9: validacao de geometria
    cob_mm = CAA_DATA[caa]["cobrimento"]
    erro_geo = validar_geometria(
        h_cm, bw_cm, cob_mm, diam_estribo_mm, diam_barra_mm, fck_mpa=fck_mpa
    )
    if erro_geo:
        raise ValueError(erro_geo)

    d_cm = altura_util_cm(h_cm, cob_mm, diam_estribo_mm, diam_barra_mm)

    fcd = fcd_mpa(fck_mpa)  # MPa
    fctm = fctm_mpa(fck_mpa)
    fctkinf = fctkinf_mpa(fck_mpa)
    fctd = fctd_kn_cm2(fck_mpa)  # kN/cm²
    lam = lambda_f(fck_mpa)  # fator lambda (NBR 6118:17.4.2.2)

    # fywd do estribo em kN/cm² (fyk entra em kN/cm²: CA-60=60). Limite de 43.5 kN/cm² (435 MPa) conf. NBR 6118:17.4.2.3
    fywd_kn_cm2 = min(fyd_kn_cm2(fyk_estribo_kn_cm2), 43.5)

    area_estribo = area_barra(diam_estribo_mm)  # cm² (1 estribo = 2 ramos)
    asw_ramo = area_estribo * 2  # cm² (estribo com 2 ramos)

    # Asw/s mínimo
    asw_min = asw_min_cm2_m(fck_mpa, bw_cm, fyk_estribo_kn_cm2)

    resultados = []
    for Vk_kn in forcas_cortantes:
        if Vk_kn is None or Vk_kn == 0:
            resultados.append(None)
            continue

        # Majoracao + modulo: entrada caracteristica com sinal, usamos |V|*gamma_f
        Vsd_aplicado = abs(Vk_kn) * gamma_f  # kN

        # Resistência do concreto à compressão diagonal (Vrd2)
        vrd2 = 0.27 * lam * fcd * bw_cm * d_cm / 10  # kN

        # Vc (contribuição do concreto) — Modelo I (NBR 6118:17.4.2.2)
        vc = round(0.6 * fctd * bw_cm * d_cm, 2)  # kN

        # Vsw (contribuição do aço) — o que o concreto nao cobre
        vsw = Vsd_aplicado - vc if Vsd_aplicado > vc else 0

        # Verificação
        vsw_pos_neg = "POSITIVO" if vsw >= 0 else "NEGATIVO"
        verificacao = "OK" if vsw >= 0 else "NÃO IRÁ TRABALHAR"

        # Asw/s necessario (dimensionado pela cortante real, nao so minimo)
        # Asw/s = Vsw / (fywd * d)  (NBR 6118:17.4.2.3, Modelo I)
        # Vsw em kN, fywd em kN/cm², d em cm -> Asw/s em cm²/cm = cm²/m * 100
        if vsw > 0 and fywd_kn_cm2 > 0 and d_cm > 0:
            asw_req = vsw / (fywd_kn_cm2 * d_cm)  # cm²/cm
            asw_req_cm2_m = asw_req * 100  # cm²/m
        else:
            asw_req_cm2_m = 0.0

        # Asw/s adotado = max(necessario, minimo)
        asw_usado = max(asw_req_cm2_m, asw_min)  # cm²/m

        # Verificação de espaçamento máximo dos estribos (NBR 6118:18.3.3.2)
        if Vsd_aplicado <= 0.67 * vrd2:
            s_max = min(0.6 * d_cm, 30.0)
        else:
            s_max = min(0.3 * d_cm, 20.0)

        # Espacamento: s = (Asw ramo) / (Asw/s) * 100 (cm)
        # asw_ramo em cm², asw_usado em cm²/m -> s em cm
        dist_estribos = (asw_ramo * 100) / asw_usado if asw_usado > 0 else 999
        # EP-02.5: o espaçamento ADOTADO é limitado pelo s_max normativo.
        dist_estribos = min(dist_estribos, s_max)
        passa_smax = "SIM"

        resultados.append(
            ResultadoCisalhamento(
                vsd_kn=round(Vsd_aplicado, 2),
                vsd_verdadeiro_kn=Vk_kn,
                fcd_mpa=round(fcd, 3),
                vrd2_kn=round(vrd2, 2),
                passa_vrd2="SIM" if Vsd_aplicado < vrd2 else "NÃO",
                fctm_mpa=round(fctm, 3),
                fctkinf_mpa=round(fctkinf, 3),
                fctd_kn_cm2=round(fctd, 5),
                vc_kn=round(vc, 2),
                vsw_kn=round(vsw, 2),
                positivo_negativo=vsw_pos_neg,
                verificacao=verificacao,
                asw_s_min_cm2_m=round(asw_min, 3),
                asw_usado_cm2_m=round(asw_usado, 3),
                diam_estribo_mm=diam_estribo_mm,
                dist_estribos_cm=round(dist_estribos, 1),
                s_max_cm=round(s_max, 1),
                passa_smax=passa_smax,
            )
        )

    return resultados


# ── Viga T – Flexão ───────────────────────────────────────────────────────────
@dataclass
class ResultadoFlexaoT:
    momento_kNm: float
    tipo: str
    kc: float
    a: float
    b: float
    x1: float
    x2: float
    bx: float
    bx_passa: str
    x_cm: float | None  # None quando bx é sentinela (seção insuficiente)
    linha_neutra_condiz: str
    bf_efetivo_cm: float
    ks: float
    as_req_cm2: float
    asmin_cm2: float
    as_necessaria_cm2: float
    diametro_mm: float
    qtd_barras: int
    eh_min_real: float
    eh_passa: str
    # Novos campos para consistência com ResultadoFlexao
    barras_suportadas: int = 0
    eh_suportado: float = 0.0
    barras_cima: int = 0
    cob_mm: float = 0.0
    espaco_disp_cm: float = 0.0
    as_lista_barras: list[float] = None
    as_linha_cm2: float = 0.0
    as_linha_adotada: float = 0.0
    # Armadura de pele (h >= 60 cm, NBR 6118:17.3.5.2.3)
    requer_pele: bool = False
    n_barras_pele_face: int = 0
    as_pele_face_cm2: float = 0.0
    phi_pele_mm: float = 0.0
    s_pele_cm: float = 0.0
    as_pele_min_face_cm2: float = 0.0
    s_pele_max_cm: float = 0.0
    tabela_pele: list = None  # lista de dicts com phi/n/s/as/cabe
    alerta: str = ""  # mensagem de alerta (dominio nao passa, etc)
    as_adotado_cm2: float = 0.0
    d_cm_real: float = 0.0
    camadas_adotadas: int = 1
    status_bitola: str = "CABE"
    # EP-01.2: convergência declarada do laço de bitola (False = recusado)
    convergiu: bool = True
    layout_convergido: object | None = None
    tabela_bitolas: list = None

    def __post_init__(self):
        if self.tabela_pele is None:
            self.tabela_pele = []
        if self.tabela_bitolas is None:
            self.tabela_bitolas = []


def bf_efetivo_viga_t(
    bw_cm: float,
    bf_cm: float,
    b1esq_cm: float | None = None,
    b1dir_cm: float | None = None,
    lo_esq_cm: float | None = None,
    lo_dir_cm: float | None = None,
    bf1esq_cm: float | None = None,
    bf1dir_cm: float | None = None,
) -> float:
    """Largura efetiva da mesa (NBR 6118:2023, 15.5.2).

    bf,ef = min(bf, bw + b1esq + b1dir), com, para cada lado:
    - b1 ≤ 0,1·l0 (l0 = distância entre pontos de momento fletor nulo);
    - b1 ≤ 0,5·bf1 (bf1 = largura da mesa adjacente do mesmo lado, isto é,
      a distância livre até a viga/laje vizinha);
    - b1 ausente → 0,0 cm (bf,ef = bw; conservador).
    """
    b1e = max(0.0, b1esq_cm) if b1esq_cm is not None else 0.0
    b1d = max(0.0, b1dir_cm) if b1dir_cm is not None else 0.0

    if lo_esq_cm is not None and lo_esq_cm > 0:
        b1e = min(b1e, 0.1 * lo_esq_cm)
    if lo_dir_cm is not None and lo_dir_cm > 0:
        b1d = min(b1d, 0.1 * lo_dir_cm)
    if bf1esq_cm is not None and bf1esq_cm > 0:
        b1e = min(b1e, 0.5 * bf1esq_cm)
    if bf1dir_cm is not None and bf1dir_cm > 0:
        b1d = min(b1d, 0.5 * bf1dir_cm)

    return min(bf_cm, bw_cm + b1e + b1d)


def calcular_flexao_viga_t(
    h_cm: float,
    bw_cm: float,
    bf_cm: float,
    hf_cm: float,
    caa: int,
    fck_mpa: float,
    diam_estribo_mm: float,
    diam_barra_mm: float,
    fyk_kn_cm2: float,
    momentos: list[float],
    b1esq_cm: float | None = None,
    b1dir_cm: float | None = None,
    lo_esq_cm: float | None = None,
    lo_dir_cm: float | None = None,
    bf1esq_cm: float | None = None,
    bf1dir_cm: float | None = None,
    gamma_f: float = GAMMA_F_RESTO,
    d_max_agregado_mm: float = 19.0,
) -> list[ResultadoFlexaoT]:
    """Calcula flexao para secao de Viga T.

    Os momentos sao recebidos como valores caracteristicos (sem majoracao).
    O coeficiente gamma_f e aplicado internamente.

    Raises:
        ValueError: se geometria invalida (h<=0, bw<5, bf<hf, d<=0, etc).
    """

    # A9: validacao de geometria
    cob_mm = CAA_DATA[caa]["cobrimento"]
    erro_geo = validar_geometria(
        h_cm, bw_cm, cob_mm, diam_estribo_mm, diam_barra_mm, fck_mpa=fck_mpa
    )
    if erro_geo:
        raise ValueError(erro_geo)
    if bf_cm < bw_cm:
        raise ValueError(f"Mesa bf={bf_cm} cm menor que alma bw={bw_cm} cm (inconsistente).")
    if hf_cm >= h_cm:
        raise ValueError(f"Altura da mesa hf={hf_cm} cm >= h={h_cm} cm (mesa maior que viga).")

    d_lin = _d_linha_estimada_cm(cob_mm, diam_estribo_mm, diam_barra_mm)
    d_cm = altura_util_cm(h_cm, cob_mm, diam_estribo_mm, diam_barra_mm)

    bf_efetivo = bf_efetivo_viga_t(
        bw_cm,
        bf_cm,
        b1esq_cm,
        b1dir_cm,
        lo_esq_cm=lo_esq_cm,
        lo_dir_cm=lo_dir_cm,
        bf1esq_cm=bf1esq_cm,
        bf1dir_cm=bf1dir_cm,
    )
    rho_min_val = rho_min(fck_mpa)
    fck_conv = fck_mpa / 10  # MPa -> kN/cm² (formula empirica)
    fyd = fyd_kn_cm2(fyk_kn_cm2)  # kN/cm² (fyk entra em kN/cm²)

    # Armadura de pele (NBR 6118:17.3.5.2.3) — calculada uma vez (independe do momento)
    pele = calcular_armadura_pele(h_cm, bw_cm, cob_mm, diam_estribo_mm, diam_barra_mm)

    resultados = []
    for Mk_kNm in momentos:
        if Mk_kNm is None or Mk_kNm == 0:
            resultados.append(None)
            continue

        # Majoracao: entrada caracteristica, aplicamos gamma_f aqui
        Md_kNm = Mk_kNm * gamma_f
        tipo = "POSITIVO" if Mk_kNm > 0 else "NEGATIVO"

        bw_calc = bf_efetivo if Mk_kNm > 0 else bw_cm

        # Loop iterativo de convergência para a bitola selecionada
        res_bitola = dimensionar_bitola_iterativa(
            h_cm=h_cm,
            bw_calculo_cm=bw_calc,
            cob_mm=cob_mm,
            diam_estribo_mm=diam_estribo_mm,
            diam_barra_mm=diam_barra_mm,
            fck_mpa=fck_mpa,
            fyk_kn_cm2=fyk_kn_cm2,
            Md_kNm=Md_kNm,
            bw_detalhamento_cm=bw_cm,
            is_t=True,
            bf_cm=bf_cm,
            hf_cm=hf_cm,
            d_max_agregado_mm=d_max_agregado_mm,
        )

        tabela_bitolas = []
        for d_cand in DIAM_BARRAS_LONG:
            if d_cand == diam_barra_mm:
                tabela_bitolas.append(res_bitola)
            else:
                res_cand = dimensionar_bitola_iterativa(
                    h_cm=h_cm,
                    bw_calculo_cm=bw_calc,
                    cob_mm=cob_mm,
                    diam_estribo_mm=diam_estribo_mm,
                    diam_barra_mm=d_cand,
                    fck_mpa=fck_mpa,
                    fyk_kn_cm2=fyk_kn_cm2,
                    Md_kNm=Md_kNm,
                    bw_detalhamento_cm=bw_cm,
                    is_t=True,
                    bf_cm=bf_cm,
                    hf_cm=hf_cm,
                    d_max_agregado_mm=d_max_agregado_mm,
                )
                tabela_bitolas.append(res_cand)

        d_cm = res_bitola.d_real_cm
        if d_cm <= 0:
            raise ValueError(
                f"Altura útil efetiva não positiva (d={d_cm:.2f} cm) para "
                f"Mk={Mk_kNm:+.1f} kN·m (Md={Md_kNm:.1f} kN·m, γf={gamma_f}) "
                f"na seção T {bw_cm:.0f}×{h_cm:.0f} cm (bf={bf_cm:.0f} cm, "
                f"hf={hf_cm:.0f} cm). A seção não suporta a armadura; "
                f"aumente h ou bw."
            )

        eta = _eta_diagrama_retangular(fck_mpa)
        bx_min = _bx_lim_ductilidade(fck_mpa)
        fcd_kn_cm2 = fcd_mpa(fck_mpa) / 10.0
        Md_kNcm = abs(Md_kNm) * 100.0

        b_kc = bf_efetivo if Mk_kNm > 0 else bw_cm
        kc = (b_kc * d_cm**2) / Md_kNcm if Md_kNcm != 0 else 0

        a_coef = 0.4
        b_coef = -d_cm
        x1 = x2 = 0.0
        as_linha_cm2 = 0.0
        dominio_4 = False

        if Mk_kNm > 0:
            # 1. Equilíbrio tratando a seção como retangular de largura bf,ef.
            x_mesa, x1m, x2m = _resolver_ln(Md_kNcm, fck_mpa, bf_efetivo, d_cm)
            md_lim_mesa, x_lim_mesa = _momento_limite_ln(fck_mpa, bf_efetivo, d_cm, bx_min)
            na_mesa = x_mesa is not None and x_mesa <= hf_cm

            if na_mesa:
                ln_condiz = "SIM"
                x1, x2 = x1m, x2m
                if Md_kNcm > md_lim_mesa:
                    as1 = md_lim_mesa / (fyd * (d_cm - 0.4 * x_lim_mesa))
                    contexto_dupla = (
                        f"Mk={Mk_kNm:+.1f} kN·m (Md={Md_kNm:.1f} kN·m), "
                        f"seção T {bw_cm:.0f}×{h_cm:.0f} cm, Ø{diam_barra_mm:g} mm"
                    )
                    d_linha_cm = _d_linha_dupla(
                        h_cm,
                        bw_cm,
                        cob_mm,
                        diam_estribo_mm,
                        diam_barra_mm,
                        Md_kNcm - md_lim_mesa,
                        fyd,
                        d_cm,
                        d_lin,
                        is_t=True,
                        bf_cm=bf_efetivo,
                        hf_cm=hf_cm,
                    )
                    as2, as_linha_cm2 = _as2_as_linha_dupla(
                        Md_kNcm - md_lim_mesa,
                        fyd,
                        d_cm,
                        d_linha_cm,
                        x_lim_mesa,
                        bw_cm,
                        h_cm,
                        is_t=True,
                        bf_cm=bf_efetivo,
                        hf_cm=hf_cm,
                        contexto=contexto_dupla,
                    )
                    as_req = as1 + as2
                    bx = bx_min
                    x_cm = x_lim_mesa
                    alerta = (
                        f"Armadura dupla utilizada na mesa (bx={bx_min:.2f}). "
                        f"As = {as_req:.2f} cm² | As' = {as_linha_cm2:.2f} cm²."
                    )
                else:
                    bx = x_mesa / d_cm
                    x_cm = x_mesa
                    if classificar_dominio(bx) == "DOMINIO_4":
                        dominio_4 = True
                        alerta = (
                            f"Domínio 4 (bx={bx:.3f} > {BX_DOMINIO_4:.3f}): seção "
                            f"recusada — a armadura de tração não escoa. "
                            f"Aumente h/bw/fck ou adote armadura de compressão."
                        )
                    else:
                        alerta = ""
                    as_req = Md_kNcm / (fyd * (d_cm - 0.4 * x_mesa))
            else:
                ln_condiz = "NÃO"
                # 2. Linha neutra na alma: decompõe o momento nas abas e na alma.
                md1 = fcd_kn_cm2 * (bf_efetivo - bw_cm) * hf_cm * (d_cm - hf_cm / 2.0)
                as1 = md1 / (fyd * (d_cm - hf_cm / 2.0)) if md1 > 0 else 0.0

                if Md_kNcm <= md1:
                    as_req = Md_kNcm / (fyd * (d_cm - hf_cm / 2.0)) if Md_kNcm > 0 else 0.0
                    bx = (hf_cm / eta) / d_cm if d_cm > 0 else 0.0
                    x_cm = bx * d_cm
                    if classificar_dominio(bx) == "DOMINIO_4":
                        dominio_4 = True
                        alerta = (
                            f"Domínio 4 (bx={bx:.3f} > {BX_DOMINIO_4:.3f}): seção "
                            f"recusada — a armadura de tração não escoa. "
                            f"Aumente h/bw/fck ou adote armadura de compressão."
                        )
                    else:
                        alerta = "Momento resistido pelas abas da mesa colaborante."
                else:
                    Md2_kNcm = Md_kNcm - md1
                    md2_lim, x_lim2 = _momento_limite_ln(fck_mpa, bw_cm, d_cm, bx_min)
                    if Md2_kNcm > md2_lim:
                        as2_1 = md2_lim / (fyd * (d_cm - 0.4 * x_lim2))
                        contexto_dupla = (
                            f"Mk={Mk_kNm:+.1f} kN·m (Md={Md_kNm:.1f} kN·m), "
                            f"seção T {bw_cm:.0f}×{h_cm:.0f} cm (alma), "
                            f"Ø{diam_barra_mm:g} mm"
                        )
                        if d_lin > hf_cm:
                            raise ValueError(
                                f"Seção T recusada: armadura de compressão fora "
                                f"da mesa (d'={d_lin:.2f} cm > hf={hf_cm:.2f} cm). "
                                f"Contexto: {contexto_dupla}"
                            )
                        d_linha_cm = _d_linha_dupla(
                            h_cm,
                            bw_cm,
                            cob_mm,
                            diam_estribo_mm,
                            diam_barra_mm,
                            Md2_kNcm - md2_lim,
                            fyd,
                            d_cm,
                            d_lin,
                            is_t=True,
                            bf_cm=bf_efetivo,
                            hf_cm=hf_cm,
                        )
                        as2_2, as_linha_cm2 = _as2_as_linha_dupla(
                            Md2_kNcm - md2_lim,
                            fyd,
                            d_cm,
                            d_linha_cm,
                            x_lim2,
                            bw_cm,
                            h_cm,
                            is_t=True,
                            bf_cm=bf_efetivo,
                            hf_cm=hf_cm,
                            contexto=contexto_dupla,
                        )
                        as2 = as2_1 + as2_2
                        as_req = as1 + as2
                        bx = bx_min
                        x_cm = x_lim2
                        alerta = (
                            f"Linha neutra fora da mesa colaborante "
                            f"(x={bx * d_cm:.1f} cm > hf={hf_cm:.1f} cm) "
                            f"com armadura dupla na alma. As = {as_req:.2f} cm² | "
                            f"As' = {as_linha_cm2:.2f} cm²."
                        )
                    else:
                        x_alma, x1w, x2w = _resolver_ln(Md2_kNcm, fck_mpa, bw_cm, d_cm)
                        if x_alma is None or x_alma <= 0:
                            bx = 999.0
                            x_cm = 999.0 * d_cm
                            as_req = 0.0
                            alerta = (
                                f"Seção insuficiente na alma para o momento "
                                f"Md2={Md2_kNcm / 100:.1f} kN·m."
                            )
                        else:
                            bx = x_alma / d_cm
                            x_cm = x_alma
                            x1, x2 = x1w, x2w
                            as2 = Md2_kNcm / (fyd * (d_cm - 0.4 * x_alma))
                            as_req = as1 + as2
                            alerta = (
                                f"Linha neutra fora da mesa colaborante "
                                f"(x={bx * d_cm:.1f} cm > hf={hf_cm:.1f} cm). "
                                f"As1 (abas) = {as1:.2f} cm² | "
                                f"As2 (alma) = {as2:.2f} cm²."
                            )
        else:
            # Momento negativo: seção retangular com largura bw.
            ln_condiz = "SIM"
            md_lim, x_lim = _momento_limite_ln(fck_mpa, bw_cm, d_cm, bx_min)
            if Md_kNcm > md_lim:
                as1 = md_lim / (fyd * (d_cm - 0.4 * x_lim))
                contexto_dupla = (
                    f"Mk={Mk_kNm:+.1f} kN·m (Md={Md_kNm:.1f} kN·m), "
                    f"seção T {bw_cm:.0f}×{h_cm:.0f} cm (momento negativo), "
                    f"Ø{diam_barra_mm:g} mm"
                )
                d_linha_cm = _d_linha_dupla(
                    h_cm,
                    bw_cm,
                    cob_mm,
                    diam_estribo_mm,
                    diam_barra_mm,
                    Md_kNcm - md_lim,
                    fyd,
                    d_cm,
                    d_lin,
                )
                as2, as_linha_cm2 = _as2_as_linha_dupla(
                    Md_kNcm - md_lim,
                    fyd,
                    d_cm,
                    d_linha_cm,
                    x_lim,
                    bw_cm,
                    h_cm,
                    contexto=contexto_dupla,
                )
                as_req = as1 + as2
                bx = bx_min
                x_cm = x_lim
                alerta = (
                    f"Momento negativo com armadura dupla (bx={bx_min:.2f}). "
                    f"As = {as_req:.2f} cm² | As' = {as_linha_cm2:.2f} cm²."
                )
            else:
                x_neg, x1n, x2n = _resolver_ln(Md_kNcm, fck_mpa, bw_cm, d_cm)
                if x_neg is None or x_neg <= 0:
                    bx = 999.0
                    x_cm = 999.0 * d_cm
                    as_req = 0.0
                    alerta = (
                        f"Seção insuficiente para o momento negativo "
                        f"Mk={Mk_kNm:+.1f} kN·m na seção {bw_cm:.0f}×{h_cm:.0f} cm."
                    )
                else:
                    bx = x_neg / d_cm
                    x_cm = x_neg
                    x1, x2 = x1n, x2n
                    as_req = Md_kNcm / (fyd * (d_cm - 0.4 * x_neg))
                    if classificar_dominio(bx) == "DOMINIO_4":
                        dominio_4 = True
                        alerta = (
                            f"Domínio 4 (bx={bx:.3f} > {BX_DOMINIO_4:.3f}): seção "
                            f"recusada — a armadura de tração não escoa. "
                            f"Aumente h/bw/fck ou adote armadura de compressão."
                        )
                    else:
                        alerta = ""

        bx_passa = "NÃO" if dominio_4 else ("SIM" if bx <= bx_min + 1e-9 else "NÃO")
        # EP-02.3: no momento negativo a tração está na mesa; o As,min usa bf,ef.
        b_asmin = bf_efetivo if Mk_kNm < 0 else bw_cm
        asmin = rho_min_val * b_asmin * h_cm / 100.0
        as_necessaria = max(as_req, asmin)

        if as_linha_cm2 > 0:
            area_barra_d = area_barra(diam_barra_mm)
            qtd_barras_linha = math.ceil(as_linha_cm2 / area_barra_d) if area_barra_d > 0 else 0
            as_linha_adotada = qtd_barras_linha * area_barra_d
        else:
            as_linha_adotada = 0.0
            qtd_barras_linha = 0

        area_barra_d = area_barra(diam_barra_mm)
        qtd_barras = math.ceil(as_necessaria / area_barra_d) if area_barra_d > 0 else 0
        qtd_barras = max(1, qtd_barras)

        # EP-02.3: status/camadas/espaçamento vêm do laço de bitola (mesma
        # semântica do caminho retangular), não de um detalhamento local com
        # "N CAMADAS" hard-coded e eh_passa="SIM".
        layout = res_bitola.layout
        status_bitola = res_bitola.status_bitola
        cabe_status = res_bitola.cabe
        camadas = res_bitola.camadas
        eh_real = res_bitola.eh_real_mm / 10.0
        eh_passa = "SIM" if res_bitola.cabe else "NÃO"
        qtd_barras = res_bitola.qtd_barras
        qtd_barras_1cam = (
            layout.layers[0].bar_count if layout is not None and layout.layers else qtd_barras
        )
        barras_cima = qtd_barras - qtd_barras_1cam
        espaco_disp = bw_cm - 2 * (cob_mm / 10.0) - 2 * (diam_estribo_mm / 10.0)
        eh_min = max(2.0, diam_barra_mm / 10.0, 1.2 * d_max_agregado_mm / 10)
        bx_passa = "NÃO" if dominio_4 else ("SIM" if bx <= bx_min + 1e-9 else "NÃO")

        # EP-02.2: domínio 4 é recusa explícita (nunca "CABE" com As,min)
        if dominio_4:
            status_bitola = "NÃO CABE"

        # EP-01.3: invariantes de integridade antes de emitir o resultado
        _validar_invariantes_flexao(
            contexto=(
                f"Mk={Mk_kNm:+.1f} kN·m (Md={Md_kNm:.1f} kN·m, γf={gamma_f}), "
                f"seção T {bw_cm:.0f}×{h_cm:.0f} cm (bf={bf_cm:.0f} cm, "
                f"hf={hf_cm:.0f} cm), Ø{diam_barra_mm:g} mm, cob={cob_mm:.0f} mm, "
                f"CAA {caa}"
            ),
            as_req_cm2=round(as_req, 3),
            as_adotado_cm2=round(qtd_barras * area_barra_d, 3),
            d_cm=round(d_cm, 2),
            qtd_barras=qtd_barras,
            area_barra_cm2=area_barra_d,
            cabe=cabe_status,
            status_bitola=status_bitola,
        )

        resultados.append(
            ResultadoFlexaoT(
                momento_kNm=abs(Md_kNm),
                tipo=tipo,
                kc=round(
                    kc if Mk_kNm > 0 else (bw_cm * d_cm**2 / Md_kNcm if Md_kNcm != 0 else 0), 3
                ),
                a=round(a_coef if Mk_kNm > 0 else (a_coef if "a_coef" in locals() else 0.0), 4),
                b=round(b_coef if Mk_kNm > 0 else (b_coef if "b_coef" in locals() else 0.0), 4),
                x1=round(x1 if "x1" in locals() else 0.0, 4),
                x2=round(x2 if "x2" in locals() else 0.0, 4),
                bx=round(bx, 4),
                bx_passa=bx_passa,
                x_cm=round(x_cm, 2) if x_cm < 999.0 else None,
                linha_neutra_condiz=ln_condiz,
                bf_efetivo_cm=round(bf_efetivo, 2),
                ks=round(1.0 / (fyd * (1.0 - 0.4 * bx)) if bx < 999.0 else 0.0, 3),
                as_req_cm2=round(as_req, 3),
                asmin_cm2=round(asmin, 3),
                as_necessaria_cm2=round(as_necessaria, 3),
                diametro_mm=diam_barra_mm,
                qtd_barras=qtd_barras,
                eh_min_real=round(eh_min, 2),
                eh_passa=eh_passa,
                barras_suportadas=qtd_barras_1cam,
                eh_suportado=round(eh_real, 2),
                barras_cima=barras_cima,
                cob_mm=cob_mm,
                espaco_disp_cm=round(espaco_disp, 2),
                as_lista_barras=[area_barra(d) for d in DIAM_BARRAS],
                requer_pele=pele["requer"],
                n_barras_pele_face=pele["n_barras_face"],
                as_pele_face_cm2=pele["as_pele_adotada_face_cm2"],
                phi_pele_mm=pele["phi_pele_mm"],
                s_pele_cm=pele["s_adotado_cm"],
                as_pele_min_face_cm2=pele["as_pele_min_face_cm2"],
                s_pele_max_cm=pele["s_max_cm"],
                tabela_pele=pele.get("tabela_phis", []),
                alerta=alerta,
                as_adotado_cm2=round(qtd_barras * area_barra_d, 3),
                d_cm_real=round(d_cm, 2),
                camadas_adotadas=camadas,
                status_bitola=status_bitola,
                convergiu=res_bitola.convergiu and not dominio_4,
                layout_convergido=layout,
                tabela_bitolas=tabela_bitolas,
                as_linha_cm2=round(as_linha_cm2, 3),
                as_linha_adotada=round(as_linha_adotada, 3),
            )
        )

    return resultados
