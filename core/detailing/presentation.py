"""
core/detailing/presentation.py
══════════════════════════════════════════════════════════════════════════════
CAMADA DE APRESENTAÇÃO — Desenho da Seção Transversal
══════════════════════════════════════════════════════════════════════════════

Estrutura em 3 peças:

  1. BeamSectionCommands  — "Painter burro": traduz SectionLayoutData em uma
                            lista de DrawCmd (comandos de desenho agnósticos).
                            Não conhece fpdf2 nem flet.canvas.

  2. FletCanvasRenderer   — Executa DrawCmd em um flet.canvas.Canvas.
                            Use dentro de um ft.Canvas no app Flet.

  3. FpdfRenderer         — Executa DrawCmd em um objeto FPDF (fpdf2).
                            Use dentro de desenhar_secao_retangular() no
                            relatorio_base.py para substituir o código atual.

NÃO contém lógica normativa (NBR). O "Painter" é burro — apenas desenha
os dados que a camada de domínio (BeamDetailer) já preparou.

Autor: Samuel Santos (https://github.com/samuel-c-santos)
Licença: vide LICENSE
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any, Protocol

from .domain import SectionLayoutData, BarPosition


# ══════════════════════════════════════════════════════════════════════════════
# Paleta de cores (RGB 0-255)
# ══════════════════════════════════════════════════════════════════════════════
_C_CONCRETE_FILL   = (235, 235, 230)   # cinza claro concreto
_C_CONCRETE_STROKE = (120, 120, 120)   # contorno da seção
_C_STIRRUP         = (0, 0, 180)       # estribo: azul portica
_C_BAR_MAIN        = (20, 30, 90)      # barras principais: azul navy
_C_BAR_MAIN_STROKE = None              # contorno das barras (removido para evitar borda branca)
_C_BAR_CORNER      = (40, 140, 60)     # barras construtivas: verde
_C_GRAMPO          = (180, 70, 10)     # grampos: laranja
_C_DIM             = (80, 80, 200)     # cotas: azul claro
_C_TEXT            = (50, 50, 50)      # texto padrão
_C_CG_LINE         = (200, 40, 40)     # linha do baricentro: vermelho


# ══════════════════════════════════════════════════════════════════════════════
# Comandos de Desenho (DrawCmd)
# Linguagem intermediária agnóstica de canvas.
# ══════════════════════════════════════════════════════════════════════════════

RGB = Tuple[int, int, int]  # shorthand


@dataclass
class CmdRect:
    """Retângulo. Coords em mm no espaço da seção (Y↑, origem canto inf-esq)."""
    x: float; y: float; w: float; h: float
    fill: Optional[RGB] = None
    stroke: Optional[RGB] = None
    line_width: float = 0.5


@dataclass
class CmdCircle:
    """Círculo."""
    cx: float; cy: float; r: float
    fill: Optional[RGB] = None
    stroke: Optional[RGB] = None
    line_width: float = 0.3


@dataclass
class CmdLine:
    """Linha simples."""
    x1: float; y1: float; x2: float; y2: float
    color: RGB = field(default_factory=lambda: _C_DIM)
    line_width: float = 0.3
    dashed: bool = False


@dataclass
class CmdPolyline:
    """Sequência de segmentos de linha (não fechada)."""
    points: List[Tuple[float, float]]   # lista de (x, y)
    color: RGB = field(default_factory=lambda: _C_STIRRUP)
    line_width: float = 1.0


@dataclass
class CmdArcPath:
    """Arco de círculo (usado nos cantos do estribo).
    Approximated as a polyline by the renderers (8 steps/quarter).
    """
    cx: float; cy: float; radius: float
    start_angle_deg: float   # graus, 0 = direita, sentido antihorário
    sweep_angle_deg: float   # varrido (positivo = antihorário)
    color: RGB = field(default_factory=lambda: _C_STIRRUP)
    line_width: float = 1.0


@dataclass
class CmdText:
    """Texto posicionado."""
    x: float; y: float
    text: str
    font_size: float = 7.0
    color: RGB = field(default_factory=lambda: _C_TEXT)
    align: str = "L"   # "L", "C", "R"


@dataclass
class CmdPolygon:
    """Polígono fechado com preenchimento opcional."""
    points: List[Tuple[float, float]]
    fill: Optional[RGB] = None
    stroke: Optional[RGB] = None
    line_width: float = 0.5


# União dos comandos
DrawCmd = CmdRect | CmdCircle | CmdLine | CmdPolyline | CmdArcPath | CmdText | CmdPolygon


# ══════════════════════════════════════════════════════════════════════════════
# Painter Burro — BeamSectionCommands
# ══════════════════════════════════════════════════════════════════════════════

class BeamSectionCommands:
    """Gera a lista de DrawCmd a partir de SectionLayoutData.

    NÃO executa os comandos. NÃO faz cálculos normativos.
    Recebe coordenadas prontas do domínio e as mapeia para comandos gráficos.

    Coordenadas internas: mm, origem canto inferior-esquerdo, Y↑.
    Os renderers convertem para o sistema de cada canvas.

    Usage::

        data = BeamDetailer().detail(inp)
        cmds = BeamSectionCommands().build(data)
        # Na tela Flet:
        FletCanvasRenderer(scale=1.8).render(cmds, canvas_shapes)
        # No PDF:
        FpdfRenderer(pdf, px=20, py=15, scale=0.5).render(cmds)
    """

    def build(self, data: SectionLayoutData) -> List[DrawCmd]:
        """Produz a lista completa de comandos de desenho."""
        cmds: List[DrawCmd] = []
        self._draw_concrete(cmds, data)
        self._draw_stirrup(cmds, data)
        self._draw_corner_bars(cmds, data)
        self._draw_main_bars(cmds, data)
        self._draw_supplementary_stirrups(cmds, data)
        self._draw_dimensions(cmds, data)
        self._draw_labels(cmds, data)
        return cmds

    # ── Bloco 1: Contorno de concreto ─────────────────────────────────────────

    def _draw_concrete(self, cmds: List[DrawCmd], d: SectionLayoutData) -> None:
        if getattr(d, "is_t", False):
            bf = d.bf
            hf = d.hf
            bw = d.bw
            h = d.h
            # Single polygon for T-beam concrete contour
            vertices = [
                ((bf - bw) / 2.0, 0.0),
                ((bf + bw) / 2.0, 0.0),
                ((bf + bw) / 2.0, h - hf),
                (bf, h - hf),
                (bf, h),
                (0.0, h),
                (0.0, h - hf),
                ((bf - bw) / 2.0, h - hf)
            ]
            cmds.append(CmdPolygon(
                points=vertices,
                fill=_C_CONCRETE_FILL,
                stroke=_C_CONCRETE_STROKE,
                line_width=0.8,
            ))
        else:
            cmds.append(CmdRect(
                x=0, y=0, w=d.bw, h=d.h,
                fill=_C_CONCRETE_FILL,
                stroke=_C_CONCRETE_STROKE,
                line_width=0.8,
            ))

    # ── Bloco 2: Estribo principal com raio de curvatura e gancho 135° ────────

    def _draw_stirrup(self, cmds: List[DrawCmd], d: SectionLayoutData) -> None:
        c  = d.c_nom
        pe = d.phi_estribo
        r  = d.stirrup_corner_radius    # raio interno dos cantos
        lh = d.hook_length              # comprimento do gancho

        # Canto interno do estribo (eixo do fio) medido da face externa:
        # distância do fio ao canto = c + pe/2
        margin = c + pe / 2

        is_t = getattr(d, "is_t", False)
        bf = d.bf if is_t else d.bw
        bw = d.bw

        # Coordenadas do retângulo do eixo do estribo:
        ex = (bf - bw) / 2.0 + margin if is_t else margin
        ey = margin
        ew = bw - 2 * margin         # width
        eh = d.h  - 2 * margin         # height

        # Construímos o estribo como uma polyline com arcos aproximados nos
        # cantos. Para simplicidade de implementação compatível com fpdf2 e
        # flet.canvas, aproximamos cada canto com 6 segmentos de linha.
        pts = self._rounded_rect_polyline(ex, ey, ew, eh, r)

        # Fecha a polyline com um ponto de ancoragem do gancho
        # (ponto de início do gancho = topo, a 60% do comprimento superior)
        hook_anchor_x = ex + ew * 0.6
        hook_anchor_y = ey + eh  # topo do estribo

        # Adiciona ponto de retorno ao início (para fechar a forma)
        pts.append((hook_anchor_x, hook_anchor_y))

        cmds.append(CmdPolyline(
            points=pts,
            color=_C_STIRRUP,
            line_width=pe * 0.7,  # espessura proporcional ao diâmetro
        ))

        # Gancho a 135° (diagonal interior de 45°): sobe e vai para esquerda
        sin45 = math.cos(math.radians(45))
        hx = lh * sin45
        hy = lh * sin45
        cmds.append(CmdPolyline(
            points=[
                (hook_anchor_x, hook_anchor_y),
                (hook_anchor_x - hx, hook_anchor_y + hy),
            ],
            color=_C_STIRRUP,
            line_width=pe * 0.7,
        ))

    # ── Bloco 3: Barras de canto superiores ───────────────────────────────────

    def _draw_corner_bars(self, cmds: List[DrawCmd], d: SectionLayoutData) -> None:
        r_vis = max(d.phi_estribo / 2, 1.5)  # raio mínimo visível
        for bar in d.bar_positions:
            if not bar.is_corner_bar:
                continue
            cmds.append(CmdCircle(
                cx=bar.x, cy=bar.y, r=r_vis,
                fill=_C_BAR_CORNER,
                stroke=_C_BAR_MAIN_STROKE,
                line_width=0.3,
            ))

    # ── Bloco 4: Barras longitudinais principais ───────────────────────────────

    def _draw_main_bars(self, cmds: List[DrawCmd], d: SectionLayoutData) -> None:
        r = d.phi_barra / 2
        for bar in d.bar_positions:
            if bar.is_corner_bar:
                continue
            cmds.append(CmdCircle(
                cx=bar.x, cy=bar.y, r=r,
                fill=_C_BAR_MAIN,
                stroke=_C_BAR_MAIN_STROKE,
                line_width=0.3,
            ))

    # ── Bloco 5: Grampos suplementares ────────────────────────────────────────

    def _draw_supplementary_stirrups(
        self, cmds: List[DrawCmd], d: SectionLayoutData
    ) -> None:
        if not d.requires_supplementary_stirrup:
            return

        pe = d.phi_estribo
        arm_w = pe * 3.0   # meia-largura do grampo
        arm_h = pe * 8.0   # altura dos braços do grampo

        for gs in d.supplementary_stirrup_positions:
            # Encontra a barra correspondente para saber o Y
            bar = next(
                (b for b in d.bar_positions
                 if not b.is_corner_bar and b.layer == gs.layer and abs(b.x - gs.x) < 1),
                None,
            )
            if bar is None:
                continue
            # Topo do grampo: acima da barra
            top_y = bar.y + d.phi_barra / 2 + pe / 2

            # Grampo em "U" invertido: dois braços verticais + travessa horizontal
            cmds.append(CmdPolyline(
                points=[
                    (gs.x - arm_w, top_y + arm_h),
                    (gs.x - arm_w, top_y),
                    (gs.x + arm_w, top_y),
                    (gs.x + arm_w, top_y + arm_h),
                ],
                color=_C_GRAMPO,
                line_width=pe * 0.6,
            ))

    # ── Bloco 6: Cotas ────────────────────────────────────────────────────────

    def _draw_dimensions(self, cmds: List[DrawCmd], d: SectionLayoutData) -> None:
        is_t = getattr(d, "is_t", False)
        bf = d.bf if is_t else d.bw
        bw = d.bw
        h = d.h
        hf = d.hf if is_t else 0.0

        y_dim = -8.0
        
        if is_t:
            # bf (no topo)
            cmds.append(CmdLine(x1=0, y1=h + 8.0, x2=bf, y2=h + 8.0,
                                color=_C_DIM, line_width=0.4))
            self._arrow_h(cmds, 0, bf, h + 8.0)
            cmds.append(CmdText(
                x=bf / 2.0, y=h + 10.0,
                text=f"bf={bf/10:.0f} cm",
                font_size=7.0, color=_C_DIM, align="C",
            ))
            
            # hf (na lateral esquerda)
            x_dim_f = -8.0
            cmds.append(CmdLine(x1=x_dim_f, y1=h - hf, x2=x_dim_f, y2=h,
                                color=_C_DIM, line_width=0.4))
            self._arrow_v(cmds, x_dim_f, h - hf, h)
            cmds.append(CmdText(
                x=x_dim_f - 3.0, y=h - hf / 2.0,
                text=f"hf={hf/10:.0f} cm",
                font_size=7.0, color=_C_DIM, align="R",
            ))

            # bw (embaixo)
            x1_w = (bf - bw) / 2.0
            x2_w = (bf + bw) / 2.0
            cmds.append(CmdLine(x1=x1_w, y1=y_dim, x2=x2_w, y2=y_dim,
                                color=_C_DIM, line_width=0.4))
            self._arrow_h(cmds, x1_w, x2_w, y_dim)
            cmds.append(CmdText(
                x=bf / 2.0, y=y_dim - 5.0,
                text=f"bw={bw/10:.0f} cm",
                font_size=7.0, color=_C_DIM, align="C",
            ))
        else:
            # bw (embaixo)
            cmds.append(CmdLine(x1=0, y1=y_dim, x2=bw, y2=y_dim,
                                color=_C_DIM, line_width=0.4))
            self._arrow_h(cmds, 0, bw, y_dim)
            cmds.append(CmdText(
                x=bw / 2.0, y=y_dim - 5.0,
                text=f"bw={bw/10:.0f} cm",
                font_size=7.0, color=_C_DIM, align="C",
            ))

        # Cota vertical h (à direita da seção)
        x_dim = bf + 8.0
        cmds.append(CmdLine(x1=x_dim, y1=0, x2=x_dim, y2=h,
                            color=_C_DIM, line_width=0.4))
        self._arrow_v(cmds, x_dim, 0, h)
        cmds.append(CmdText(
            x=x_dim + 3.0, y=h / 2.0,
            text=f"h={h/10:.0f} cm",
            font_size=7.0, color=_C_DIM, align="L",
        ))

        # Cota cobrimento (traço pontilhado pequeno)
        y_cob = h * 0.25
        x1_cob = (bf - bw) / 2.0 if is_t else 0.0
        cmds.append(CmdLine(
            x1=x1_cob, y1=y_cob, x2=x1_cob + d.c_nom, y2=y_cob,
            color=_C_DIM, line_width=0.3, dashed=True,
        ))
        cmds.append(CmdText(
            x=x1_cob + d.c_nom / 2.0, y=y_cob + 3.0,
            text=f"c={d.c_nom:.0f}", font_size=6.0, color=_C_DIM, align="C",
        ))

        # Linha tracejada do baricentro (vermelho)
        cmds.append(CmdLine(
            x1=0, y1=d.y_cg, x2=bf, y2=d.y_cg,
            color=_C_CG_LINE, line_width=0.4, dashed=True,
        ))
        cmds.append(CmdText(
            x=bf / 2.0, y=d.y_cg + 3.0,
            text="CG arm.", font_size=6.0, color=_C_CG_LINE, align="C",
        ))

    # ── Bloco 7: Rótulos de armadura ──────────────────────────────────────────

    def _draw_labels(self, cmds: List[DrawCmd], d: SectionLayoutData) -> None:
        is_t = getattr(d, "is_t", False)
        bf = d.bf if is_t else d.bw
        for lyr in d.layers:
            cmds.append(CmdText(
                x=bf + 5.0,
                y=lyr.y_centroid,
                text=(
                    f"{lyr.bar_count}\u00d8{d.phi_barra:.0f}mm "
                    f"({lyr.h_spacing/10:.1f}cm)"
                    if lyr.h_spacing > 0 else f"{lyr.bar_count}\u00d8{d.phi_barra:.0f}mm"
                ),
                font_size=7.5,
                color=_C_TEXT,
                align="L",
            ))

        # d efetiva
        cmds.append(CmdText(
            x=-5.0, y=d.d_efetiva / 2.0,
            text=f"d={d.d_efetiva:.1f}mm",
            font_size=6.5, color=_C_DIM, align="R",
        ))

    # ── Auxiliares ────────────────────────────────────────────────────────────

    @staticmethod
    def _rounded_rect_polyline(
        x: float, y: float, w: float, h: float, r: float, steps: int = 6
    ) -> List[Tuple[float, float]]:
        """Gera pontos de um retângulo com cantos arredondados (Y↑)."""
        pts: List[Tuple[float, float]] = []

        def arc_pts(cx, cy, r, a_start_deg, a_end_deg):
            n = steps
            result = []
            for k in range(n + 1):
                t = math.radians(a_start_deg + (a_end_deg - a_start_deg) * k / n)
                result.append((cx + r * math.cos(t), cy + r * math.sin(t)))
            return result

        r = min(r, w / 2, h / 2)  # garante que r não excede a seção

        # Cantos em sentido antihorário, origem no lado inferior-esquerdo
        # Inferior-esquerdo (270° → 180°)
        pts += arc_pts(x + r, y + r, r, 270, 180)
        # Inferior-direito (180° → 90°)
        pts += arc_pts(x + w - r, y + r, r, 180, 90)
        # Superior-direito (90° → 0°)
        pts += arc_pts(x + w - r, y + h - r, r, 90, 0)
        # Superior-esquerdo (0° → -90°)
        pts += arc_pts(x + r, y + h - r, r, 0, -90)
        # Fechar
        pts.append(pts[0])
        return pts

    @staticmethod
    def _arrow_h(cmds, x1, x2, y, size=2.5):
        cmds.append(CmdPolyline(
            points=[(x1 + size, y - size / 2), (x1, y), (x1 + size, y + size / 2)],
            color=_C_DIM, line_width=0.3,
        ))
        cmds.append(CmdPolyline(
            points=[(x2 - size, y - size / 2), (x2, y), (x2 - size, y + size / 2)],
            color=_C_DIM, line_width=0.3,
        ))

    @staticmethod
    def _arrow_v(cmds, x, y1, y2, size=2.5):
        cmds.append(CmdPolyline(
            points=[(x - size / 2, y1 + size), (x, y1), (x + size / 2, y1 + size)],
            color=_C_DIM, line_width=0.3,
        ))
        cmds.append(CmdPolyline(
            points=[(x - size / 2, y2 - size), (x, y2), (x + size / 2, y2 - size)],
            color=_C_DIM, line_width=0.3,
        ))


# ══════════════════════════════════════════════════════════════════════════════
# Renderer 1: Flet Canvas (flet.canvas)
# ══════════════════════════════════════════════════════════════════════════════

class FletCanvasRenderer:
    """Executa DrawCmd em um flet.canvas.Canvas.

    Converte as coordenadas do domínio (Y↑, mm) para o sistema Flet
    (Y↓, pixels), aplicando o fator de escala.

    Usage::

        import flet as ft
        import flet.canvas as cv

        data = BeamDetailer().detail(inp)
        cmds = BeamSectionCommands().build(data)

        shapes = []
        renderer = FletCanvasRenderer(scale=1.8, section_height_mm=data.h)
        renderer.render(cmds, shapes)

        canvas = cv.Canvas(shapes=shapes, width=..., height=...)
    """

    def __init__(self, scale: float = 1.5, section_height_mm: float = 500.0):
        """
        Args:
            scale: Fator de conversão mm → pixels.
            section_height_mm: Altura total da seção em mm (para inverter Y).
        """
        self.scale = scale
        self.H = section_height_mm  # altura em mm (para flip Y)

    def render(self, cmds: List[DrawCmd], shapes: list) -> None:
        """Adiciona shapes Flet à lista `shapes`.

        Args:
            cmds: Lista de DrawCmd produzida por BeamSectionCommands.
            shapes: Lista de cv.Shape que será atribuída a cv.Canvas.shapes.
        """
        # Import tardio para não forçar dependência de flet em testes unitários.
        import flet.canvas as cv

        for cmd in cmds:
            shape = self._to_flet(cmd, cv)
            if shape is not None:
                shapes.append(shape)

    def _px(self, mm: float) -> float:
        """mm → pixels (X)."""
        return mm * self.scale

    def _py(self, mm: float) -> float:
        """mm → pixels (Y), com flip (Y↑ domínio → Y↓ Flet)."""
        return (self.H - mm) * self.scale

    def _color(self, rgb: Optional[RGB]) -> Optional[str]:
        if rgb is None:
            return None
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def _to_flet(self, cmd: DrawCmd, cv: Any) -> Optional[Any]:
        import flet as ft

        if isinstance(cmd, CmdRect):
            # Flet canvas usa Y↓, então y do rect = topo em pixels
            top_px = self._py(cmd.y + cmd.h)
            return cv.Rect(
                x=self._px(cmd.x), y=top_px,
                width=self._px(cmd.w), height=self._px(cmd.h),
                paint=ft.Paint(
                    color=self._color(cmd.fill) if cmd.fill else None,
                    stroke_color=self._color(cmd.stroke) if cmd.stroke else None,
                    stroke_width=cmd.line_width * self.scale,
                    style=(
                        ft.PaintingStyle.FILL_AND_STROKE
                        if cmd.fill and cmd.stroke
                        else ft.PaintingStyle.FILL if cmd.fill
                        else ft.PaintingStyle.STROKE
                    ),
                ),
            )

        if isinstance(cmd, CmdCircle):
            return cv.Circle(
                x=self._px(cmd.cx), y=self._py(cmd.cy),
                radius=self._px(cmd.r),
                paint=ft.Paint(
                    color=self._color(cmd.fill) if cmd.fill else None,
                    stroke_color=self._color(cmd.stroke) if cmd.stroke else None,
                    stroke_width=cmd.line_width * self.scale,
                    style=(
                        ft.PaintingStyle.FILL_AND_STROKE
                        if cmd.fill and cmd.stroke
                        else ft.PaintingStyle.FILL if cmd.fill
                        else ft.PaintingStyle.STROKE
                    ),
                ),
            )

        if isinstance(cmd, (CmdLine, CmdPolyline)):
            if isinstance(cmd, CmdLine):
                pts_mm = [(cmd.x1, cmd.y1), (cmd.x2, cmd.y2)]
                color = cmd.color
                lw = cmd.line_width
            else:
                pts_mm = cmd.points
                color = cmd.color
                lw = cmd.line_width

            if len(pts_mm) < 2:
                return None

            path_elements = [
                cv.Path.MoveTo(self._px(pts_mm[0][0]), self._py(pts_mm[0][1]))
            ]
            for px_mm, py_mm in pts_mm[1:]:
                path_elements.append(cv.Path.LineTo(self._px(px_mm), self._py(py_mm)))

            return cv.Path(
                elements=path_elements,
                paint=ft.Paint(
                    color=self._color(color),
                    stroke_width=lw * self.scale,
                    style=ft.PaintingStyle.STROKE,
                ),
            )

        if isinstance(cmd, CmdPolygon):
            if len(cmd.points) < 3:
                return None
            path_elements = [
                cv.Path.MoveTo(self._px(cmd.points[0][0]), self._py(cmd.points[0][1]))
            ]
            for px_mm, py_mm in cmd.points[1:]:
                path_elements.append(cv.Path.LineTo(self._px(px_mm), self._py(py_mm)))
            path_elements.append(cv.Path.Close())
            return cv.Path(
                elements=path_elements,
                paint=ft.Paint(
                    color=self._color(cmd.fill) if cmd.fill else None,
                    stroke_color=self._color(cmd.stroke) if cmd.stroke else None,
                    stroke_width=cmd.line_width * self.scale,
                    style=(
                        ft.PaintingStyle.FILL_AND_STROKE
                        if cmd.fill and cmd.stroke
                        else ft.PaintingStyle.FILL if cmd.fill
                        else ft.PaintingStyle.STROKE
                    ),
                ),
            )

        if isinstance(cmd, CmdText):
            return cv.Text(
                x=self._px(cmd.x),
                y=self._py(cmd.y),
                text=cmd.text,
                style=ft.TextStyle(size=cmd.font_size * self.scale * 0.65),
                # color será aplicado via style se suportado
            )

        # CmdArcPath: approximado via CmdPolyline já no Painter, não deve chegar aqui
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Renderer 2: fpdf2 (FPDF)
# ══════════════════════════════════════════════════════════════════════════════

class FpdfRenderer:
    """Executa DrawCmd em um objeto FPDF (fpdf2).

    Converte coordenadas do domínio (Y↑, mm absolutos da seção) para
    coordenadas da página PDF (Y↓, mm a partir do topo da página),
    aplicando o fator de escala e o offset de posicionamento na página.

    Usage::

        data = BeamDetailer().detail(inp)
        cmds = BeamSectionCommands().build(data)

        # px, py = posição do canto superior-esquerdo da seção na página PDF
        renderer = FpdfRenderer(
            pdf=pdf_obj,
            px=ML + 5,       # mm da margem esquerda
            py=pdf.get_y(),  # mm do cursor atual
            scale=0.5,       # fator mm-seção → mm-página
            section_height_mm=data.h,
        )
        renderer.render(cmds)

    Substitui a antiga desenhar_secao_retangular() com fidelidade muito maior.
    """

    def __init__(
        self,
        pdf: Any,
        px: float,
        py: float,
        scale: float,
        section_height_mm: float,
    ):
        """
        Args:
            pdf: Instância de FPDF (ou PorticaPDF).
            px: Posição X do canto superior-esquerdo da seção na página (mm).
            py: Posição Y do canto superior-esquerdo da seção na página (mm).
            scale: Fator de conversão: mm-domínio → mm-página.
                   Exemplo: seção de 300 mm de largura em 60 mm de largura na
                   página → scale = 60/300 = 0.2
            section_height_mm: Altura total da seção em mm (para inverter Y).
        """
        self.pdf = pdf
        self.px = px
        self.py = py
        self.scale = scale
        self.H = section_height_mm

    def render(self, cmds: List[DrawCmd]) -> None:
        """Executa todos os comandos no PDF."""
        for cmd in cmds:
            self._exec(cmd)

    # ── Conversão de coordenadas ─────────────────────────────────────────────

    def _tx(self, x_mm: float) -> float:
        """X do domínio → X na página PDF (mm)."""
        return self.px + x_mm * self.scale

    def _ty(self, y_mm: float) -> float:
        """Y do domínio (↑) → Y na página PDF (↓, mm)."""
        return self.py + (self.H - y_mm) * self.scale

    def _sc(self, mm: float) -> float:
        """Escala uma dimensão."""
        return mm * self.scale

    def _set_color(self, rgb: Optional[RGB], is_fill: bool) -> None:
        if rgb is None:
            return
        if is_fill:
            self.pdf.set_fill_color(*rgb)
        else:
            self.pdf.set_draw_color(*rgb)

    # ── Execução dos comandos ────────────────────────────────────────────────

    def _exec(self, cmd: DrawCmd) -> None:
        pdf = self.pdf

        if isinstance(cmd, CmdRect):
            w = self._sc(cmd.w)
            h = self._sc(cmd.h)
            # Topo-esquerdo na página: y do domínio é o canto inferior da seção
            x_pg = self._tx(cmd.x)
            y_pg = self._ty(cmd.y + cmd.h)  # topo da seção em coord. página

            if cmd.fill:
                self._set_color(cmd.fill, is_fill=True)
            if cmd.stroke:
                self._set_color(cmd.stroke, is_fill=False)
                pdf.set_line_width(cmd.line_width)

            style = "FD" if (cmd.fill and cmd.stroke) else "F" if cmd.fill else "D"
            pdf.rect(x_pg, y_pg, w, h, style=style)

        elif isinstance(cmd, CmdCircle):
            r = self._sc(cmd.r)
            cx = self._tx(cmd.cx)
            cy = self._ty(cmd.cy)

            if cmd.fill:
                self._set_color(cmd.fill, is_fill=True)
            if cmd.stroke:
                self._set_color(cmd.stroke, is_fill=False)
                pdf.set_line_width(cmd.line_width)

            style = "FD" if (cmd.fill and cmd.stroke) else "F" if cmd.fill else "D"
            # fpdf2: ellipse(x_topo_esq, y_topo_esq, w, h)
            pdf.ellipse(cx - r, cy - r, r * 2, r * 2, style=style)

        elif isinstance(cmd, CmdLine):
            self._set_color(cmd.color, is_fill=False)
            pdf.set_line_width(cmd.line_width)
            if cmd.dashed:
                pdf.set_dash_pattern(dash=2, gap=1.5)
            pdf.line(self._tx(cmd.x1), self._ty(cmd.y1),
                     self._tx(cmd.x2), self._ty(cmd.y2))
            if cmd.dashed:
                pdf.set_dash_pattern()  # reset

        elif isinstance(cmd, CmdPolyline):
            if len(cmd.points) < 2:
                return
            self._set_color(cmd.color, is_fill=False)
            pdf.set_line_width(cmd.line_width)
            pts_pg = [(self._tx(x), self._ty(y)) for x, y in cmd.points]
            for k in range(len(pts_pg) - 1):
                pdf.line(pts_pg[k][0], pts_pg[k][1],
                         pts_pg[k + 1][0], pts_pg[k + 1][1])

        elif isinstance(cmd, CmdText):
            r_mm, g_mm, b_mm = cmd.color
            pdf.set_text_color(r_mm, g_mm, b_mm)
            pdf.set_font("Courier", "", cmd.font_size)
            x_pg = self._tx(cmd.x)
            y_pg = self._ty(cmd.y)
            # Ajuste de alinhamento
            align = {"L": "L", "C": "C", "R": "R"}.get(cmd.align, "L")
            pdf.set_xy(x_pg, y_pg)
            pdf.cell(40, 4, cmd.text, border=0, align=align)

        elif isinstance(cmd, CmdPolygon):
            if len(cmd.points) < 3:
                return
            if cmd.fill:
                self._set_color(cmd.fill, is_fill=True)
            if cmd.stroke:
                self._set_color(cmd.stroke, is_fill=False)
                pdf.set_line_width(cmd.line_width)
            pts_pg = [(self._tx(x), self._ty(y)) for x, y in cmd.points]
            style = "FD" if (cmd.fill and cmd.stroke) else "F" if cmd.fill else "D"
            pdf.polygon(pts_pg, style=style)

        elif isinstance(cmd, CmdArcPath):
            # Não deve ser emitido diretamente pelo BeamSectionCommands,
            # mas tratamos como fallback (sem-op)
            pass


# ══════════════════════════════════════════════════════════════════════════════
# Função de conveniência para substituir desenhar_secao_retangular()
# ══════════════════════════════════════════════════════════════════════════════

def desenhar_secao_com_detailer(
    pdf: Any,
    h_cm: float,
    bw_cm: float,
    cob_mm: float,
    phi_estribo_mm: float,
    phi_barra_inf_mm: float,
    n_barras_inf: int,
    phi_barra_sup_mm: float = 0.0,
    n_barras_sup: int = 0,
    d_max_agregado_mm: float = 19.0,
    px: Optional[float] = None,
    py: Optional[float] = None,
    max_h_mm_pagina: float = 80.0,
    max_w_mm_pagina: float = 55.0,
    is_t: bool = False,
    bf_cm: float = 0.0,
    hf_cm: float = 0.0,
    n_barras_pele: int = 0,
    phi_pele_mm: float = 0.0,
) -> SectionLayoutData:
    """Wrapper plug-in para relatorio_base.py.

    Substitui a chamada à antiga `desenhar_secao_retangular()` com uma que usa
    o pipeline completo (domínio → painter → renderer), adicionando distribuição
    correta de camadas, grampos e estribo realista.

    Retorna o SectionLayoutData para uso posterior (legenda, tabela, etc.).
    """
    from .domain import BeamDetailer, BeamDetailingInput  # import local p/ evitar circular

    h_mm = h_cm * 10.0
    bw_mm = bw_cm * 10.0
    bf_mm = bf_cm * 10.0 if is_t else bw_mm

    # Fator de escala: domínio em mm, página em mm (unidades PDF)
    scale = min(max_h_mm_pagina / h_mm, max_w_mm_pagina / bf_mm)

    if px is None:
        px = pdf.get_x()
    if py is None:
        py = pdf.get_y()

    # ── Domínio: barras inferiores ─────────────────────────────────────────
    detailer = BeamDetailer()
    data_inf = detailer.detail(BeamDetailingInput(
        bw=bw_mm,
        h=h_mm,
        c_nom=cob_mm,
        phi_estribo=phi_estribo_mm,
        phi_barra=phi_barra_inf_mm,
        d_max_agregado=d_max_agregado_mm,
        total_bars=n_barras_inf,
        is_t=is_t,
        bf_cm=bf_cm,
        hf_cm=hf_cm,
        is_superior=False,
    ))

    # ── Comandos e render das barras inferiores ────────────────────────────
    painter = BeamSectionCommands()
    cmds = painter.build(data_inf)

    renderer = FpdfRenderer(
        pdf=pdf, px=px, py=py, scale=scale, section_height_mm=h_mm
    )
    renderer.render(cmds)

    # ── Barras superiores (se houver, sobrepõe com cor diferente) ──────────
    if n_barras_sup > 0 and phi_barra_sup_mm > 0:
        data_sup = detailer.detail(BeamDetailingInput(
            bw=bw_mm, h=h_mm, c_nom=cob_mm, phi_estribo=phi_estribo_mm,
            phi_barra=phi_barra_sup_mm, d_max_agregado=d_max_agregado_mm,
            total_bars=n_barras_sup,
            is_t=is_t,
            bf_cm=bf_cm,
            hf_cm=hf_cm,
            is_superior=True,
        ))
        # Desenha apenas as barras da armadura de compressão (face superior)
        # Reusa o mesmo renderer; inverte verticalmente no espaço disponível.
        sup_renderer = FpdfRenderer(
            pdf=pdf, px=px, py=py, scale=scale, section_height_mm=h_mm
        )
        for bar in data_sup.bar_positions:
            if bar.is_corner_bar:
                continue
            # Espelha Y: barras superiores ficam perto do topo
            y_espelhado = h_mm - bar.y
            r = max(phi_barra_sup_mm * scale / 2, 1.0)
            cx = px + bar.x * scale
            cy = py + y_espelhado * scale
            pdf.set_fill_color(*_C_BAR_MAIN)
            # Sem contorno (apenas preenchimento)
            pdf.ellipse(cx - r, cy - r, r * 2, r * 2, style="F")

    # ── Armadura de pele (faces laterais) ──────────────────────────────────
    if n_barras_pele > 0 and phi_pele_mm > 0:
        pdf.set_fill_color(197, 90, 17)   # Orange800
        # Sem contorno (apenas preenchimento)
        r_pele = max(phi_pele_mm * scale / 2.0, 1.0)
        
        # Posicionamento X na alma
        if is_t:
            alma_x = px + (bf_mm - bw_mm) / 2.0 * scale
            e_off = (cob_mm + phi_estribo_mm / 2.0) * scale
            x_face_esq = alma_x + e_off + (phi_estribo_mm / 2.0 + phi_pele_mm / 2.0) * scale
            x_face_dir = alma_x + bw_mm * scale - e_off - (phi_estribo_mm / 2.0 + phi_pele_mm / 2.0) * scale
        else:
            e_off = (cob_mm + phi_estribo_mm / 2.0) * scale
            x_face_esq = px + e_off + (phi_estribo_mm / 2.0 + phi_pele_mm / 2.0) * scale
            x_face_dir = px + bw_mm * scale - e_off - (phi_estribo_mm / 2.0 + phi_pele_mm / 2.0) * scale
            
        layer_count_inf = data_inf.layer_count if data_inf else 0
        layer_count_sup = data_sup.layer_count if (n_barras_sup > 0 and phi_barra_sup_mm > 0 and 'data_sup' in locals()) else 0
        ev_min_inf_mm = data_inf.ev_min if (data_inf and hasattr(data_inf, 'ev_min')) else max(20.0, phi_barra_inf_mm, 22.8)
        ev_min_sup_mm = data_sup.ev_min if (n_barras_sup > 0 and phi_barra_sup_mm > 0 and 'data_sup' in locals() and hasattr(data_sup, 'ev_min')) else max(20.0, phi_barra_sup_mm, 22.8)

        # Determinar limites brutos (sem gaps) medidos em cm a partir do topo da viga
        if is_t:
            y_top_raw_cm = hf_cm + (cob_mm / 10.0 + phi_estribo_mm / 10.0)
        else:
            y_top_raw_cm = cob_mm / 10.0 + phi_estribo_mm / 10.0
            if n_barras_sup > 0 and phi_barra_sup_mm > 0 and 'data_sup' in locals() and data_sup and data_sup.bar_positions:
                top_bars_bottoms = []
                for bar in data_sup.bar_positions:
                    if not bar.is_corner_bar:
                        top_bars_bottoms.append((bar.y + phi_barra_sup_mm / 2.0) / 10.0)
                if top_bars_bottoms:
                    y_top_raw_cm = max(top_bars_bottoms)
            elif layer_count_sup > 0:
                y_top_raw_cm += layer_count_sup * (phi_barra_sup_mm / 10.0) + (layer_count_sup - 1) * (ev_min_sup_mm / 10.0)

        y_bottom_raw_cm = h_cm - (cob_mm / 10.0 + phi_estribo_mm / 10.0)
        if data_inf and data_inf.bar_positions:
            bottom_bars_tops = []
            for bar in data_inf.bar_positions:
                if not bar.is_corner_bar:
                    bottom_bars_tops.append(h_cm - (bar.y + phi_barra_inf_mm / 2.0) / 10.0)
            if bottom_bars_tops:
                y_bottom_raw_cm = min(bottom_bars_tops)
        elif layer_count_inf > 0:
            y_bottom_raw_cm -= layer_count_inf * (phi_barra_inf_mm / 10.0) + (layer_count_inf - 1) * (ev_min_inf_mm / 10.0)

        ev_min_cm = ev_min_inf_mm / 10.0
        h_free_cm = y_bottom_raw_cm - y_top_raw_cm
        phi_pele_cm = phi_pele_mm / 10.0
        d_livre_cm = (h_free_cm - n_barras_pele * phi_pele_cm) / (n_barras_pele + 1.0)

        if d_livre_cm >= ev_min_cm:
            ys_cm = [y_top_raw_cm + (i + 1) * d_livre_cm + (i + 0.5) * phi_pele_cm for i in range(n_barras_pele)]
        else:
            # Fallback
            y_top_est = hf_cm + (cob_mm / 10.0 + phi_estribo_mm / 10.0) if is_t else cob_mm / 10.0 + phi_estribo_mm / 10.0
            y_bottom_est = h_cm - (cob_mm / 10.0 + phi_estribo_mm / 10.0)
            s_pele_fb = (y_bottom_est - y_top_est) / (n_barras_pele + 1.0)
            ys_cm = [y_top_est + (i + 1) * s_pele_fb for i in range(n_barras_pele)]

        for face_x in [x_face_esq, x_face_dir]:
            for y_bar_cm in ys_cm:
                y_bar = py + y_bar_cm * 10.0 * scale
                pdf.ellipse(face_x - r_pele, y_bar - r_pele, r_pele * 2, r_pele * 2, style="F")

    # Avança o cursor do PDF para após o desenho
    pdf.set_y(py + h_mm * scale + 8)

    return data_inf
