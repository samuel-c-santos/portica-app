import os
import tempfile

import ezdxf
import pytest

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
            {"x": 160.0, "y": 655.0},
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
            nome_arquivo=dxf_path,
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

        # EP-03.2: geometria — contorno, estribo e barras conferem com os dados
        msp = doc.modelspace()
        contorno = next(e for e in msp if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "CONCRETO")
        xs_c = [p[0] for p in contorno.get_points("xy")]
        ys_c = [p[1] for p in contorno.get_points("xy")]
        # bbox do contorno = seção 20×70 cm
        assert min(xs_c) == pytest.approx(0.0, abs=1e-6)
        assert max(xs_c) == pytest.approx(20.0, abs=1e-6)
        assert min(ys_c) == pytest.approx(0.0, abs=1e-6)
        assert max(ys_c) == pytest.approx(70.0, abs=1e-6)
        assert contorno.closed

        estribo = next(e for e in msp if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "ESTRIBO")
        xs_e = [p[0] for p in estribo.get_points("xy")]
        ys_e = [p[1] for p in estribo.get_points("xy")]
        # estribo = contorno inset do cobrimento 3 cm
        assert min(xs_e) == pytest.approx(3.0, abs=1e-6)
        assert max(xs_e) == pytest.approx(17.0, abs=1e-6)
        assert min(ys_e) == pytest.approx(3.0, abs=1e-6)
        assert max(ys_e) == pytest.approx(67.0, abs=1e-6)
        assert estribo.closed
        assert len(estribo) == 4

        # barras: eixos dentro do estribo (bar_positions em mm → cm no DXF)
        barras = [e for e in msp if e.dxftype() == "CIRCLE" and e.dxf.layer == "ARMADURA_LONG"]
        assert len(barras) == len(bar_positions)
        for c in barras:
            assert min(xs_e) <= c.dxf.center.x <= max(xs_e)
            assert min(ys_e) <= c.dxf.center.y <= max(ys_e)
            assert c.dxf.radius == pytest.approx(16.0 / 10.0 / 2.0, abs=1e-6)


def test_exportar_secao_dxf_t():
    """Valida se o exportador DXF gera um arquivo legível e com os layers esperados para seção T."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dxf_path = os.path.join(tmpdir, "secao_t.dxf")

        bar_positions = [{"x": 40.0, "y": 45.0}, {"x": 160.0, "y": 45.0}]

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
            nome_arquivo=dxf_path,
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
            nome_arquivo=dxf_path,
        )

        assert os.path.exists(dxf_path)
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        # Filtra polilinhas do layer 'ESTRIBO_SUPLEMENTAR'
        supl_polylines = [
            e for e in msp if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "ESTRIBO_SUPLEMENTAR"
        ]

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
            nome_arquivo=dxf_path,
        )

        assert os.path.exists(dxf_path)
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        # Filtra os círculos de armadura de pele
        pele_circles = [
            e for e in msp if e.dxftype() == "CIRCLE" and e.dxf.layer == "ARMADURA_PELE"
        ]

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


def test_exportar_secao_dxf_t_translacao_para_o_eixo_da_alma():
    """Barras da viga T são transladadas de bf/2; a mesa mantém a posição real.

    bf=60, bw=20, h=70. Barra inferior no centro da alma x=300 mm → x=0 cm.
    Barra superior na mesa x=100 mm → 10 − 30 = −20 cm (dentro da mesa, que
    vai de −30 a +30). O detalhador já entrega as barras no referencial da
    mesa; não há mais transformação afim para a alma.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        dxf_path = os.path.join(tmpdir, "secao_t_afim.dxf")
        exportar_secao_dxf(
            bw_cm=20.0,
            h_cm=70.0,
            cob_cm=3.0,
            phi_estribo_mm=5.0,
            bar_positions=[
                {"x": 300.0, "y": 45.0},
                {"x": 100.0, "y": 655.0},
            ],
            phi_barra_mm=16.0,
            is_t=True,
            bf_cm=60.0,
            hf_cm=10.0,
            nome_arquivo=dxf_path,
        )
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        barras = sorted(
            (e for e in msp if e.dxftype() == "CIRCLE" and e.dxf.layer == "ARMADURA_LONG"),
            key=lambda c: c.dxf.center.y,
        )
        assert barras[0].dxf.center.x == pytest.approx(0.0, abs=1e-6)
        assert barras[1].dxf.center.x == pytest.approx(-20.0, abs=1e-6)
