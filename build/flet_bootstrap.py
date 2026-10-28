"""
Preparacao do cliente desktop do Flet para o executavel congelado.

O Portica App e um app Flet *desktop*: o cliente grafico (o binario Flutter
que desenha a janela) nao faz parte do pacote Python. Em uma maquina limpa ele
precisa ser baixado uma unica vez (~30 MB) do GitHub Releases do Flet.

Sem este passo, o executavel comportaria mal o primeiro uso:

- sem internet, a janela abriria e fecharia sem explicacao (o traceback do
  PyInstaller aparece numa caixa de dialogo cruda, ou nada);
- o usuario nao saberia que o download e normal, unico e pequeno.

Este modulo cuida disso:

1. `client_state()` diz se o cliente ja esta disponivel (embutido no .exe ou
   em cache local);
2. `prepare_desktop_client()` baixa o cliente que faltar, mostrando uma tela de
   progresso;
3. em caso de falha, levanta `FletClientError` com uma mensagem em portugues
   que explica o que fazer — a interface do app nunca e aberta nesse estado.

Nada aqui altera o app em si: `edicoes/main.py` nao sabe que este modulo
existe.
"""

import os
import queue
import shutil
import sys
import tempfile
import threading
import zipfile
from pathlib import Path


CLIENT_HOME = Path.home() / ".flet" / "client"
DOWNLOAD_TIMEOUT_S = 60
CHUNK = 256 * 1024


class FletClientError(RuntimeError):
    """Falha ao preparar o cliente desktop do Flet."""


# --------------------------------------------------------------------------
# Descoberta do estado do cliente
# --------------------------------------------------------------------------

def _flet_desktop():
    try:
        import flet_desktop
    except ImportError:
        return None
    return flet_desktop


def _flavor() -> str:
    """Replica a escolha de 'flavor' do Flet (full/light)."""
    env = os.environ.get("FLET_DESKTOP_FLAVOR", "").strip().lower()
    if env in ("full", "light"):
        return env
    return "light" if sys.platform.startswith("linux") else "full"


def _version(flet_desktop) -> str:
    try:
        import flet_desktop.version as version_module
        return version_module.version
    except Exception:
        return "0.0.0"


def _cache_dir(flet_desktop) -> Path:
    return CLIENT_HOME / f"flet-desktop-{_flavor()}-{_version(flet_desktop)}"


def _bundled_archive(flet_desktop) -> Path | None:
    """Arquivo do cliente embutido no proprio executavel (se houver)."""
    try:
        bin_dir = Path(flet_desktop.get_package_bin_dir())
        artifact = flet_desktop.get_artifact_filename()
    except Exception:
        return None
    archive = bin_dir / artifact
    return archive if archive.is_file() else None


def client_state() -> str:
    """Retorna 'bundled', 'cached' ou 'missing'."""
    flet_desktop = _flet_desktop()
    if flet_desktop is None:
        return "missing"
    if _bundled_archive(flet_desktop) is not None:
        return "bundled"
    cache = _cache_dir(flet_desktop)
    if (cache / "flet").is_dir():
        return "cached"
    return "missing"


# --------------------------------------------------------------------------
# Download e extracao
# --------------------------------------------------------------------------

def _download_url(flet_desktop) -> str:
    url = os.environ.get("FLET_CLIENT_URL")
    if url:
        return url
    return (
        "https://github.com/flet-dev/flet/releases/download/"
        f"v{_version(flet_desktop)}/{flet_desktop.get_artifact_filename()}"
    )


def _extract_archive(archive: Path, target_dir: Path, flet_desktop) -> None:
    """Extrai o cliente no cache local, de forma atomica (dir temporario + rename)."""
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(
        tempfile.mkdtemp(prefix=f"{target_dir.name}.", dir=str(target_dir.parent))
    )
    try:
        safe_extract = getattr(flet_desktop, "safe_zip_extractall", None)
        if safe_extract is not None:
            safe_extract(zipfile.ZipFile(str(archive)), str(temp_dir))
        else:
            with zipfile.ZipFile(str(archive)) as zf:
                zf.extractall(str(temp_dir))
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        temp_dir.rename(target_dir)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def _download_and_extract(flet_desktop, progress=None) -> None:
    """Baixa o cliente do Flet e o instala no cache local."""
    import urllib.error
    import urllib.request

    url = _download_url(flet_desktop)
    if progress:
        progress(None, "Conectando...")

    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_S) as response:
            total = response.headers.get("Content-Length")
            total = int(total) if total else None
            handle_fd, archive_name = tempfile.mkstemp(
                prefix="flet-client-", suffix=".zip"
            )
            os.close(handle_fd)
            archive = Path(archive_name)
            downloaded = 0
            with archive.open("wb") as handle:
                while True:
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    handle.write(chunk)
                    downloaded += len(chunk)
                    if progress:
                        progress(total, downloaded)
    except urllib.error.URLError as exc:
        raise FletClientError(
            "Nao foi possivel baixar o cliente grafico do Flet "
            f"({url}).\n\n"
            f"Motivo: {exc.reason if hasattr(exc, 'reason') else exc}\n\n"
            "Este download acontece uma unica vez (cerca de 30 MB) e exige "
            "internet. Conecte-se a uma rede e execute o Portica App novamente. "
            "Se a sua rede usa proxy ou firewall, libere o acesso a github.com."
        ) from exc
    except Exception as exc:
        raise FletClientError(
            "Nao foi possivel baixar o cliente grafico do Flet "
            f"({url}).\n\nMotivo: {exc}"
        ) from exc

    try:
        _extract_archive(archive, _cache_dir(flet_desktop), flet_desktop)
    except Exception as exc:
        raise FletClientError(
            "O cliente grafico do Flet foi baixado, mas nao pode ser "
            f"instalado.\n\nMotivo: {exc}"
        ) from exc
    finally:
        try:
            archive.unlink()
        except OSError:
            pass


