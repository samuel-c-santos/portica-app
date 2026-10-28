import os
import tempfile
import pytest
import ezdxf
from core.detailing.dxf_export import exportar_secao_dxf

def test_exportar_secao_dxf_retangular():
    """Valida se o exportador DXF gera um arquivo legível e com os layers esperados para seção retangular."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dxf_path = os.path.join(tmpdir, "secao_ret.dxf")
        
        # Dados de exemplo
        bar_positions = [
            {"x": 40.0, "y": 45.0},
            {"x": 100.0, "y": 45.0},
            {"x": 160.0, "y": 45.0},
            {"x": 40.0, "y": 655.0},
            {"x": 160.0, "y": 655.0}
        ]
        
        exportar_secao_dxf(
            bw_cm=20.0,
            h_cm=70.0,
            cob_cm=3.0,
            phi_estribo_mm=5.0,
            bar_positions=bar_positions,
            phi_barra_mm=16.0,
            n_barras_pele=2,
            phi_pele_mm=5.0,
            is_t=False,
            nome_arquivo=dxf_path
        )
        
        assert os.path.exists(dxf_path)
        
        # Tenta ler o arquivo DXF gerado
        doc = ezdxf.readfile(dxf_path)
        assert doc is not None
        
        # Verifica se os layers foram criados
        layer_names = [layer.dxf.name for layer in doc.layers]
        assert "CONCRETO" in layer_names
        assert "ESTRIBO" in layer_names
        assert "ARMADURA_LONG" in layer_names
        assert "ARMADURA_PELE" in layer_names


def test_exportar_secao_dxf_t():
    """Valida se o exportador DXF gera um arquivo legível e com os layers esperados para seção T."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dxf_path = os.path.join(tmpdir, "secao_t.dxf")
        
        bar_positions = [
            {"x": 40.0, "y": 45.0},
            {"x": 160.0, "y": 45.0}
        ]
        
        exportar_secao_dxf(
            bw_cm=20.0,
            h_cm=70.0,
            cob_cm=3.0,
            phi_estribo_mm=5.0,
            bar_positions=bar_positions,
            phi_barra_mm=16.0,
            n_barras_pele=0,
            phi_pele_mm=0.0,
            is_t=True,
            bf_cm=60.0,
            hf_cm=10.0,
            nome_arquivo=dxf_path
        )
        
        assert os.path.exists(dxf_path)
        doc = ezdxf.readfile(dxf_path)
        assert doc is not None
        
        # Verifica se os layers foram criados
        layer_names = [layer.dxf.name for layer in doc.layers]
        assert "CONCRETO" in layer_names
        assert "ESTRIBO" in layer_names


