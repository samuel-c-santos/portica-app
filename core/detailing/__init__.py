"""
core/detailing/__init__.py
Pacote de detalhamento de seção transversal de viga.
Exporta as interfaces públicas das duas camadas.
"""
from .domain import BeamDetailer, BeamDetailingInput, SectionLayoutData
from .dxf_export import exportar_secao_dxf
from .presentation import (
    BeamSectionCommands,
    FletCanvasRenderer,
    FpdfRenderer,
    desenhar_secao_com_detailer,
)

__all__ = [
    "BeamDetailingInput",
    "SectionLayoutData",
    "BeamDetailer",
    "BeamSectionCommands",
    "FletCanvasRenderer",
    "FpdfRenderer",
    "desenhar_secao_com_detailer",
    "exportar_secao_dxf",
]
