"""
Módulo para detecção automática de seções críticas a partir de esforços do FTOOL.
Fase 2.2 — Detecção automática de seções críticas
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional


@dataclass
class SecaoCritica:
    x: float          # posição (m)
    momento: float    # momento fletor (kN·m)
    cortante: float   # esforço cortante (kN)
    tipo: str         # "MÁX", "MÍN", "APOIO", "M_NULO", "EXTREMO"
    descricao: str    # descrição textual da seção
    origem: str = ""  # nome da combinação de origem (ex: "Combinação 1")


def interpolar_y(curva: List[Tuple[float, float]], x_target: float) -> float:
    """
    Interpola linearmente o valor de y para um x_target em uma curva (lista de tuplas (x, y)).
    Se houver descontinuidade (múltiplos valores de y para o mesmo x_target),
    retorna o valor de maior valor absoluto (crítico para dimensionamento).
    """
    if not curva:
        return 0.0

    # Ordena para garantir
    sorted_curva = sorted(curva, key=lambda p: p[0])

    # Verifica se existe o ponto exato na curva (ou muito próximo)
    matches = [pt[1] for pt in sorted_curva if abs(pt[0] - x_target) < 1e-5]
    if matches:
        return max(matches, key=abs)

    if x_target <= sorted_curva[0][0]:
        return sorted_curva[0][1]
    if x_target >= sorted_curva[-1][0]:
        return sorted_curva[-1][1]

    # Interpolação linear
    for i in range(len(sorted_curva) - 1):
        x1, y1 = sorted_curva[i]
        x2, y2 = sorted_curva[i + 1]
        if x1 <= x_target <= x2:
            if abs(x2 - x1) < 1e-5:
                return max(y1, y2, key=abs)
            return y1 + (x_target - x1) * (y2 - y1) / (x2 - x1)

    return 0.0


def detectar_maximos_locais(pontos: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Detecta máximos locais na curva de momentos ou cortantes.
    Um ponto (xi, yi) é máximo local se yi >= yi-1 e yi >= yi+1.
    (>= em vez de > para capturar platôs de pico)
    Pontos extremos/fronteira são considerados máximos locais se forem maiores ou iguais que seus vizinhos imediatos.
    """
    if len(pontos) < 2:
        return []

    sorted_pts = sorted(pontos, key=lambda p: p[0])
    maximos = []
    n = len(sorted_pts)

    if sorted_pts[0][1] >= sorted_pts[1][1]:
        maximos.append(sorted_pts[0])

    for i in range(1, n - 1):
        if sorted_pts[i][1] >= sorted_pts[i - 1][1] and sorted_pts[i][1] >= sorted_pts[i + 1][1]:
            maximos.append(sorted_pts[i])

    if sorted_pts[-1][1] >= sorted_pts[-2][1]:
        maximos.append(sorted_pts[-1])

    return maximos


