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
from typing import Any

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
    phi_mm: float | None = None
    is_skin_bar: bool = False

    def __repr__(self) -> str:
        tipo = (
            "CANTO" if self.is_corner_bar else ("PELE" if self.is_skin_bar else f"cam{self.layer}")
        )
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
    bw: float  # Largura da alma (mm)
    h: float  # Altura total (mm)
    c_nom: float  # Cobrimento nominal (mm)
    phi_estribo: float  # Diâmetro do estribo principal (mm)
    phi_barra: float  # Diâmetro das barras principais (mm)
    d_max_agregado: float  # Diâmetro máximo do agregado (mm)
    total_bars: int  # Quantidade total de barras principais

    # ── Limites normativos ───────────────────────────────────────────────────
    eh_min: float  # Espaçamento horiz. mínimo normativo (mm)
    ev_min: float  # Espaçamento vert. mínimo entre camadas (mm)

    # ── Layout das camadas ───────────────────────────────────────────────────
    layer_count: int
    layers: list[ReinforcementLayer]

    # ── Posições de todas as barras ──────────────────────────────────────────
    bar_positions: list[BarPosition]

    # ── Grampos suplementares ────────────────────────────────────────────────
    requires_supplementary_stirrup: bool
    supplementary_stirrup_positions: list[SupplementaryStirrup]

    # ── Baricentro e altura útil efetiva ─────────────────────────────────────
    y_cg: float  # Coord. Y do centróide da arm. tracionada (mm, de baixo)
    d_efetiva: float  # Altura útil efetiva (mm): igual a y_cg pois Y↑ de baixo

    is_t: bool = False
    bf: float = 0.0  # Largura da mesa (mm)
    hf: float = 0.0  # Altura da mesa (mm)
    warnings: list[str] = field(default_factory=list)
    skin_bar_positions: list[BarPosition] = field(default_factory=list)
    total_bars_sup: int = 0
    phi_barra_sup: float | None = None
    phi_canto: float | None = None

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


