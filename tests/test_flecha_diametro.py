"""
Teste de regressão: flecha deve variar com o diâmetro da barra.
Valida que o bug de flecha constante (independente de φ) foi corrigido.
"""

import os
import pytest

from ui.ftool.els import calcular_flecha

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")


def _ler_dados():
    """Lê momentos e deformações dos arquivos de amostra."""
    from ui.ftool.parser import parse_momento, parse_deformacao
    mom = parse_momento(os.path.join(SAMPLES_DIR, "test_momento_fletor.txt"))
    deform = parse_deformacao(os.path.join(SAMPLES_DIR, "test_deformacoes.txt"))
    return mom, deform


def test_flecha_varia_com_diametro_barra():
    """Flecha deve ser diferente para diâmetros de barra diferentes.
    
    Bug anterior: flecha usava curvaturas do FTOOL (fixas), ignorando I_eq.
    Após correção: flecha é calculada por integração numérica de M/(E*I_eq),
    onde I_eq depende de As (que depende do diâmetro).
    """
    momentos, deformacoes = _ler_dados()
    
    # Parâmetros fixos
    h_cm = 70.0
    bw_cm = 20.0
    fck_mpa = 30.0
    
    # Cenário 1: φ10 (As menor, d menor)
    d_cm_phi10 = h_cm - 3.0 - 0.5 - 1.0/2  # cob + estribo + φ/2
    as_phi10 = 3.0  # cm² (exemplo: 3φ10 = 2.36 cm², mas vamos usar 3.0 para simplificar)
    
    flecha_phi10 = calcular_flecha(
        h_cm=h_cm, bw_cm=bw_cm, d_cm=d_cm_phi10,
        fck_mpa=fck_mpa, as_tracao_cm2=as_phi10,
        momentos=momentos, deformacoes=deformacoes,
    )
    
    # Cenário 2: φ20 (As maior, d menor ainda)
    d_cm_phi20 = h_cm - 3.0 - 0.5 - 2.0/2
    as_phi20 = 9.0  # cm² (exemplo: 3φ20 = 9.42 cm²)
    
    flecha_phi20 = calcular_flecha(
        h_cm=h_cm, bw_cm=bw_cm, d_cm=d_cm_phi20,
        fck_mpa=fck_mpa, as_tracao_cm2=as_phi20,
        momentos=momentos, deformacoes=deformacoes,
    )
    
    # Cenário 3: φ16 com As intermediário
    d_cm_phi16 = h_cm - 3.0 - 0.5 - 1.6/2
    as_phi16 = 6.0  # cm²
    
    flecha_phi16 = calcular_flecha(
        h_cm=h_cm, bw_cm=bw_cm, d_cm=d_cm_phi16,
        fck_mpa=fck_mpa, as_tracao_cm2=as_phi16,
        momentos=momentos, deformacoes=deformacoes,
    )
    
    # Validações
    assert "erro" not in flecha_phi10
    assert "erro" not in flecha_phi20
    assert "erro" not in flecha_phi16
    
    # As flechas devem ser diferentes (não constantes)
    f10 = flecha_phi10["flecha_imediata_cm"]
    f16 = flecha_phi16["flecha_imediata_cm"]
    f20 = flecha_phi20["flecha_imediata_cm"]
    
    assert f10 > 0, f"Flecha φ10 deve ser positiva: {f10}"
    assert f16 > 0, f"Flecha φ16 deve ser positiva: {f16}"
    assert f20 > 0, f"Flecha φ20 deve ser positiva: {f20}"
    
    # Não devem ser todas iguais (bug principal)
    assert not (abs(f10 - f16) < 0.001 and abs(f16 - f20) < 0.001), \
        f"Flechas são idênticas (bug): φ10={f10:.3f}, φ16={f16:.3f}, φ20={f20:.3f}"
    
    # Maior As → menor flecha (mais rígido)
    # φ20 tem As=9.0, φ16 tem As=6.0, φ10 tem As=3.0
    # Então: f20 < f16 < f10 (em termos absolutos)
    assert f20 < f10, f"Flecha φ20 ({f20:.3f}) deveria ser < φ10 ({f10:.3f})"
    assert f16 < f10, f"Flecha φ16 ({f16:.3f}) deveria ser < φ10 ({f10:.3f})"


def test_flecha_secao_t_varia_com_as():
    """Flecha em seção T também deve variar com As."""
    momentos, deformacoes = _ler_dados()
    
    h_cm, bw_cm = 70.0, 20.0
    bf_cm, hf_cm = 60.0, 10.0
    fck_mpa = 30.0
    d_cm = 65.0
    
    # As baixo
    flecha_baixo = calcular_flecha(
        h_cm=h_cm, bw_cm=bw_cm, d_cm=d_cm,
        fck_mpa=fck_mpa, as_tracao_cm2=4.0,
        momentos=momentos, deformacoes=deformacoes,
        is_t=True, bf_cm=bf_cm, hf_cm=hf_cm,
    )
    
    # As alto
    flecha_alto = calcular_flecha(
        h_cm=h_cm, bw_cm=bw_cm, d_cm=d_cm,
        fck_mpa=fck_mpa, as_tracao_cm2=10.0,
        momentos=momentos, deformacoes=deformacoes,
        is_t=True, bf_cm=bf_cm, hf_cm=hf_cm,
    )
    
    f_baixo = flecha_baixo["flecha_imediata_cm"]
    f_alto = flecha_alto["flecha_imediata_cm"]
    
    assert f_baixo > 0 and f_alto > 0
    assert abs(f_baixo - f_alto) > 0.01, \
        f"Flechas T são idênticas: As_baixo={f_baixo:.3f}, As_alto={f_alto:.3f}"
    
    # Maior As → menor flecha
    assert f_alto < f_baixo, f"Flecha As_alto ({f_alto:.3f}) deveria ser < As_baixo ({f_baixo:.3f})"


if __name__ == "__main__":
    test_flecha_varia_com_diametro_barra()
    test_flecha_secao_t_varia_com_as()
