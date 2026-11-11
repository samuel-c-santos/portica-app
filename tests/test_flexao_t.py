"""Testes de viga T (flexao com mesa colaborante)."""

import pytest

from core.calculos import bf_efetivo_viga_t, calcular_flexao_viga_t


class TestVigaT:
    """Cobertura: calculo de flexao para secao T."""

    def test_as_calculo_t(self, viga_exemplo_t, momentos_exemplo):
        """As,req = 4,805 cm² para Mk=96,9 em T 20×70 (bf,ef=60).

        EP-02.1: conta à mão pelo equilíbrio NBR 6118:2023, §17.3.2:
            d = 65,7 ; bf,ef = min(60, 20+20+20) = 60 cm
            fcd = 0,85·30/1,4/10 = 1,82143 kN/cm²
            Md/(fcd·bf) = 13566/(1,82143·60) = 124,126 cm²
            0,4x² − 65,7x + 124,126 = 0  →  x² − 164,25x + 310,315 = 0
            Δ = 164,25² − 4·310,315 = 25736,8 → √Δ = 160,427
            x = (164,25 − 160,427)/2 = 1,912 cm ; βx = 0,02910
            0,8x = 1,53 cm < hf = 12 (LN na mesa)
            z = 65,7 − 0,4·1,912 = 64,935 cm
            As = 13566/(43,4783·64,935) = 4,805 cm²
        """
        res = calcular_flexao_viga_t(
            h_cm=viga_exemplo_t["h_cm"],
            bw_cm=viga_exemplo_t["bw_cm"],
            bf_cm=viga_exemplo_t["bf_cm"],
            hf_cm=viga_exemplo_t["hf_cm"],
            caa=viga_exemplo_t["caa"],
            fck_mpa=viga_exemplo_t["fck_mpa"],
            diam_estribo_mm=viga_exemplo_t["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo_t["diam_barra_mm"],
            fyk_mpa=viga_exemplo_t["fyk_mpa"],
            momentos=momentos_exemplo,
            b1esq_cm=viga_exemplo_t["b1esq_cm"],
            b1dir_cm=viga_exemplo_t["b1dir_cm"],
            gamma_f=viga_exemplo_t["gamma_f"],
        )
        r = res[0]
        assert r is not None
        assert r.linha_neutra_condiz == "SIM"
        assert r.as_req_cm2 == pytest.approx(4.805, abs=0.02), f"As: {r.as_req_cm2}"
        assert r.as_necessaria_cm2 >= r.asmin_cm2 - 0.01

    def test_ln_dentro_mesa(self, viga_exemplo_t):
        """Para momento baixo, LN deve ficar dentro da mesa."""
        res = calcular_flexao_viga_t(
            h_cm=viga_exemplo_t["h_cm"],
            bw_cm=viga_exemplo_t["bw_cm"],
            bf_cm=viga_exemplo_t["bf_cm"],
            hf_cm=viga_exemplo_t["hf_cm"],
            caa=viga_exemplo_t["caa"],
            fck_mpa=viga_exemplo_t["fck_mpa"],
            diam_estribo_mm=viga_exemplo_t["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo_t["diam_barra_mm"],
            fyk_mpa=viga_exemplo_t["fyk_mpa"],
            momentos=[30.0],  # momento baixo
            b1esq_cm=viga_exemplo_t["b1esq_cm"],
            b1dir_cm=viga_exemplo_t["b1dir_cm"],
            gamma_f=viga_exemplo_t["gamma_f"],
        )
        r = res[0]
        assert r is not None
        assert r.linha_neutra_condiz == "SIM"

    def test_bf_efetivo_limitado(self):
        """bf efetivo nao deve ultrapassar bf."""
        bf_ef = bf_efetivo_viga_t(bw_cm=20, bf_cm=60, b1esq_cm=20, b1dir_cm=20)
        assert bf_ef <= 60.0

    def test_bf_efetivo_sem_b1(self):
        """Sem b1, bf efetivo deve ser igual a bf."""
        bf_ef = bf_efetivo_viga_t(bw_cm=20, bf_cm=60)
        assert bf_ef == 60.0

    def test_pele_viga_t(self, viga_exemplo_t):
        """Viga T com h=70 deve requerer armadura de pele."""
        res = calcular_flexao_viga_t(
            h_cm=viga_exemplo_t["h_cm"],
            bw_cm=viga_exemplo_t["bw_cm"],
            bf_cm=viga_exemplo_t["bf_cm"],
            hf_cm=viga_exemplo_t["hf_cm"],
            caa=viga_exemplo_t["caa"],
            fck_mpa=viga_exemplo_t["fck_mpa"],
            diam_estribo_mm=viga_exemplo_t["diam_estribo_mm"],
            diam_barra_mm=viga_exemplo_t["diam_barra_mm"],
            fyk_mpa=viga_exemplo_t["fyk_mpa"],
            momentos=[100.0],
            b1esq_cm=viga_exemplo_t["b1esq_cm"],
            b1dir_cm=viga_exemplo_t["b1dir_cm"],
            gamma_f=viga_exemplo_t["gamma_f"],
        )
        r = res[0]
        assert r is not None
        assert r.requer_pele is True

    def test_ln_fora_mesa(self):
        """Para momento alto em mesa fina, LN deve ficar fora da mesa e gerar alerta."""
        res = calcular_flexao_viga_t(
            h_cm=50,
            bw_cm=15,
            bf_cm=60,
            hf_cm=5,  # mesa fina
            caa=2,
            fck_mpa=25,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_mpa=50.0,
            momentos=[180.0],  # momento alto
            b1esq_cm=20,
            b1dir_cm=20,
            gamma_f=1.4,
        )
        r = res[0]
        assert r is not None
        assert r.linha_neutra_condiz == "NÃO"
        assert r.as_req_cm2 > 0
        assert "Linha neutra fora da mesa" in r.alerta

    def test_bf_efetivo_lo_limit(self):
        """bf efetivo deve ser limitado por 0.1 * lo."""
        # lo_esq_cm = 100 -> limite b1e = 10.0 cm
        # lo_dir_cm = 150 -> limite b1d = 15.0 cm
        # bw_cm = 20, bf_cm = 100, b1esq_cm = 20, b1dir_cm = 20
        # Com lo_esq/lo_dir: b1e limitado para 10, b1d limitado para 15 -> bf_ef = 20 + 10 + 15 = 45.0
        bf_ef = bf_efetivo_viga_t(
            bw_cm=20, bf_cm=100, b1esq_cm=20, b1dir_cm=20, lo_esq_cm=100, lo_dir_cm=150
        )
        assert bf_ef == 45.0

    def test_ln_na_alma_simples(self):
        """Verifica dimensionamento de viga T com LN na alma e armadura simples."""
        res = calcular_flexao_viga_t(
            h_cm=50,
            bw_cm=15,
            bf_cm=60,
            hf_cm=5,
            caa=2,
            fck_mpa=25,
            diam_estribo_mm=5.0,
            diam_barra_mm=12.5,
            fyk_mpa=50.0,
            momentos=[170.0],  # momento intermediário (LN na alma sob NBR)
            b1esq_cm=20,
            b1dir_cm=20,
            gamma_f=1.4,
        )
        r = res[0]
        assert r is not None
        assert r.linha_neutra_condiz == "NÃO"
        assert r.as_req_cm2 > 0
        assert r.as_linha_cm2 == 0
        assert "As1 (abas)" in r.alerta

    def test_ln_na_alma_dupla(self):
        """Verifica dimensionamento de viga T com LN na alma e armadura dupla."""
        res = calcular_flexao_viga_t(
            h_cm=50,
            bw_cm=15,
            bf_cm=60,
            hf_cm=5,
            caa=2,
            fck_mpa=25,
            diam_estribo_mm=5.0,
            diam_barra_mm=12.5,
            fyk_mpa=50.0,
            momentos=[240.0],  # momento elevado (dupla na alma sob NBR)
            b1esq_cm=20,
            b1dir_cm=20,
            gamma_f=1.4,
        )
        r = res[0]
        assert r is not None
        assert r.linha_neutra_condiz == "NÃO"
        assert r.as_req_cm2 > 0
        assert r.as_linha_cm2 > 0
        assert "armadura dupla na alma" in r.alerta
