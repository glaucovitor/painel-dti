"""Painel "Indicadores do Projeto" — réplica web do relatório Power BI.

Executar:
    pip install -r requirements.txt
    python app.py                # http://127.0.0.1:5000

A planilha é baixada do link do SharePoint (LINK_PLANILHA) e guardada em
./dados/Entregas_DTI.xlsx. Se o link estiver indisponível, o painel usa essa
cópia local. Sem link, a planilha local é relida sempre que o arquivo muda.
"""
import os

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

import dados

BASE = os.path.dirname(os.path.abspath(__file__))
PLANILHA = os.environ.get("PLANILHA", os.path.join(BASE, "dados", "Entregas_DTI.xlsx"))

# Link de compartilhamento da planilha no SharePoint. Quando definido, o painel
# baixa a planilha por ele (no máximo a cada INTERVALO segundos) e grava em
# PLANILHA; se o download falhar, usa a última cópia local.
# Para desligar e usar só o arquivo local, deixe LINK_PLANILHA = "".
LINK_PLANILHA = os.environ.get(
    "LINK_PLANILHA",
    "https://unbbr.sharepoint.com/:x:/s/ITRAC-DITSSCMGI/IQCgTJJgLVy3R4-2o2v3-LYJAdoYpdwUcOR5WNjvb--M1Zw?e=MUUY4P",
)
INTERVALO = int(os.environ.get("INTERVALO", 300))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

PAGINAS = [
    ("visao_geral", "Visão Geral", "globo"),
    ("oficinas", "Oficinas Colaborativas", "pessoas"),
    ("atividades", "Entregas por Atividades", "entrega"),
    ("reacao", "Avaliação de Reação", "ideia"),
    ("impacto", "Avaliação de Impacto", "impacto"),
]

LOGOS = [  # arquivo opcional em static/img/  ->  texto usado se não existir
    ("colaboragov.png", "COLABORAGOV"),
    ("colaboralab.png", "COLABORALAB"),
    ("itrac.png", "itrac"),
    ("unb.png", "Universidade de Brasília"),
]


@app.context_processor
def contexto():
    img = os.path.join(BASE, "static", "img")
    logos = [{"arquivo": a if os.path.exists(os.path.join(img, a)) else None, "texto": t} for a, t in LOGOS]
    return {"paginas": PAGINAS, "logos": logos, "link": bool(LINK_PLANILHA),
            "erro_link": dados.status_link["erro"] if LINK_PLANILHA else ""}


def _sincronizar(forcar=False):
    if LINK_PLANILHA:
        dados.baixar_planilha(LINK_PLANILHA, PLANILHA, INTERVALO, forcar)


def _render(pagina: str):
    _sincronizar()
    if not os.path.exists(PLANILHA):
        return render_template("sem_planilha.html", caminho=PLANILHA), 503
    d = dados.obter(PLANILHA)
    return render_template(f"{pagina}.html", pagina=pagina, dados=d, atualizado_em=d["atualizado_em"])


@app.route("/")
def visao_geral():
    return _render("visao_geral")


@app.route("/oficinas")
def oficinas():
    return _render("oficinas")


@app.route("/atividades")
def atividades():
    return _render("atividades")


@app.route("/reacao")
def reacao():
    return _render("reacao")


@app.route("/impacto")
def impacto():
    return _render("impacto")


@app.route("/api/dados")
def api_dados():
    _sincronizar()
    if not os.path.exists(PLANILHA):
        abort(503)
    return jsonify(dados.obter(PLANILHA))


@app.post("/sincronizar")
def sincronizar():
    _sincronizar(forcar=True)
    return redirect(request.referrer or url_for("visao_geral"))


@app.post("/atualizar")
def atualizar():
    f = request.files.get("planilha")
    if not f or not f.filename.lower().endswith(".xlsx"):
        abort(400, "Envie um arquivo .xlsx")
    os.makedirs(os.path.dirname(PLANILHA), exist_ok=True)
    tmp = PLANILHA + ".tmp"
    f.save(tmp)
    try:
        dados._carregar(tmp)  # valida antes de substituir
    except Exception as e:  # noqa: BLE001
        os.remove(tmp)
        abort(400, f"Planilha inválida: {e}")
    os.replace(tmp, PLANILHA)
    return redirect(request.referrer or url_for("visao_geral"))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
