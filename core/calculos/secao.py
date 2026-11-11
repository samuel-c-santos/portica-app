"""
MODELO DE SECAO UNICO (EP-04.1) - fonte unica de geometria, cobrimento e materiais.

Modulo-folha: nao importa nenhum outro modulo do app, para que
``engenharia``, ``ui.ftool.*`` e ``core.detailing`` possam consumi-lo sem ciclos.

Convencao unica de ``d`` (altura util, cm):

    d' = cob/10 + phi_estribo/10 + phi_barra/20      (centro da barra ao bordo)
    d  = h - d'

Qualquer calculo de ``d`` no sistema deve passar por :func:`d_linha_cm` /
:func:`altura_util_cm` ou por :attr:`BeamModel.d_cm`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

# Constantes normativas (NBR 6118:2023)
ALPHA_C = 0.85
GAMMA_C = 1.40


# Cobrimento nominal por CAA (NBR 6118 Tab. 7.2, vigas) - fonte unica.
CAA_COBRIMENTO_MM = {1: 25, 2: 30, 3: 40, 4: 50}


def d_linha_cm(cob_mm: float, diam_estribo_mm: float, diam_barra_mm: float) -> float:
    """Distancia do centro da barra de borda ao bordo da seção (cm)."""
    return cob_mm / 10.0 + diam_estribo_mm / 10.0 + diam_barra_mm / 20.0


def altura_util_cm(
    h_cm: float, cob_mm: float, diam_estribo_mm: float, diam_barra_mm: float
) -> float:
    """Altura util d = h - d' (cm). Unica definicao de ``d`` do sistema."""
    return h_cm - d_linha_cm(cob_mm, diam_estribo_mm, diam_barra_mm)


def alpha_c(fck_mpa: float) -> float:
    """Fator alpha_c do diagrama retangular (NBR 6118:2023, 8.2.10)."""
    if fck_mpa <= 50:
        return ALPHA_C
    return ALPHA_C * (1.0 - (fck_mpa - 50.0) / 200.0)


def lambda_f(fck_mpa: float) -> float:
    """Fator lambda (NBR 6118:17.4.2.2): min(0,80; 1 - fck/250)."""
    return min(0.80, 1.0 - fck_mpa / 250.0)


def fcd_mpa(fck_mpa: float) -> float:
    """Resistencia de calculo do concreto (MPa) com alpha_c da classe."""
    return alpha_c(fck_mpa) * fck_mpa / GAMMA_C


def fctm_mpa(fck_mpa: float) -> float:
    """Resistencia media a tracao (MPa), fck <= 50."""
    return 0.30 * fck_mpa ** (2 / 3)


def fctd_kn_cm2(fck_mpa: float) -> float:
    """Resistencia de calculo a tracao (kN/cm2): 0,7*fctm/gamma_c."""
    return 0.7 * fctm_mpa(fck_mpa) / 10 / GAMMA_C


def ecs_gpa(fck_mpa: float) -> float:
    """Modulo de elasticidade secante Ecs (GPa), NBR 6118:8.2.8."""
    e_ci = 5600 * math.sqrt(fck_mpa)
    alpha_i = 0.8 + 0.2 * (fck_mpa / 80)
    return e_ci * alpha_i / 1000


@dataclass(frozen=True)
class BeamModel:
    """Secao de viga imutavel: geometria + cobrimento + materiais.

    ``bf``/``hf`` so valem para secao T (``bf > bw``). Alturas/larguras em cm,
    ``fyk_kn_cm2`` em kN/cm2 (CA-50 = 50), ``fck_mpa`` em MPa.
    """

    h: float
    bw: float
    fck_mpa: float
    fyk_kn_cm2: float = 50.0
    caa: int = 1
    diam_estribo_mm: float = 5.0
    diam_barra_mm: float = 16.0
    bf: float | None = None
    hf: float | None = None
    cob_mm_override: float | None = None  # cobrimento explicito (senao, da CAA)

    # --- derivadas geometricas -------------------------------------------
    @property
    def cob_mm(self) -> float:
        if self.cob_mm_override is not None:
            return self.cob_mm_override
        return float(CAA_COBRIMENTO_MM[self.caa])

    @property
    def d_linha_cm(self) -> float:
        return d_linha_cm(self.cob_mm, self.diam_estribo_mm, self.diam_barra_mm)

    @property
    def d_cm(self) -> float:
        return self.h - self.d_linha_cm

    @property
    def is_t(self) -> bool:
        return self.bf is not None and self.hf is not None and self.bf > self.bw

    # --- derivadas de materiais ------------------------------------------
    @property
    def fcd(self) -> float:
        return fcd_mpa(self.fck_mpa)

    @property
    def fctm(self) -> float:
        return fctm_mpa(self.fck_mpa)

    @property
    def fctd(self) -> float:
        return fctd_kn_cm2(self.fck_mpa)

    @property
    def Ecs(self) -> float:  # noqa: N802 (nome pedido no EP-04.1)
        return ecs_gpa(self.fck_mpa)

    @property
    def alpha_c(self) -> float:
        return alpha_c(self.fck_mpa)

    @property
    def lambda_(self) -> float:
        return lambda_f(self.fck_mpa)

    # ``lambda`` e palavra reservada; exposta tambem via getattr(model, "lambda").
    def __getattr__(self, name: str):
        if name == "lambda":
            return lambda_f(self.fck_mpa)
        raise AttributeError(name)

    def com(self, **mudancas) -> BeamModel:
        """Novo modelo com campos substituidos (imutabilidade)."""
        return replace(self, **mudancas)
