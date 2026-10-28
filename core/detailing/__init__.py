"""
core/detailing/__init__.py
Pacote de detalhamento de seção transversal de viga.
Exporta as interfaces públicas das duas camadas.
"""
from .domain import BeamDetailingInput, SectionLayoutData, BeamDetailer
from .presentation import (
    BeamSectionCommands,
    FletCanvasRenderer,
    FpdfRenderer,
    desenhar_secao_com_detailer,
)
from .dxf_export import exportar_secao_dxf

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
