"""
CALCULOS ESTRUTURAIS - Flexao e Cisalhamento
Norma: NBR 6118:2023
Autor: Samuel Santos (https://github.com/samuel-c-santos)
Licenca: vide LICENSE
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional
from core.detailing import BeamDetailer, BeamDetailingInput, SectionLayoutData

# ── Constantes ────────────────────────────────────────────────────────────────
ALPHA_C = 0.85   # NBR 6118
GAMMA_C = 1.40   # Coeficiente do concreto
GAMMA_S = 1.15   # Coeficiente do aço
GAMMA_F_PP = 1.30  # Peso próprio
GAMMA_F_RESTO = 1.40  # Demais ações


def lambda_f(fck_mpa: float) -> float:
    """Fator lambda para resistencia a compressao diagonal (NBR 6118:17.4.2.2).
    lambda = 1 - fck/250 (para fck > 50). Se fck <= 50, lambda = 0.80.
    """
    return min(0.80, 1.0 - fck_mpa / 250.0)

# Tabela 11.1 - NBR 6118:2023 - Coeficientes γf (simplificação por combinação)
# O app recebe esforços característicos (sem majorar) e aplica γf internamente.
GAMMA_F_TABLE = {
    "normais":       {"nome": "Normais",                    "gamma_f": 1.4},
    "especiais":     {"nome": "Especiais ou de construcao", "gamma_f": 1.2},
    "excepcionais":  {"nome": "Excepcionais",               "gamma_f": 1.0},
}

# Diâmetros de barra disponíveis (mm)
DIAM_BARRAS = [5, 6.3, 8, 10, 12.5, 16, 20, 25, 32]      # estribos e pele
DIAM_BARRAS_LONG = [10, 12.5, 16, 20, 25, 32]                # armadura longitudinal (NBR 6118: φ≥10mm)


# ── Classes de Agressividade Ambiental ───────────────────────────────────────
CAA_DATA = {
    1: {"nome": "Fraca",       "cobrimento": 25, "ac_max": 0.65, "fck_min": 20},
    2: {"nome": "Moderada",    "cobrimento": 30, "ac_max": 0.60, "fck_min": 25},
    3: {"nome": "Forte",       "cobrimento": 40, "ac_max": 0.55, "fck_min": 30},
    4: {"nome": "Muito Forte", "cobrimento": 50, "ac_max": 0.50, "fck_min": 35},
}

# Tabela de rho_min para flexão (fck em MPa)
RHO_MIN_TABLE = {
    20: 0.150, 25: 0.150, 30: 0.150, 35: 0.164, 40: 0.179,
    45: 0.194, 50: 0.208, 55: 0.211, 60: 0.219, 65: 0.226,
    70: 0.233, 75: 0.239, 80: 0.245, 85: 0.251, 90: 0.256,
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


def fcd_mpa(fck: float) -> float:
    return ALPHA_C * fck / GAMMA_C


def fyd_kn_cm2(fyk_kn_cm2: float) -> float:
    """Resistencia de calculo do aco em kN/cm².

    O UI passa fyk em kN/cm² (CA-50 = 50, CA-60 = 60, CA-25 = 25),
    equivalente a MPa/10. Retorna fyd em kN/cm² (nao divide por 10).
    """
    return fyk_kn_cm2 / GAMMA_S


def fctm_mpa(fck: float) -> float:
    return 0.30 * fck ** (2 / 3)


def fck_to_kgf_cm2(fck_mpa: float) -> float:
    """Converte fck de MPa para kgf/cm2 (1 MPa = 10,1972 kgf/cm2)."""
    return fck_mpa * 10.1972


def fctkinf_mpa(fck: float) -> float:
    return 0.7 * fctm_mpa(fck)


def fctd_kn_cm2(fck: float) -> float:
    return fctkinf_mpa(fck) / 10 / GAMMA_C


def validar_geometria(
    h_cm: float,
    bw_cm: float,
    cob_mm: float,
    diam_estribo_mm: float,
    diam_barra_mm: float,
) -> Optional[str]:
    """A9: valida geometria antes de calcular. Retorna mensagem de erro ou None.

    Criterios minimos:
    - h > 0, bw > 0
    - d = h - d' > 0 (altura util positiva)
    - h >= 5 cm (minimo pratico para viga)
    - bw >= 5 cm (minimo normativo)
    - diametros > 0
    """
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

    d_lin = cob_mm / 10 + diam_estribo_mm / 10 + diam_barra_mm / 20
    d_cm = h_cm - d_lin
    if d_cm <= 0:
        return (
            f"Altura util d={d_cm:.1f} cm invalida. "
            f"d'={d_lin:.1f} cm (cob={cob_mm}mm + estribo={diam_estribo_mm}mm + barra/2={diam_barra_mm/2:.1f}mm). "
            f"Aumente h ou reduza cobrimento/bitola."
        )
    return None


def rho_min(fck: float) -> float:
    """Taxa mínima de armadura de flexão."""
    fck_vals = sorted(RHO_MIN_TABLE.keys())
    closest = min(fck_vals, key=lambda x: abs(x - fck))
    return RHO_MIN_TABLE[closest]


def asw_min_cm2_m(fck: float, bw_cm: float, fyk_estribo_mpa: float = 500) -> float:
    """Asw/s mínimo (cm²/m) para estribos.
    
    A tabela ASW_S_TABLE_CA50 armazena:
      [0] = ρ_min em % (apenas referência)
      [1] = Asw_min/s por cm de bw para CA-50 (cm²/m/cm)
      [2] = Asw_min/s por cm de bw para CA-60 (cm²/m/cm)
    """
    fck_key = min(ASW_S_TABLE_CA50.keys(), key=lambda x: abs(x - fck))
    _, ca50, ca60 = ASW_S_TABLE_CA50[fck_key]
    rho = ca50 if fyk_estribo_mpa <= 500 else ca60
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
    PHI_OPCOES = [6.3, 8.0, 10.0, 12.5, 16.0, 5.0]  # 6.3 ou 8 preferencial (construtibilidade)

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

    # Altura util aproximada
    d_cm = h_cm - cob_mm / 10 - phi_estribo_mm / 10

    # Espacamento maximo vertical entre barras de pele (NBR 6118)
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
        
        # O diâmetro da barra de pele deve ser menor ou igual ao diâmetro do estribo (NBR 6118:17.3.5.2.3)
        cabe = (s_adot <= s_max if n > 1 else True) and (phi <= phi_estribo_mm)

        tabela_phis.append({
            "phi_mm": phi,
            "n_barras_face": n,
            "s_cm": round(s_adot, 1),
            "as_cm2": round(as_adot, 3),
            "cabe": cabe,
        })

    # Adotar o menor diametro que atenda a area minima e aos critérios normativos
    melhor = None
    for item in tabela_phis:
        if item["cabe"] and item["as_cm2"] >= as_pele_min_face:
            melhor = item
            break
    if not melhor:
        # Fallback: encontrar qualquer uma que atenda phi <= phi_estribo_mm
        opcoes_validas = [item for item in tabela_phis if item["phi_mm"] <= phi_estribo_mm]
        if opcoes_validas:
            melhor = min(opcoes_validas, key=lambda x: x["phi_mm"])
        else:
            melhor = tabela_phis[-1]  # fallback absoluto
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
    tipo: str           # "POSITIVO" ou "NEGATIVO"
    kc: float
    a: float
    b: float
    x1: float
    x2: float
    bx: float
    bx_passa: str       # "SIM" ou "NÃO"
    x_cm: float
    ks: float
    as_req_cm2: float
    asmin_cm2: float
    as_usado_cm2: float
    diametro_mm: float
    qtd_barras: int
    eh_min_real: float
    eh_passa: str
    barras_suportadas: int
    eh_suportado: float
    barras_cima: int
    cob_mm: float
    espaco_disp_cm: float
    as_lista_barras: List[float]  # área por diâmetro (cm²)
    # Armadura de pele (h >= 60 cm, NBR 6118:17.3.5.2.3)
    requer_pele: bool = False
    n_barras_pele_face: int = 0
    as_pele_face_cm2: float = 0.0
    phi_pele_mm: float = 0.0
    s_pele_cm: float = 0.0
    as_pele_min_face_cm2: float = 0.0
    s_pele_max_cm: float = 0.0
    tabela_pele: List = None  # lista de dicts com phi/n/s/as/cabe
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
    layout_convergido: Optional[object] = None
    tabela_bitolas: List = None

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
    layout: Optional[SectionLayoutData]
    iteracoes: int
    cabe: bool


def dimensionar_bitola_iterativa(
    h_cm: float,
    bw_calculo_cm: float,
    cob_mm: float,
    diam_estribo_mm: float,
    diam_barra_mm: float,
    fck_mpa: float,
    fyk_mpa: float,
    Md_kNm: float,
    bw_detalhamento_cm: Optional[float] = None,
    d_max_agregado_mm: float = 19.0,
    max_iter: int = 5,
    tol_mm: float = 1.0,
) -> ResultadoBitola:
    """Realiza o loop de convergência iterativa para encontrar a armadura e o detalhamento geométrico."""
    if bw_detalhamento_cm is None:
        bw_detalhamento_cm = bw_calculo_cm

    detailer = BeamDetailer()
    d_lin_est = cob_mm / 10.0 + diam_estribo_mm / 10.0 + diam_barra_mm / 20.0
    d_cm = h_cm - d_lin_est
    d_inicial_cm = d_cm

    iteracoes_feitas = 0
    layout_final = None
    as_req_final = 0.0
    as_usado_final = 0.0
    qtd_barras = 0

    for it in range(1, max_iter + 1):
        iteracoes_feitas = it

        Md_kNcm = abs(Md_kNm) * 100.0
        kc = (bw_calculo_cm * d_cm**2) / Md_kNcm if Md_kNcm != 0 else 0

        fck_conv = fck_mpa / 10.0
        fyd = fyd_kn_cm2(fyk_mpa)
        a_coef = -0.192 * fck_conv * kc
        b_coef = 0.48 * fck_conv * kc
        c_coef = -1.0

        delta = b_coef**2 - 4 * a_coef * c_coef
        if delta < 0 or a_coef == 0:
            bx = 999.0
            x1 = x2 = 0.0
        else:
            sq = math.sqrt(delta)
            x1 = (-b_coef + sq) / (2 * a_coef)
            x2 = (-b_coef - sq) / (2 * a_coef)
            if x1 < 0:
                bx = x2 if 0 < x2 < 0.628 else 999.0
            elif x2 < 0:
                bx = x1 if 0 < x1 < 0.628 else 999.0
            else:
                cand = sorted([x1, x2])
                bx = cand[0] if 0 < cand[0] < 0.628 else (cand[1] if 0 < cand[1] < 0.628 else 999.0)

        bx_min = 0.45 if fck_mpa <= 50 else 0.35
        kc_lim = 1.0 / (fck_conv * bx_min * (0.48 - 0.192 * bx_min))
        Md_lim_kNcm = (bw_calculo_cm * d_cm**2) / kc_lim
        Md_lim_kNm = Md_lim_kNcm / 100.0

        if abs(Md_kNm) > Md_lim_kNm:
            md_exc_kNcm = (abs(Md_kNm) - Md_lim_kNm) * 100.0
            ks_lim = 1.0 / (fyd * (1.0 - bx_min / 2.0))
            as1 = ks_lim * Md_lim_kNcm / d_cm
            denom = d_cm - d_lin_est if (d_cm - d_lin_est) > 0 else 0.1
            as2 = md_exc_kNcm / (fyd * denom)
            as_req = as1 + as2
        else:
            if bx >= bx_min or bx >= 0.628:
                as_req = 0.0
            else:
                ks = 1.0 / (fyd * (1.0 - bx / 2.0))
                as_req = ks * Md_kNcm / d_cm

        asmin = rho_min(fck_mpa) * bw_detalhamento_cm * h_cm / 100.0
        as_usado = max(as_req, asmin)
        as_req_final = as_req
        as_usado_final = as_usado

        a_bar = area_barra(diam_barra_mm)
        qtd_barras = math.ceil(as_usado / a_bar) if a_bar > 0 else 0
        qtd_barras = max(1, qtd_barras)

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

        if abs(d_cm * 10.0 - layout.d_efetiva) < tol_mm:
            d_cm = d_real_cm
            break
        d_cm = d_real_cm

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
    )


def calcular_flexao_viga_comum(
    h_cm: float,
    bw_cm: float,
    caa: int,
    fck_mpa: float,
    diam_estribo_mm: float,
    diam_barra_mm: float,
    fyk_mpa: float,
    momentos: List[float],
    gamma_f: float = GAMMA_F_RESTO,
) -> List[ResultadoFlexao]:
    """Calcula flexao para uma secao retangular com multiplos momentos.

    Os momentos sao recebidos como valores caracteristicos (sem majoracao).
    O coeficiente gamma_f e aplicado internamente.

    Raises:
        ValueError: se geometria invalida (h<=0, bw<5, d<=0, etc).
    """

    # A9: validacao de geometria antes de calcular
    cob_mm = CAA_DATA[caa]["cobrimento"]
    erro_geo = validar_geometria(h_cm, bw_cm, cob_mm, diam_estribo_mm, diam_barra_mm)
    if erro_geo:
        raise ValueError(erro_geo)

    # Parametros da CAA
    d_lin   = cob_mm / 10 + diam_estribo_mm / 10 + diam_barra_mm / 20
    d_cm    = h_cm - d_lin

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
            fyk_mpa=fyk_mpa,
            Md_kNm=Md_kNm,
            bw_detalhamento_cm=bw_cm,
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
                    fyk_mpa=fyk_mpa,
                    Md_kNm=Md_kNm,
                    bw_detalhamento_cm=bw_cm,
                )
                tabela_bitolas.append(res_cand)

        # Adota a altura útil convergida no cálculo final
        d_cm = res_bitola.d_real_cm

        # KC = bw·d² / Md
        # Formula empirica (coef 0.192/0.48) exige Md em kN·cm e fcd em kN/cm².
        # Converte Md para kN·cm (×100) para consistencia de unidades.
        Md_kNcm = abs(Md_kNm) * 100
        kc = (bw_cm * d_cm**2) / Md_kNcm if Md_kNcm != 0 else 0

        # Coeficientes da equacao do 2º grau: a·x² + b·x + c = 0
        # fck/10 ~ fcd empirico da planilha (em kN/cm²)
        fck_conv = fck_mpa / 10            # MPa -> kN/cm² (formula empirica)
        fyd = fyd_kn_cm2(fyk_mpa)          # kN/cm² (fyk entra em kN/cm²)

        a_coef = -0.192 * fck_conv * kc
        b_coef = 0.48 * fck_conv * kc
        c_coef = -1

        delta = b_coef**2 - 4 * a_coef * c_coef
        if delta < 0 or a_coef == 0:
            bx = 999
            x1 = x2 = 0
        else:
            sq = math.sqrt(delta)
            x1 = (-b_coef + sq) / (2 * a_coef)
            x2 = (-b_coef - sq) / (2 * a_coef)

            # Selecionar x válido (0 < x < 0.628)
            if x1 < 0:
                bx = x2 if 0 < x2 < 0.628 else 999
            elif x2 < 0:
                bx = x1 if 0 < x1 < 0.628 else 999
            else:
                # Ambas positivas: escolher a menor dentro do dominio 0 < bx < 0.628
                cand = sorted([x1, x2])
                bx = cand[0] if 0 < cand[0] < 0.628 else (cand[1] if 0 < cand[1] < 0.628 else 999)

        # bx mínimo/limite conforme NBR 6118
        bx_min = 0.45 if fck_mpa <= 50 else 0.35
        kc_lim = 1.0 / (fck_conv * bx_min * (0.48 - 0.192 * bx_min))
        Md_lim_kNcm = (bw_cm * d_cm**2) / kc_lim
        Md_lim_kNm = Md_lim_kNcm / 100

        # Inicializar variáveis de armadura dupla
        armadura_dupla = False
        as_linha_cm2 = 0.0
        as_linha_adotada = 0.0
        md_limite_knm = Md_lim_kNm
        md_excedente_knm = 0.0

        # Verificar se armadura dupla é necessária
        if abs(Md_kNm) > Md_lim_kNm:
            armadura_dupla = True
            md_excedente_knm = abs(Md_kNm) - Md_lim_kNm
            md_exc_kNcm = md_excedente_knm * 100
            
            # ks limite
            ks = 1 / (fyd * (1 - bx_min / 2))
            
            # As1 (tracionada limite)
            as1 = ks * Md_lim_kNcm / d_cm
            
            # As2 (tracionada adicional) e As' (comprimida)
            as2 = md_exc_kNcm / (fyd * (d_cm - d_lin))
            as_linha_cm2 = as2
            
            # As total requerida
            as_req = as1 + as2
            
            bx = bx_min
            bx_passa = "SIM"
            alerta = (
                f"Armadura dupla utilizada (bx={bx_min:.2f}). "
                f"As = {as_req:.2f} cm² | As' = {as_linha_cm2:.2f} cm²."
            )
        else:
            # Armadura simples
            bx_passa = "SIM" if bx < bx_min else "NÃO"
            dominio_ok = bx < 0.628
            if not dominio_ok or bx >= bx_min:
                ks = 0
                as_req = 0
            else:
                ks = 1 / (fyd * (1 - bx / 2))
                as_req = ks * Md_kNcm / d_cm

            # Alerta da armadura simples
            if bx >= 999:
                alerta = (
                    f"Seção insuficiente para o momento Mk={Mk_kNm:+.1f} kN·m "
                    f"(Md={Md_kNm:.1f} kN·m, γf={gamma_f}). "
                    f"KC={kc:.2f} abaixo do mínimo para a seção {bw_cm:.0f}×{h_cm:.0f} cm. "
                    f"Soluções: aumente h ou bw, aumente fck, ou reduza o momento."
                )
            elif bx >= 0.628:
                alerta = (
                    f"Relação bx={bx:.3f} acima do limite 0,628 (domínio 4). "
                    f"Mk={Mk_kNm:+.1f} kN·m, seção {bw_cm:.0f}×{h_cm:.0f} cm. "
                    f"Soluções: aumente h para reduzir bx, ou aumente bw."
                )
            else:
                alerta = ""

        # Altura da linha neutra
        x_cm = bx * d_cm

        # Asmin
        asmin = rho_min_val * bw_cm * h_cm / 100  # cm²

        # As utilizado
        as_usado = max(as_req, asmin)

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
        eh_min = max(2.0, diam_barra_mm / 10, 1.2 * 1.9)
        eh_passa = "SIM" if res_bitola.cabe else "NÃO"
        if res_bitola.layout and res_bitola.layout.layers:
            eh_real = res_bitola.eh_real_mm / 10.0
            qtd_barras_1cam = res_bitola.layout.layers[0].bar_count
            barras_cima = qtd_barras - qtd_barras_1cam
        else:
            eh_real = 0.0
            qtd_barras_1cam = qtd_barras
            barras_cima = 0

        # Armadura de pele (NBR 6118:17.3.5.2.3) — já calculada fora do loop
        resultados.append(ResultadoFlexao(
            momento_kNm=abs(Md_kNm),
            tipo=tipo,
            kc=round(kc, 3),
            a=round(a_coef, 6),
            b=round(b_coef, 6),
            x1=round(x1, 4),
            x2=round(x2, 4),
            bx=round(bx, 4),
            bx_passa=bx_passa,
            x_cm=round(x_cm, 2),
            ks=round(ks, 3),
            as_req_cm2=round(as_req, 3),
            asmin_cm2=round(asmin, 3),
            as_usado_cm2=round(as_usado, 3),
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
            status_bitola=res_bitola.status_bitola,
            layout_convergido=res_bitola.layout,
            tabela_bitolas=tabela_bitolas,
        ))

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
    fyk_estribo_mpa: float,
    fyk_barra_mpa: float,
    caa: int,
    forcas_cortantes: List[float],
    gamma_f: float = GAMMA_F_RESTO,
) -> List[ResultadoCisalhamento]:
    """Calcula cisalhamento para uma secao retangular (largura da alma bw).

    As forcas cortantes sao recebidas como valores caracteristicos (com sinal,
    sem majorar). O coeficiente gamma_f e aplicado internamente sobre o modulo
    |V|.

    Raises:
        ValueError: se geometria invalida.
    """

    # A9: validacao de geometria
    cob_mm = CAA_DATA[caa]["cobrimento"]
    erro_geo = validar_geometria(h_cm, bw_cm, cob_mm, diam_estribo_mm, diam_barra_mm)
    if erro_geo:
        raise ValueError(erro_geo)

    d_lin   = cob_mm / 10 + diam_estribo_mm / 10 + diam_barra_mm / 20
    d_cm    = h_cm - d_lin

    fcd = fcd_mpa(fck_mpa)         # MPa
    fctm = fctm_mpa(fck_mpa)
    fctkinf = fctkinf_mpa(fck_mpa)
    fctd = fctd_kn_cm2(fck_mpa)    # kN/cm²
    lam = lambda_f(fck_mpa)        # fator lambda (NBR 6118:17.4.2.2)

    # fywd do estribo em kN/cm² (fyk entra em kN/cm²: CA-60=60). Limite de 43.5 kN/cm² (435 MPa) conf. NBR 6118:17.4.2.3
    fywd_kn_cm2 = min(fyd_kn_cm2(fyk_estribo_mpa), 43.5)

    area_estribo = area_barra(diam_estribo_mm)  # cm² (1 estribo = 2 ramos)
    asw_ramo = area_estribo * 2  # cm² (estribo com 2 ramos)

    # Asw/s mínimo
    asw_min = asw_min_cm2_m(fck_mpa, bw_cm, fyk_estribo_mpa)

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

        # Espacamento: s = (Asw ramo) / (Asw/s) * 100 (cm)
        # asw_ramo em cm², asw_usado em cm²/m -> s em cm
        dist_estribos = (asw_ramo * 100) / asw_usado if asw_usado > 0 else 999

        # Verificação de espaçamento máximo dos estribos (NBR 6118:18.3.3.2)
        if Vsd_aplicado <= 0.67 * vrd2:
            s_max = min(0.6 * d_cm, 30.0)
        else:
            s_max = min(0.3 * d_cm, 20.0)

        passa_smax = "SIM" if dist_estribos <= s_max + 0.05 else "NÃO"

        resultados.append(ResultadoCisalhamento(
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
        ))

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
    x_cm: float
    linha_neutra_condiz: str
    bf_efetivo_cm: float
    ks: float
    as_req_cm2: float
    asmin_cm2: float
    as_usado_cm2: float
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
    as_lista_barras: List[float] = None
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
    tabela_pele: List = None  # lista de dicts com phi/n/s/as/cabe
    alerta: str = ""  # mensagem de alerta (dominio nao passa, etc)
    as_adotado_cm2: float = 0.0
    d_cm_real: float = 0.0
    camadas_adotadas: int = 1
    status_bitola: str = "CABE"
    layout_convergido: Optional[object] = None
    tabela_bitolas: List = None

    def __post_init__(self):
        if self.tabela_pele is None:
            self.tabela_pele = []
        if self.tabela_bitolas is None:
            self.tabela_bitolas = []


def bf_efetivo_viga_t(
    bw_cm: float, bf_cm: float,
    b1esq_cm: Optional[float] = None, b1dir_cm: Optional[float] = None,
    lo_esq_cm: Optional[float] = None, lo_dir_cm: Optional[float] = None,
) -> float:
    """Largura efetiva da mesa (NBR 6118:15.5.2):
       bf,ef = bw + b1esq + b1dir, limitado por:
       - b1 <= 0.5*bf1 (largura da mesa adjacente do outro lado, se houver)
       - b1 <= 0.1*a (a = distância entre faces de apoios)

       Para um vão isolado, simplificamos: bf,ef = min(bf, bw + b1esq + b1dir).
       Se b1esq/b1dir não forem fornecidos, retorna bf integral.
    """
    if b1esq_cm is None and b1dir_cm is None:
        return bf_cm
    b1e = b1esq_cm if b1esq_cm is not None else 0.0
    b1d = b1dir_cm if b1dir_cm is not None else 0.0

    # Limit b1 by 0.1 * span as per NBR 6118 15.5.2
    if lo_esq_cm is not None and lo_esq_cm > 0:
        b1e = min(b1e, 0.1 * lo_esq_cm)
    if lo_dir_cm is not None and lo_dir_cm > 0:
        b1d = min(b1d, 0.1 * lo_dir_cm)

    bf_calc = bw_cm + b1e + b1d
    return min(bf_cm, bf_calc)


def calcular_flexao_viga_t(
    h_cm: float,
    bw_cm: float,
    bf_cm: float,
    hf_cm: float,
    caa: int,
    fck_mpa: float,
    diam_estribo_mm: float,
    diam_barra_mm: float,
    fyk_mpa: float,
    momentos: List[float],
    b1esq_cm: Optional[float] = None,
    b1dir_cm: Optional[float] = None,
    lo_esq_cm: Optional[float] = None,
    lo_dir_cm: Optional[float] = None,
    gamma_f: float = GAMMA_F_RESTO,
) -> List[ResultadoFlexaoT]:
    """Calcula flexao para secao de Viga T.

    Os momentos sao recebidos como valores caracteristicos (sem majoracao).
    O coeficiente gamma_f e aplicado internamente.

    Raises:
        ValueError: se geometria invalida (h<=0, bw<5, bf<hf, d<=0, etc).
    """

    # A9: validacao de geometria
    cob_mm = CAA_DATA[caa]["cobrimento"]
    erro_geo = validar_geometria(h_cm, bw_cm, cob_mm, diam_estribo_mm, diam_barra_mm)
    if erro_geo:
        raise ValueError(erro_geo)
    if bf_cm < bw_cm:
        raise ValueError(f"Mesa bf={bf_cm} cm menor que alma bw={bw_cm} cm (inconsistente).")
    if hf_cm >= h_cm:
        raise ValueError(f"Altura da mesa hf={hf_cm} cm >= h={h_cm} cm (mesa maior que viga).")

    d_lin   = cob_mm / 10 + diam_estribo_mm / 10 + diam_barra_mm / 20
    d_cm    = h_cm - d_lin

    bf_efetivo = bf_efetivo_viga_t(bw_cm, bf_cm, b1esq_cm, b1dir_cm, lo_esq_cm=lo_esq_cm, lo_dir_cm=lo_dir_cm)
    rho_min_val = rho_min(fck_mpa)
    fck_conv = fck_mpa / 10   # MPa -> kN/cm² (formula empirica)
    fyd = fyd_kn_cm2(fyk_mpa)  # kN/cm² (fyk entra em kN/cm²)

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
            fyk_mpa=fyk_mpa,
            Md_kNm=Md_kNm,
            bw_detalhamento_cm=bw_cm,
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
                    fyk_mpa=fyk_mpa,
                    Md_kNm=Md_kNm,
                    bw_detalhamento_cm=bw_cm,
                )
                tabela_bitolas.append(res_cand)

        d_cm = res_bitola.d_real_cm
        
        # Fator eta de profundidade para classes de concreto
        if fck_mpa <= 50:
            eta = 0.8
        else:
            eta = 0.8 - (fck_mpa - 50) / 400.0

        # Relação limite bx_min conforme NBR 6118
        bx_min = 0.45 if fck_mpa <= 50 else 0.35
        kc_lim = 1.0 / (fck_conv * bx_min * (0.48 - 0.192 * bx_min))

        Md_kNcm = abs(Md_kNm) * 100.0
        
        if Mk_kNm > 0:
            # Momento positivo: compressão no topo (mesa)
            # 1. Tenta calcular assumindo LN na mesa (largura bf_efetivo)
            kc = (bf_efetivo * d_cm**2) / Md_kNcm if Md_kNcm != 0 else 0
            a_coef = -0.192 * fck_conv * kc
            b_coef = 0.48 * fck_conv * kc
            c_coef = -1.0
            
            delta = b_coef**2 - 4 * a_coef * c_coef
            if delta < 0 or a_coef == 0:
                bx = 999.0
                x1 = x2 = 0.0
            else:
                sq = math.sqrt(delta)
                x1 = (-b_coef + sq) / (2 * a_coef)
                x2 = (-b_coef - sq) / (2 * a_coef)
                if x1 < 0:
                    bx = x2 if 0 < x2 < 0.628 else 999.0
                elif x2 < 0:
                    bx = x1 if 0 < x1 < 0.628 else 999.0
                else:
                    cand = sorted([x1, x2])
                    bx = cand[0] if 0 < cand[0] < 0.628 else (cand[1] if 0 < cand[1] < 0.628 else 999.0)
            
            x_cm = bx * d_cm
            
            # Verifica se a linha neutra está realmente na mesa colaborante
            if eta * x_cm < hf_cm:
                ln_condiz = "SIM"
                if bx >= 999.0:
                    alerta = (
                        f"Seção insuficiente para o momento Mk={Mk_kNm:+.1f} kN·m "
                        f"(Md={Md_kNm:.1f} kN·m, γf={gamma_f}). "
                        f"KC={kc:.2f} abaixo do mínimo para a seção {bf_efetivo:.0f}×{h_cm:.0f} cm."
                    )
                    as_req = 0.0
                    as_linha_cm2 = 0.0
                elif bx >= 0.628:
                    alerta = (
                        f"Relação bx={bx:.3f} acima do limite 0,628 (domínio 4). "
                        f"Soluções: aumente h para reduzir bx, ou aumente bw."
                    )
                    as_req = 0.0
                    as_linha_cm2 = 0.0
                elif bx >= bx_min:
                    # Armadura dupla na mesa colaborante
                    Md_lim_kNcm = (bf_efetivo * d_cm**2) / kc_lim
                    md_exc_kNcm = Md_kNcm - Md_lim_kNcm
                    ks_lim = 1.0 / (fyd * (1.0 - bx_min / 2.0))
                    as1 = ks_lim * Md_lim_kNcm / d_cm
                    denom = d_cm - d_lin if (d_cm - d_lin) > 0 else 0.1
                    as2 = md_exc_kNcm / (fyd * denom)
                    as_req = as1 + as2
                    as_linha_cm2 = as2
                    alerta = (
                        f"Armadura dupla utilizada na mesa (bx={bx_min:.2f}). "
                        f"As = {as_req:.2f} cm² | As' = {as_linha_cm2:.2f} cm²."
                    )
                    bx = bx_min
                else:
                    ks = 1.0 / (fyd * (1.0 - bx / 2.0))
                    as_req = ks * Md_kNcm / d_cm
                    as_linha_cm2 = 0.0
                    alerta = ""
            else:
                ln_condiz = "NÃO"
                # Linha neutra na alma: decomposição do momento fletor
                alpha_c = 0.85
                if fck_mpa > 50:
                    alpha_c = 0.85 * (1.0 - (fck_mpa - 50) / 200.0)
                stress_block_fcd = alpha_c * (fck_mpa / 1.4) / 10.0 # kN/cm^2
                
                Md1_kNcm = stress_block_fcd * (bf_efetivo - bw_cm) * hf_cm * (d_cm - hf_cm / 2.0)
                
                if Md_kNcm <= Md1_kNcm:
                    as_req = Md_kNcm / (fyd * (d_cm - hf_cm / 2.0))
                    as_linha_cm2 = 0.0
                    alerta = "Momento resistido pelas abas da mesa colaborante."
                    bx = (hf_cm / eta) / d_cm if d_cm > 0 else 0.0
                else:
                    Md2_kNcm = Md_kNcm - Md1_kNcm
                    Md2_lim_kNcm = (bw_cm * d_cm**2) / kc_lim
                    if Md2_kNcm > Md2_lim_kNcm:
                        # Armadura dupla necessária na alma
                        Md2_exc_kNcm = Md2_kNcm - Md2_lim_kNcm
                        
                        ks_lim = 1.0 / (fyd * (1.0 - bx_min / 2.0))
                        as2_1 = ks_lim * Md2_lim_kNcm / d_cm
                        
                        denom = d_cm - d_lin if (d_cm - d_lin) > 0 else 0.1
                        as2_2 = Md2_exc_kNcm / (fyd * denom)
                        as2 = as2_1 + as2_2
                        as_linha_cm2 = as2_2
                        
                        as1 = Md1_kNcm / (fyd * (d_cm - hf_cm / 2.0))
                        as_req = as1 + as2
                        bx = bx_min
                        alerta = (
                            f"Linha neutra fora da mesa colaborante (0,8x={eta * bx * d_cm:.1f} cm >= hf={hf_cm:.1f} cm) "
                            f"com armadura dupla na alma. As = {as_req:.2f} cm² | As' = {as_linha_cm2:.2f} cm²."
                        )
                    else:
                        kc2 = (bw_cm * d_cm**2) / Md2_kNcm
                        a_coef2 = -0.192 * fck_conv * kc2
                        b_coef2 = 0.48 * fck_conv * kc2
                        c_coef2 = -1.0
                        
                        delta2 = b_coef2**2 - 4 * a_coef2 * c_coef2
                        if delta2 < 0 or a_coef2 == 0:
                            bx2 = 999.0
                            x1_2 = x2_2 = 0.0
                        else:
                            sq2 = math.sqrt(delta2)
                            x1_2 = (-b_coef2 + sq2) / (2 * a_coef2)
                            x2_2 = (-b_coef2 - sq2) / (2 * a_coef2)
                            if x1_2 < 0:
                                bx2 = x2_2 if 0 < x2_2 < 0.628 else 999.0
                            elif x2_2 < 0:
                                bx2 = x1_2 if 0 < x1_2 < 0.628 else 999.0
                            else:
                                cand2 = sorted([x1_2, x2_2])
                                bx2 = cand2[0] if 0 < cand2[0] < 0.628 else (cand2[1] if 0 < cand2[1] < 0.628 else 999.0)
                        
                        bx = bx2
                        if bx2 >= 999.0:
                            alerta = f"Seção insuficiente na alma para o momento Md2={Md2_kNcm/100:.1f} kN·m."
                            as_req = 0.0
                            as_linha_cm2 = 0.0
                        elif bx2 >= 0.628:
                            alerta = f"bx na alma ({bx2:.3f}) acima de 0,628. Aumente a seção."
                            as_req = 0.0
                            as_linha_cm2 = 0.0
                        else:
                            ks2 = 1.0 / (fyd * (1.0 - bx2 / 2.0))
                            as2 = ks2 * Md2_kNcm / d_cm
                            as_linha_cm2 = 0.0
                            
                            as1 = Md1_kNcm / (fyd * (d_cm - hf_cm / 2.0))
                            as_req = as1 + as2
                            alerta = (
                                f"Linha neutra fora da mesa colaborante (0,8x={eta * bx2 * d_cm:.1f} cm >= hf={hf_cm:.1f} cm). "
                                f"As1 (abas) = {as1:.2f} cm² | As2 (alma) = {as2:.2f} cm²."
                            )
        else:
            # Momento negativo: compressão na base (largura bw_cm)
            ln_condiz = "SIM"
            kc = (bw_cm * d_cm**2) / Md_kNcm if Md_kNcm != 0 else 0
            a_coef = -0.192 * fck_conv * kc
            b_coef = 0.48 * fck_conv * kc
            c_coef = -1.0
            
            delta = b_coef**2 - 4 * a_coef * c_coef
            if delta < 0 or a_coef == 0:
                bx = 999.0
                x1 = x2 = 0.0
            else:
                sq = math.sqrt(delta)
                x1 = (-b_coef + sq) / (2 * a_coef)
                x2 = (-b_coef - sq) / (2 * a_coef)
                if x1 < 0:
                    bx = x2 if 0 < x2 < 0.628 else 999.0
                elif x2 < 0:
                    bx = x1 if 0 < x1 < 0.628 else 999.0
                else:
                    cand = sorted([x1, x2])
                    bx = cand[0] if 0 < cand[0] < 0.628 else (cand[1] if 0 < cand[1] < 0.628 else 999.0)
            
            if bx >= 999.0:
                alerta = (
                    f"Seção insuficiente para o momento negativo Mk={Mk_kNm:+.1f} kN·m "
                    f"na seção {bw_cm:.0f}×{h_cm:.0f} cm."
                )
                as_req = 0.0
                as_linha_cm2 = 0.0
            elif bx >= 0.628:
                alerta = f"bx={bx:.3f} acima do limite 0,628 para momento negativo."
                as_req = 0.0
                as_linha_cm2 = 0.0
            elif bx >= bx_min:
                # Armadura dupla para momento negativo
                Md_lim_kNcm = (bw_cm * d_cm**2) / kc_lim
                md_exc_kNcm = Md_kNcm - Md_lim_kNcm
                ks_lim = 1.0 / (fyd * (1.0 - bx_min / 2.0))
                as1 = ks_lim * Md_lim_kNcm / d_cm
                denom = d_cm - d_lin if (d_cm - d_lin) > 0 else 0.1
                as2 = md_exc_kNcm / (fyd * denom)
                as_req = as1 + as2
                as_linha_cm2 = as2
                bx = bx_min
                alerta = (
                    f"Momento negativo com armadura dupla (bx={bx_min:.2f}). "
                    f"As = {as_req:.2f} cm² | As' = {as_linha_cm2:.2f} cm²."
                )
            else:
                ks = 1.0 / (fyd * (1.0 - bx / 2.0))
                as_req = ks * Md_kNcm / d_cm
                as_linha_cm2 = 0.0
                alerta = ""
        
        asmin = rho_min_val * bw_cm * h_cm / 100.0
        as_usado = max(as_req, asmin)
        
        if as_linha_cm2 > 0:
            area_barra_d = area_barra(diam_barra_mm)
            qtd_barras_linha = math.ceil(as_linha_cm2 / area_barra_d) if area_barra_d > 0 else 0
            as_linha_adotada = qtd_barras_linha * area_barra_d
        else:
            as_linha_adotada = 0.0
            qtd_barras_linha = 0
            
        area_barra_d = area_barra(diam_barra_mm)
        qtd_barras = math.ceil(as_usado / area_barra_d) if area_barra_d > 0 else 0
        qtd_barras = max(1, qtd_barras)
        
        # Detalha as barras reais para obter o espaçamento e disposição corretos
        try:
            inp = BeamDetailingInput(
                bw=bw_cm * 10.0,
                h=h_cm * 10.0,
                c_nom=cob_mm,
                phi_estribo=diam_estribo_mm,
                phi_barra=diam_barra_mm,
                d_max_agregado=19.0,
                total_bars=qtd_barras,
            )
            layout = BeamDetailer().detail(inp)
            cabe_status = True
            eh_real = min(lyr.h_spacing for lyr in layout.layers) / 10.0 if layout.layers else 0.0
            eh_passa = "SIM"
            qtd_barras_1cam = layout.layers[0].bar_count if layout.layers else qtd_barras
            barras_cima = qtd_barras - qtd_barras_1cam
            camadas = layout.layer_count
            status_bitola = "CABE" if camadas == 1 else f"{camadas} CAMADAS"
        except ValueError:
            layout = None
            cabe_status = False
            eh_real = 0.0
            eh_passa = "NÃO"
            qtd_barras_1cam = qtd_barras
            barras_cima = 0
            camadas = 0
            status_bitola = "NÃO CABE"

        x_cm = bx * d_cm
        bx_passa = "SIM" if bx < bx_min else "NÃO"
        espaco_disp = bw_cm - 2 * (cob_mm / 10.0) - 2 * (diam_estribo_mm / 10.0)
        eh_min = max(2.0, diam_barra_mm / 10.0, 1.2 * 1.9)
        
        resultados.append(ResultadoFlexaoT(
            momento_kNm=abs(Md_kNm),
            tipo=tipo,
            kc=round(kc if Mk_kNm > 0 else (bw_cm * d_cm**2 / Md_kNcm if Md_kNcm != 0 else 0), 3),
            a=round(a_coef if Mk_kNm > 0 else (a_coef if 'a_coef' in locals() else 0.0), 4),
            b=round(b_coef if Mk_kNm > 0 else (b_coef if 'b_coef' in locals() else 0.0), 4),
            x1=round(x1 if 'x1' in locals() else 0.0, 4),
            x2=round(x2 if 'x2' in locals() else 0.0, 4),
            bx=round(bx, 4),
            bx_passa=bx_passa,
            x_cm=round(x_cm, 2),
            linha_neutra_condiz=ln_condiz,
            bf_efetivo_cm=round(bf_efetivo, 2),
            ks=round(1.0 / (fyd * (1.0 - bx / 2.0)) if bx < 999.0 else 0.0, 3),
            as_req_cm2=round(as_req, 3),
            asmin_cm2=round(asmin, 3),
            as_usado_cm2=round(as_usado, 3),
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
            layout_convergido=layout,
            tabela_bitolas=tabela_bitolas,
            as_linha_cm2=round(as_linha_cm2, 3),
            as_linha_adotada=round(as_linha_adotada, 3),
        ))

    return resultados