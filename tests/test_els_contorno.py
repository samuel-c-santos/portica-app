"""
Testes do problema de contorno do ELS (EP-01.6).

O motor de flecha resolve um problema que não é o da viga modelada:
- BCs de bi-apoiada aplicadas a qualquer modelo FTOOL (multi-vão/engaste);
- sinal da curvatura destruído (abs);
- limites L/250 e L/350 com L = comprimento total, não o vão;
- BC f(L)=0 imposta no último ponto de momento;
- Ieq impresso ≠ Ieq usado na integração;
- Mr/I_ii de sinal global aplicados a todas as estações;
- cobrimento fixo de 3 cm no chamador (ignorando a CAA);
- as_tracao = máxima da viga inteira (errada em momento negativo).

DoD: limite L/250 contra o vão; sinal de M preservado; d do ELS = d da
flexão; ELS de multi-vão recusado com mensagem.
"""

import pytest

from ui.ftool.dimensionamento import (
    armadura_secao_critica_els,
    d_els_cm,
)
from ui.ftool.els import (
    _validar_modelo_biapoiado,
    calcular_flecha,
)

# ── Caso analítico: bi-apoiada com carga uniforme ────────────────────────────
# f_max = 5·q·L⁴/(384·EI) (estádio I, pois M < Mr)
L_M = 7.5
MMAX = 60.0  # kN·m < Mr ≈ 71.2 kN·m → I_eq = Ic em toda a viga
Q = 8.0 * MMAX / L_M**2  # kN/m


def _momentos_biapoiados(n=76):
    pts = []
    for i in range(n):
        x = L_M * i / (n - 1)
        m = Q * x * (L_M - x) / 2.0
        pts.append((round(x, 4), m))
    return pts


def _deformacoes_biapoiadas(n=76):
    # (x, d, θ, κ) do FTOOL: para viga bi-apoiada d=0 nas extremidades
    pts = []
    for i in range(n):
        x = L_M * i / (n - 1)
        pts.append((round(x, 4), 0.0 if i in (0, n - 1) else 1e-6, 0.0, 0.0))
    return pts


class TestModeloBiapoiado:
    def test_viga_continua_recusada(self):
        """Momento ≠ 0 nas extremidades → não é bi-apoiada → recusar."""
        momentos = [(0.0, -135.6), (3.75, 100.0), (7.5, -95.0)]  # engaste/contínuo
        erro = _validar_modelo_biapoiado(momentos)
        assert erro is not None
        assert "bi-apoiada" in erro.lower()

    def test_biapoiada_aceita(self):
        momentos = _momentos_biapoiados()
        assert _validar_modelo_biapoiado(momentos) is None

    def test_balanco_recusado(self):
        """Viga com balanço: momento na ponta do balanço ≠ 0 → recusar."""
        momentos = [(0.0, 0.0), (5.0, 80.0), (6.5, -60.0)]
        erro = _validar_modelo_biapoiado(momentos)
        assert erro is not None

    def test_flecha_retorna_erro_para_nao_biapoiada(self):
        momentos = [(0.0, -135.6), (3.75, 100.0), (7.5, -95.0)]
        res = calcular_flecha(
            h_cm=70,
            bw_cm=20,
            d_cm=65,
            fck_mpa=30,
            as_tracao_cm2=7.5,
            momentos=momentos,
            deformacoes=_deformacoes_biapoiadas(),
        )
        assert "erro" in res
        assert "bi-apoiada" in res["erro"]


