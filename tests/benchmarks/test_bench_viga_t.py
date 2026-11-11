"""
Benchmark normativo: viga T — largura efetiva da mesa e As,min (EP-03.1).

bf,ef — NBR 6118:2023, §15.5.2:
    b1 ≤ 0,1·l0 (50% do vão entre faces de apoios... l0 = vão teórico);
    bf,ef = bw + b1,esq + b1,dir, também ≤ bf total.

As,min — Tabela 17.3 com a largura da zona tracionada; no motor o mínimo
usa a ALMA (bw) para ambas as armaduras (EP-02.3 registrou que a armadura
superior de viga T deveria usar a mesa) — o benchmark trava o comportamento
da alma, que é normativo para a armadura inferior.
"""

import pytest

from core.calculos.engenharia import bf_efetivo_viga_t, rho_min


class TestBfEfetivo:
    """bf,ef = min(bf, bw + b1e + b1d) com b1 ≤ 0,1·l0 (quando l0 informado)."""

    def test_sem_b1_retorna_bf_integral(self):
        # Comportamento do motor: sem b1 → bf integral (EP-02.3 registrará
        # a decisão de tornar o default 0,0)
        assert bf_efetivo_viga_t(20.0, 60.0) == 60.0

    def test_b1_limitado_por_0_1_lo(self):
        # b1e = b1d = 8 cm; l0 = 60 cm → limite 0,1·l0 = 6 cm
        # bf,ef = min(60, 20 + 6 + 6) = 32 cm
        assert bf_efetivo_viga_t(20.0, 60.0, 8.0, 8.0, 60.0, 60.0) == pytest.approx(32.0, abs=0.01)

    def test_b1_nao_excede_bf(self):
        # b1 grande: bf,ef = min(bf, bw + b1e + b1d) = min(60, 20+50+50) = 60
        assert bf_efetivo_viga_t(20.0, 60.0, 50.0, 50.0) == pytest.approx(60.0, abs=0.01)

    def test_l0_simetrico_b1_iguais(self):
        # b1e = 5, l0 = 40 → 0,1·40 = 4 ; bf,ef = min(60, 20+4+4) = 28
        assert bf_efetivo_viga_t(20.0, 60.0, 5.0, 5.0, 40.0, 40.0) == pytest.approx(28.0, abs=0.01)


class TestAsMinVigaT:
    """As,min do motor usa a alma: As,min = ρ_min·bw·h/100 (Tabela 17.3)."""

    def test_as_min_alma_fck30(self):
        # As,min = 0,150/100·15·50 = 1,125 cm² (bw=15, h=50)
        # Confere via calcular_flexao_viga_t com momento que zera As,req
        from core.calculos.engenharia import calcular_flexao_viga_t

        r = calcular_flexao_viga_t(
            h_cm=50.0,
            bw_cm=15.0,
            bf_cm=60.0,
            hf_cm=10.0,
            caa=2,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=12.5,
            fyk_mpa=50.0,
            momentos=[10.0],
        )[0]
        assert r.asmin_cm2 == pytest.approx(rho_min(30) * 15.0 * 50.0 / 100.0, abs=0.01)
        assert r.asmin_cm2 == pytest.approx(1.125, abs=0.01)
