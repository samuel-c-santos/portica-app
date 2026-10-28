"""
Testes para Envelope de Combinações (Fase 2.5).
"""

import os
import pytest
from ui.ftool.parser import parse_momento, parse_cortante
from ui.ftool.envelope import calcular_envelope, detectar_secoes_envelope, gerar_relatorio_envelope


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DATA_DIR = os.path.join(BASE_DIR, "samples")
MOMENTO_FILE = os.path.join(TEST_DATA_DIR, "test_momento_fletor.txt")
CORTANTE_FILE = os.path.join(TEST_DATA_DIR, "test_esforcos_cortantes.txt")


@pytest.fixture
def base_curves():
    """Lê as curvas originais de teste."""
    momentos = parse_momento(MOMENTO_FILE)
    cortantes = parse_cortante(CORTANTE_FILE)
    return momentos, cortantes


def test_1_envelope_combinacoes_identicas(base_curves):
    """1. Testar que envelope de duas combinações idênticas coincide com os valores originais."""
    momentos, cortantes = base_curves
    
    combs = [
        {"nome": "Combinação 1", "momentos": momentos, "cortantes": cortantes},
        {"nome": "Combinação 2", "momentos": momentos, "cortantes": cortantes},
    ]
    
    env = calcular_envelope(combs)
    
    # Valores máximos e mínimos devem coincidir em tamanho e valores
    assert len(env["momentos_max"]) == len(momentos)
    assert len(env["momentos_min"]) == len(momentos)
    
    for i, (orig_x, orig_m) in enumerate(momentos):
        assert env["momentos_max"][i][0] == pytest.approx(orig_x)
        assert env["momentos_max"][i][1] == pytest.approx(orig_m)
        assert env["momentos_min"][i][1] == pytest.approx(orig_m)


def test_2_envelope_valores_limites(base_curves):
    """2. Testar que os limites do envelope de teste estão próximos aos valores de referência."""
    momentos, cortantes = base_curves
    combs = [
        {"nome": "Combinação 1", "momentos": momentos, "cortantes": cortantes},
        {"nome": "Combinação 2", "momentos": momentos, "cortantes": cortantes},
    ]
    
    env = calcular_envelope(combs)
    
    max_m = max(p[1] for p in env["momentos_max"])
    min_m = min(p[1] for p in env["momentos_min"])
    max_v = max(p[1] for p in env["cortantes_max"])
    min_v = min(p[1] for p in env["cortantes_min"])
    
    # M máx ≈ +135,9, M min ≈ -135,6
    assert max_m == pytest.approx(135.9, abs=0.5)
    assert min_m == pytest.approx(-135.6, abs=0.5)
    
    # V máx ≈ +132,4, V min ≈ -122,6
    assert max_v == pytest.approx(132.4, abs=0.5)
    assert min_v == pytest.approx(-122.6, abs=0.5)


def test_3_detectar_secoes_envelope(base_curves):
    """3. Testar que a detecção de seções críticas do envelope extrai os pontos e assinala as origens."""
    momentos, cortantes = base_curves
    combs = [
        {"nome": "Comb 1", "momentos": momentos, "cortantes": cortantes},
        {"nome": "Comb 2", "momentos": momentos, "cortantes": cortantes},
    ]
    
    env = calcular_envelope(combs)
    secoes = detectar_secoes_envelope(combs, env)
    
    assert len(secoes) > 0
    # Verifica se algum ponto tem tipo MÁX perto de 3.1m
    max_sec = next((s for s in secoes if s.tipo == "MÁX" and abs(s.x - 3.1) < 0.2), None)
    assert max_sec is not None
    assert "Comb 1" in max_sec.origem or "Comb 2" in max_sec.origem


def test_4_gerar_relatorio_envelope(base_curves):
    """4. Testar a geração do relatório textual do envelope."""
    momentos, cortantes = base_curves
    combs = [
        {"nome": "Combinação A", "momentos": momentos, "cortantes": cortantes},
        {"nome": "Combinação B", "momentos": momentos, "cortantes": cortantes},
    ]
    env = calcular_envelope(combs)
    secoes = detectar_secoes_envelope(combs, env)
    
    dados_viga = {
        "h_cm": 70.0,
        "bw_cm": 20.0,
        "caa": 2,
        "fck_mpa": 30.0,
        "diam_estribo_mm": 5.0,
        "diam_barra_mm": 16.0,
        "fyk_mpa": 50.0,
        "fyk_estribo_mpa": 60.0,
        "gamma_f": 1.4,
    }
    
    relatorio = gerar_relatorio_envelope(dados_viga, env, secoes)
    
    assert "RELATÓRIO DO ENVELOPE DE COMBINAÇÕES" in relatorio
    assert "Combinação A" in relatorio
    assert "Seção em x =" in relatorio


def test_5_envelope_vazio():
    """5. Testar que envelope com lista vazia retorna dicionário vazio."""
    env = calcular_envelope([])
    assert env["momentos_max"] == []
    assert env["momentos_min"] == []
    assert env["cortantes_max"] == []
    assert env["cortantes_min"] == []


def test_6_envelope_combinacoes_diferentes(base_curves):
    """6. Testar envelope com uma combinação majorada por 1.2."""
    momentos, cortantes = base_curves
    
    # Combinação 2 terá todos os valores multiplicados por 1.2
    momentos_2 = [(x, m * 1.2) for x, m in momentos]
    cortantes_2 = [(x, v * 1.2) for x, v in cortantes]
    
    combs = [
        {"nome": "Comb 1", "momentos": momentos, "cortantes": cortantes},
        {"nome": "Comb 2", "momentos": momentos_2, "cortantes": cortantes_2},
    ]
    
    env = calcular_envelope(combs)
    
    # Para momento positivo, a Comb 2 (majorada) deve governar o máximo
    # Para momento negativo, a Comb 2 (majorada mais negativa) deve governar o mínimo
    for idx, (x, m) in enumerate(momentos):
        env_max = env["momentos_max"][idx][1]
        env_min = env["momentos_min"][idx][1]
        
        if m > 0:
            assert env_max == pytest.approx(m * 1.2)
            assert env_min == pytest.approx(m)
        elif m < 0:
            assert env_max == pytest.approx(m)
            assert env_min == pytest.approx(m * 1.2)