# --------------------------------------------------------------------------
# Interface de progresso / erro
# --------------------------------------------------------------------------

def _message_box(title: str, text: str, error: bool = False) -> None:
    """Caixa de dialogo nativa do Windows (usada como fallback sem tkinter)."""
    try:
        import ctypes
        flags = 0x10 if error else 0x40  # MB_ICONERROR / MB_ICONINFORMATION
        ctypes.windll.user32.MessageBoxW(None, text, title, flags)
    except Exception:
        sys.stderr.write(f"{title}\n{text}\n")


def _download_with_tkinter(flet_desktop) -> None:
    """Baixa o cliente mostrando uma janela de progresso."""
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("Portica App - primeira execucao")
    root.resizable(False, False)
    root.configure(padx=18, pady=14)

    tk.Label(
        root,
        text="Preparando o Portica App...",
        font=("Segoe UI", 12, "bold"),
        justify="left",
    ).pack(anchor="w")
    tk.Label(
        root,
        text=(
            "O cliente grafico do Flet sera baixado uma unica vez "
            "(cerca de 30 MB).\n"
            "E preciso estar conectado a internet nesta primeira execucao; "
            "depois disso o app funciona offline."
        ),
        justify="left",
        wraplength=460,
    ).pack(anchor="w", pady=(8, 12))

    bar = ttk.Progressbar(root, mode="indeterminate", length=460)
    bar.pack(fill="x")
    status = tk.Label(root, text="Iniciando...", anchor="w", justify="left")
    status.pack(fill="x", pady=(8, 0))

    events: "queue.Queue[tuple]" = queue.Queue()
    failure: list[Exception] = []

    def worker() -> None:
        def progress(total, downloaded):
            events.put(("progress", total, downloaded))

        try:
            _download_and_extract(flet_desktop, progress=progress)
            events.put(("done", None, None))
        except Exception as exc:  # noqa: BLE001 - repassado para a UI
            failure.append(exc)
            events.put(("error", None, None))

    def poll() -> None:
        try:
            while True:
                kind, total, downloaded = events.get_nowait()
                if kind == "progress":
                    if total:
                        bar.configure(mode="determinate")
                        bar["value"] = downloaded * 100.0 / total
                        status.configure(
                            text=f"Baixando... {downloaded / 1048576:.1f} MB "
                            f"de {total / 1048576:.1f} MB "
                            f"({downloaded * 100.0 / total:.0f}%)"
                        )
                    else:
                        status.configure(text="Baixando... (tamanho desconhecido)")
                elif kind == "done":
                    root.quit()
                    return
                elif kind == "error":
                    root.quit()
                    return
        except queue.Empty:
            pass
        root.after(100, poll)

    root.after(100, poll)
    bar.start(12)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    root.mainloop()
    bar.stop()

    if failure:
        error = failure[0]
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "Portica App - nao foi possivel iniciar", str(error)
            )
        except Exception:
            _message_box("Portica App - nao foi possivel iniciar", str(error), error=True)
        raise error


def _download_with_message_box(flet_desktop) -> None:
    """Fallback sem tkinter: avisa e baixa sem tela de progresso."""
    _message_box(
        "Portica App - primeira execucao",
        "O cliente grafico do Flet sera baixado uma unica vez "
        "(cerca de 30 MB).\n"
        "E preciso estar conectado a internet nesta primeira execucao.",
    )
    try:
        _download_and_extract(flet_desktop)
    except FletClientError as exc:
        _message_box(
            "Portica App - nao foi possivel iniciar", str(exc), error=True
        )
        raise


# --------------------------------------------------------------------------
# API principal
# --------------------------------------------------------------------------

def prepare_desktop_client() -> str:
    """Garante que o cliente desktop do Flet esteja pronto.

    Retorna o estado final ('bundled', 'cached' ou 'missing' se o Flet
    resolver o cliente por conta propria). Levanta `FletClientError` com
    mensagem amigavel quando o download falha.
    """
    flet_desktop = _flet_desktop()
    if flet_desktop is None:
        return "missing"

    state = client_state()
    if state in ("bundled", "cached"):
        return state

    try:
        import tkinter  # noqa: F401 - apenas para checar disponibilidade
    except ImportError:
        _download_with_message_box(flet_desktop)
    else:
        try:
            _download_with_tkinter(flet_desktop)
        except FletClientError:
            raise
        except Exception as exc:
            raise FletClientError(
                "Nao foi possivel preparar o cliente grafico do Flet.\n\n"
                f"Motivo: {exc}"
            ) from exc

    return client_state()
