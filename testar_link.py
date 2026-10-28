"""Verifica se o link do SharePoint baixa a planilha sem login.

    python testar_link.py
"""
import os
import tempfile

import app
import dados

if not app.LINK_PLANILHA:
    raise SystemExit("LINK_PLANILHA está vazio em app.py.")

destino = os.path.join(tempfile.mkdtemp(), "teste.xlsx")
print("Baixando:", dados._url_download(app.LINK_PLANILHA))
dados.baixar_planilha(app.LINK_PLANILHA, destino, forcar=True)
if dados.status_link["erro"]:
    print("FALHOU:", dados.status_link["erro"])
    print("O painel vai continuar usando a cópia local em", app.PLANILHA)
else:
    d = dados._carregar(destino)
    print(f"OK: {len(d['entregas'])} entregas e {len(d['oficinas'])} oficinas lidas pelo link.")
