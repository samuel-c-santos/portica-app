"""
Benchmark normativo: armadura de pele (EP-03.1).

NBR 6118:2023, §17.3.5.2.3 — vigas com h ≥ 60 cm exigem armadura lateral
mínima nas faces laterais:

    As,pele,min/face = 0,10%·A_c,alma   (cap de 5 cm²/m por face)
    s_pele,max = min(20 cm; d/3)   [a NBR §18.3.3.2-II limita a 3/2·h/2 =
    o motor usa min(20, d/3) — simplificação registrada no EP-02.6]
    espaçamento uniforme: s_adot = h_interna/(n + 1), h_interna = h − 2(c + φe)

Casos à mão (bw=20, h=70, φe=8mm, φl=16mm):

    CAA I (cob=25): d = 70 − 2,5 − 0,8 = 66,7 ; s_max = min(20, 22,23) = 20
        A_c,alma = 20·70 = 1400 ; As,min = 0,001·1400 = 1,4 cm² (< 3,5)
        h_interna = 70 − 2·(2,5 + 0,8) = 63,4 ; n_espac = ceil(63,4/20 − 1) = 3
        φ6,3 (área 0,3117): n_área = ceil(1,4/0,3117) = 5 → n = 5
        As,adot = 5·0,3117 = 1,5585 ; s_adot = 63,4/6 = 10,57 cm (arredondado 10,6)
        φ6,3 ≤ φe=8 ✓ → adota φ6,3, n=5, s=10,6

    CAA III (cob=40): d = 70 − 4 − 0,8 = 65,2 ; s_max = min(20, 21,73) = 20
        As,min = 1,4 ; h_interna = 70 − 2·4,8 = 60,4 ; n_espac = ceil(60,4/20−1) = 3
        φ6,3: n = 5 ; As,adot = 1,5585 ; s_adot = 60,4/6 = 10,07 cm (arredondado 10,1)
"""

import pytest

from core.calculos.engenharia import area_barra, calcular_armadura_pele

BASE = dict(h_cm=70.0, bw_cm=20.0, phi_estribo_mm=8.0, phi_barra_mm=16.0)


class TestPeleCAA1:
    def _pele(self, cob=25.0):
        return calcular_armadura_pele(cob_mm=cob, **BASE)

    def test_as_pele_min_face(self):
        # As,min = min(0,001·1400; 5·70/100) = min(1,4; 3,5) = 1,4 cm²/face
        assert self._pele()["as_pele_min_face_cm2"] == pytest.approx(1.4, abs=0.001)

    def test_s_pele_max(self):
        # s_max = min(20; 67/3) = 20 cm
        assert self._pele()["s_max_cm"] == pytest.approx(20.0, abs=0.05)

    def test_adotada_phi_6_3_n_5(self):
        r = self._pele()
        assert r["phi_pele_mm"] == pytest.approx(6.3, abs=0.01)
        assert r["n_barras_face"] == 5
        assert r["as_pele_adotada_face_cm2"] == pytest.approx(5 * area_barra(6.3), abs=0.01)

    def test_s_adotado(self):
        # s_adot = h_interna/(n+1) = 63,4/6 = 10,567 cm (retornado arredondado: 10,6)
        assert self._pele()["s_adotado_cm"] == pytest.approx(63.4 / 6.0, abs=0.05)


class TestPeleCAA3:
    def _pele(self):
        return calcular_armadura_pele(cob_mm=40.0, **BASE)

    def test_s_adotado_cobrimento_maior(self):
        # h_interna = 70 − 2·(4+0,8) = 60,4 ; s_adot = 60,4/6 = 10,067 cm (10,1)
        assert self._pele()["s_adotado_cm"] == pytest.approx(60.4 / 6.0, abs=0.05)

    def test_as_min_independe_do_cobrimento(self):
        # A_c,alma e o cap não dependem do cobrimento
        assert self._pele()["as_pele_min_face_cm2"] == pytest.approx(1.4, abs=0.001)

    def test_s_max_por_d(self):
        # d = 65,5 ; d/3 = 21,83 > 20 → s_max = 20
        assert self._pele()["s_max_cm"] == pytest.approx(20.0, abs=0.05)


class TestPeleNaoRequer:
    def test_h_50_nao_requer_pele(self):
        r = calcular_armadura_pele(
            h_cm=50.0, bw_cm=20.0, cob_mm=30.0, phi_estribo_mm=8.0, phi_barra_mm=16.0
        )
        assert r["requer"] is False
        assert r["as_pele_adotada_face_cm2"] == 0.0
