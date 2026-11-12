"""Splash de abertura do executável (EP-05.10).

O `.exe` onefile leva dezenas de segundos para descompactar em disco lento
(Google Drive, antivírus). Sem splash, a janela só aparece no fim e o usuário
não tem sinal de que o programa está abrindo. Estes testes garantem que a
imagem existe e que entra na linha de comando do PyInstaller.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "portica_build",
    Path(__file__).resolve().parent.parent / "build" / "build_portica.py",
)
build_portica = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(build_portica)


def test_splash_versionada():
    assert build_portica.SPLASH_FILE.is_file(), (
        "core/assets/splash.png ausente: o executável abriria sem splash"
    )


def test_build_passa_splash_ao_pyinstaller(tmp_path: Path):
    cmd = build_portica.build_command(tmp_path, tmp_path, [])
    assert f"--splash={build_portica.SPLASH_FILE}" in cmd
