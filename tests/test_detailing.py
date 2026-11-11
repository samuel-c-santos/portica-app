"""
Testes para o modulo de detailing de estribos.
"""

import os

from ui.ftool.detailing import detalhar_estribos, gerar_tabela_detailing

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORTANTE_FILE = os.path.join(BASE_DIR, "samples", "test_esforcos_cortantes.txt")


def _ler_cortantes():
    from ui.ftool.parser import parse_cortante

    return parse_cortante(CORTANTE_FILE)


def test_detailing_tem_zonas():
    cortantes = _ler_cortantes()
    regioes = detalhar_estribos(
        h_cm=70,
        bw_cm=20,
        fck_mpa=30,
        fyk_mpa=50,
        fyk_estribo_kn_cm2=60,
        caa=2,
        cortantes=cortantes,
        phi_estribo_mm=5.0,
        gamma_f=1.4,
    )
    assert len(regioes) > 0


def test_cobre_toda_viga():
    cortantes = _ler_cortantes()
    regioes = detalhar_estribos(
        h_cm=70, bw_cm=20, fck_mpa=30, fyk_mpa=50, fyk_estribo_kn_cm2=60, caa=2, cortantes=cortantes
    )
    assert regioes[0]["x_inicio"] == 0.0
    assert abs(regioes[-1]["x_fim"] - 7.5) < 0.1
    for i in range(len(regioes) - 1):
        assert abs(regioes[i]["x_fim"] - regioes[i + 1]["x_inicio"]) < 0.05


def test_espacamento_dentro_limite():
    """EP-02.5: espaçamento adotado ≤ s_max real (Vsd/Vrd2), não 30 cm fixo."""
    cortantes = _ler_cortantes()
    regioes = detalhar_estribos(
        h_cm=70,
        bw_cm=20,
        fck_mpa=30,
        fyk_mpa=50,
        fyk_estribo_kn_cm2=60,
        caa=2,
        cortantes=cortantes,
        phi_estribo_mm=5.0,
        diam_barra_mm=16.0,
        cobrimento_mm=30.0,
    )
    for r in regioes:
        assert r["espacamento_cm"] <= r["s_max_cm"] + 0.05


def test_espacamento_limitado_pelo_smax_nao_por_30_fixo():
    """Ø8 com cortante baixa: o s necessário (≈43 cm) é cortado pelo s_max."""
    cortantes = _ler_cortantes()
    regioes = detalhar_estribos(
        h_cm=70,
        bw_cm=20,
        fck_mpa=30,
        fyk_mpa=50,
        fyk_estribo_kn_cm2=50,
        caa=2,
        cortantes=cortantes,
        phi_estribo_mm=8.0,
        diam_barra_mm=16.0,
        cobrimento_mm=30.0,
    )
    assert regioes
    for r in regioes:
        assert r["espacamento_cm"] <= r["s_max_cm"] + 0.05
        # o teto antigo de 30 cm não é mais aplicado cegamente
        if r["s_max_cm"] < 30.0:
            assert r["espacamento_cm"] <= r["s_max_cm"] + 0.05


def test_sem_cortantes():
    assert (
        detalhar_estribos(
            h_cm=70, bw_cm=20, fck_mpa=30, fyk_mpa=50, fyk_estribo_kn_cm2=60, caa=2, cortantes=[]
        )
        == []
    )


def test_gerar_tabela():
    cortantes = _ler_cortantes()
    regioes = detalhar_estribos(
        h_cm=70, bw_cm=20, fck_mpa=30, fyk_mpa=50, fyk_estribo_kn_cm2=60, caa=2, cortantes=cortantes
    )
    texto = gerar_tabela_detailing(regioes)
    assert "DETALHAMENTO DE ESTRIBOS" in texto
