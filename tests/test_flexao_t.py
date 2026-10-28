"""Testes de viga T (flexao com mesa colaborante)."""
import pytest
from core.calculos import calcular_flexao_viga_t, bf_efetivo_viga_t


class TestVigaT:
    """Cobertura: calculo de flexao para secao T."""

    def test_as_calculo_t(self, viga_exemplo_t, momentos_exemplo):
        """As para viga T deve ser menor que retangular equivalente (mesa ajuda)."""
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
        assert r.as_req_cm2 > 0
        assert r.as_usado_cm2 >= r.asmin_cm2 - 0.01

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
            bw_cm=20, bf_cm=100, b1esq_cm=20, b1dir_cm=20,
            lo_esq_cm=100, lo_dir_cm=150
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
            momentos=[130.0],  # momento intermediário
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
            momentos=[200.0],  # momento bastante elevado
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

