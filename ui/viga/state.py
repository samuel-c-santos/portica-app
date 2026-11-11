"""Estado tipado da tela de viga (EP-04.3).

Substitui o ``state = {...}`` mutado por closures. ``VigaState`` e um dataclass
com campos tipados; mantem o protocolo de mapeamento (``state["k"]``,
``state.get("k")``, ``"k" in state``) para os helpers que ja o consomem
(``ui.entrada``, ``ui.ftool.envelope``). Chave desconhecida levanta ``KeyError``
(um typo deixa de criar estado fantasma).

``ViewContext`` e o unico objeto compartilhado entre os modulos de ``ui/viga``:
guarda a pagina, o estado e as referencias dos controles. Nao ha estado em closure.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass, field, fields
from typing import Any

from ui.entrada import ENTRADA_MANUAL


@dataclass
class VigaState(MutableMapping):
    tipo_viga: str = "V1"
    entrada: str = ENTRADA_MANUAL
    ftool_path: str | None = None
    ftool_filename: str | None = None
    resultados_flex: Any = None
    resultados_cis: Any = None
    pdf_path: str | None = None
    ftool_momentos: Any = None
    ftool_cortantes: Any = None
    ftool_deformacoes: Any = None
    ftool_secoes_criticas: Any = None
    combinacoes: list = field(default_factory=list)
    temp_momento_path: str | None = None
    temp_cortante_path: str | None = None
    ftool_momento_path: str | None = None
    ftool_cortante_path: str | None = None
    ftool_deformacao_path: str | None = None
    # preenchidos pelo processamento FTOOL / ELS
    ftool_ajustes_els: Any = None
    ftool_resultado_els: Any = None
    ftool_detalhamento: Any = None
    ftool_envelope_momentos: Any = None
    ftool_envelope_cortantes: Any = None
    d_max_agregado_mm: Any = None
    _modal_results_content: Any = None
    _png_preview_temp: Any = None

    @classmethod
    def para_modo(cls, modo: str) -> VigaState:
        """Estado inicial: id padrao da viga depende do modo (comum | t)."""
        return cls(tipo_viga="V1" if modo == "comum" else "VT1")

    # --- protocolo de mapeamento ------------------------------------------
    @classmethod
    def _chaves(cls) -> set[str]:
        return {f.name for f in fields(cls)}

    def __getitem__(self, key: str) -> Any:
        if key not in self._chaves():
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key not in self._chaves():
            raise KeyError(key)
        setattr(self, key, value)

    def __delitem__(self, key: str) -> None:
        self[key] = None

    def __contains__(self, key: object) -> bool:
        # como no dict original: as chaves iniciais sempre existem; as demais
        # passam a existir quando recebem valor.
        if not isinstance(key, str) or key not in self._chaves():
            return False
        return key in _CHAVES_INICIAIS or getattr(self, key) is not None

    def __iter__(self):
        return iter(k for k in (f.name for f in fields(self)) if k in self)

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        if key not in self._chaves():
            return default
        valor = getattr(self, key)
        if key in _CHAVES_INICIAIS:
            return valor  # no dict original a chave existia (mesmo com None)
        return default if valor is None else valor


# Chaves que o ``state`` dict original ja criava na inicializacao da tela.
_CHAVES_INICIAIS = frozenset(
    {
        "tipo_viga",
        "entrada",
        "ftool_path",
        "ftool_filename",
        "resultados_flex",
        "resultados_cis",
        "pdf_path",
        "ftool_momentos",
        "ftool_cortantes",
        "ftool_deformacoes",
        "ftool_secoes_criticas",
        "combinacoes",
        "temp_momento_path",
        "temp_cortante_path",
        "ftool_momento_path",
        "ftool_cortante_path",
        "ftool_deformacao_path",
    }
)


class ViewContext:
    """Contexto explicito da tela: pagina, parametros, estado e controles.

    Os controles sao atribuidos pelos passos ``setup_*`` de cada modulo. Os
    callbacks (antes closures) sao ``functools.partial(fn, ctx)``.
    """

    def __init__(
        self,
        page,
        modo,
        on_back,
        fp_image,
        fp_pdf,
        fp_load_project,
        fp_save_project,
        fp_dxf,
        initial_file=None,
        state: VigaState | None = None,
    ):
        self.page = page
        self.modo = modo
        self.on_back = on_back
        self.fp_image = fp_image
        self.fp_pdf = fp_pdf
        self.fp_load_project = fp_load_project
        self.fp_save_project = fp_save_project
        self.fp_dxf = fp_dxf
        self.initial_file = initial_file
        self.state = state if state is not None else VigaState.para_modo(modo)
