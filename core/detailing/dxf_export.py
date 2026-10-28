import math
import ezdxf
from typing import List, Dict, Any, Optional

def exportar_secao_dxf(
    bw_cm: float,
    h_cm: float,
    cob_cm: float,
    phi_estribo_mm: float,
    bar_positions: List[Any],
    phi_barra_mm: float,
    n_barras_pele: int = 0,
    phi_pele_mm: float = 0.0,
    is_t: bool = False,
    bf_cm: Optional[float] = None,
    hf_cm: Optional[float] = None,
    nome_arquivo: str = "secao_viga.dxf"
):
    """
    Gera um arquivo DXF contendo o detalhamento da seção transversal da viga.
    Todas as coordenadas internas e no DXF são salvas em CENTÍMETROS.
    """
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # --- CRIAÇÃO DE LAYERS ---
    doc.layers.add('CONCRETO', color=7)       # Cor 7 (Branco/Preto)
    doc.layers.add('ESTRIBO', color=5)        # Cor 5 (Azul)
    doc.layers.add('ESTRIBO_SUPLEMENTAR', color=30)  # Cor 30 (Laranja)
    doc.layers.add('ARMADURA_LONG', color=1)  # Cor 1 (Vermelho)
    doc.layers.add('ARMADURA_PELE', color=2)  # Cor 2 (Amarelo)
    if is_t:
        doc.layers.add('ARMADURA_COSTURA', color=3) # Cor 3 (Verde)

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
            (-half_bw, h_cm - hf_cm)
        ]
        
        # Armadura de costura: duas linhas horizontais na mesa
        y_costura_sup = h_cm - cob_cm
        y_costura_inf = h_cm - hf_cm + cob_cm
        x_mesa_esq = -half_bf + cob_cm
        x_mesa_dir = half_bf - cob_cm
        
        msp.add_line(
            (x_mesa_esq, y_costura_sup),
            (x_mesa_dir, y_costura_sup),
            dxfattribs={'layer': 'ARMADURA_COSTURA'}
        )
        msp.add_line(
            (x_mesa_esq, y_costura_inf),
            (x_mesa_dir, y_costura_inf),
            dxfattribs={'layer': 'ARMADURA_COSTURA'}
        )
    else:
        x_shift = 0.0
        # 1. Contorno de Concreto (Retângulo)
        vertices_concreto = [
            (0.0, 0.0),
            (bw_cm, 0.0),
            (bw_cm, h_cm),
            (0.0, h_cm)
        ]

    msp.add_lwpolyline(
        vertices_concreto,
        close=True,
        dxfattribs={'layer': 'CONCRETO'}
    )

    # 2. Desenhar Estribo (Polyline Fechada)
    ex1, ey1 = cob_cm, cob_cm
    ex2, ey2 = bw_cm - cob_cm, h_cm - cob_cm
    vertices_estribo = [
        (ex1 + x_shift, ey1),
        (ex2 + x_shift, ey1),
        (ex2 + x_shift, ey2),
        (ex1 + x_shift, ey2)
    ]
    msp.add_lwpolyline(
        vertices_estribo,
        close=True,
        dxfattribs={'layer': 'ESTRIBO'}
    )

    # 3. Desenhar Armaduras Longitudinais Principais
    # Se for seção T, vamos verificar se as barras superiores precisam ser comprimidas para caber na alma
    superior_bars_need_mapping = False
    if is_t and bf_cm:
        for bar in bar_positions:
            bx = bar.get("x") if isinstance(bar, dict) else getattr(bar, "x", None)
            by = bar.get("y") if isinstance(bar, dict) else getattr(bar, "y", None)
            if bx is not None and by is not None:
                # Se for barra superior (na metade de cima) e estiver fora dos limites da alma (bw)
                if by > (h_cm * 10.0) / 2.0 and bx > (bw_cm * 10.0):
                    superior_bars_need_mapping = True
                    break

    for bar in bar_positions:
        bx = bar.get("x") if isinstance(bar, dict) else getattr(bar, "x", None)
        by = bar.get("y") if isinstance(bar, dict) else getattr(bar, "y", None)
        b_phi = (bar.get("phi_mm") if isinstance(bar, dict) else getattr(bar, "phi_mm", None)) or phi_barra_mm
        r_vis_cm = (b_phi / 10.0) / 2.0
        if bx is not None and by is not None:
            # Se for barra superior e precisamos mapear/comprimir para a alma
            if is_t and bf_cm and superior_bars_need_mapping and by > (h_cm * 10.0) / 2.0:
                bx_mapped = bx * (bw_cm / bf_cm)
            else:
                bx_mapped = bx

            cx = (bx_mapped / 10.0) + x_shift
            cy = by / 10.0
            msp.add_circle(
                (cx, cy),
                r_vis_cm,
                dxfattribs={'layer': 'ARMADURA_LONG'}
            )

    # 4. Desenhar Armadura de Pele (Laterais)
    if n_barras_pele > 0 and phi_pele_mm > 0:
        phi_pele_cm = phi_pele_mm / 10.0
        x_pele_esq = cob_cm + phi_est_cm + (phi_pele_cm / 2.0)
        x_pele_dir = bw_cm - cob_cm - phi_est_cm - (phi_pele_cm / 2.0)

        # 1. Encontrar o topo/fundo real da última camada de armadura principal (em cm)
        topo_cm = None
        fundo_sup_cm = None
        if bar_positions:
            bottom_bars_tops = []
            top_bars_bottoms = []
            for bar in bar_positions:
                by = bar.get("y") if isinstance(bar, dict) else getattr(bar, "y", None)
                b_layer = bar.get("layer") if isinstance(bar, dict) else getattr(bar, "layer", None)
                b_phi = (bar.get("phi_mm") if isinstance(bar, dict) else getattr(bar, "phi_mm", None)) or phi_barra_mm
                if by is not None:
                    # Considerar barra inferior se layer >= 0 ou se (layer é None) por estar na metade de baixo
                    is_bottom = False
                    is_top = False
                    if b_layer is not None:
                        if b_layer >= 0:
                            is_bottom = True
                        else:
                            is_top = True
                    else:
                        if by < (h_cm * 10.0) / 2.0:
                            is_bottom = True
                        else:
                            is_top = True
                    
                    if is_bottom:
                        bottom_bars_tops.append((by + b_phi / 2.0) / 10.0)
                    if is_top:
                        top_bars_bottoms.append((by - b_phi / 2.0) / 10.0)
                        
            if bottom_bars_tops:
                topo_cm = max(bottom_bars_tops)
            if top_bars_bottoms:
                fundo_sup_cm = min(top_bars_bottoms)

        # Calcular ev_min (em cm)
        ev_min_cm = max(2.0, phi_barra_mm / 10.0, 2.28)

        # Determinar limites brutos (sem gaps)
        y_bottom_raw_cm = topo_cm if topo_cm is not None else (cob_cm + phi_est_cm)
        if fundo_sup_cm is not None:
            y_top_raw_cm = fundo_sup_cm
        else:
            if is_t and hf_cm is not None:
                y_top_raw_cm = h_cm - hf_cm
            else:
                y_top_raw_cm = h_cm - (cob_cm + phi_est_cm)

        # Verificar se podemos usar a nova distribuição com folga borda a borda (clearance) uniforme
        usar_fallback = True
        if bar_positions:
            h_free_cm = y_top_raw_cm - y_bottom_raw_cm
            d_livre_cm = (h_free_cm - n_barras_pele * phi_pele_cm) / (n_barras_pele + 1.0)
            if d_livre_cm >= ev_min_cm:
                usar_fallback = False

        if usar_fallback:
            # Fallback com a fórmula antiga
            h_interna = h_cm - 2.0 * (cob_cm + phi_est_cm)
            s_pele = h_interna / (n_barras_pele + 1)
            ys_pele = [(cob_cm + phi_est_cm) + (i + 1) * s_pele for i in range(n_barras_pele)]
        else:
            # Distribuição perfeitamente uniforme de folga livre borda a borda
            ys_pele = [y_bottom_raw_cm + (i + 1) * d_livre_cm + (i + 0.5) * phi_pele_cm for i in range(n_barras_pele)]

        # Desenhar círculos de pele
        for y_curr in ys_pele:
            # Face Esquerda
            msp.add_circle(
                (x_pele_esq + x_shift, y_curr),
                phi_pele_cm / 2.0,
                dxfattribs={'layer': 'ARMADURA_PELE'}
            )
            # Face Direita
            msp.add_circle(
                (x_pele_dir + x_shift, y_curr),
                phi_pele_cm / 2.0,
                dxfattribs={'layer': 'ARMADURA_PELE'}
            )

    # 5. Desenhar Grampos (Estribos Suplementares) para camadas com 3 ou mais barras
    layers_dict = {}
    layers_phi = {}
    for bar in bar_positions:
        bx = bar.get("x") if isinstance(bar, dict) else getattr(bar, "x", None)
        by = bar.get("y") if isinstance(bar, dict) else getattr(bar, "y", None)
        layer = bar.get("layer") if isinstance(bar, dict) else getattr(bar, "layer", None)
        is_corner = bar.get("is_corner_bar") if isinstance(bar, dict) else getattr(bar, "is_corner_bar", False)
        b_phi = (bar.get("phi_mm") if isinstance(bar, dict) else getattr(bar, "phi_mm", None)) or phi_barra_mm
        
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
                (x_right - hook_len_cm + x_shift, y_open)
            ]
            msp.add_lwpolyline(
                vertices_grampo,
                close=False,
                dxfattribs={'layer': 'ESTRIBO_SUPLEMENTAR'}
            )

    # Salva o arquivo DXF
    doc.saveas(nome_arquivo)