def test_exportar_secao_dxf_com_grampos():
    """Valida se o exportador DXF cria polilinhas para os grampos se houver 2ª camada com >= 3 barras (sup e inf)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dxf_path = os.path.join(tmpdir, "secao_grampos.dxf")
        
        # 3 barras no layer 0 (inf 1ª), 3 barras no layer 1 (inf 2ª)
        # 3 barras no layer -1 (sup 1ª), 3 barras no layer -2 (sup 2ª)
        bar_positions = [
            {"x": 40.0, "y": 45.0, "layer": 0, "is_corner_bar": False},
            {"x": 100.0, "y": 45.0, "layer": 0, "is_corner_bar": False},
            {"x": 160.0, "y": 45.0, "layer": 0, "is_corner_bar": False},
            
            {"x": 40.0, "y": 100.0, "layer": 1, "is_corner_bar": False},
            {"x": 100.0, "y": 100.0, "layer": 1, "is_corner_bar": False},
            {"x": 160.0, "y": 100.0, "layer": 1, "is_corner_bar": False},
            
            {"x": 40.0, "y": 655.0, "layer": -1, "is_corner_bar": False},
            {"x": 100.0, "y": 655.0, "layer": -1, "is_corner_bar": False},
            {"x": 160.0, "y": 655.0, "layer": -1, "is_corner_bar": False},
            
            {"x": 40.0, "y": 600.0, "layer": -2, "is_corner_bar": False},
            {"x": 100.0, "y": 600.0, "layer": -2, "is_corner_bar": False},
            {"x": 160.0, "y": 600.0, "layer": -2, "is_corner_bar": False},
        ]
        
        exportar_secao_dxf(
            bw_cm=20.0,
            h_cm=70.0,
            cob_cm=3.0,
            phi_estribo_mm=5.0,
            bar_positions=bar_positions,
            phi_barra_mm=16.0,
            n_barras_pele=0,
            phi_pele_mm=0.0,
            is_t=False,
            nome_arquivo=dxf_path
        )
        
        assert os.path.exists(dxf_path)
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        
        # Filtra polilinhas do layer 'ESTRIBO_SUPLEMENTAR'
        supl_polylines = [e for e in msp if e.dxftype() == 'LWPOLYLINE' and e.dxf.layer == 'ESTRIBO_SUPLEMENTAR']
        
        # Deve ter exatamente 2 estribos suplementares (grampo inf e grampo sup)
        assert len(supl_polylines) == 2
        
        for grampo in supl_polylines:
            assert not grampo.closed
            assert len(grampo) == 6


def test_exportar_secao_dxf_com_pele_e_camadas_duplas():
    """Valida se as coordenadas Y da armadura de pele respeitam os limites impostos pelas camadas inferior e superior."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dxf_path = os.path.join(tmpdir, "secao_pele_dupla.dxf")
        
        # 2 camadas inferiores (layer 0 em y=45.0, layer 1 em y=100.0)
        # 2 camadas superiores (layer -1 em y=655.0, layer -2 em y=600.0)
        bar_positions = [
            {"x": 40.0, "y": 45.0, "layer": 0, "phi_mm": 16.0},
            {"x": 160.0, "y": 45.0, "layer": 0, "phi_mm": 16.0},
            {"x": 40.0, "y": 100.0, "layer": 1, "phi_mm": 16.0},
            {"x": 160.0, "y": 100.0, "layer": 1, "phi_mm": 16.0},
            
            {"x": 40.0, "y": 655.0, "layer": -1, "phi_mm": 16.0},
            {"x": 160.0, "y": 655.0, "layer": -1, "phi_mm": 16.0},
            {"x": 40.0, "y": 600.0, "layer": -2, "phi_mm": 16.0},
            {"x": 160.0, "y": 600.0, "layer": -2, "phi_mm": 16.0},
        ]
        
        exportar_secao_dxf(
            bw_cm=20.0,
            h_cm=70.0,
            cob_cm=3.0,
            phi_estribo_mm=5.0,
            bar_positions=bar_positions,
            phi_barra_mm=16.0,
            n_barras_pele=2,
            phi_pele_mm=10.0,
            is_t=False,
            nome_arquivo=dxf_path
        )
        
        assert os.path.exists(dxf_path)
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        
        # Filtra os círculos de armadura de pele
        pele_circles = [e for e in msp if e.dxftype() == 'CIRCLE' and e.dxf.layer == 'ARMADURA_PELE']
        
        # Como n_barras_pele = 2 por face (total de 4 círculos no modelo space)
        assert len(pele_circles) == 4
        
        # Coordenadas Y dos círculos de pele
        ys = sorted(list(set(c.dxf.center.y for c in pele_circles)))
        assert len(ys) == 2
        
        # O limite inferior bruto é topo_cm = (100.0 + 8.0) / 10.0 = 10.8 cm
        # O limite superior bruto é fundo_sup_cm = (600.0 - 8.0) / 10.0 = 59.2 cm
        # h_free = 59.2 - 10.8 = 48.4 cm
        # Como n_barras_pele = 2: d_livre_cm = (48.4 - 2 * 1.0) / 3 = 15.4667 cm
        # ys_pele deve ser exatamente [10.8 + 15.4667 + 0.5, 10.8 + 30.9333 + 1.5] = [26.7667, 43.2333]
        assert abs(ys[0] - 26.7667) < 1e-3
        assert abs(ys[1] - 43.2333) < 1e-3

