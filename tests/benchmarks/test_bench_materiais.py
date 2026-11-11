"""
Benchmark normativo: constantes e propriedades de materiais (EP-03.1).

Cada valor é calculado à mão, independentemente do motor, conforme a
NBR 6118:2023. Os docstrings trazem a fórmula e a conta.
"""

import pytest

from core.calculos.engenharia import (
    fcd_mpa,
    fctd_kn_cm2,
    fctkinf_mpa,
    fctm_mpa,
    lambda_f,
)
from ui.ftool.els import _e_modulus


class TestLamina:
    """λ (fator do diagrama retangular) — NBR 6118:2023, §17.4.2.2.

    λ = 0,8 para fck ≤ 50 MPa; λ = 1 − fck/250 para fck > 50 MPa.
    """

    def test_lambda_fck30(self):
        assert lambda_f(30) == pytest.approx(0.80, abs=1e-9)

    def test_lambda_fck50(self):
        assert lambda_f(50) == pytest.approx(0.80, abs=1e-9)

    def test_lambda_fck70(self):
        # λ = 1 − 70/250 = 1 − 0,28 = 0,72
        assert lambda_f(70) == pytest.approx(0.72, abs=1e-9)

    def test_lambda_fck90(self):
        # λ = 1 − 90/250 = 1 − 0,36 = 0,64
        assert lambda_f(90) == pytest.approx(0.64, abs=1e-9)


class TestFcd:
    """fcd = αc·fck/γc, γc = 1,4 — NBR 6118:2023, §8.2.10.

    αc = 0,85 (fck ≤ 50); αc = 0,85·[1 − (fck−50)/200] (fck > 50).
    """

    def test_fcd_fck30(self):
        # fcd = 0,85·30/1,4 = 25,5/1,4 = 18,2143 MPa
        assert fcd_mpa(30) == pytest.approx(18.2143, abs=0.001)

    def test_fcd_fck50(self):
        # fcd = 0,85·50/1,4 = 42,5/1,4 = 30,3571 MPa
        assert fcd_mpa(50) == pytest.approx(30.3571, abs=0.001)

    def test_fcd_fck90(self):
        # αc = 0,85·(1−40/200) = 0,85·0,8 = 0,68
        # fcd = 0,68·90/1,4 = 61,2/1,4 = 43,7143 MPa
        assert fcd_mpa(90) == pytest.approx(43.7143, abs=0.001)


class TestTracao:
    """Resistências à tração — NBR 6118:2023, §8.2.5."""

    def test_fctm_fck30(self):
        # fctm = 0,30·fck^(2/3) = 0,30·30^(2/3)
        # 30^(2/3) = (30³)^(2/9)... direto: 30^(1/3) = 3,10723 → ² = 9,65489
        # fctm = 0,30·9,65489 = 2,89647 MPa
        assert fctm_mpa(30) == pytest.approx(2.8965, abs=0.001)

    def test_fctm_fck50(self):
        # fctm = 0,30·50^(2/3): 50^(1/3) = 3,68403 → ² = 13,5721
        # fctm = 0,30·13,5721 = 4,0716 MPa
        assert fctm_mpa(50) == pytest.approx(4.0716, abs=0.001)

    def test_fctkinf_fck30(self):
        # fctk,inf = 0,7·fctm = 0,7·2,89647 = 2,02753 MPa
        assert fctkinf_mpa(30) == pytest.approx(2.0275, abs=0.001)

    def test_fctd_fck30(self):
        # fctd = fctk,inf/γc = 2,02753/1,4 = 1,44824 MPa = 0,144824 kN/cm²
        assert fctd_kn_cm2(30) == pytest.approx(0.144824, abs=0.00001)


class TestModuloElasticidade:
    """Ecs — NBR 6118:2023, §8.2.8.

    Eci = 5600·√fck (MPa); αi = 0,8 + 0,2·fck/80; Ecs = αi·Eci.
    """

    def test_ecs_fck30(self):
        # Eci = 5600·5,47723 = 30672,5 MPa
        # αi = 0,8 + 0,2·30/80 = 0,875
        # Ecs = 0,875·30672,5 = 26838,4 MPa = 26,8384 GPa
        assert _e_modulus(30) == pytest.approx(26.8384, abs=0.01)

    def test_ecs_fck50(self):
        # Eci = 5600·7,07107 = 39597,9 MPa
        # αi = 0,8 + 0,2·50/80 = 0,925
        # Ecs = 0,925·39597,9 = 36628,1 MPa = 36,6281 GPa
        assert _e_modulus(50) == pytest.approx(36.6281, abs=0.01)