def ev_min_mm(d_max_agregado_mm: float, phi_barra_mm: float) -> float:
    """Espaçamento vertical mínimo entre camadas (NBR 6118:2023, 18.3.2.2).

    Regra única usada pelo detalhamento e pela exportação DXF (EP-02.5):
    e_v,min = max(20 mm; φ; 1,33·d_max). O fator 1,33 é o adotado
    historicamente pelo motor e é conservador em relação ao mínimo 0,5·d_max
    da norma; mantê-lo em uma única definição evita divergência entre
    desenho, DXF e relatório.
    """
    return max(20.0, phi_barra_mm, 1.33 * d_max_agregado_mm)


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

    # Limite normativo de camadas de armadura concentrada.
    # NBR 6118:2023 (§18.3.2): a armadura longitudinal deve ser concentrada
    # em poucas camadas (no máximo 3-4) para viabilizar concretagem e
    # vibrado. Acima disso, a seção é recusada em vez de empilhar camadas
    # até "caber" (que produzia d_efetiva negativa em silêncio).
    _MAX_LAYERS: int = 4

    def detail(self, inp: BeamDetailingInput) -> SectionLayoutData:
        """Executa o detalhamento e retorna um SectionLayoutData.

        Raises:
            ValueError: Se os parâmetros tornarem a seção geometricamente
                        inviável (espaço negativo, bitola impossível, etc.).
        """
        self._validate(inp)
        warnings: list[str] = []

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
        ev_min = ev_min_mm(inp.d_max_agregado, inp.phi_barra)

        # ── 3. Número máximo de barras por camada ─────────────────────────────
        if inp.phi_barra > h_space:
            raise ValueError(
                f"Diâmetro da barra φ={inp.phi_barra} mm maior que o espaço "
                f"horizontal interno disponível {h_space:.1f} mm."
            )
        n_max_por_camada = max(
            1, int(math.floor((h_space - inp.phi_barra) / (inp.phi_barra + eh_min)) + 1)
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
        layer_counts = self._distribute_layers(inp.total_bars, n_max_por_camada, warnings)
        layer_count = len(layer_counts)
        if layer_count > self._MAX_LAYERS:
            raise ValueError(
                f"Seção recusada: {inp.total_bars} barras φ{inp.phi_barra} mm exigem "
                f"{layer_count} camadas, acima do limite de {self._MAX_LAYERS} "
                f"(NBR 6118:2023, §18.3.2). Aumente a seção, reduza a quantidade "
                f"de barras ou use bitola maior."
            )

        # ── 5. Posições Y de cada camada ──────────────────────────────────────
        phi_canto = inp.phi_canto_superior if inp.phi_canto_superior else inp.phi_barra

        y_inf_estribo = inp.c_nom + inp.phi_estribo
        y_sup_estribo = inp.h - inp.c_nom - inp.phi_estribo

        y_layer0_center = y_inf_estribo + inp.phi_barra / 2
        y_canto_center = y_sup_estribo - phi_canto / 2
        y_last_layer_center = y_layer0_center + (layer_count - 1) * (inp.phi_barra + ev_min)

        # Blindagem geométrica (EP-01.1): a última camada deve caber dentro
        # da seção. Sem esta guarda, o detalhador empilhava camadas até além
        # da face superior e devolvia y_cg > h e d_efetiva negativa.
        y_limite_topo = inp.h - inp.c_nom - inp.phi_estribo
        if y_last_layer_center + inp.phi_barra / 2.0 > y_limite_topo:
            raise ValueError(
                f"Seção recusada: a última camada de armadura "
                f"(y = {y_last_layer_center + inp.phi_barra / 2.0:.1f} mm) "
                f"ultrapassa o limite interno da seção "
                f"(h − c − φe = {y_limite_topo:.1f} mm). "
                f"Reduza a quantidade de barras ou aumente a altura da seção."
            )

        clearance = (y_canto_center - phi_canto / 2) - (y_last_layer_center + inp.phi_barra / 2)
        if clearance < ev_min and layer_count > 1:
            warnings.append(
                f"Atenção: folga entre última camada de armadura e as barras de "
                f"canto superiores é {clearance:.1f} mm < e_v,mín={ev_min:.1f} mm."
            )

        # ── 6. Objetos ReinforcementLayer e coordenadas X das barras ──────────
        reinforcement_layers: list[ReinforcementLayer] = []
        bar_positions: list[BarPosition] = []

        for i, n in enumerate(layer_counts):
            y_center = y_layer0_center + i * (inp.phi_barra + ev_min)

            if n <= 1:
                h_spacing = 0.0
            else:
                h_spacing = (h_space - n * inp.phi_barra) / (n - 1)

            if h_spacing < eh_min - 0.5 and n > 1:
                warnings.append(
                    f"Camada {i + 1}: espaçamento horizontal real "
                    f"{h_spacing:.1f} mm < e_h,mín={eh_min:.1f} mm."
                )

            reinforcement_layers.append(
                ReinforcementLayer(
                    index=i,
                    bar_count=n,
                    y_centroid=round(y_center, 3),
                    h_spacing=round(h_spacing, 3),
                )
            )

            if n <= 1:
                x_first = x_inf_estribo + h_space / 2
            else:
                width_occupied = n * inp.phi_barra + (n - 1) * h_spacing
                offset = (h_space - width_occupied) / 2
                x_first = x_inf_estribo + offset + inp.phi_barra / 2

            for j in range(n):
                x = x_first + j * (inp.phi_barra + h_spacing)
                bar_positions.append(
                    BarPosition(
                        x=round(x, 3),
                        y=round(y_center, 3),
                        layer=i,
                        is_corner_bar=False,
                    )
                )

        # Reindexa as barras por camada uma única vez (evita varrer toda a
        # lista de barras para cada camada — O(camadas × barras) → O(barras)).
        bars_by_layer: dict[int, list[BarPosition]] = {}
        for b in bar_positions:
            bars_by_layer.setdefault(b.layer, []).append(b)

        # ── 7. Barras de canto superiores construtivas ────────────────────────
        if is_t:
            # Em viga T, o estribo principal fica na alma de largura bw_mm,
            # então as barras de canto construtivas de suporte do estribo
            # devem se alinhar nos cantos da alma (para segurar o estribo).
            x_canto_min = (bf_mm - bw_mm) / 2.0 + inp.c_nom + inp.phi_estribo + phi_canto / 2
            x_canto_max = (bf_mm + bw_mm) / 2.0 - inp.c_nom - inp.phi_estribo - phi_canto / 2
        else:
            layer0_bars = sorted(bars_by_layer.get(0, []), key=lambda b: b.x)
            x_canto_min_lim = x_inf_estribo + phi_canto / 2
            x_canto_max_lim = inp.bw - inp.c_nom - inp.phi_estribo - phi_canto / 2
            if layer0_bars:
                x_canto_min = max(x_canto_min_lim, min(layer0_bars[0].x, x_canto_max_lim))
                x_canto_max = max(x_canto_min_lim, min(layer0_bars[-1].x, x_canto_max_lim))
            else:
                x_canto_min = x_canto_min_lim
                x_canto_max = x_canto_max_lim

        for x_c in [x_canto_min, x_canto_max]:
            bar_positions.append(
                BarPosition(
                    x=round(x_c, 3),
                    y=round(y_canto_center, 3),
                    layer=-1,
                    is_corner_bar=True,
                )
            )

        # ── 8. Grampos suplementares (NBR 6118:18.3.2.3) ─────────────────────
        requires_grampos = False
        grampo_positions: list[SupplementaryStirrup] = []

        for lyr in reinforcement_layers:
            if lyr.bar_count < 3:
                continue
            lyr_bars = sorted(bars_by_layer.get(lyr.index, []), key=lambda b: b.x)
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

        # Invariante final (EP-01.1): nunca devolver altura útil não positiva.
        # Com as guardas acima ele é alcançado, mas fica como blindagem
        # explícita contra qualquer futura regressão geométrica.
        if d_efetiva <= 0:
            raise ValueError(
                f"Seção recusada: altura útil efetiva não positiva "
                f"(d = {d_efetiva:.1f} mm). A armadura não cabe na seção; "
                f"aumente a altura ou reduza a armadura."
            )

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
    def _distribute_layers(total_bars: int, n_max: int, warnings: list[str]) -> list[int]:
        """Distribui barras em camadas (camada inferior mais cheia).

        Returns:
            Lista de inteiros: contagem de barras por camada,
            do índice 0 (inferior) ao índice n-1 (superior).
        """
        if total_bars <= n_max:
            return [total_bars]

        layers: list[int] = []
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


# ── Posicionamento Único de Armadura de Pele (EP-04.4) ────────────────────────


def posicionar_armadura_pele(
    h_mm: float,
    bw_mm: float,
    cob_mm: float,
    phi_estribo_mm: float,
    n_barras_pele_face: int,
    phi_pele_mm: float,
    bar_positions: list[Any] | None = None,
    is_t: bool = False,
    bf_mm: float = 0.0,
    hf_mm: float = 0.0,
    d_max_agregado_mm: float = 19.0,
    phi_barra_inf_mm: float = 16.0,
    phi_barra_sup_mm: float = 10.0,
) -> tuple[float, float, list[float]]:
    """Calcula as coordenadas (x_face_esq, x_face_dir, [y1, y2, ...]) em mm para armadura de pele.

    EP-04.4: fonte única de verdade do posicionamento da armadura de pele (NBR 6118).
    Substitui as 4 implementações divergentes anteriores.
    Retorna coordenadas em mm, com origem no canto inferior-esquerdo (Y para cima).
    """
    if n_barras_pele_face <= 0 or phi_pele_mm <= 0:
        return 0.0, 0.0, []

    # 1. Posições X nas duas faces da alma
    alma_x0 = (bf_mm - bw_mm) / 2.0 if (is_t and bf_mm > bw_mm) else 0.0
    e_off = cob_mm + phi_estribo_mm / 2.0
    bar_off = phi_estribo_mm / 2.0 + phi_pele_mm / 2.0
    x_face_esq = alma_x0 + e_off + bar_off
    x_face_dir = alma_x0 + bw_mm - e_off - bar_off

    # 2. Posições Y entre a última camada inferior e a primeira superior
    topo_bottom_bars = None
    fundo_top_bars = None

    if bar_positions:
        bottom_tops = []
        top_bottoms = []
        for b in bar_positions:
            by = b.get("y") if isinstance(b, dict) else getattr(b, "y", None)
            blayer = b.get("layer") if isinstance(b, dict) else getattr(b, "layer", None)
            is_corner = (
                b.get("is_corner_bar")
                if isinstance(b, dict)
                else getattr(b, "is_corner_bar", False)
            )
            is_skin = (
                b.get("is_skin_bar") if isinstance(b, dict) else getattr(b, "is_skin_bar", False)
            )
            bphi = (b.get("phi_mm") if isinstance(b, dict) else getattr(b, "phi_mm", None)) or (
                phi_barra_sup_mm if blayer is not None and blayer < 0 else phi_barra_inf_mm
            )
            if by is None or is_skin:
                continue

            # Classifica como inferior ou superior
            if blayer is not None:
                if blayer >= 0 and not is_corner:
                    bottom_tops.append(by + bphi / 2.0)
                else:
                    top_bottoms.append(by - bphi / 2.0)
            else:
                if by < h_mm / 2.0:
                    bottom_tops.append(by + bphi / 2.0)
                else:
                    top_bottoms.append(by - bphi / 2.0)

        if bottom_tops:
            topo_bottom_bars = max(bottom_tops)
        if top_bottoms:
            fundo_top_bars = min(top_bottoms)

    ev_min = ev_min_mm(d_max_agregado_mm, max(phi_barra_inf_mm, phi_barra_sup_mm))

    y_bottom_raw = topo_bottom_bars if topo_bottom_bars is not None else (cob_mm + phi_estribo_mm)
    if fundo_top_bars is not None:
        y_top_raw = fundo_top_bars
    else:
        if is_t and hf_mm > 0:
            y_top_raw = h_mm - hf_mm
        else:
            y_top_raw = h_mm - (cob_mm + phi_estribo_mm)

    h_free = y_top_raw - y_bottom_raw
    d_livre = (h_free - n_barras_pele_face * phi_pele_mm) / (n_barras_pele_face + 1.0)

    if d_livre >= ev_min:
        ys = [
            y_bottom_raw + (i + 1) * d_livre + (i + 0.5) * phi_pele_mm
            for i in range(n_barras_pele_face)
        ]
    else:
        # Fallback uniforme entre estribos (ou alma para viga T)
        y_bottom_est = cob_mm + phi_estribo_mm
        y_top_est = (h_mm - hf_mm) if (is_t and hf_mm > 0) else (h_mm - cob_mm - phi_estribo_mm)
        s_fb = (y_top_est - y_bottom_est) / (n_barras_pele_face + 1.0)
        ys = [y_bottom_est + (i + 1) * s_fb for i in range(n_barras_pele_face)]

    return x_face_esq, x_face_dir, ys


# ── Detalhamento Consolidado da Seção Completa (EP-04.4) ──────────────────────


def detalhar_secao_completa(
    h_cm: float,
    bw_cm: float,
    cob_mm: float,
    phi_estribo_mm: float,
    phi_barra_inf_mm: float,
    n_barras_inf: int,
    phi_barra_sup_mm: float = 0.0,
    n_barras_sup: int = 0,
    d_max_agregado_mm: float = 19.0,
    is_t: bool = False,
    bf_cm: float = 0.0,
    hf_cm: float = 0.0,
    n_barras_pele: int = 0,
    phi_pele_mm: float = 0.0,
    layout_convergido: SectionLayoutData | None = None,
) -> SectionLayoutData:
    """Consolida o detalhamento completo de armação da seção transversal (EP-04.4).

    Gera a seção com todas as barras inferiores, superiores, pele e grampos.
    Única fonte de geometria para PDF, Flet e DXF.
    """
    h_mm = h_cm * 10.0
    bw_mm = bw_cm * 10.0
    bf_mm = bf_cm * 10.0 if is_t else bw_mm
    hf_mm = hf_cm * 10.0 if is_t else 0.0
    detailer = BeamDetailer()

    # 1. Armadura inferior
    if layout_convergido is not None and isinstance(layout_convergido, SectionLayoutData):
        data_inf = layout_convergido
    else:
        inp_inf = BeamDetailingInput(
            bw=bw_mm,
            h=h_mm,
            c_nom=cob_mm,
            phi_estribo=phi_estribo_mm,
            phi_barra=phi_barra_inf_mm,
            d_max_agregado=d_max_agregado_mm,
            total_bars=max(1, n_barras_inf),
            is_t=is_t,
            bf_cm=bf_cm,
            hf_cm=hf_cm,
            is_superior=False,
        )
        try:
            data_inf = detailer.detail(inp_inf)
        except ValueError as err:
            # Seção recusada geometricamente (ex: relatório de viga que NÃO CABE).
            # Para fins de desenho esquemático, tenta detalhar com a quantidade máxima de barras que cabem.
            data_inf = None
            for n_try in range(min(n_barras_inf, 8), 0, -1):
                try:
                    inp_try = BeamDetailingInput(
                        bw=bw_mm,
                        h=h_mm,
                        c_nom=cob_mm,
                        phi_estribo=phi_estribo_mm,
                        phi_barra=phi_barra_inf_mm,
                        d_max_agregado=d_max_agregado_mm,
                        total_bars=n_try,
                        is_t=is_t,
                        bf_cm=bf_cm,
                        hf_cm=hf_cm,
                        is_superior=False,
                    )
                    data_inf = detailer.detail(inp_try)
                    data_inf.warnings.append(str(err))
                    break
                except ValueError:
                    continue
            if data_inf is None:
                raise err

    all_bars: list[BarPosition] = []
    # Copia as barras inferiores principais
    for b in data_inf.bar_positions:
        if not b.is_corner_bar:
            all_bars.append(
                BarPosition(
                    x=b.x,
                    y=b.y,
                    layer=b.layer,
                    is_corner_bar=False,
                    phi_mm=phi_barra_inf_mm,
                )
            )

    all_grampos: list[SupplementaryStirrup] = list(data_inf.supplementary_stirrup_positions)
    requires_grampos = data_inf.requires_supplementary_stirrup

    # 2. Armadura superior
    if n_barras_sup > 0 and phi_barra_sup_mm > 0:
        inp_sup = BeamDetailingInput(
            bw=bw_mm,
            h=h_mm,
            c_nom=cob_mm,
            phi_estribo=phi_estribo_mm,
            phi_barra=phi_barra_sup_mm,
            d_max_agregado=d_max_agregado_mm,
            total_bars=n_barras_sup,
            is_t=is_t,
            bf_cm=bf_cm,
            hf_cm=hf_cm,
            is_superior=True,
        )
        try:
            data_sup = detailer.detail(inp_sup)
        except ValueError:
            data_sup = None
            for n_try in range(min(n_barras_sup, 8), 0, -1):
                try:
                    inp_try = BeamDetailingInput(
                        bw=bw_mm,
                        h=h_mm,
                        c_nom=cob_mm,
                        phi_estribo=phi_estribo_mm,
                        phi_barra=phi_barra_sup_mm,
                        d_max_agregado=d_max_agregado_mm,
                        total_bars=n_try,
                        is_t=is_t,
                        bf_cm=bf_cm,
                        hf_cm=hf_cm,
                        is_superior=True,
                    )
                    data_sup = detailer.detail(inp_try)
                    break
                except ValueError:
                    continue
        if data_sup is not None:
            for b in data_sup.bar_positions:
                if not b.is_corner_bar:
                    y_mirrored = h_mm - b.y
                    layer_sup = -(b.layer + 1)
                    all_bars.append(
                        BarPosition(
                            x=b.x,
                            y=round(y_mirrored, 3),
                            layer=layer_sup,
                            is_corner_bar=False,
                            phi_mm=phi_barra_sup_mm,
                        )
                    )
            if data_sup.requires_supplementary_stirrup:
                requires_grampos = True
                for gs in data_sup.supplementary_stirrup_positions:
                    all_grampos.append(SupplementaryStirrup(x=gs.x, layer=-(gs.layer + 1)))
        else:
            for b in data_inf.bar_positions:
                if b.is_corner_bar:
                    all_bars.append(b)
    else:
        # Se não há armadura superior, mantém as barras de canto construtivas de data_inf
        for b in data_inf.bar_positions:
            if b.is_corner_bar:
                all_bars.append(b)

    # 3. Armadura de pele
    skin_bars: list[BarPosition] = []
    if n_barras_pele > 0 and phi_pele_mm > 0:
        x_esq, x_dir, ys = posicionar_armadura_pele(
            h_mm=h_mm,
            bw_mm=bw_mm,
            cob_mm=cob_mm,
            phi_estribo_mm=phi_estribo_mm,
            n_barras_pele_face=n_barras_pele,
            phi_pele_mm=phi_pele_mm,
            bar_positions=all_bars,
            is_t=is_t,
            bf_mm=bf_mm,
            hf_mm=hf_mm,
            d_max_agregado_mm=d_max_agregado_mm,
            phi_barra_inf_mm=phi_barra_inf_mm,
            phi_barra_sup_mm=phi_barra_sup_mm if phi_barra_sup_mm > 0 else phi_barra_inf_mm,
        )
        for y_bar in ys:
            b_esq = BarPosition(
                x=round(x_esq, 3),
                y=round(y_bar, 3),
                layer=-99,
                is_corner_bar=False,
                is_skin_bar=True,
                phi_mm=phi_pele_mm,
            )
            b_dir = BarPosition(
                x=round(x_dir, 3),
                y=round(y_bar, 3),
                layer=-99,
                is_corner_bar=False,
                is_skin_bar=True,
                phi_mm=phi_pele_mm,
            )
            skin_bars.extend([b_esq, b_dir])

    return SectionLayoutData(
        bw=bw_mm,
        h=h_mm,
        c_nom=cob_mm,
        phi_estribo=phi_estribo_mm,
        phi_barra=phi_barra_inf_mm,
        d_max_agregado=d_max_agregado_mm,
        total_bars=n_barras_inf,
        eh_min=data_inf.eh_min,
        ev_min=data_inf.ev_min,
        layer_count=data_inf.layer_count,
        layers=data_inf.layers,
        bar_positions=all_bars,
        requires_supplementary_stirrup=requires_grampos,
        supplementary_stirrup_positions=all_grampos,
        y_cg=data_inf.y_cg,
        d_efetiva=data_inf.d_efetiva,
        is_t=is_t,
        bf=bf_mm,
        hf=hf_mm,
        warnings=data_inf.warnings,
        skin_bar_positions=skin_bars,
        total_bars_sup=n_barras_sup,
        phi_barra_sup=phi_barra_sup_mm,
    )
