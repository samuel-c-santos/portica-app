"""
core/detailing/domain.py
══════════════════════════════════════════════════════════════════════════════
CAMADA DE DOMÍNIO — Regras de Negócio (NBR 6118:2023)
══════════════════════════════════════════════════════════════════════════════

Responsabilidade ÚNICA: receber os parâmetros brutos de uma seção de viga e
retornar um SectionLayoutData com todas as coordenadas e metadados calculados.

NÃO contém lógica de desenho, lógica de UI Flet, nem acesso a fpdf2.

Autor: Samuel da Costa dos Santos (https://github.com/samuel-c-santos)
Licença: vide LICENSE
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Entidades de Domínio
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BarPosition:
    """Posição do eixo de uma barra na seção transversal.

    Coordenadas em mm, com origem no canto inferior-esquerdo externo do
    concreto. Eixo X → direita, eixo Y → cima.

    Attributes:
        x: Posição horizontal do eixo da barra (mm).
        y: Posição vertical do eixo da barra (mm).
        layer: Índice da camada (0 = camada mais próxima à face tracionada).
               -1 = barra construtiva de canto superior (porta-estribo).
        is_corner_bar: True se a barra é construtiva de canto (não entra no
                       cálculo do baricentro da armadura de cálculo).
    """
    x: float
    y: float
    layer: int
    is_corner_bar: bool = False

    def __repr__(self) -> str:
        tipo = "CANTO" if self.is_corner_bar else f"cam{self.layer}"
        return f"Bar({tipo} x={self.x:.1f} y={self.y:.1f})"


@dataclass(frozen=True)
class ReinforcementLayer:
    """Descreve uma camada de armadura longitudinal principal.

    Attributes:
        index: Índice da camada (0 = inferior, n-1 = superior).
        bar_count: Quantidade de barras nesta camada.
        y_centroid: Posição Y do centróide das barras (mm, desde face inferior).
        h_spacing: Espaçamento horizontal real entre barras adjacentes (mm).
                   0 se há apenas 1 barra na camada.
    """
    index: int
    bar_count: int
    y_centroid: float
    h_spacing: float


@dataclass(frozen=True)
class SupplementaryStirrup:
    """Grampo suplementar (estribo de travamento de barra central).

    Attributes:
        x: Posição X do eixo da barra travada (mm, coord. absolutas da seção).
        layer: Camada em que a barra travada se encontra.
    """
    x: float
    layer: int


@dataclass
class SectionLayoutData:
    """Resultado completo do detalhamento de seção — produzido por BeamDetailer.

    É o único objeto que a camada de Apresentação recebe. Contém todos os dados
    necessários para desenhar a seção sem precisar re-calcular nada.

    Coordinates convention
    ──────────────────────
    Origem: canto inferior-esquerdo externo do concreto.
    X: cresce para a direita (mm).
    Y: cresce para cima (mm).
    """

    # ── Parâmetros de entrada (espelhados para o relatório) ──────────────────
    bw: float           # Largura da alma (mm)
    h: float            # Altura total (mm)
    c_nom: float        # Cobrimento nominal (mm)
    phi_estribo: float  # Diâmetro do estribo principal (mm)
    phi_barra: float    # Diâmetro das barras principais (mm)
    d_max_agregado: float  # Diâmetro máximo do agregado (mm)
    total_bars: int     # Quantidade total de barras principais

    # ── Limites normativos ───────────────────────────────────────────────────
    eh_min: float   # Espaçamento horiz. mínimo normativo (mm)
    ev_min: float   # Espaçamento vert. mínimo entre camadas (mm)

    # ── Layout das camadas ───────────────────────────────────────────────────
    layer_count: int
    layers: List[ReinforcementLayer]

    # ── Posições de todas as barras ──────────────────────────────────────────
    bar_positions: List[BarPosition]

    # ── Grampos suplementares ────────────────────────────────────────────────
    requires_supplementary_stirrup: bool
    supplementary_stirrup_positions: List[SupplementaryStirrup]

    # ── Baricentro e altura útil efetiva ─────────────────────────────────────
    y_cg: float      # Coord. Y do centróide da arm. tracionada (mm, de baixo)
    d_efetiva: float # Altura útil efetiva (mm): igual a y_cg pois Y↑ de baixo

    is_t: bool = False
    bf: float = 0.0     # Largura da mesa (mm)
    hf: float = 0.0     # Altura da mesa (mm)
    warnings: List[str] = field(default_factory=list)

    # ── Propriedades derivadas (para o Painter) ───────────────────────────────
    @property
    def stirrup_corner_radius(self) -> float:
        """Raio de curvatura interno do estribo (mm). NBR 6118:9.4.2: r ≥ 3φ."""
        return 3.0 * self.phi_estribo

    @property
    def hook_length(self) -> float:
        """Comprimento do gancho de ancoragem do estribo (mm)."""
        return min(6.0 * self.phi_estribo, 80.0)

    def __repr__(self) -> str:
        return (
            f"SectionLayoutData(bw={self.bw}, h={self.h}, "
            f"layers={self.layer_count}, bars={self.total_bars}, "
            f"yCG={self.y_cg:.1f}, d={self.d_efetiva:.1f})"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Parâmetros de Entrada
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class BeamDetailingInput:
    bw: float
    h: float
    c_nom: float
    phi_estribo: float
    phi_barra: float
    d_max_agregado: float
    total_bars: int
    phi_canto_superior: float | None = None
    is_t: bool = False
    bf_cm: float = 0.0
    hf_cm: float = 0.0
    is_superior: bool = False


# ══════════════════════════════════════════════════════════════════════════════
# UseCase: BeamDetailer
# ══════════════════════════════════════════════════════════════════════════════

class BeamDetailer:
    """UseCase: calcula o layout de armadura na seção transversal de viga.

    Implementa as prescrições da NBR 6118:2023, §18.3.2.

    Algoritmo
    ─────────
    1. Valida os parâmetros de entrada.
    2. Calcula o espaço horizontal interno disponível (h_space).
    3. Calcula os espaçamentos mínimos normativos e_h e e_v.
    4. Determina o número máximo de barras por camada (n_max_por_camada).
    5. Distribui as barras em 1…N camadas ("camada inferior mais cheia").
    6. Calcula coordenadas X,Y exatas de cada barra.
    7. Adiciona as barras de canto superiores construtivas (alinhadas em X
       com as barras extremas da camada 0 — requisito de passagem do vibrador).
    8. Detecta a necessidade de grampos suplementares (NBR 6118:18.3.2.3).
    9. Recalcula baricentro y_cg e altura útil efetiva d.

    Usage::

        detailer = BeamDetailer()
        data = detailer.detail(BeamDetailingInput(
            bw=200, h=500, c_nom=25, phi_estribo=6.3,
            phi_barra=10, d_max_agregado=19, total_bars=10,
        ))
        # data.layer_count == 2 (5 + 5 barras)
    """

    # Limite máximo de span não-travado entre barras para grampos (mm).
    # NBR 6118:18.3.2.3: travamento quando distância entre cantos > 15 cm.
    _MAX_UNSUPPORTED_SPAN_MM: float = 150.0

    def detail(self, inp: BeamDetailingInput) -> SectionLayoutData:
        """Executa o detalhamento e retorna um SectionLayoutData.

        Raises:
            ValueError: Se os parâmetros tornarem a seção geometricamente
                        inviável (espaço negativo, bitola impossível, etc.).
        """
        self._validate(inp)
        warnings: List[str] = []

        is_t = inp.is_t
        bf_mm = inp.bf_cm * 10.0 if is_t else inp.bw
        hf_mm = inp.hf_cm * 10.0 if is_t else 0.0
        bw_mm = inp.bw

        # ── 1. Espaço horizontal interno disponível ───────────────────────────
        if is_t:
            if inp.is_superior:
                # Armadura superior: distribuída na mesa
                h_space = bf_mm - 2 * inp.c_nom - 2 * inp.phi_estribo
                x_inf_estribo = inp.c_nom + inp.phi_estribo
            else:
                # Armadura inferior: distribuída na alma
                h_space = bw_mm - 2 * inp.c_nom - 2 * inp.phi_estribo
                x_inf_estribo = (bf_mm - bw_mm) / 2.0 + inp.c_nom + inp.phi_estribo
        else:
            h_space = bw_mm - 2 * inp.c_nom - 2 * inp.phi_estribo
            x_inf_estribo = inp.c_nom + inp.phi_estribo

        if h_space <= 0:
            raise ValueError(
                f"Espaço horizontal interno nulo ou negativo: {h_space:.1f} mm. "
                f"Aumente a seção ou reduza cobrimento/estribo."
            )

        # ── 2. Espaçamentos mínimos normativos ────────────────────────────────
        eh_min = max(20.0, inp.phi_barra, 1.2 * inp.d_max_agregado)
        ev_min = max(20.0, inp.phi_barra, 1.33 * inp.d_max_agregado)

        # ── 3. Número máximo de barras por camada ─────────────────────────────
        if inp.phi_barra > h_space:
            raise ValueError(
                f"Diâmetro da barra φ={inp.phi_barra} mm maior que o espaço "
                f"horizontal interno disponível {h_space:.1f} mm."
            )
        n_max_por_camada = max(
            1,
            int(math.floor((h_space - inp.phi_barra) / (inp.phi_barra + eh_min)) + 1)
        )
        if n_max_por_camada >= 2:
            eh_check = (h_space - n_max_por_camada * inp.phi_barra) / (n_max_por_camada - 1)
            if eh_check < 0:
                n_max_por_camada -= 1
        if n_max_por_camada < 1:
            raise ValueError(
                f"Impossível alocar sequer 1 barra φ={inp.phi_barra} mm no "
                f"espaço disponível de {h_space:.1f} mm."
            )

        # ── 4. Distribuição em camadas ────────────────────────────────────────
        layer_counts = self._distribute_layers(
            inp.total_bars, n_max_por_camada, warnings
        )
        layer_count = len(layer_counts)

        # ── 5. Posições Y de cada camada ──────────────────────────────────────
        phi_canto = inp.phi_canto_superior if inp.phi_canto_superior else inp.phi_barra

        y_inf_estribo = inp.c_nom + inp.phi_estribo
        y_sup_estribo = inp.h - inp.c_nom - inp.phi_estribo

        y_layer0_center = y_inf_estribo + inp.phi_barra / 2
        y_canto_center = y_sup_estribo - phi_canto / 2
        y_last_layer_center = y_layer0_center + (layer_count - 1) * (inp.phi_barra + ev_min)
        
        clearance = (y_canto_center - phi_canto / 2) - (y_last_layer_center + inp.phi_barra / 2)
        if clearance < ev_min and layer_count > 1:
            warnings.append(
                f"Atenção: folga entre última camada de armadura e as barras de "
                f"canto superiores é {clearance:.1f} mm < e_v,mín={ev_min:.1f} mm."
            )

        # ── 6. Objetos ReinforcementLayer e coordenadas X das barras ──────────
        reinforcement_layers: List[ReinforcementLayer] = []
        bar_positions: List[BarPosition] = []

        for i, n in enumerate(layer_counts):
            y_center = y_layer0_center + i * (inp.phi_barra + ev_min)

            if n <= 1:
                h_spacing = 0.0
            else:
                h_spacing = (h_space - n * inp.phi_barra) / (n - 1)

            if h_spacing < eh_min - 0.5 and n > 1:
                warnings.append(
                    f"Camada {i+1}: espaçamento horizontal real "
                    f"{h_spacing:.1f} mm < e_h,mín={eh_min:.1f} mm."
                )

            reinforcement_layers.append(ReinforcementLayer(
                index=i,
                bar_count=n,
                y_centroid=round(y_center, 3),
                h_spacing=round(h_spacing, 3),
            ))

            if n <= 1:
                x_first = x_inf_estribo + h_space / 2
            else:
                width_occupied = n * inp.phi_barra + (n - 1) * h_spacing
                offset = (h_space - width_occupied) / 2
                x_first = x_inf_estribo + offset + inp.phi_barra / 2

            for j in range(n):
                x = x_first + j * (inp.phi_barra + h_spacing)
                bar_positions.append(BarPosition(
                    x=round(x, 3),
                    y=round(y_center, 3),
                    layer=i,
                    is_corner_bar=False,
                ))

        # ── 7. Barras de canto superiores construtivas ────────────────────────
        if is_t:
            # Em viga T, o estribo principal fica na alma de largura bw_mm,
            # então as barras de canto construtivas de suporte do estribo
            # devem se alinhar nos cantos da alma (para segurar o estribo).
            x_canto_min = (bf_mm - bw_mm) / 2.0 + inp.c_nom + inp.phi_estribo + phi_canto / 2
            x_canto_max = (bf_mm + bw_mm) / 2.0 - inp.c_nom - inp.phi_estribo - phi_canto / 2
        else:
            layer0_bars = sorted(
                [b for b in bar_positions if b.layer == 0], key=lambda b: b.x
            )
            x_canto_min_lim = x_inf_estribo + phi_canto / 2
            x_canto_max_lim = inp.bw - inp.c_nom - inp.phi_estribo - phi_canto / 2
            if layer0_bars:
                x_canto_min = max(x_canto_min_lim, min(layer0_bars[0].x, x_canto_max_lim))
                x_canto_max = max(x_canto_min_lim, min(layer0_bars[-1].x, x_canto_max_lim))
            else:
                x_canto_min = x_canto_min_lim
                x_canto_max = x_canto_max_lim

        for x_c in [x_canto_min, x_canto_max]:
            bar_positions.append(BarPosition(
                x=round(x_c, 3),
                y=round(y_canto_center, 3),
                layer=-1,
                is_corner_bar=True,
            ))

        # ── 8. Grampos suplementares (NBR 6118:18.3.2.3) ─────────────────────
        requires_grampos = False
        grampo_positions: List[SupplementaryStirrup] = []

        for lyr in reinforcement_layers:
            if lyr.bar_count < 3:
                continue
            lyr_bars = sorted(
                [b for b in bar_positions if b.layer == lyr.index], key=lambda b: b.x
            )
            span = lyr_bars[-1].x - lyr_bars[0].x
            if span > self._MAX_UNSUPPORTED_SPAN_MM:
                requires_grampos = True
                for b in lyr_bars[1:-1]:
                    grampo_positions.append(SupplementaryStirrup(x=b.x, layer=lyr.index))

        if requires_grampos:
            warnings.append(
                "Grampos suplementares necessários para travar barras centrais (NBR 6118:18.3.2.3)."
            )

        # ── 9. Baricentro e altura útil efetiva ──────────────────────────────
        main_bars = [b for b in bar_positions if not b.is_corner_bar]
        if main_bars:
            y_cg_raw = sum(b.y for b in main_bars) / len(main_bars)
        else:
            y_cg_raw = y_layer0_center

        if inp.is_superior:
            y_cg = inp.h - y_cg_raw
            d_efetiva = y_cg
        else:
            y_cg = y_cg_raw
            d_efetiva = inp.h - y_cg

        return SectionLayoutData(
            bw=inp.bw,
            h=inp.h,
            c_nom=inp.c_nom,
            phi_estribo=inp.phi_estribo,
            phi_barra=inp.phi_barra,
            d_max_agregado=inp.d_max_agregado,
            total_bars=inp.total_bars,
            eh_min=round(eh_min, 3),
            ev_min=round(ev_min, 3),
            layer_count=layer_count,
            layers=reinforcement_layers,
            bar_positions=bar_positions,
            requires_supplementary_stirrup=requires_grampos,
            supplementary_stirrup_positions=grampo_positions,
            y_cg=round(y_cg, 3),
            d_efetiva=round(d_efetiva, 3),
            warnings=warnings,
            is_t=is_t,
            bf=bf_mm,
            hf=hf_mm,
        )

    # ── Auxiliares ────────────────────────────────────────────────────────────

    @staticmethod
    def _validate(inp: BeamDetailingInput) -> None:
        """Valida os parâmetros de entrada. Lança ValueError se inválido."""
        erros = []
        if inp.bw <= 0:
            erros.append(f"bw={inp.bw} deve ser > 0")
        if inp.h <= 0:
            erros.append(f"h={inp.h} deve ser > 0")
        if inp.c_nom <= 0:
            erros.append(f"c_nom={inp.c_nom} deve ser > 0")
        if inp.phi_estribo <= 0:
            erros.append(f"phi_estribo={inp.phi_estribo} deve ser > 0")
        if inp.phi_barra <= 0:
            erros.append(f"phi_barra={inp.phi_barra} deve ser > 0")
        if inp.d_max_agregado <= 0:
            erros.append(f"d_max_agregado={inp.d_max_agregado} deve ser > 0")
        if inp.total_bars < 1:
            erros.append(f"total_bars={inp.total_bars} deve ser >= 1")
        if erros:
            raise ValueError("Parâmetros inválidos: " + "; ".join(erros))

    @staticmethod
    def _distribute_layers(
        total_bars: int, n_max: int, warnings: List[str]
    ) -> List[int]:
        """Distribui barras em camadas (camada inferior mais cheia).

        Returns:
            Lista de inteiros: contagem de barras por camada,
            do índice 0 (inferior) ao índice n-1 (superior).
        """
        if total_bars <= n_max:
            return [total_bars]

        layers: List[int] = []
        remaining = total_bars
        while remaining > 0:
            count = min(remaining, n_max)
            layers.append(count)
            remaining -= count

        # Balanceamento: Se a última camada tem apenas 1 barra e a anterior tem mais de 2 barras,
        # movemos 1 barra para a última camada. Isso evita assimetria e facilita fixação construtiva.
        if len(layers) >= 2 and layers[-1] == 1 and layers[-2] > 2:
            layers[-1] += 1
            layers[-2] -= 1

        warnings.append(
            f"Armadura distribuída em {len(layers)} camadas: "
            + " + ".join(str(c) for c in layers)
            + f" barras (máx {n_max} por camada com e_h normativo)."
        )
        return layers
