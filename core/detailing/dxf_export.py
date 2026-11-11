from typing import Any

import ezdxf

from core.detailing.domain import posicionar_armadura_pele


def exportar_secao_dxf(
    bw_cm: float,
    h_cm: float,
    cob_cm: float,
    phi_estribo_mm: float,
    bar_positions: list[Any],
    phi_barra_mm: float,
    n_barras_pele: int = 0,
    phi_pele_mm: float = 0.0,
    is_t: bool = False,
    bf_cm: float | None = None,
    hf_cm: float | None = None,
    d_max_agregado_mm: float = 19.0,
    nome_arquivo: str = "secao_viga.dxf",
):
    """
    Gera um arquivo DXF contendo o detalhamento da seção transversal da viga.
    Todas as coordenadas internas e no DXF são salvas em CENTÍMETROS.
    """
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # --- CRIAÇÃO DE LAYERS ---
    doc.layers.add("CONCRETO", color=7)  # Cor 7 (Branco/Preto)
    doc.layers.add("ESTRIBO", color=5)  # Cor 5 (Azul)
    doc.layers.add("ESTRIBO_SUPLEMENTAR", color=30)  # Cor 30 (Laranja)
    doc.layers.add("ARMADURA_LONG", color=1)  # Cor 1 (Vermelho)
    doc.layers.add("ARMADURA_PELE", color=2)  # Cor 2 (Amarelo)
    if is_t:
        doc.layers.add("ARMADURA_COSTURA", color=3)  # Cor 3 (Verde)

    phi_est_cm = phi_estribo_mm / 10.0

    # Define deslocamento horizontal se for seção T para centralizar
    if is_t and bf_cm and hf_cm:
        half_bf = bf_cm / 2.0
        half_bw = bw_cm / 2.0
        x_shift = -half_bw

        # 1. Contorno de Concreto (T-shape)
        vertices_concreto = [
            (-half_bw, 0.0),
            (half_bw, 0.0),
            (half_bw, h_cm - hf_cm),
            (half_bf, h_cm - hf_cm),
            (half_bf, h_cm),
            (-half_bf, h_cm),
            (-half_bf, h_cm - hf_cm),
            (-half_bw, h_cm - hf_cm),
        ]

        # Armadura de costura: duas linhas horizontais na mesa
        y_costura_sup = h_cm - cob_cm
        y_costura_inf = h_cm - hf_cm + cob_cm
        x_mesa_esq = -half_bf + cob_cm
        x_mesa_dir = half_bf - cob_cm

        msp.add_line(
            (x_mesa_esq, y_costura_sup),
            (x_mesa_dir, y_costura_sup),
            dxfattribs={"layer": "ARMADURA_COSTURA"},
        )
        msp.add_line(
            (x_mesa_esq, y_costura_inf),
            (x_mesa_dir, y_costura_inf),
            dxfattribs={"layer": "ARMADURA_COSTURA"},
        )
    else:
        x_shift = 0.0
        # 1. Contorno de Concreto (Retângulo)
        vertices_concreto = [(0.0, 0.0), (bw_cm, 0.0), (bw_cm, h_cm), (0.0, h_cm)]

    msp.add_lwpolyline(vertices_concreto, close=True, dxfattribs={"layer": "CONCRETO"})

    # 2. Desenhar Estribo (Polyline Fechada)
    ex1, ey1 = cob_cm, cob_cm
    ex2, ey2 = bw_cm - cob_cm, h_cm - cob_cm
    vertices_estribo = [
        (ex1 + x_shift, ey1),
        (ex2 + x_shift, ey1),
        (ex2 + x_shift, ey2),
        (ex1 + x_shift, ey2),
    ]
    msp.add_lwpolyline(vertices_estribo, close=True, dxfattribs={"layer": "ESTRIBO"})

    # 3. Desenhar Armaduras Longitudinais Principais
    # Coordenadas das barras vêm em mm com origem no canto inferior-esquerdo
    # da MESA (viga T) ou da seção (retangular). No DXF T o referencial é
    # centrado no eixo da alma, então aplica-se a translação (e, para barras
    # superiores fora da alma, uma transformação afim explícita).
    for bar in bar_positions:
        bx = bar.get("x") if isinstance(bar, dict) else getattr(bar, "x", None)
        by = bar.get("y") if isinstance(bar, dict) else getattr(bar, "y", None)
        b_phi = (
            bar.get("phi_mm") if isinstance(bar, dict) else getattr(bar, "phi_mm", None)
        ) or phi_barra_mm
        r_vis_cm = (b_phi / 10.0) / 2.0
        if bx is not None and by is not None:
            x_cm = bx / 10.0
            if is_t and bf_cm:
                # Translação: centro da mesa (bf/2) → 0.
                x_cm = x_cm - bf_cm / 2.0
                # Barras superiores fora da alma: mapeia a largura da mesa
                # para a largura da alma preservando o centro (afim, não
                # escala com origem no canto).
                if by > (h_cm * 10.0) / 2.0 and abs(x_cm) > bw_cm / 2.0:
                    x_cm = x_cm * (bw_cm / bf_cm)
            cy = by / 10.0
            msp.add_circle((x_cm, cy), r_vis_cm, dxfattribs={"layer": "ARMADURA_LONG"})

    # 4. Desenhar Armadura de Pele (Laterais)
    if n_barras_pele > 0 and phi_pele_mm > 0:
        phi_pele_cm = phi_pele_mm / 10.0
        x_esq_mm, x_dir_mm, ys_pele_mm = posicionar_armadura_pele(
            h_mm=h_cm * 10.0,
            bw_mm=bw_cm * 10.0,
            cob_mm=cob_cm * 10.0,
            phi_estribo_mm=phi_estribo_mm,
            n_barras_pele_face=n_barras_pele,
            phi_pele_mm=phi_pele_mm,
            bar_positions=bar_positions,
            is_t=is_t,
            bf_mm=(bf_cm or 0.0) * 10.0,
            hf_mm=(hf_cm or 0.0) * 10.0,
            d_max_agregado_mm=d_max_agregado_mm,
            phi_barra_inf_mm=phi_barra_mm,
        )

        x_pele_esq_cm = x_esq_mm / 10.0 - (bf_cm / 2.0 if is_t and bf_cm else 0.0)
        x_pele_dir_cm = x_dir_mm / 10.0 - (bf_cm / 2.0 if is_t and bf_cm else 0.0)

        for y_mm in ys_pele_mm:
            y_curr = y_mm / 10.0
            msp.add_circle(
                (x_pele_esq_cm, y_curr),
                phi_pele_cm / 2.0,
                dxfattribs={"layer": "ARMADURA_PELE"},
            )
            msp.add_circle(
                (x_pele_dir_cm, y_curr),
                phi_pele_cm / 2.0,
                dxfattribs={"layer": "ARMADURA_PELE"},
            )

    # 5. Desenhar Grampos (Estribos Suplementares) para camadas com 3 ou mais barras
    layers_dict = {}
    layers_phi = {}
    for bar in bar_positions:
        bx = bar.get("x") if isinstance(bar, dict) else getattr(bar, "x", None)
        by = bar.get("y") if isinstance(bar, dict) else getattr(bar, "y", None)
        layer = bar.get("layer") if isinstance(bar, dict) else getattr(bar, "layer", None)
        is_corner = (
            bar.get("is_corner_bar")
            if isinstance(bar, dict)
            else getattr(bar, "is_corner_bar", False)
        )
        b_phi = (
            bar.get("phi_mm") if isinstance(bar, dict) else getattr(bar, "phi_mm", None)
        ) or phi_barra_mm

        # Camada 0 (1ª camada inferior) e Camada -1 (1ª camada superior) não precisam de grampos
        if is_corner or layer is None or layer in (0, -1) or bx is None or by is None:
            continue

        if layer not in layers_dict:
            layers_dict[layer] = []
        layers_dict[layer].append(by)
        layers_phi[layer] = b_phi

    for layer_idx, ys in layers_dict.items():
        if len(ys) >= 3:
            y_bar_cm = sum(ys) / len(ys) / 10.0
            b_phi = layers_phi[layer_idx]
            phi_barra_cm = b_phi / 10.0
            phi_est_cm = phi_estribo_mm / 10.0
            grampo_off_cm = (phi_est_cm / 2.0) + (phi_barra_cm / 2.0)

            x_left = cob_cm
            x_right = bw_cm - cob_cm
            hook_len_cm = 1.0  # Gancho de ancoragem de 1cm (10mm)

            # Se layer_idx > 0: Camada inferior suspensa (∪ - pernas para cima, dobra horizontal no topo)
            if layer_idx > 0:
                y_closed = y_bar_cm - grampo_off_cm
                y_open = y_bar_cm + grampo_off_cm
            # Se layer_idx < -1: Camada superior suspensa (∩ - pernas para baixo, dobra horizontal na base)
            else:
                y_closed = y_bar_cm + grampo_off_cm
                y_open = y_bar_cm - grampo_off_cm

            vertices_grampo = [
                (x_left + hook_len_cm + x_shift, y_open),
                (x_left + x_shift, y_open),
                (x_left + x_shift, y_closed),
                (x_right + x_shift, y_closed),
                (x_right + x_shift, y_open),
                (x_right - hook_len_cm + x_shift, y_open),
            ]
            msp.add_lwpolyline(
                vertices_grampo, close=False, dxfattribs={"layer": "ESTRIBO_SUPLEMENTAR"}
            )

    # Salva o arquivo DXF
    doc.saveas(nome_arquivo)
