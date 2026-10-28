"""
Build unificado do Pórtica App (PyInstaller, onefile/windowed).

Gera um unico executavel Windows:

    dist/portica.exe

Entry point da aplicacao: `edicoes/main.py` (app unificado, F1a).
Script congelado: `build/launcher.py` — e o bootstrap que configura o
SSL/certifi antes de qualquer import e chama `edicoes.main.main`.

O workdir e criado fora do repositorio (Google Drive nao lida bem com os
milhares de arquivos temporarios do PyInstaller); o executavel final e
copiado de volta para `dist/`.

Uso:
    python build/build_portica.py
    python build/build_portica.py --bundle-client   # inclui o cliente Flet no .exe
    python build/build_portica.py --keep-work       # preserva o workdir temporario

Nao instala nada: se o PyInstaller nao estiver no ambiente, o script
reporta e para.
"""

import argparse
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"

# Entrada da aplicacao (unificada na F1a) e bootstrap congelado.
APP_ENTRY = PROJECT_ROOT / "edicoes" / "main.py"
FROZEN_SCRIPT = BUILD_DIR / "launcher.py"

ASSETS_DIR = PROJECT_ROOT / "core" / "assets"
ICON_FILE = ASSETS_DIR / "logo.ico"
VERSION_FILE = PROJECT_ROOT / "core" / "version.py"
CHECKSUM_FILE = PROJECT_ROOT / "SHA256SUMS.txt"

APP_NAME = "portica"

EXCLUDED_MODULES = [
    "matplotlib",
    "scipy",
    "pandas",
    "IPython",
    "jupyter",
    "pytest",
    "pygments",
    "rich",
]

HIDDEN_IMPORTS = [
    "core",
    "core.calculos",
    "core.detailing",
    "ui",
    "ui.ftool",
    "edicoes",
    "edicoes.main",
    "flet",
    "flet_desktop",
    # A distribuicao chama-se "fpdf2", mas o modulo importavel e "fpdf".
    "fpdf",
    "ezdxf",
    "numpy",
]


def log(message: str) -> None:
    print(message, flush=True)


def fail(message: str) -> None:
    log(f"[ERRO] {message}")
    sys.exit(1)


def read_version() -> str:
    """Le APP_VERSION de core/version.py sem importar o pacote."""
    try:
        text = VERSION_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"nao foi possivel ler {VERSION_FILE}: {exc}")
    match = re.search(r'^\s*APP_VERSION\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if not match:
        fail(f"APP_VERSION nao encontrado em {VERSION_FILE}")
    return match.group(1)


def package_dir(module_name: str) -> Path:
    """Localiza o pacote instalado no site-packages do Python em uso."""
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, ValueError) as exc:
        fail(f"nao foi possivel localizar o pacote '{module_name}': {exc}")
    if spec is None:
        fail(
            f"pacote '{module_name}' nao encontrado no ambiente "
            f"({sys.executable}). Instale as dependencias de requirements.txt."
        )
    locations = list(spec.submodule_search_locations or [])
    if not locations:
        fail(f"pacote '{module_name}' sem diretorio de conteudo")
    return Path(locations[0])


def find_flet_desktop_archive() -> Path | None:
    """Arquivo de cliente desktop do Flet empacotado (opcional)."""
    try:
        flet_desktop_dir = package_dir("flet_desktop")
    except SystemExit:
        return None
    archive = flet_desktop_dir / "app" / "flet-windows.zip"
    return archive if archive.is_file() else None


def zip_cached_flet_client(target_dir: Path) -> Path | None:
    """Empacota o cliente Flet ja cacheado em ~/.flet/client, se existir."""
    home = Path.home() / ".flet" / "client"
    if not home.is_dir():
        return None
    candidates = sorted(p for p in home.iterdir() if p.is_dir())
    if not candidates:
        return None
    source = candidates[-1] / "flet"
    if not source.is_dir():
        return None
    target_dir.mkdir(parents=True, exist_ok=True)
    archive = target_dir / "flet-windows.zip"
    log(f"[BUILD] empacotando cliente Flet cacheado: {source}")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(source.rglob("*")):
            if item.is_file():
                zf.write(item, Path("flet") / item.relative_to(source))
    return archive


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_command(work: Path, dist: Path, data_args: list[str]) -> list[str]:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        f"--name={APP_NAME}",
        f"--distpath={dist}",
        f"--workpath={work}",
        f"--specpath={work}",
        f"--paths={PROJECT_ROOT}",
    ]
    cmd.extend(data_args)
    cmd.append(f"--icon={ICON_FILE}")
    for module in EXCLUDED_MODULES:
        cmd.append(f"--exclude-module={module}")
    for module in HIDDEN_IMPORTS:
        cmd.append(f"--hidden-import={module}")
    cmd.append(str(FROZEN_SCRIPT))
    return cmd


