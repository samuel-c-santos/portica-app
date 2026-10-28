"""
Módulo de Estado Limite de Serviço (ELS) — flecha e fissuração.
NBR 6118:2014 — itens 17.3.2 e 17.3.3.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
import math

from core.calculos.engenharia import (
    fcd_mpa, fctm_mpa, fyd_kn_cm2, CAA_DATA,
)


@dataclass
class AjustesELS:
    """Ajustes manuais para verificação de ELS.
    
    Permite ao engenheiro explorar alternativas para atender aos limites de ELS
    sem modificar o dimensionamento automático da armadura.
    
    Attributes:
        barras_extras: Número de barras adicionais (0-10)
        phi_minimo_mm: Forçar diâmetro mínimo das barras (mm)
        h_override_cm: Substituir altura da viga (cm)
        fck_override_mpa: Substituir resistência do concreto (MPa)
    """
    barras_extras: int = 0
    phi_minimo_mm: Optional[float] = None
    h_override_cm: Optional[float] = None
    fck_override_mpa: Optional[float] = None
    
    def aplicar_ajustes(
        self,
        h_cm: float,
        d_cm: float,
        as_tracao_cm2: float,
        fck_mpa: float,
        phi_barra_mm: float,
        diam_estribo_mm: float = 5.0,
        cobrimento_mm: float = 25.0,
    ) -> Tuple[float, float, float, float, float]:
        """Aplica os ajustes aos parâmetros de cálculo.
        
        Args:
            h_cm: Altura original da viga (cm)
            d_cm: Altura útil original (cm)
            as_tracao_cm2: Área de aço original (cm²)
            fck_mpa: Resistência do concreto original (MPa)
            phi_barra_mm: Diâmetro das barras original (mm)
            diam_estribo_mm: Diâmetro do estribo (mm)
            cobrimento_mm: Cobrimento nominal (mm)
        
        Returns:
            Tuple com (h_cm_ajustado, d_cm_ajustado, as_ajustado, fck_ajustado, phi_ajustado)
        """
        # Aplicar override de h
        h_ajustado = self.h_override_cm if self.h_override_cm is not None else h_cm
        
        # Aplicar override de fck
        fck_ajustado = self.fck_override_mpa if self.fck_override_mpa is not None else fck_mpa
        
        # Aplicar override de phi mínimo
        phi_ajustado = self.phi_minimo_mm if self.phi_minimo_mm is not None else phi_barra_mm
        
        # Recalcular d_cm se h ou phi mudaram
        if h_ajustado != h_cm or phi_ajustado != phi_barra_mm:
            d_ajustado = h_ajustado - cobrimento_mm/10 - diam_estribo_mm/10 - phi_ajustado/20
        else:
            d_ajustado = d_cm
        
        # Aplicar barras extras (soma área proporcional ao phi usado)
        if self.barras_extras > 0:
            area_barra = math.pi * (phi_ajustado / 20) ** 2  # mm -> cm²
            as_ajustado = as_tracao_cm2 + self.barras_extras * area_barra
        else:
            as_ajustado = as_tracao_cm2
        
        return h_ajustado, d_ajustado, as_ajustado, fck_ajustado, phi_ajustado


def _e_modulus(fck_mpa: float) -> float:
    """Módulo de elasticidade secante (Ecs) em GPa. NBR 6118:8.2.8."""
    e_ci = 5600 * math.sqrt(fck_mpa)  # MPa
    alfa_e = 0.8 + 0.2 * (fck_mpa / 80)
    return e_ci * alfa_e / 1000  # GPa


def _propriedades_secao_t(h_cm: float, bw_cm: float, bf_cm: float, hf_cm: float) -> Tuple[float, float]:
    """Retorna o y_cg (a partir da base) e o Ic (cm4) da seção T."""
    a_alma = bw_cm * (h_cm - hf_cm)
    y_alma = (h_cm - hf_cm) / 2.0
    
    a_mesa = bf_cm * hf_cm
    y_mesa = h_cm - hf_cm / 2.0
    
    area_total = a_alma + a_mesa
    if area_total <= 0:
        return h_cm / 2.0, 0.0
        
    y_cg = (a_alma * y_alma + a_mesa * y_mesa) / area_total
    
    i_alma = (bw_cm * (h_cm - hf_cm) ** 3) / 12.0
    i_alma_steiner = i_alma + a_alma * (y_cg - y_alma) ** 2
    
    i_mesa = (bf_cm * hf_cm ** 3) / 12.0
    i_mesa_steiner = i_mesa + a_mesa * (y_cg - y_mesa) ** 2
    
    i_c = i_alma_steiner + i_mesa_steiner
    return y_cg, i_c


def _momento_inercia_bruto_viga(
    bw_cm: float, h_cm: float, is_t: bool = False, bf_cm: Optional[float] = None, hf_cm: Optional[float] = None
) -> Tuple[float, float]:
    """Retorna (y_cg_da_base, Ic_cm4) da viga."""
    if is_t and bf_cm is not None and hf_cm is not None and bf_cm > bw_cm and hf_cm < h_cm:
        return _propriedades_secao_t(h_cm, bw_cm, bf_cm, hf_cm)
    else:
        y_cg = h_cm / 2.0
        i_c = bw_cm * h_cm ** 3 / 12.0
        return y_cg, i_c


def _momento_fissuracao(
    bw_cm: float, h_cm: float, fctm_mpa: float,
    is_t: bool = False, bf_cm: Optional[float] = None, hf_cm: Optional[float] = None,
    positivo: bool = True
) -> float:
    """Momento de fissuração Mr (kN·cm). NBR 6118:17.3.1."""
    alpha = 1.3 if is_t else 1.5
    y_cg, ic = _momento_inercia_bruto_viga(bw_cm, h_cm, is_t, bf_cm, hf_cm)
    yt = y_cg if positivo else h_cm - y_cg
    if yt <= 0:
        yt = h_cm / 2.0
    fct = fctm_mpa / 10.0  # MPa → kN/cm²
    return alpha * fct * ic / yt  # kN·cm


def _estadio_ii_viga(
    h_cm: float, bw_cm: float, d_cm: float, as_cm2: float, alfa_e: float,
    is_t: bool = False, bf_cm: Optional[float] = None, hf_cm: Optional[float] = None,
    positivo: bool = True
) -> Tuple[float, float]:
    """Calcula linha neutra x_ii e momento de inércia I_ii no estádio II (T ou Retangular)."""
    if is_t and bf_cm is not None and hf_cm is not None and bf_cm > bw_cm and hf_cm < h_cm and positivo:
        # Seção T sob momento positivo (mesa comprimida no topo)
        # 1. Tenta assumir x_ii <= hf_cm
        a = bf_cm / 2.0
        b = alfa_e * as_cm2
        c = -alfa_e * as_cm2 * d_cm
        
        delta = b ** 2 - 4 * a * c
        if delta < 0 or a == 0:
            x_ii = 0.001
        else:
            x_ii = (-b + math.sqrt(delta)) / (2 * a)
            
        if x_ii <= hf_cm:
            if x_ii <= 0:
                x_ii = 0.001
            if x_ii > h_cm:
                x_ii = h_cm
            i_ii = bf_cm * x_ii ** 3 / 3.0 + alfa_e * as_cm2 * (d_cm - x_ii) ** 2
            return x_ii, i_ii
        else:
            # LN na alma (x_ii > hf_cm)
            a = bw_cm / 2.0
            b = (bf_cm - bw_cm) * hf_cm + alfa_e * as_cm2
            c = -((bf_cm - bw_cm) * hf_cm ** 2 / 2.0 + alfa_e * as_cm2 * d_cm)
            
            delta = b ** 2 - 4 * a * c
            if delta < 0 or a == 0:
                x_ii = 0.001
            else:
                x_ii = (-b + math.sqrt(delta)) / (2 * a)
                
            if x_ii <= 0:
                x_ii = 0.001
            if x_ii > h_cm:
                x_ii = h_cm
                
            i_ii = (bw_cm * x_ii ** 3 / 3.0 +
                    (bf_cm - bw_cm) * hf_cm ** 3 / 12.0 +
                    (bf_cm - bw_cm) * hf_cm * (x_ii - hf_cm / 2.0) ** 2 +
                    alfa_e * as_cm2 * (d_cm - x_ii) ** 2)
            return x_ii, i_ii
    else:
        # Seção retangular (ou T sob momento negativo, onde a mesa está tracionada)
        rho = as_cm2 / (bw_cm * d_cm) if (bw_cm * d_cm) > 0 else 0
        x_ii = d_cm * (math.sqrt(alfa_e ** 2 * rho ** 2 + 2 * alfa_e * rho) - alfa_e * rho)
        if x_ii <= 0:
            x_ii = 0.001
        if x_ii > h_cm:
            x_ii = h_cm
        i_ii = bw_cm * x_ii ** 3 / 3.0 + alfa_e * as_cm2 * (d_cm - x_ii) ** 2
        return x_ii, i_ii


def _inercia_equivalente(mk_knm: float, mr_kncm: float, ic_cm4: float, i_ii_cm4: float) -> float:
    """Momento de inércia equivalente (I_eq). NBR 6118:17.3.2.1.1."""
    mk_kncm = mk_knm * 100  # kN·m → kN·cm
    if mk_kncm <= mr_kncm or mr_kncm <= 0:
        return ic_cm4  # Estádio I (não fissurado)
    razao = mr_kncm / mk_kncm
    ieq = razao ** 3 * ic_cm4 + (1 - razao ** 3) * i_ii_cm4
    return max(ieq, i_ii_cm4)


def calcular_flecha(
    h_cm: float, bw_cm: float, d_cm: float,
    fck_mpa: float, as_tracao_cm2: float,
    momentos: List[Tuple[float, float]],
    deformacoes: List[Tuple[float, float, float, float]],
    gamma_f: float = 1.4,
    tempo_meses: float = 12.0,
    is_t: bool = False,
    bf_cm: Optional[float] = None,
    hf_cm: Optional[float] = None,
    ajustes: Optional[AjustesELS] = None,
    phi_barra_mm: float = 12.5,
    diam_estribo_mm: float = 5.0,
    cobrimento_mm: float = 25.0,
) -> dict:
    """
    Calcula flecha imediata e diferida para viga.

    Args:
        momentos: Lista de (x, Mk) — posição (m) e momento característico (kN·m)
        deformacoes: Lista de (x, d, θ, κ) do FTOOL
        tempo_meses: Idade da estrutura para cálculo da flecha diferida
        ajustes: Ajustes manuais para ELS (opcional)
        phi_barra_mm: Diâmetro das barras original (mm)
        diam_estribo_mm: Diâmetro do estribo (mm)
        cobrimento_mm: Cobrimento nominal (mm)

    Returns:
        Dict com resultados da verificação de flecha
    """
    if not deformacoes:
        return {"erro": "Dados de deformação não fornecidos."}

    # Aplicar ajustes manuais se fornecidos
    if ajustes is not None:
        h_cm, d_cm, as_tracao_cm2, fck_mpa, _ = ajustes.aplicar_ajustes(
            h_cm, d_cm, as_tracao_cm2, fck_mpa, phi_barra_mm,
            diam_estribo_mm, cobrimento_mm
        )

    L = max(p[0] for p in deformacoes)
    fctm = fctm_mpa(fck_mpa)
    ecs = _e_modulus(fck_mpa) * 1000 / 10  # GPa → kN/cm² (×1000/10 = ×100)
    alfa_e = 21000 / ecs  # Es / Ecs (adimensional)

    # Identificar o sinal do momento crítico para saber se a mesa está comprimida (momento positivo)
    momento_critico = 0.0
    if momentos:
        momento_critico = max(momentos, key=lambda p: abs(p[1]))[1]
    positivo = momento_critico >= 0

    y_cg, ic = _momento_inercia_bruto_viga(bw_cm, h_cm, is_t, bf_cm, hf_cm)
    mr = _momento_fissuracao(bw_cm, h_cm, fctm, is_t, bf_cm, hf_cm, positivo)
    x_ii, i_ii = _estadio_ii_viga(h_cm, bw_cm, d_cm, as_tracao_cm2, alfa_e, is_t, bf_cm, hf_cm, positivo)

    # I_eq para o momento máximo em valor absoluto
    mk_max = max(abs(p[1]) for p in momentos) if momentos else 0
    ieq = _inercia_equivalente(mk_max, mr, ic, i_ii)

    # Flecha por integração numérica das curvaturas reais (M/EI_eq)
    # Método: integração dupla com condições de contorno para viga bi-apoiada
    # f(0) = 0 e f(L) = 0
    momentos_sorted = sorted(momentos, key=lambda p: p[0])
    
    if len(momentos_sorted) >= 2:
        # Calcular curvaturas em cada ponto
        xs = [p[0] for p in momentos_sorted]  # posições em m
        kappas = []
        for x, mk in momentos_sorted:
            mk_abs = abs(mk)
            ieq_local = _inercia_equivalente(mk_abs, mr, ic, i_ii)
            if ieq_local <= 0:
                ieq_local = ic
            # κ = M / (E * I) — conversão: M em kN·cm, E em kN/cm², I em cm4 → κ em 1/cm
            mk_kncm = mk_abs * 100  # kN·m → kN·cm
            kappa = mk_kncm / (ecs * ieq_local)  # 1/cm
            kappas.append(kappa)
        
        # Integração numérica pelo método dos trapézios
        # θ(x) = ∫κ dx + C1
        # f(x) = ∫θ dx + C1*x + C2
        # Condições de contorno: f(0) = 0 → C2 = 0
        #                        f(L) = 0 → C1 = -∫θ dx / L
        
        # Primeira integração: θ(x) = ∫κ dx (sem constante ainda)
        thetas_raw = [0.0]  # θ(0) = 0 (valor relativo)
        for i in range(1, len(xs)):
            dx_cm = (xs[i] - xs[i-1]) * 100  # m → cm
            dtheta = (kappas[i-1] + kappas[i]) / 2 * dx_cm  # adimensional (radianos)
            theta_i = thetas_raw[-1] + dtheta
            thetas_raw.append(theta_i)
        
        # Segunda integração: f(x) = ∫θ dx (sem constantes ainda)
        flechas_raw = [0.0]  # f(0) = 0
        for i in range(1, len(xs)):
            dx_cm = (xs[i] - xs[i-1]) * 100  # m → cm
            df = (thetas_raw[i-1] + thetas_raw[i]) / 2 * dx_cm  # cm
            f_i = flechas_raw[-1] + df
            flechas_raw.append(f_i)
        
        # Aplicar condição de contorno f(L) = 0
        # f(L) = f_raw(L) + C1*L = 0 → C1 = -f_raw(L)/L
        L_cm = xs[-1] * 100  # comprimento total em cm
        if L_cm > 0:
            C1 = -flechas_raw[-1] / L_cm  # constante de integração (adimensional)
        else:
            C1 = 0.0
        
        # Calcular flechas finais com constante de integração
        flechas_finais = []
        for i, x in enumerate(xs):
            x_cm = x * 100
            f_final = flechas_raw[i] + C1 * x_cm
            flechas_finais.append(f_final)
        
        # Flecha máxima (valor absoluto máximo)
        flecha_imediata = max(abs(f) for f in flechas_finais)
    else:
        # Fallback: usar curvatura máxima se não houver pontos suficientes
        curv_max = max(abs(p[3]) for p in deformacoes) if deformacoes else 0
        flecha_imediata = curv_max * L ** 2 / 8 * 100  # m → cm

    # Flecha diferida (NBR 6118:17.3.2.1.2)
    alfa_f = 2.0 if tempo_meses > 6 else (tempo_meses / 6) * 2.0
    flecha_diferida = alfa_f * flecha_imediata
    flecha_total = flecha_imediata + flecha_diferida

    # Limites (NBR 6118: Tabela 13.3)
    limite_total = L * 100 / 250  # cm (L/250)
    limite_ativo = L * 100 / 350  # cm (L/350)
    passa_total = flecha_total <= limite_total
    passa_ativo = flecha_diferida <= limite_ativo

    return {
        "ic_cm4": round(ic, 1),
        "i_ii_cm4": round(i_ii, 1),
        "ieq_cm4": round(ieq, 1),
        "mr_kncm": round(mr, 1),
        "mk_max_knm": round(mk_max, 2),
        "flecha_imediata_cm": round(flecha_imediata, 2),
        "flecha_diferida_cm": round(flecha_diferida, 2),
        "flecha_total_cm": round(flecha_total, 2),
        "limite_total_cm": round(limite_total, 2),
        "limite_ativo_cm": round(limite_ativo, 2),
        "passa_total": passa_total,
        "passa_ativo": passa_ativo,
        "dica": _sugerir_correcao_flecha(flecha_total, limite_total, fck_mpa, h_cm, as_tracao_cm2, 12.5),
    }


def calcular_fissuracao(
    h_cm: float, bw_cm: float, d_cm: float,
    caa: int, fck_mpa: float, fyk_mpa: float,
    as_tracao_cm2: float, phi_barra_mm: float,
    momentos: List[Tuple[float, float]],
    gamma_f: float = 1.4,
    is_t: bool = False,
    bf_cm: Optional[float] = None,
    hf_cm: Optional[float] = None,
    ajustes: Optional[AjustesELS] = None,
    diam_estribo_mm: float = 5.0,
    cobrimento_mm: float = 25.0,
) -> dict:
    """
    Calcula abertura de fissura (wk). NBR 6118:17.3.3.2.

    Args:
        ajustes: Ajustes manuais para ELS (opcional)
        diam_estribo_mm: Diâmetro do estribo (mm)
        cobrimento_mm: Cobrimento nominal (mm)

    Returns:
        Dict com wk calculado e verificação
    """
    if not momentos:
        return {"erro": "Dados de momento não fornecidos."}

    # Aplicar ajustes manuais se fornecidos
    if ajustes is not None:
        h_cm, d_cm, as_tracao_cm2, fck_mpa, phi_barra_mm = ajustes.aplicar_ajustes(
            h_cm, d_cm, as_tracao_cm2, fck_mpa, phi_barra_mm,
            diam_estribo_mm, cobrimento_mm
        )

    # Parâmetros
    fctm = fctm_mpa(fck_mpa)
    fyd = fyd_kn_cm2(fyk_mpa) * 10  # kN/cm² → MPa (×10)
    ecs = _e_modulus(fck_mpa) * 1000  # GPa → MPa
    alfa_e = 210000 / ecs  # Es/Ecs
    fct = fctm

    # Momento máximo de serviço (sem majoração por gamma_f)
    mk_max = max(abs(p[1]) for p in momentos)
    m_els_kncm = mk_max * 100  # kN·m → kN·cm

    # Identificar o sinal do momento crítico para saber se a mesa está comprimida (momento positivo)
    momento_critico = 0.0
    if momentos:
        momento_critico = max(momentos, key=lambda p: abs(p[1]))[1]
    positivo = momento_critico >= 0

    # Área de concreto envolvida (Acr)
    c_nom = CAA_DATA.get(caa, {}).get("cobrimento", 3.0) / 10  # cm
    phie = phi_barra_mm / 10  # mm → cm

    # Tensão na armadura (estádio II) - corrigido modular ratio alfa_e
    d_util = d_cm
    x_ii, i_ii = _estadio_ii_viga(h_cm, bw_cm, d_util, as_tracao_cm2, alfa_e, is_t, bf_cm, hf_cm, positivo)
    if i_ii <= 0:
        i_ii = 0.01

    # σs = αe × M_els × (d - x_ii) / I_ii
    # Conversão de kN/cm² para MPa: multiplica por 10
    sigma_s_mpa = 10.0 * alfa_e * m_els_kncm * (d_util - x_ii) / i_ii

    # Cálculo de wk (item 17.3.3.2 - NBR 6118)
    eta_b = 2.25  # CA-50 (nervurado)
    phir = phie  # cm

    if sigma_s_mpa <= 0:
        wk_final = 0.0
        wk1 = 0.0
        wk2 = 0.0
    else:
        termo1 = phir / (12.5 * eta_b)
        termo2 = sigma_s_mpa / 210000
        
        # wk1: baseado no diâmetro e resistência à tração
        termo3_w1 = 3 * sigma_s_mpa / fct if fct > 0 else 0
        wk1 = termo1 * termo2 * termo3_w1 * 10  # cm → mm
        
        # wk2: baseado na taxa de armadura da área de envolvimento (rho_ri)
        h_cr = min(2.5 * (h_cm - d_util), (h_cm - x_ii) / 3.0, 0.5 * h_cm)
        
        if not positivo and is_t and bf_cm is not None and bf_cm > bw_cm:
            # Tração no topo em viga T (mesa colaborante tracionada)
            if hf_cm is not None:
                if h_cr <= hf_cm:
                    a_cr = bf_cm * h_cr
                else:
                    a_cr = bf_cm * hf_cm + bw_cm * (h_cr - hf_cm)
            else:
                a_cr = bf_cm * h_cr
        else:
            # Tração na alma (momento positivo ou viga retangular)
            a_cr = bw_cm * h_cr
            
        rho_ri = max(0.005, as_tracao_cm2 / a_cr)
        
        termo3_w2 = 4 / rho_ri + 45
        wk2 = termo1 * termo2 * termo3_w2 * 10  # cm → mm
        
        # Abertura de fissura de projeto wk é o menor dos dois valores
        wk_final = min(wk1, wk2)

    # Limite (Tabela 13.4 NBR 6118)
    limites = {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.1}  # CAA → w_k (mm)
    w_lim = limites.get(caa, 0.3)
    passa = wk_final <= w_lim

    return {
        "sigma_s_mpa": round(sigma_s_mpa, 1),
        "wk_mm": round(wk_final, 2),
        "wk_limite_mm": w_lim,
        "passa": passa,
        "x_ii_cm": round(x_ii, 2),
        "i_ii_cm4": round(i_ii, 1),
        "dica": _sugerir_correcao_fissuracao(wk_final, w_lim, sigma_s_mpa, fck_mpa, as_tracao_cm2, phi_barra_mm),
    }


def _sugerir_correcao_flecha(flecha_total, limite, fck, h_cm, as_atual, phi_atual):
    """Sugere acoes para reduzir flecha."""
    if flecha_total <= limite:
        return ""
    sugestoes = []
    excesso = (flecha_total / limite - 1) * 100
    
    if excesso > 50:
        sugestoes.append(f"Aumente a altura h da viga (atual={h_cm} cm)")
        sugestoes.append("Aumente o fck do concreto (melhora Ecs)")
    elif excesso > 20:
        sugestoes.append(f"Aumente a altura h (atual={h_cm} cm)")
        sugestoes.append(f"Aumente a armadura (As atual={as_atual:.2f} cm2)")
    else:
        sugestoes.append(f"Aumente a armadura (As atual={as_atual:.2f} cm2)")
        if phi_atual < 25:
            sugestoes.append("Use barras de maior diametro")
    
    return " | ".join(sugestoes[:2])


def _sugerir_correcao_fissuracao(wk, w_lim, sigma_s, fck, as_atual, phi_atual):
    """Sugere acoes para reduzir abertura de fissura."""
    if wk <= w_lim:
        return ""
    sugestoes = []
    # Proximo diametro menor valido (>=10mm)
    diametros_validos = [10, 12.5, 16, 20, 25, 32]
    idx = diametros_validos.index(phi_atual) if phi_atual in diametros_validos else -1
    if idx > 0:
        phi_menor = diametros_validos[idx - 1]
        sugestoes.append(f"Troque {phi_atual:.0f}mm por {phi_menor:.0f}mm (mais barras finas distribuem melhor a fissuracao)")
    if sigma_s > 250:
        sugestoes.append(f"Aumente a armadura (As atual={as_atual:.2f} cm², sigma_s={sigma_s:.0f} MPa)")
    sugestoes.append("Aumente a altura h da secao")
    return " | ".join(sugestoes[:2])


def gerar_relatorio_els(flecha: dict, fissuracao: dict) -> str:
    """Gera texto do relatorio ELS."""
    linhas = []
    linhas.append("=" * 55)
    linhas.append("  VERIFICACOES ELS (Estado Limite de Servico)")
    linhas.append("=" * 55)

    # Flecha
    linhas.append("")
    linhas.append("  -- FLECHA (NBR 6118:17.3.2) --")
    if "erro" in flecha:
        linhas.append(f"  {flecha['erro']}")
    else:
        linhas.append(f"  I_eq = {flecha['ieq_cm4']:.0f} cm4")
        linhas.append(f"  Mr   = {flecha['mr_kncm']:.1f} kN.cm")
        linhas.append(f"  Flecha imediata : {flecha['flecha_imediata_cm']:.2f} cm")
        linhas.append(f"  Flecha diferida : {flecha['flecha_diferida_cm']:.2f} cm")
        linhas.append(f"  Flecha total    : {flecha['flecha_total_cm']:.2f} cm")
        linhas.append(f"  Limite L/250    : {flecha['limite_total_cm']:.2f} cm")
        status_t = "OK" if flecha['passa_total'] else "NAO PASSA"
        linhas.append(f"  -> {status_t}")
        linhas.append(f"  Limite L/350    : {flecha['limite_ativo_cm']:.2f} cm")
        status_a = "OK" if flecha['passa_ativo'] else "NAO PASSA"
        linhas.append(f"  -> {status_a}")

    # Fissuracao
    linhas.append("")
    linhas.append("  -- FISSURACAO (NBR 6118:17.3.3) --")
    if "erro" in fissuracao:
        linhas.append(f"  {fissuracao['erro']}")
    else:
        linhas.append(f"  w_k  = {fissuracao['wk_mm']:.2f} mm")
        linhas.append(f"  w_lim = {fissuracao['wk_limite_mm']:.1f} mm")
        status = "OK" if fissuracao['passa'] else "NAO PASSA"
        linhas.append(f"  -> {status}")

    linhas.append("")
    linhas.append("=" * 55)
    return "\n".join(linhas)
