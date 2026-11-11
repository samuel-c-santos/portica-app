"""
core/detailing/__init__.py
Pacote de detalhamento de seção transversal de viga.
Exporta as interfaces públicas das duas camadas.
"""

from .domain import (
    BeamDetailer,
    BeamDetailingInput,
    SectionLayoutData,
    detalhar_secao_completa,
    posicionar_armadura_pele,
)
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
    "detalhar_secao_completa",
    "posicionar_armadura_pele",
    "desenhar_secao_com_detailer",
    "exportar_secao_dxf",
]