class TestFlechaAnalitica:
    def test_flecha_bate_com_formula_analitica(self):
        """f = 5·q·L⁴/(384·EI), estádio I puro (M < Mr em toda a viga)."""
        momentos = _momentos_biapoiados()
        res = calcular_flecha(
            h_cm=70,
            bw_cm=20,
            d_cm=65,
            fck_mpa=30,
            as_tracao_cm2=7.5,
            momentos=momentos,
            deformacoes=_deformacoes_biapoiadas(),
            tempo_meses=12.0,
        )
        assert "erro" not in res

        ic = res["ic_cm4"]
        ecs = _e_modulus_kn_cm2(30)
        L_cm = L_M * 100
        f_analitica = 5.0 * (Q / 100.0) * L_cm**4 / (384.0 * ecs * ic)
        # imediata = analítica; total = 3× (αf = 2,0 + 1)
        assert res["flecha_imediata_cm"] == pytest.approx(f_analitica, rel=0.02)
        assert res["flecha_total_cm"] == pytest.approx(3.0 * f_analitica, rel=0.02)

    def test_sinal_do_momento_preservado(self):
        """Flecha com M negativo uniforme = flecha com M positivo uniforme."""
        momentos_pos = _momentos_biapoiados()
        momentos_neg = [(x, -m) for x, m in momentos_pos]
        deform = _deformacoes_biapoiadas()
        res_pos = calcular_flecha(
            h_cm=70,
            bw_cm=20,
            d_cm=65,
            fck_mpa=30,
            as_tracao_cm2=7.5,
            momentos=momentos_pos,
            deformacoes=deform,
        )
        res_neg = calcular_flecha(
            h_cm=70,
            bw_cm=20,
            d_cm=65,
            fck_mpa=30,
            as_tracao_cm2=7.5,
            momentos=momentos_neg,
            deformacoes=deform,
        )
        assert res_neg["flecha_total_cm"] == pytest.approx(res_pos["flecha_total_cm"], rel=1e-6)


def _e_modulus_kn_cm2(fck_mpa: float) -> float:
    """Ecs em kN/cm² (mesma conversão do módulo de flecha)."""
    from ui.ftool.els import _e_modulus

    return _e_modulus(fck_mpa) * 1000 / 10


class TestLimitesNoVao:
    def test_limite_l250_no_vao(self):
        """L/250 usa o vão (max−min), não o comprimento total."""
        momentos = [(0.0, 0.0), (2.5, 50.0), (5.0, 0.0)]
        res = calcular_flecha(
            h_cm=70,
            bw_cm=20,
            d_cm=65,
            fck_mpa=30,
            as_tracao_cm2=7.5,
            momentos=momentos,
            deformacoes=_deformacoes_biapoiadas(),
        )
        assert res["limite_total_cm"] == pytest.approx(500 / 250, abs=1e-2)
        assert res["limite_ativo_cm"] == pytest.approx(500 / 350, abs=1e-2)

    def test_vao_nao_comeca_em_zero(self):
        """Vão = xs[-1] − xs[0], mesmo se a malha não começa em 0."""
        momentos = [(1.0, 0.0), (3.5, 50.0), (6.0, 0.0)]
        res = calcular_flecha(
            h_cm=70,
            bw_cm=20,
            d_cm=65,
            fck_mpa=30,
            as_tracao_cm2=7.5,
            momentos=momentos,
            deformacoes=_deformacoes_biapoiadas(),
        )
        assert res["limite_total_cm"] == pytest.approx(500 / 250, abs=1e-6)


class TestIeqUsado:
    def test_ieq_retornado_e_o_da_estacao_critica(self):
        """O I_eq impresso é o usado na estação de momento crítico."""
        momentos = _momentos_biapoiados()
        res = calcular_flecha(
            h_cm=70,
            bw_cm=20,
            d_cm=65,
            fck_mpa=30,
            as_tracao_cm2=7.5,
            momentos=momentos,
            deformacoes=_deformacoes_biapoiadas(),
        )
        mk_max = max(abs(p[1]) for p in momentos)
        # I_eq no momento crítico: estádio I (M < Mr) → I_eq = Ic
        assert res["mk_max_knm"] == pytest.approx(mk_max, abs=0.01)
        assert res["ieq_cm4"] == res["ic_cm4"]


