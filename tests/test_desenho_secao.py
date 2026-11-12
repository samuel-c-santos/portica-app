"""Regressões de desenho da seção transversal (EP-04.4).

O refactor que unificou as quatro funções de desenho quebrou a geometria:
o estribo era fechado com um ponto de gancho fora de ordem (traço diagonal
cortando a seção), a espessura de linha não era escalada (borrão azul no PDF)
e, na viga T, o DXF usava barras detalhadas como seção retangular (barras
fora do concreto).
"""

from __future__ import annotations

import math
from pathlib import Path

import ezdxf

from core.detailing.domain import detalhar_secao_completa
from core.detailing.dxf_export import exportar_secao_dxf
from core.detailing.presentation import BeamSectionCommands, CmdPolyline, CmdText

BW_CM, H_CM = 20.0, 70.0


def _comandos_retangular():
    data = detalhar_secao_completa(
        h_cm=H_CM,
        bw_cm=BW_CM,
        cob_mm=30,
        phi_estribo_mm=6.3,
        phi_barra_inf_mm=16,
        n_barras_inf=4,
        phi_barra_sup_mm=16,
        n_barras_sup=4,
        n_barras_pele=5,
        phi_pele_mm=6.3,
    )
    return data, BeamSectionCommands().build(data)


def test_estribo_e_polyline_fechada_sem_saltos():
    """O estribo tem de ser um retângulo contínuo, não um zigue-zague."""
    data, cmds = _comandos_retangular()

    estribo = max(
        (c for c in cmds if isinstance(c, CmdPolyline)),
        key=lambda c: len(c.points),
    )
    pts = estribo.points

    assert pts[0] == pts[-1], "a polyline do estribo deve fechar no primeiro ponto"

    # Cada segmento tem de ser um lado reto (alinhado a X ou Y) ou um arco
    # curto de canto. O bug original criava uma diagonal do canto inferior
    # esquerdo até o topo, que não é nem uma coisa nem outra.
    for i in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        alinhado = abs(x2 - x1) < 0.5 or abs(y2 - y1) < 0.5
        curto = math.dist((x1, y1), (x2, y2)) <= 2 * data.stirrup_corner_radius
        assert alinhado or curto, (
            f"segmento diagonal no estribo: ({x1:.1f},{y1:.1f})->({x2:.1f},{y2:.1f})"
        )


def test_estribo_dentro_da_secao():
    data, cmds = _comandos_retangular()
    estribo = max((c for c in cmds if isinstance(c, CmdPolyline)), key=lambda c: len(c.points))
    xs = [p[0] for p in estribo.points]
    ys = [p[1] for p in estribo.points]
    assert min(xs) >= -0.1 and max(xs) <= data.bw + 0.1
    assert min(ys) >= -0.1 and max(ys) <= data.h + 0.1


def test_sem_rotulos_de_armadura_em_cima_da_legenda():
    """Rótulos por camada (x = bf + 5) colidiam com a legenda do relatório."""
    data, cmds = _comandos_retangular()
    rotulos = [
        c for c in cmds if isinstance(c, CmdText) and ("Ø" in c.text or c.text.startswith("d="))
    ]
    fora = [t for t in rotulos if t.x > data.bw + 1.0]
    assert not fora, [(t.text, t.x) for t in fora]


def test_dxf_viga_t_mantem_barras_dentro_do_concreto(tmp_path: Path):
    """Todas as barras do DXF devem cair na mesa ou na alma."""
    bf, hf = 60.0, 12.0
    data = detalhar_secao_completa(
        h_cm=H_CM,
        bw_cm=BW_CM,
        cob_mm=30,
        phi_estribo_mm=5,
        phi_barra_inf_mm=16,
        n_barras_inf=10,
        phi_barra_sup_mm=16,
        n_barras_sup=2,
        n_barras_pele=5,
        phi_pele_mm=6.3,
        is_t=True,
        bf_cm=bf,
        hf_cm=hf,
    )
    posicoes = [
        {
            "x": b.x,
            "y": b.y,
            "layer": b.layer,
            "is_corner_bar": b.is_corner_bar,
            "phi_mm": b.phi_mm,
        }
        for b in data.bar_positions
    ]
    destino = tmp_path / "secao_t.dxf"
    exportar_secao_dxf(
        bw_cm=BW_CM,
        h_cm=H_CM,
        cob_cm=3.0,
        phi_estribo_mm=5,
        bar_positions=posicoes,
        phi_barra_mm=16,
        n_barras_pele=5,
        phi_pele_mm=6.3,
        is_t=True,
        bf_cm=bf,
        hf_cm=hf,
        nome_arquivo=str(destino),
    )

    msp = ezdxf.readfile(destino).modelspace()
    barras = [
        (e.dxf.center.x, e.dxf.center.y)
        for layer in ("ARMADURA_LONG", "ARMADURA_PELE")
        for e in msp.query(f"CIRCLE[layer=='{layer}']")
    ]
    assert barras, "o DXF precisa conter as barras"
    for x, y in barras:
        na_mesa = abs(x) <= bf / 2 and (H_CM - hf) <= y <= H_CM
        na_alma = abs(x) <= BW_CM / 2 and 0 <= y <= (H_CM - hf)
        assert na_mesa or na_alma, f"barra fora do concreto: x={x:.1f} y={y:.1f}"
