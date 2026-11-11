"""
Testes das guardas de denominador e validação de entrada (EP-01.4).

DoD: fck=0, seção sem braço para armadura dupla e combinação malformada
produzem erro explícito — nunca ZeroDivisionError/KeyError cru nem
número sentinela (X = 999·d).
"""

import pytest

from core.calculos.engenharia import calcular_flexao_viga_comum, calcular_flexao_viga_t
from ui.ftool.envelope import calcular_envelope, detectar_secoes_envelope


class TestFckValidacao:
    def test_fck_zero_produz_erro_explicito(self):
        with pytest.raises(ValueError, match="fck"):
            calcular_flexao_viga_comum(
                h_cm=50.0,
                bw_cm=20.0,
                caa=2,
                fck_mpa=0.0,
                diam_estribo_mm=5.0,
                diam_barra_mm=16.0,
                fyk_mpa=50.0,
                momentos=[60.0],
            )

    def test_fck_negativo_produz_erro_explicito(self):
        with pytest.raises(ValueError, match="fck"):
            calcular_flexao_viga_comum(
                h_cm=50.0,
                bw_cm=20.0,
                caa=2,
                fck_mpa=-30.0,
                diam_estribo_mm=5.0,
                diam_barra_mm=16.0,
                fyk_mpa=50.0,
                momentos=[60.0],
            )

    def test_fck_zero_viga_t_produz_erro_explicito(self):
        with pytest.raises(ValueError, match="fck"):
            calcular_flexao_viga_t(
                h_cm=50.0,
                bw_cm=15.0,
                bf_cm=60.0,
                hf_cm=10.0,
                caa=2,
                fck_mpa=0.0,
                diam_estribo_mm=5.0,
                diam_barra_mm=12.5,
                fyk_mpa=50.0,
                momentos=[80.0],
            )


class TestBracoArmaduraDupla:
    def test_secao_rasa_sem_braco_recusada_com_erro_legivel(self):
        """h=8, Ø12.5, cob=30: d − d' < 0 → recusa com braço citado.

        Antes: fallback silencioso de denominador 0,1 cm gerava As,req
        negativo (−55,77 cm²) que só era pego (por sorte) pela invariante
        de As,req ≥ 0 do EP-01.3, sem explicar a causa.
        """
        with pytest.raises(ValueError, match="braço"):
            calcular_flexao_viga_comum(
                h_cm=8.0,
                bw_cm=20.0,
                caa=2,
                fck_mpa=30.0,
                diam_estribo_mm=6.3,
                diam_barra_mm=12.5,
                fyk_mpa=50.0,
                momentos=[10.0],
            )


class TestEnvelopeCombMalformada:
    def test_combinacao_sem_momentos_nao_levanta_keyerror(self):
        """Combinação com só cortantes não pode explodir em KeyError."""
        combinacoes = [
            {
                "nome": "C1",
                "momentos": [(0.0, 0.0), (5.0, 100.0), (10.0, 0.0)],
                "cortantes": [(0.0, 50.0), (5.0, 0.0), (10.0, -50.0)],
            },
            {
                "nome": "C2",
                "cortantes": [(0.0, 30.0), (10.0, -30.0)],
            },
        ]
        env = calcular_envelope(combinacoes)
        secoes = detectar_secoes_envelope(combinacoes, env)
        assert isinstance(secoes, list)

    def test_combinacao_sem_cortantes_nao_levanta_keyerror(self):
        combinacoes = [
            {
                "nome": "C1",
                "momentos": [(0.0, 0.0), (5.0, 100.0), (10.0, 0.0)],
            },
        ]
        env = calcular_envelope(combinacoes)
        secoes = detectar_secoes_envelope(combinacoes, env)
        assert isinstance(secoes, list)


class TestSemSentinelaBx999:
    def test_t_negativo_x_cm_nunca_sentinela(self):
        """Seção recusada nunca imprime X = 999·d no resultado.

        EP-02.1: o equilíbrio NBR + armadura dupla elimina o sentinela bx=999
        do caminho retangular; a seção é recusada pelo detalhamento, com x
        finito e menor que d.
        """
        res = calcular_flexao_viga_t(
            h_cm=50.0,
            bw_cm=12.0,
            bf_cm=60.0,
            hf_cm=10.0,
            caa=2,
            fck_mpa=30.0,
            diam_estribo_mm=5.0,
            diam_barra_mm=16.0,
            fyk_mpa=50.0,
            momentos=[-400.0],
        )
        r = res[0]
        assert r.bx == pytest.approx(0.45, abs=1e-9)
        assert r.bx < 0.628
        assert r.x_cm is not None and r.x_cm < r.d_cm_real
        assert r.status_bitola in ("NÃO CABE", "NÃO CONVERGIU")
