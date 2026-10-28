"""Testes de conversao de unidades e constantes do motor."""
import pytest
from core.calculos import (
    fcd_mpa, fyd_kn_cm2, fctm_mpa, fck_to_kgf_cm2,
    area_barra, rho_min, GAMMA_F_TABLE,
    ALPHA_C, GAMMA_C, GAMMA_S,
)


class TestConversaoUnidades:
    """Cobertura: funcoes de conversao e constantes."""

    def test_fcd_mpa(self):
        """fcd = alpha_c * fck / gamma_c = 0.85 * 30 / 1.4 = 18.21."""
        assert abs(fcd_mpa(30) - 18.214) < 0.01

    def test_fyd_kn_cm2(self):
        """fyd = fyk / gamma_s. fyk=50 (kN/cm2) -> fyd=43.48 kN/cm2."""
        assert abs(fyd_kn_cm2(50) - 43.478) < 0.01

    def test_fyd_ca60(self):
        """CA-60: fyk=60 kN/cm2 -> fyd=52.17 kN/cm2."""
        assert abs(fyd_kn_cm2(60) - 52.174) < 0.01

    def test_fyd_ca25(self):
        """CA-25: fyk=25 kN/cm2 -> fyd=21.74 kN/cm2."""
        assert abs(fyd_kn_cm2(25) - 21.739) < 0.01

    def test_fctm_mpa_fck30(self):
        """fctm = 0.30 * fck^(2/3). Para fck=30: ~2.9 MPa."""
        assert abs(fctm_mpa(30) - 2.896) < 0.01

    def test_fck_to_kgf_cm2(self):
        """1 MPa = 10.1972 kgf/cm2. fck=30 -> 305.9."""
        assert abs(fck_to_kgf_cm2(30) - 305.916) < 0.1

    def test_area_barra_16mm(self):
        """Area de barra 16mm = pi * 1.6^2 / 4 = 2.011 cm2."""
        assert abs(area_barra(16) - 2.011) < 0.01

    def test_area_barra_5mm(self):
        """Area de barra 5mm = pi * 0.5^2 / 4 = 0.196 cm2."""
        assert abs(area_barra(5) - 0.196) < 0.01

    def test_rho_min_fck30(self):
        """rho_min para fck=30 deve ser 0.150%."""
        assert abs(rho_min(30) - 0.150) < 0.001

    def test_rho_min_fck50(self):
        """rho_min para fck=50 deve ser 0.208%."""
        assert abs(rho_min(50) - 0.208) < 0.001


class TestGammaFTable:
    """Cobertura: tabela de coeficientes gamma_f (NBR 6118 Tabela 11.1)."""

    def test_tabela_tem_3_combinacoes(self):
        assert len(GAMMA_F_TABLE) == 3

    def test_normais_1_4(self):
        assert GAMMA_F_TABLE["normais"]["gamma_f"] == 1.4

    def test_especiais_1_2(self):
        assert GAMMA_F_TABLE["especiais"]["gamma_f"] == 1.2

    def test_excepcionais_1_0(self):
        assert GAMMA_F_TABLE["excepcionais"]["gamma_f"] == 1.0

    def test_todos_tem_nome(self):
        for k, v in GAMMA_F_TABLE.items():
            assert "nome" in v
            assert "gamma_f" in v