def main() -> None:
    parser = argparse.ArgumentParser(description="Build unificado do Portica App")
    parser.add_argument(
        "--bundle-client",
        action="store_true",
        help="inclui o cliente desktop do Flet dentro do executavel (offline na 1a execucao)",
    )
    parser.add_argument(
        "--keep-work",
        action="store_true",
        help="mantem o workdir temporario do PyInstaller",
    )
    args = parser.parse_args()

    log("=" * 62)
    log("[BUILD] Portica App - build unico (PyInstaller)")
    log("=" * 62)

    if importlib.util.find_spec("PyInstaller") is None:
        fail(
            "PyInstaller nao esta instalado neste ambiente. "
            "Instale com 'pip install pyinstaller' antes de rodar este script."
        )

    version = read_version()

    for required in (APP_ENTRY, FROZEN_SCRIPT, ASSETS_DIR, ICON_FILE):
        if not required.exists():
            fail(f"arquivo/pasta necessario ausente: {required}")

    flet_dir = package_dir("flet")
    certifi_dir = package_dir("certifi")
    cacert = certifi_dir / "cacert.pem"
    if not cacert.is_file():
        fail(f"cacert.pem do certifi nao encontrado em {certifi_dir}")

    # Workdir temporario fora do Google Drive.
    work_root = Path(tempfile.mkdtemp(prefix="portica_build_"))
    work = work_root / "work"
    dist_temp = work_root / "dist"
    work.mkdir(parents=True, exist_ok=True)
    dist_temp.mkdir(parents=True, exist_ok=True)

    data_args = [
        f"--add-data={ASSETS_DIR}{os.pathsep}core/assets",
        f"--add-data={flet_dir / 'controls'}{os.pathsep}flet/controls",
        f"--add-data={cacert}{os.pathsep}certifi",
    ]

    client_archive = find_flet_desktop_archive()
    if client_archive is not None:
        data_args.append(
            f"--add-data={client_archive}{os.pathsep}flet_desktop/app"
        )
        log("[BUILD] cliente desktop do Flet empacotado (offline na 1a execucao)")
    elif args.bundle_client:
        bundled = zip_cached_flet_client(work_root / "client")
        if bundled is None:
            fail(
                "nao ha cliente Flet em ~/.flet/client para empacotar. "
                "Rode o app uma vez (online) ou instale 'flet-desktop'."
            )
        data_args.append(
            f"--add-data={bundled}{os.pathsep}flet_desktop/app"
        )
    else:
        log(
            "[AVISO] cliente desktop do Flet nao embutido: na primeira execucao "
            "em uma maquina limpa ele sera baixado (ou lido do cache ~/.flet)."
        )

    log(f"[BUILD] versao app   : {version}")
    log(f"[BUILD] entry point  : {APP_ENTRY}")
    log(f"[BUILD] script frozen: {FROZEN_SCRIPT}")
    log(f"[BUILD] workdir      : {work_root}")
    log(f"[BUILD] python       : {sys.executable}")

    cmd = build_command(work, dist_temp, data_args)
    log("")
    log(f"[BUILD] executando: {' '.join(cmd)}")
    log("")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        fail("PyInstaller terminou com erro.")

    built = dist_temp / f"{APP_NAME}.exe"
    if not built.is_file():
        fail(f"executavel nao encontrado em {built}")

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    final_exe = DIST_DIR / f"{APP_NAME}.exe"
    shutil.copy2(built, final_exe)

    size_mb = final_exe.stat().st_size / 1024 / 1024
    digest = sha256_file(final_exe)

    CHECKSUM_FILE.write_text(
        f"{digest}  {final_exe.name}\n", encoding="utf-8", newline="\n"
    )

    zip_path = DIST_DIR / f"{APP_NAME}-v{version}-windows-x64.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(final_exe, final_exe.name)
        zf.write(CHECKSUM_FILE, CHECKSUM_FILE.name)

    log("")
    log("=" * 62)
    log("[OK] build concluido")
    log(f"   executavel : {final_exe} ({size_mb:.1f} MB)")
    log(f"   sha256     : {digest}")
    log(f"   checksum   : {CHECKSUM_FILE}")
    log(f"   pacote zip : {zip_path}")
    log("=" * 62)

    if not args.keep_work:
        shutil.rmtree(work_root, ignore_errors=True)
        log(f"[BUILD] workdir temporario removido: {work_root}")
    else:
        log(f"[BUILD] workdir temporario mantido: {work_root}")


if __name__ == "__main__":
    main()