def detectar_minimos_locais(pontos: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Detecta mínimos locais na curva.
    Um ponto (xi, yi) é mínimo local se yi <= yi-1 e yi <= yi+1.
    (<= em vez de < para capturar platôs de vale)
    Pontos extremos/fronteira são considerados mínimos locais se forem menores ou iguais que seus vizinhos imediatos.
    """
    if len(pontos) < 2:
        return []

    sorted_pts = sorted(pontos, key=lambda p: p[0])
    minimos = []
    n = len(sorted_pts)

    if sorted_pts[0][1] <= sorted_pts[1][1]:
        minimos.append(sorted_pts[0])

    for i in range(1, n - 1):
        if sorted_pts[i][1] <= sorted_pts[i - 1][1] and sorted_pts[i][1] <= sorted_pts[i + 1][1]:
            minimos.append(sorted_pts[i])

    if sorted_pts[-1][1] <= sorted_pts[-2][1]:
        minimos.append(sorted_pts[-1])

    return minimos


def detectar_apoios(momentos: List[Tuple[float, float]], cortantes: List[Tuple[float, float]]) -> List[float]:
    """
    Detecta as posições x dos apoios:
    1. Descontinuidades na curva de cortante (dois pontos com mesmo x)
    2. Extremos do vão (x_min, x_max) — assume-se que todo vão tem apoios nas extremidades
    """
    apoios = []
    sorted_cortantes = sorted(cortantes, key=lambda p: p[0])
    sorted_momentos = sorted(momentos, key=lambda p: p[0])

    # 1. Descontinuidades de cortante
    for i in range(1, len(sorted_cortantes)):
        x_prev, _ = sorted_cortantes[i - 1]
        x_curr, _ = sorted_cortantes[i]
        if abs(x_curr - x_prev) < 1e-5:
            if not apoios or abs(apoios[-1] - x_curr) > 1e-5:
                apoios.append(x_curr)

    # 2. Extremos do vão são sempre apoios
    if sorted_momentos:
        x_min = sorted_momentos[0][0]
        x_max = sorted_momentos[-1][0]
        if not any(abs(x_min - a) < 1e-5 for a in apoios):
            apoios.append(x_min)
        if not any(abs(x_max - a) < 1e-5 for a in apoios):
            apoios.append(x_max)

    return apoios


def detectar_pontos_momento_nulo(pontos: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Detecta onde M(x) cruza o zero (mudança de sinal entre pontos consecutivos).
    Faz a interpolação linear para achar a coordenada x exata onde M = 0.
    """
    pontos_nulo = []
    sorted_pts = sorted(pontos, key=lambda p: p[0])
    n = len(sorted_pts)
    
    i = 0
    while i < n:
        x, m = sorted_pts[i]
        if abs(m) < 1e-10:
            pontos_nulo.append((x, 0.0))
            i += 1
            continue
            
        if i < n - 1:
            x_next, m_next = sorted_pts[i + 1]
            if m * m_next < 0:
                # Interpolação linear da raiz
                x_zero = x - m * (x_next - x) / (m_next - m)
                pontos_nulo.append((x_zero, 0.0))
        i += 1
        
    return pontos_nulo


def calcular_lo_para_secao(
    x_secao: float,
    pontos_momento_nulo: List[Tuple[float, float]],
    x_min: float,
    x_max: float
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calcula os vãos teóricos l0 esquerdo e direito para uma seção crítica.
    
    l0 é a distância entre pontos de momento nulo (NBR 6118:15.5.2).
    Para cada seção, retorna (l0_esq, l0_dir) em cm:
    - l0_esq: distância do ponto de M=0 à esquerda até o ponto de M=0 à direita
    - l0_dir: mesma coisa (vão teórico ao redor da seção)
    
    Se não houver pontos de M=0, retorna (None, None) — sem limitação de b1.
    
    Args:
        x_secao: posição x da seção crítica (m)
        pontos_momento_nulo: lista de (x, 0.0) onde M cruza zero
        x_min: extremo esquerdo da viga (m)
        x_max: extremo direito da viga (m)
    
    Returns:
        (l0_esq_cm, l0_dir_cm) em cm, ou (None, None) se não aplicável
    """
    if not pontos_momento_nulo:
        return None, None
    
    # Encontrar pontos de M=0 adjacentes à seção
    x_nulos = sorted([x for x, _ in pontos_momento_nulo])
    
    # Ponto de M=0 à esquerda (mais próximo e < x_secao)
    x_nulo_esq = None
    for xn in reversed(x_nulos):
        if xn < x_secao - 1e-5:
            x_nulo_esq = xn
            break
    
    # Ponto de M=0 à direita (mais próximo e > x_secao)
    x_nulo_dir = None
    for xn in x_nulos:
        if xn > x_secao + 1e-5:
            x_nulo_dir = xn
            break
    
    # Se não encontrou pontos de M=0 em ambos os lados, não há limitação
    if x_nulo_esq is None or x_nulo_dir is None:
        return None, None
    
    # l0 = distância entre os dois pontos de M=0
    lo_m = x_nulo_dir - x_nulo_esq
    lo_cm = lo_m * 100
    
    return lo_cm, lo_cm


def detectar_todas_secoes(momentos: List[Tuple[float, float]], cortantes: List[Tuple[float, float]]) -> List[SecaoCritica]:
    """
    Orquestra todas as detecções (máximos, mínimos, apoios, momentos nulos, extremos)
    e retorna uma lista de SecaoCritica ordenada por x.
    Valores ausentes em uma curva são interpolados. Duplicatas são fundidas de acordo com
    uma prioridade de tipo de seção.
    """
    if not momentos:
        return []

    sorted_momentos = sorted(momentos, key=lambda p: p[0])
    x_min = sorted_momentos[0][0]
    x_max = sorted_momentos[-1][0]

    # 1. Obter os x-candidatos para cada tipo
    x_extremos = [x_min, x_max]
    x_maximos = [x for x, _ in detectar_maximos_locais(sorted_momentos)]
    x_minimos = [x for x, _ in detectar_minimos_locais(sorted_momentos)]
    x_apoios = detectar_apoios(sorted_momentos, cortantes)
    x_nulos = [x for x, _ in detectar_pontos_momento_nulo(sorted_momentos)]

    # 2. Fundir e obter todos os x únicos ordenados
    todos_candidatos = sorted(x_extremos + x_maximos + x_minimos + x_apoios + x_nulos)
    unique_x = []
    for cx in todos_candidatos:
        if not any(abs(cx - ux) < 1e-5 for ux in unique_x):
            unique_x.append(cx)

    # 3. Classificar e criar cada SecaoCritica
    secoes = []
    for x in unique_x:
        # Determinar tipo por ordem de prioridade
        tipo = ""
        descricao = ""
        
        is_apoio = any(abs(x - xa) < 1e-5 for xa in x_apoios)
        is_max = any(abs(x - xm) < 1e-5 for xm in x_maximos)
        is_min = any(abs(x - xm) < 1e-5 for xm in x_minimos)
        is_extremo = any(abs(x - xe) < 1e-5 for xe in x_extremos)
        is_nulo = any(abs(x - xn) < 1e-5 for xn in x_nulos)
        
        if is_apoio:
            tipo = "APOIO"
            if abs(x - x_min) < 1e-5:
                descricao = "Apoio esquerdo"
            elif abs(x - x_max) < 1e-5:
                descricao = "Apoio direito"
            else:
                descricao = "Apoio interno"
        elif is_max:
            tipo = "MÁX"
            descricao = "Momento máximo local"
        elif is_min:
            tipo = "MÍN"
            descricao = "Momento mínimo local"
        elif is_extremo:
            tipo = "EXTREMO"
            if abs(x - x_min) < 1e-5:
                descricao = "Extremo esquerdo"
            else:
                descricao = "Extremo direito"
        elif is_nulo:
            tipo = "M_NULO"
            descricao = "Momento nulo (cruzamento)"
        else:
            tipo = "EXTREMO"
            descricao = "Seção de extremo"

        # Interpolar esforços correspondentes
        val_m = interpolar_y(momentos, x)
        val_v = interpolar_y(cortantes, x)

        secoes.append(SecaoCritica(
            x=round(x, 4),
            momento=round(val_m, 2),
            cortante=round(val_v, 2),
            tipo=tipo,
            descricao=descricao
        ))

    return secoes
