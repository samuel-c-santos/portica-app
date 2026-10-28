"""
Wrapper para configurar SSL antes de executar o app.
Resolve o problema de certificados no PyInstaller.

Ordem de execucao no executavel congelado:
  1. configuracao de SSL/certifi (antes de qualquer import que use rede);
  2. preparacao do cliente desktop do Flet (download unico na primeira
     execucao, com tela de progresso e mensagem de erro amigavel);
  3. inicio do app unificado (`edicoes.main`).
"""

import os
import sys

# Configura certificados SSL antes de qualquer importacao
if getattr(sys, 'frozen', False):
    # Rodando como executavel PyInstaller
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# Importa e executa o app principal
if __name__ == "__main__":
    from flet_bootstrap import FletClientError, prepare_desktop_client

    # App unificado: existe uma unica edicao (F1a).
    from edicoes import main

    # ft.run() substitui ft.app(), deprecado no Flet 0.80+.
    import flet as ft

    try:
        prepare_desktop_client()
    except FletClientError as exc:
        # A mensagem de erro ja foi apresentada ao usuario (dialogo nativo);
        # aqui nao ha stack trace para o usuario.
        try:
            sys.stderr.write(f"{exc}\n")
        except Exception:
            pass  # executavel sem console: sys.stderr pode ser None
        sys.exit(1)

    ft.run(main.main)
