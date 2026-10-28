"""
Helper de arquivos temporarios com seguranca contra race condition (TOCTOU).

Substitui `tempfile.mktemp` (deprecated) por `tempfile.mkstemp`.
Tambem suporta empacotamento PyInstaller via `sys._MEIPASS`.
"""

import os
import sys
import tempfile


def temp_path(suffix: str = "", prefix: str = "tmp", dir: str = None) -> str:
    """Cria arquivo temporario e retorna apenas o path.

    Diferente de mktemp (deprecated por causa de TOCTOU), usa mkstemp
    que cria o arquivo atomicamente, sem janela de race condition.
    """
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
    os.close(fd)
    return path


def resource_path(rel_path: str) -> str:
    """Retorna path absoluto para recurso (assets, etc).

    Funciona tanto em dev (script .py) quanto em PyInstaller:
    - Em dev: usa a raiz do projeto (dois níveis acima de utils_tempfile.py)
    - Em PyInstaller: usa sys._MEIPASS (temp dir do bundle)
    """
    if getattr(sys, "_MEIPASS", None):
        base = sys._MEIPASS
    else:
        # utils_tempfile.py está em core/, então dois níveis acima = raiz do projeto
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel_path)
