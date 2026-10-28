"""Fixtures compartilhadas para os testes do Pórtica App."""
import sys
import os

# Garante que o diretorio do app esta no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.calculos import (
    calcular_flexao_viga_comum,
    calcular_flexao_viga_t,
    calcular_cisalhamento_viga_comum,
    calcular_armadura_pele,
)


# ── Fixtures de viga exemplo (caso real test/) ────────────────────────────────

@pytest.fixture
def viga_exemplo():
    """Viga retangular 20x70, fck=30, CA-50, CAA-2, estribo 5mm.
    Campos compartilhados entre flexao e cisalhamento.
    """
    return {
        "h_cm": 70,
        "bw_cm": 20,
        "caa": 2,
        "fck_mpa": 30,
        "diam_estribo_mm": 5,
        "diam_barra_mm": 16,
        "fyk_mpa": 50,
        "fyk_estribo_mpa": 60,
        "gamma_f": 1.4,
    }


@pytest.fixture
def viga_exemplo_flexao(viga_exemplo):
    """Parametros para calcular_flexao_viga_comum (sem fyk_estribo_mpa)."""
    return {k: v for k, v in viga_exemplo.items() if k != "fyk_estribo_mpa"}


@pytest.fixture
def viga_exemplo_cisalhamento(viga_exemplo):
    """Parametros para calcular_cisalhamento_viga_comum."""
    return {
        "h_cm": viga_exemplo["h_cm"],
        "bw_cm": viga_exemplo["bw_cm"],
        "fck_mpa": viga_exemplo["fck_mpa"],
        "diam_estribo_mm": viga_exemplo["diam_estribo_mm"],
        "diam_barra_mm": viga_exemplo["diam_barra_mm"],
        "fyk_estribo_mpa": viga_exemplo["fyk_estribo_mpa"],
        "fyk_barra_mpa": viga_exemplo["fyk_mpa"],
        "caa": viga_exemplo["caa"],
        "gamma_f": viga_exemplo["gamma_f"],
    }


@pytest.fixture
def viga_exemplo_t():
    """Viga T 20x70 com mesa 60x12, fck=30, CA-50."""
    return {
        "h_cm": 70,
        "bw_cm": 20,
        "bf_cm": 60,
        "hf_cm": 12,
        "caa": 2,
        "fck_mpa": 30,
        "diam_estribo_mm": 5,
        "diam_barra_mm": 16,
        "fyk_mpa": 50,
        "b1esq_cm": 20,
        "b1dir_cm": 20,
        "gamma_f": 1.4,
    }


@pytest.fixture
def momentos_exemplo():
    """Momentos caracteristicos do caso test/ (kN.m)."""
    return [96.9, -96.9, 50.0]  # Mk (sem majorar)


@pytest.fixture
def cortantes_exemplo():
    """Cortantes caracteristicos do caso test/ (kN, com sinal)."""
    return [132.0, 48.0, 3.0, -123.0]


# ── Valores de referencia (calculados/manual) ─────────────────────────────────

VALORES_REFERENCIA = {
    "Md_194_88": 194.88,   # 139.2 * 1.4
    "As_esperado_8": 8.0,   # As para Md=194.88, viga 20x70, fck=30
    "Vsd_184_8": 184.8,     # 132.0 * 1.4
    "Vsd_172_2": 172.2,     # |-123.0| * 1.4
    "Vsd_60": 60.0,         # 50.0 * 1.2 (especiais)
}
