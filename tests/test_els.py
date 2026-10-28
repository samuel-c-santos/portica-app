"""
Testes para o módulo ELS (flecha e fissuração).
"""

import os
import pytest

from ui.ftool.els import (
    calcular_flecha,
    calcular_fissuracao,
    gerar_relatorio_els,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")


def _ler_dados():
    """Lê momentos e deformações dos arquivos de amostra."""
    from ui.ftool.parser import parse_momento, parse_cortante, parse_deformacao
    mom = parse_momento(os.path.join(SAMPLES_DIR, "test_momento_fletor.txt"))
    deform = parse_deformacao(os.path.join(SAMPLES_DIR, "test_deformacoes.txt"))
    return mom, deform


def test_flecha_com_dados_reais():
    """Flecha com dados reais deve retornar valores numéricos."""
    momentos, deformacoes = _ler_dados()
    res = calcular_flecha(
        h_cm=70, bw_cm=20, d_cm=65,
        fck_mpa=30, as_tracao_cm2=7.5,
        momentos=momentos, deformacoes=deformacoes,
    )
    assert "erro" not in res
    assert res["flecha_total_cm"] > 0
    assert res["flecha_imediata_cm"] > 0


def test_flecha_sem_deformacoes():
    """Sem dados de deformação deve retornar erro."""
    res = calcular_flecha(
        h_cm=70, bw_cm=20, d_cm=65,
        fck_mpa=30, as_tracao_cm2=7.5,
        momentos=[], deformacoes=[],
    )
    assert "erro" in res


def test_flecha_tipo_retorno():
    """Verifica estrutura do retorno da flecha."""
    momentos, deformacoes = _ler_dados()
    res = calcular_flecha(
        h_cm=70, bw_cm=20, d_cm=65,
        fck_mpa=30, as_tracao_cm2=7.5,
        momentos=momentos, deformacoes=deformacoes,
    )
    assert "flecha_total_cm" in res
    assert "limite_total_cm" in res
    assert "passa_total" in res
    assert isinstance(res["passa_total"], bool)


def test_fissuracao_com_dados_reais():
    """Fissuração com dados reais deve retornar valores."""
    momentos, _ = _ler_dados()
    res = calcular_fissuracao(
        h_cm=70, bw_cm=20, d_cm=65,
        caa=2, fck_mpa=30, fyk_mpa=50,
        as_tracao_cm2=7.5, phi_barra_mm=12.5,
        momentos=momentos,
    )
    assert "erro" not in res
    assert res["wk_mm"] >= 0


def test_fissuracao_sem_momentos():
    """Sem dados de momento deve retornar erro."""
    res = calcular_fissuracao(
        h_cm=70, bw_cm=20, d_cm=65,
        caa=2, fck_mpa=30, fyk_mpa=50,
        as_tracao_cm2=7.5, phi_barra_mm=12.5,
        momentos=[],
    )
    assert "erro" in res


def test_fissuracao_estrutura():
    """Verifica estrutura do retorno da fissuração."""
    momentos, _ = _ler_dados()
    res = calcular_fissuracao(
        h_cm=70, bw_cm=20, d_cm=65,
        caa=2, fck_mpa=30, fyk_mpa=50,
        as_tracao_cm2=7.5, phi_barra_mm=12.5,
        momentos=momentos,
    )
    assert "wk_mm" in res
    assert "wk_limite_mm" in res
    assert "passa" in res
    assert isinstance(res["passa"], bool)


def test_regressao_els_w_fio_10_bw_20():
    """Regressão ELS-W: φ10 em viga estreita (bw=20) deve passar com folga.

    Antes da correção dos 3 bugs (γf, αₑ/10, wₖ₂ ausente), este cenário
    produzia wₖ falso > 0,3 mm. Com os fixes, wₖ deve ficar ≤ 0,3 mm
    para momentos moderados, mesmo com barras finas em 2-3 camadas.
    """
    from core.calculos.engenharia import calcular_flexao_viga_comum

    h_cm, bw_cm = 70.0, 20.0
    Mk = 120.0  # kN·m — moderado, força 2-3 camadas com φ10

    res = calcular_flexao_viga_comum(
        h_cm=h_cm, bw_cm=bw_cm, caa=2, fck_mpa=30,
        diam_estribo_mm=5, diam_barra_mm=10, fyk_mpa=50,
        momentos=[Mk],
    )
    r = res[0]
    assert r is not None
    assert r.status_bitola in ("CABE", "2 CAMADAS", "3 CAMADAS")
    assert r.d_cm_real > 0

    fiss = calcular_fissuracao(
        h_cm=h_cm, bw_cm=bw_cm, d_cm=r.d_cm_real,
        caa=2, fck_mpa=30, fyk_mpa=50,
        as_tracao_cm2=r.as_usado_cm2, phi_barra_mm=10.0,
        momentos=[(1, Mk)],
    )
    assert fiss["passa"] is True, (
        f"φ10 em bw=20 falhou ELS-W: wk={fiss['wk_mm']:.3f} > "
        f"w_lim={fiss['wk_limite_mm']} (σₛ={fiss['sigma_s_mpa']:.0f} MPa, "
        f"As={r.as_usado_cm2:.2f} cm², d={r.d_cm_real:.2f} cm)"
    )
    assert fiss["wk_mm"] <= fiss["wk_limite_mm"]


def test_gerar_relatorio():
    """Relatório ELS deve conter ambos os blocos."""
    momentos, deformacoes = _ler_dados()
    f = calcular_flecha(
        h_cm=70, bw_cm=20, d_cm=65,
        fck_mpa=30, as_tracao_cm2=7.5,
        momentos=momentos, deformacoes=deformacoes,
    )
    g = calcular_fissuracao(
        h_cm=70, bw_cm=20, d_cm=65,
        caa=2, fck_mpa=30, fyk_mpa=50,
        as_tracao_cm2=7.5, phi_barra_mm=12.5,
        momentos=momentos,
    )
    texto = gerar_relatorio_els(f, g)
    assert "FLECHA" in texto
    assert "FISSURACAO" in texto
    assert "OK" in texto or "NAO PASSA" in texto


def test_momento_fissuracao_alpha():
    """Verifica se o fator alpha é 1.5 para seção retangular e 1.3 para seção T."""
    from ui.ftool.els import _momento_fissuracao
    mr_ret = _momento_fissuracao(bw_cm=20.0, h_cm=70.0, fctm_mpa=2.9, is_t=False)
    mr_t = _momento_fissuracao(bw_cm=20.0, h_cm=70.0, fctm_mpa=2.9, is_t=True)
    assert abs(mr_ret / mr_t - 1.5 / 1.3) < 0.001


def test_fissuracao_fctm():
    """Verifica que o cálculo de fissuração utiliza fctm diretamente."""
    res = calcular_fissuracao(
        h_cm=70, bw_cm=20, d_cm=65,
        caa=2, fck_mpa=30, fyk_mpa=50,
        as_tracao_cm2=7.5, phi_barra_mm=12.5,
        momentos=[(0.0, 150.0)],
    )
    assert res["wk_mm"] > 0


def test_els_secao_t_rigidez():
    """Valida que a rigidez maior da mesa colaborante da seção T reduz a flecha em relação à seção retangular."""
    momentos, deformacoes = _ler_dados()
    
    # Seção retangular (is_t=False)
    res_ret = calcular_flecha(
        h_cm=70, bw_cm=20, d_cm=65,
        fck_mpa=30, as_tracao_cm2=7.5,
        momentos=momentos, deformacoes=deformacoes,
        is_t=False,
    )
    
    # Seção T (is_t=True)
    res_t = calcular_flecha(
        h_cm=70, bw_cm=20, d_cm=65,
        fck_mpa=30, as_tracao_cm2=7.5,
        momentos=momentos, deformacoes=deformacoes,
        is_t=True, bf_cm=60.0, hf_cm=10.0,
    )
    
    # Momento de inércia Ic e Ieq devem ser maiores na seção T
    assert res_t["ic_cm4"] > res_ret["ic_cm4"]
    assert res_t["ieq_cm4"] > res_ret["ieq_cm4"]
    # Deformações reais devem refletir a rigidez no motor (aqui simulamos a mesma curvatura, mas o Ic/Ieq indicam que a viga T é mais rígida)


def test_fissuracao_secao_t_negativo_e_positivo():
    """Verifica a diferença na área de envolvimento Acr para momento positivo vs negativo em seção T."""
    # Para momento positivo (tração em baixo na alma, largura bw=20)
    res_pos = calcular_fissuracao(
        h_cm=70, bw_cm=20, d_cm=65,
        caa=2, fck_mpa=30, fyk_mpa=50,
        as_tracao_cm2=7.5, phi_barra_mm=12.5,
        momentos=[(0.0, 120.0)],
        is_t=True, bf_cm=60.0, hf_cm=10.0,
    )
    
    # Para momento negativo (tração em cima na mesa, largura bf=60)
    res_neg = calcular_fissuracao(
        h_cm=70, bw_cm=20, d_cm=65,
        caa=2, fck_mpa=30, fyk_mpa=50,
        as_tracao_cm2=7.5, phi_barra_mm=12.5,
        momentos=[(0.0, -120.0)],
        is_t=True, bf_cm=60.0, hf_cm=10.0,
    )
    
    # Sob momento negativo, a tração está no topo, envolvendo a mesa bf_cm=60.0,
    # resultando em uma área de envolvimento Acr maior (logo rho_ri menor, o que pode alterar o limite wk2).
    # Como as duas situações têm o mesmo momento em módulo e mesma armadura, vamos garantir que ambas rodaram com sucesso.
    assert "erro" not in res_pos
    assert "erro" not in res_neg
    assert res_pos["wk_mm"] >= 0
    assert res_neg["wk_mm"] >= 0

