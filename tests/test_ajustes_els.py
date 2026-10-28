"""
Testes para a feature de Ajustes Manuais para ELS.
"""

import os
import pytest

from ui.ftool.els import (
    AjustesELS,
    calcular_flecha,
    calcular_fissuracao,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")


def _ler_dados():
    """Lê momentos e deformações dos arquivos de amostra."""
    from ui.ftool.parser import parse_momento, parse_deformacao
    mom = parse_momento(os.path.join(SAMPLES_DIR, "test_momento_fletor.txt"))
    deform = parse_deformacao(os.path.join(SAMPLES_DIR, "test_deformacoes.txt"))
    return mom, deform


def test_ajustes_els_default():
    """Testa que AjustesELS com valores default não altera os parâmetros."""
    ajustes = AjustesELS()
    
    h_cm, d_cm, as_cm2, fck_mpa, phi_mm = ajustes.aplicar_ajustes(
        h_cm=70.0, d_cm=65.0, as_tracao_cm2=5.0,
        fck_mpa=30.0, phi_barra_mm=12.5
    )
    
    assert h_cm == 70.0
    assert d_cm == 65.0
    assert as_cm2 == 5.0
    assert fck_mpa == 30.0
    assert phi_mm == 12.5


def test_ajustes_barras_extras():
    """Testa que barras_extras aumenta a área de aço."""
    ajustes = AjustesELS(barras_extras=2)
    
    h_cm, d_cm, as_cm2, fck_mpa, phi_mm = ajustes.aplicar_ajustes(
        h_cm=70.0, d_cm=65.0, as_tracao_cm2=5.0,
        fck_mpa=30.0, phi_barra_mm=12.5
    )
    
    # Área de uma barra φ12.5 = π * (1.25/2)² = 1.227 cm²
    area_barra = 3.14159 * (1.25 / 2) ** 2
    as_esperado = 5.0 + 2 * area_barra
    
    assert abs(as_cm2 - as_esperado) < 0.01
    assert h_cm == 70.0
    assert d_cm == 65.0


def test_ajustes_h_override():
    """Testa que h_override_cm altera h e recalcula d."""
    ajustes = AjustesELS(h_override_cm=75.0)
    
    h_cm, d_cm, as_cm2, fck_mpa, phi_mm = ajustes.aplicar_ajustes(
        h_cm=70.0, d_cm=65.0, as_tracao_cm2=5.0,
        fck_mpa=30.0, phi_barra_mm=12.5,
        cobrimento_mm=25.0, diam_estribo_mm=5.0
    )
    
    assert h_cm == 75.0
    # d = h - cob - estribo - phi/2 = 75 - 2.5 - 0.5 - 0.625 = 71.375
    assert abs(d_cm - 71.375) < 0.01


def test_ajustes_fck_override():
    """Testa que fck_override_mpa altera fck."""
    ajustes = AjustesELS(fck_override_mpa=35.0)
    
    h_cm, d_cm, as_cm2, fck_mpa, phi_mm = ajustes.aplicar_ajustes(
        h_cm=70.0, d_cm=65.0, as_tracao_cm2=5.0,
        fck_mpa=30.0, phi_barra_mm=12.5
    )
    
    assert fck_mpa == 35.0
    assert h_cm == 70.0
    assert d_cm == 65.0


def test_ajustes_phi_minimo():
    """Testa que phi_minimo_mm altera phi e recalcula d."""
    ajustes = AjustesELS(phi_minimo_mm=16.0)
    
    h_cm, d_cm, as_cm2, fck_mpa, phi_mm = ajustes.aplicar_ajustes(
        h_cm=70.0, d_cm=65.0, as_tracao_cm2=5.0,
        fck_mpa=30.0, phi_barra_mm=12.5,
        cobrimento_mm=25.0, diam_estribo_mm=5.0
    )
    
    assert phi_mm == 16.0
    # d = h - cob - estribo - phi/2 = 70 - 2.5 - 0.5 - 0.8 = 66.2
    assert abs(d_cm - 66.2) < 0.01


def test_ajustes_combinados():
    """Testa combinação de múltiplos ajustes."""
    ajustes = AjustesELS(
        barras_extras=2,
        h_override_cm=75.0,
        fck_override_mpa=35.0
    )
    
    h_cm, d_cm, as_cm2, fck_mpa, phi_mm = ajustes.aplicar_ajustes(
        h_cm=70.0, d_cm=65.0, as_tracao_cm2=5.0,
        fck_mpa=30.0, phi_barra_mm=12.5,
        cobrimento_mm=25.0, diam_estribo_mm=5.0
    )
    
    assert h_cm == 75.0
    assert fck_mpa == 35.0
    assert phi_mm == 12.5
    # d = 75 - 2.5 - 0.5 - 0.625 = 71.375
    assert abs(d_cm - 71.375) < 0.01
    # As aumentado com 2 barras extras
    area_barra = 3.14159 * (1.25 / 2) ** 2
    as_esperado = 5.0 + 2 * area_barra
    assert abs(as_cm2 - as_esperado) < 0.01


def test_calcular_flecha_com_ajustes():
    """Testa que calcular_flecha aceita ajustes e produz resultados diferentes."""
    momentos, deformacoes = _ler_dados()
    
    # Sem ajustes
    resultado_base = calcular_flecha(
        h_cm=70.0, bw_cm=20.0, d_cm=65.0,
        fck_mpa=30.0, as_tracao_cm2=5.0,
        momentos=momentos, deformacoes=deformacoes,
    )
    
    # Com ajustes (aumentar h)
    ajustes = AjustesELS(h_override_cm=75.0)
    resultado_ajustado = calcular_flecha(
        h_cm=70.0, bw_cm=20.0, d_cm=65.0,
        fck_mpa=30.0, as_tracao_cm2=5.0,
        momentos=momentos, deformacoes=deformacoes,
        ajustes=ajustes,
    )
    
    # Flecha deve ser menor com h maior
    assert resultado_ajustado['flecha_total_cm'] < resultado_base['flecha_total_cm']


def test_calcular_fissuracao_com_ajustes():
    """Testa que calcular_fissuracao aceita ajustes e produz resultados diferentes."""
    momentos, _ = _ler_dados()
    
    # Sem ajustes
    resultado_base = calcular_fissuracao(
        h_cm=70.0, bw_cm=20.0, d_cm=65.0,
        caa=2, fck_mpa=30.0, fyk_mpa=50.0,
        as_tracao_cm2=5.0, phi_barra_mm=12.5,
        momentos=momentos,
    )
    
    # Com ajustes (aumentar barras)
    ajustes = AjustesELS(barras_extras=3)
    resultado_ajustado = calcular_fissuracao(
        h_cm=70.0, bw_cm=20.0, d_cm=65.0,
        caa=2, fck_mpa=30.0, fyk_mpa=50.0,
        as_tracao_cm2=5.0, phi_barra_mm=12.5,
        momentos=momentos,
        ajustes=ajustes,
    )
    
    # wk deve ser menor com mais armadura
    assert resultado_ajustado['wk_mm'] < resultado_base['wk_mm']


def test_ajustes_nao_passa_para_passa():
    """Testa que ajustes podem fazer uma viga que não passa a passar."""
    momentos, deformacoes = _ler_dados()
    
    # Viga com flecha alta (sem ajustes)
    resultado_base = calcular_flecha(
        h_cm=70.0, bw_cm=20.0, d_cm=65.0,
        fck_mpa=30.0, as_tracao_cm2=4.0,
        momentos=momentos, deformacoes=deformacoes,
    )
    
    # Aplicar ajustes para reduzir flecha
    ajustes = AjustesELS(
        h_override_cm=80.0,
        barras_extras=3
    )
    resultado_ajustado = calcular_flecha(
        h_cm=70.0, bw_cm=20.0, d_cm=65.0,
        fck_mpa=30.0, as_tracao_cm2=4.0,
        momentos=momentos, deformacoes=deformacoes,
        ajustes=ajustes,
    )
    
    # Flecha deve reduzir significativamente
    reducao = (resultado_base['flecha_total_cm'] - resultado_ajustado['flecha_total_cm']) / resultado_base['flecha_total_cm']
    assert reducao > 0.3  # Pelo menos 30% de redução


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
