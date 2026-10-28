"""Testes da armadura de pele (NBR 6118:17.3.5.2.3)."""
import pytest
from core.calculos import calcular_armadura_pele, calcular_flexao_viga_comum


class TestArmaduraPele:
    """Cobertura: armadura de pele para vigas com h >= 60 cm."""

    def test_h_menor_60_nao_requer(self):
        """Viga com h < 60 cm nao requer armadura de pele."""
        pele = calcular_armadura_pele(50, 20, 30, 5, 16)
        assert pele["requer"] is False
        assert pele["n_barras_face"] == 0

    def test_h_60_requer(self):
        """Viga com h = 60 cm requer armadura de pele."""
        pele = calcular_armadura_pele(60, 20, 30, 5, 16)
        assert pele["requer"] is True
        assert pele["n_barras_face"] > 0

    def test_h_70_requer(self):
        """Viga com h = 70 cm requer armadura de pele."""
        pele = calcular_armadura_pele(70, 20, 30, 5, 16)
        assert pele["requer"] is True
        assert pele["n_barras_face"] > 0

    def test_espacamento_dentro_limite(self):
        """Espacamento adotado deve ser <= s_max (20 cm ou d/3)."""
        pele = calcular_armadura_pele(70, 20, 30, 5, 16)
        assert pele["requer"] is True
        assert pele["s_adotado_cm"] <= pele["s_max_cm"] + 0.1

    def test_area_minima_por_face(self):
        """Area por face deve ser >= 0,10% x A_c,alma (ate 5 cm2/m)."""
        h, bw = 70, 20
        pele = calcular_armadura_pele(h, bw, 30, 5, 16)
        assert pele["requer"] is True
        ac_alma = bw * h  # cm2
        as_min_teorico = min(0.001 * ac_alma, 5.0 * bw / 100)
        assert pele["as_pele_adotada_face_cm2"] >= as_min_teorico - 0.01

    def test_tabela_phis_completa(self):
        """Tabela deve ter 6 opcoes de diametro."""
        pele = calcular_armadura_pele(70, 20, 30, 5, 16)
        assert pele["requer"] is True
        assert len(pele["tabela_phis"]) == 6
        phis = [item["phi_mm"] for item in pele["tabela_phis"]]
        assert 5.0 in phis
        assert 16.0 in phis

    def test_tabela_phis_tem_dados(self):
        """Cada item da tabela deve ter n, s, as e cabe."""
        pele = calcular_armadura_pele(70, 20, 30, 5, 16)
        for item in pele["tabela_phis"]:
            assert item["n_barras_face"] > 0
            assert item["s_cm"] > 0
            assert item["as_cm2"] > 0
            assert isinstance(item["cabe"], bool)

    def test_phi_menor_mais_barras(self):
        """Diametro menor deve exigir mais barras (ou igual)."""
        pele = calcular_armadura_pele(90, 20, 30, 5, 16)
        n_phi5 = next(item["n_barras_face"] for item in pele["tabela_phis"] if item["phi_mm"] == 5.0)
        n_phi16 = next(item["n_barras_face"] for item in pele["tabela_phis"] if item["phi_mm"] == 16.0)
        assert n_phi5 >= n_phi16

    def test_pele_no_resultado_flexao(self):
        """ResultadoFlexao deve ter campos de pele preenchidos."""
        res = calcular_flexao_viga_comum(
            h_cm=70, bw_cm=20, caa=2, fck_mpa=30,
            diam_estribo_mm=5, diam_barra_mm=16,
            fyk_mpa=50, momentos=[100.0], gamma_f=1.4
        )
        r = res[0]
        assert r.requer_pele is True
        assert r.n_barras_pele_face > 0
        assert r.phi_pele_mm > 0
        assert len(r.tabela_pele) == 6