class TestAcrVigaT:
    def test_acr_t_positivo_com_hcr_acima_da_mesa(self):
        """Tração na alma de viga T com h_cr > hf: a área da mesa entra."""
        from ui.ftool.els import _area_envolvida

        # h_cr = 10 cm > hf = 8 cm → a_cr = bf·hf + bw·(h_cr − hf)
        a_cr = _area_envolvida(
            h_cm=70,
            bw_cm=20,
            bf_cm=60,
            hf_cm=8,
            h_cr=10.0,
            is_t=True,
            positivo=True,
        )
        assert a_cr == pytest.approx(60 * 8 + 20 * 2, abs=1e-6)

    def test_acr_t_positivo_com_hcr_na_mesa(self):
        from ui.ftool.els import _area_envolvida

        a_cr = _area_envolvida(
            h_cm=70,
            bw_cm=20,
            bf_cm=60,
            hf_cm=8,
            h_cr=6.0,
            is_t=True,
            positivo=True,
        )
        assert a_cr == pytest.approx(20 * 6, abs=1e-6)

    def test_acr_t_negativo_usa_mesa(self):
        from ui.ftool.els import _area_envolvida

        a_cr = _area_envolvida(
            h_cm=70,
            bw_cm=20,
            bf_cm=60,
            hf_cm=8,
            h_cr=10.0,
            is_t=True,
            positivo=False,
        )
        assert a_cr == pytest.approx(60 * 8 + 20 * 2, abs=1e-6)


class TestCobrimentoEDoEls:
    def test_cobrimento_els_usa_caa(self):
        """O cobrimento do ELS vem da CAA (antes: 3 cm fixo)."""
        d1 = d_els_cm({"h_cm": 70.0, "diam_estribo_mm": 5.0, "diam_barra_mm": 12.5, "caa": 1})
        d4 = d_els_cm({"h_cm": 70.0, "diam_estribo_mm": 5.0, "diam_barra_mm": 12.5, "caa": 4})
        # CAA I: cob=25mm; CAA IV: cob=50mm
        assert d1 == pytest.approx(70 - 2.5 - 0.5 - 0.625, abs=1e-6)
        assert d4 == pytest.approx(70 - 5.0 - 0.5 - 0.625, abs=1e-6)

    def test_d_els_usa_d_da_flexao_quando_disponivel(self):
        """A d do ELS é a mesma da flexão (d convergida)."""
        d = d_els_cm(
            {"h_cm": 70.0, "diam_estribo_mm": 5.0, "diam_barra_mm": 12.5, "caa": 2},
            d_cm_flexao=63.5,
        )
        assert d == pytest.approx(63.5, abs=1e-6)


class TestArmaduraSecaoCritica:
    def test_armadura_da_secao_critica_nao_maximo_global(self):
        """ELS usa a armadura da seção de maior |Mk|, não o máximo global.

        Antes: max(as de todas as seções) alimentava I_ii — em região de
        momento negativo usava a armadura errada (inferior).
        """
        from ui.ftool.secoes_criticas import SecaoCritica

        secoes = [
            SecaoCritica(x=1.0, momento=100.0, cortante=50.0, tipo="MÁX", descricao="p"),
            SecaoCritica(x=4.0, momento=-250.0, cortante=80.0, tipo="MÍN", descricao="n"),
        ]

        # Simula resultados alinhados (as_necessaria_cm2)
        class RF:
            def __init__(self, as_necessaria_cm2, bf_efetivo_cm=None):
                self.as_necessaria_cm2 = as_necessaria_cm2
                self.bf_efetivo_cm = bf_efetivo_cm

        resultados = [
            {"resultado_flexao": RF(8.0, 40.0)},
            {"resultado_flexao": RF(14.0, 20.0)},
        ]
        as_tracao, bf_ef = armadura_secao_critica_els(secoes, resultados)
        assert as_tracao == pytest.approx(14.0, abs=1e-6)  # seção de M=-250
        assert bf_ef == pytest.approx(20.0, abs=1e-6)

    def test_sem_secoes_retorna_zero(self):
        assert armadura_secao_critica_els([], []) == (0.0, None)
