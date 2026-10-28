"""
Testes para detecção automática de seções críticas (Fase 2.2).
"""

import os
import pytest
from typing import List, Tuple

from ui.ftool.parser import parse_momento, parse_cortante
from ui.ftool.secoes_criticas import (
    SecaoCritica,
    interpolar_y,
    detectar_maximos_locais,
    detectar_minimos_locais,
    detectar_apoios,
    detectar_pontos_momento_nulo,
    detectar_todas_secoes,
)

# Caminho para os arquivos reais
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DATA_DIR = os.path.join(BASE_DIR, "samples")
MOMENTO_FILE = os.path.join(TEST_DATA_DIR, "test_momento_fletor.txt")
CORTANTE_FILE = os.path.join(TEST_DATA_DIR, "test_esforcos_cortantes.txt")


@pytest.fixture
def dados_reais() -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """Retorna as listas de momentos e cortantes reais lidas do test/."""
    momentos = parse_momento(MOMENTO_FILE)
    cortantes = parse_cortante(CORTANTE_FILE)
    return momentos, cortantes


def test_1_detectar_maximos_locais_real(dados_reais):
    """1. Máximo local detectado corretamente (M máx ≈ +135,9 em x≈3,1)."""
    momentos, _ = dados_reais
    maximos = detectar_maximos_locais(momentos)
    
    # Encontra o pico positivo
    max_positivo = max(maximos, key=lambda p: p[1])
    assert pytest.approx(max_positivo[0], abs=0.1) == 3.1
    assert pytest.approx(max_positivo[1], abs=0.1) == 135.9


def test_2_detectar_minimos_locais_real(dados_reais):
    """2. Mínimo local detectado corretamente (M min ≈ -135,6 em x=0)."""
    momentos, _ = dados_reais
    minimos = detectar_minimos_locais(momentos)
    
    # M min ≈ -135,6 kN·m em x=0
    mini_x0 = [pt for pt in minimos if pt[0] == 0.0]
    assert len(mini_x0) == 1
    assert pytest.approx(mini_x0[0][1], abs=0.1) == -135.6


def test_3_detectar_apoios_real(dados_reais):
    """3. Apoio interno detectado (x=3,0)."""
    momentos, cortantes = dados_reais
    apoios = detectar_apoios(momentos, cortantes)
    
    # Apoio interno em x=3,0 m (devido à descontinuidade de V de +48,4 para +3,4)
    assert len(apoios) >= 1
    assert any(pytest.approx(x, abs=1e-5) == 3.0 for x in apoios)


def test_4_detectar_pontos_momento_nulo_real(dados_reais):
    """4. Pontos de momento nulo detectados."""
    momentos, _ = dados_reais
    pontos_nulo = detectar_pontos_momento_nulo(momentos)
    
    # Momento começa em -135.6, vai a +135.9, e depois termina em -132.4.
    # Deve cruzar o zero duas vezes (uma no vão 1 e outra no vão 2).
    assert len(pontos_nulo) == 2
    
    # As posições devem estar em ordem crescente
    x_nulos = [pt[0] for pt in pontos_nulo]
    assert x_nulos[0] < x_nulos[1]
    
    # Primeiro cruzamento entre x=1.1 (M=-6.9) e x=1.2 (M=3.2)
    # Segundo cruzamento entre x=6.2 (M=3.3) e x=6.3 (M=-5.5)
    assert 1.1 < x_nulos[0] < 1.2
    assert 6.2 < x_nulos[1] < 6.3


def test_5_interpolacao_cortante_no_maximo(dados_reais):
    """5. Interpolação de cortante na posição de um máximo."""
    momentos, cortantes = dados_reais
    maximos = detectar_maximos_locais(momentos)
    
    max_positivo = max(maximos, key=lambda p: p[1])
    x_max = max_positivo[0] # x ≈ 3.1
    
    v_no_max = interpolar_y(cortantes, x_max)
    # Na posição de máximo momento, V deve ser muito próximo de zero
    assert pytest.approx(v_no_max, abs=1.5) == 0.0


def test_6_secoes_criticas_ordenadas_por_x(dados_reais):
    """6. Seções críticas ordenadas por x."""
    momentos, cortantes = dados_reais
    secoes = detectar_todas_secoes(momentos, cortantes)
    
    assert len(secoes) > 0
    
    # Garante que as posições estão em ordem estritamente crescente
    for i in range(1, len(secoes)):
        assert secoes[i].x > secoes[i - 1].x


def test_7_dataclass_secao_critica():
    """7. Dataclass SecaoCritica funciona."""
    secao = SecaoCritica(
        x=2.5,
        momento=120.5,
        cortante=-45.2,
        tipo="MÁX",
        descricao="Teste secao"
    )
    assert secao.x == 2.5
    assert secao.momento == 120.5
    assert secao.cortante == -45.2
    assert secao.tipo == "MÁX"
    assert secao.descricao == "Teste secao"


def test_8_secoes_extremos_incluidas(dados_reais):
    """8. Seção no extremo (x=0, x=L) incluída."""
    momentos, cortantes = dados_reais
    secoes = detectar_todas_secoes(momentos, cortantes)
    
    # Primeira seção em x = 0.0
    assert secoes[0].x == 0.0
    # Última seção em x = 7.5
    assert secoes[-1].x == 7.5


def test_interpolacao_limites():
    """Valida a interpolação para pontos fora dos limites ou discretização fina."""
    curva = [(1.0, 10.0), (2.0, 20.0), (3.0, 30.0)]
    
    # Abaixo do limite inferior
    assert interpolar_y(curva, 0.5) == 10.0
    # Acima do limite superior
    assert interpolar_y(curva, 3.5) == 30.0
    # Exato no ponto
    assert interpolar_y(curva, 2.0) == 20.0
    # Interpolação no meio
    assert interpolar_y(curva, 1.5) == 15.0


def test_interpolacao_descontinuidade():
    """Valida que a interpolação em uma descontinuidade escolhe o valor crítico (maior absoluto)."""
    # Descontinuidade no x = 2.0
    curva = [(1.0, 10.0), (2.0, -50.0), (2.0, 100.0), (3.0, 30.0)]
    
    val = interpolar_y(curva, 2.0)
    assert val == 100.0
    
    # Outra descontinuidade onde o negativo é maior em módulo
    curva2 = [(1.0, 10.0), (2.0, -120.0), (2.0, 30.0), (3.0, 10.0)]
    val2 = interpolar_y(curva2, 2.0)
    assert val2 == -120.0
