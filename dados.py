"""Leitura da planilha Entregas_DTI.xlsx e cálculo dos indicadores do painel.

A planilha é relida automaticamente sempre que o arquivo muda no disco
(cache por data de modificação), então basta substituir o .xlsx para
o painel refletir os novos dados.
"""
from __future__ import annotations

import os
import re
import threading
import unicodedata
from collections import Counter
from datetime import datetime, date

import pandas as pd

_lock = threading.Lock()
_cache: dict = {"mtime": None, "dados": None}

# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------

def _txt(v) -> str:
    """Converte qualquer célula em texto limpo ('' para vazio)."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NA:
        return ""
    if isinstance(v, (datetime, pd.Timestamp)):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    s = str(v).strip()
    return "" if s.lower() in ("nan", "nat", "none", "-") else re.sub(r"\s+", " ", s)


def _num(v) -> float | None:
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


def _excel_date(v):
    """Datas podem vir como datetime, serial do Excel ou texto com várias datas."""
    if isinstance(v, (datetime, pd.Timestamp)):
        return pd.Timestamp(v)
    n = _num(v)
    if n is not None and 20000 < n < 80000:
        return pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)
    return None


def _texto_data(v) -> str:
    d = _excel_date(v)
    return d.strftime("%d/%m/%Y") if d is not None else _txt(v)


def _primeira_data(v):
    """Data usada para ordenar: a primeira dd/mm/aaaa encontrada."""
    d = _excel_date(v)
    if d is not None:
        return d
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", _txt(v))
    if m:
        return pd.Timestamp(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def _link(v) -> str:
    s = _txt(v)
    return s if s.lower().startswith("http") else ""


# ---------------------------------------------------------------------------
# nuvem de palavras
# ---------------------------------------------------------------------------

STOPWORDS = set("""
a à ao aos as às até após com como da das de del dela dele deles do dos e é em
entre era essa esse esta este eu foi foram há isso isto já la lhe mais mas me
mesmo meu muito na nas não nem no nos nós o os ou para pela pelas pelo pelos
por qual quando que quem se sem ser seu sua são só também te tem ter um uma
umas uns vez sobre seus suas sendo será serão são deve pode cada onde todo toda
todos todas foram teve ter tendo estão está estar via sob obs id ainda bem
objetivo objetivos oficina oficinas teve gerais geral realizar realizadas
realizada realizado encontro principal principais d
""".split())


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def nuvem_palavras(textos: list[str], limite: int = 70) -> list[list]:
    cont: Counter = Counter()
    forma: dict = {}
    for t in textos:
        for w in re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]+", t):
            lw = w.lower()
            if len(lw) < 3 or lw in STOPWORDS or _sem_acento(lw) in STOPWORDS:
                continue
            chave = _sem_acento(lw)
            cont[chave] += 1
            forma.setdefault(chave, lw)
    return [[forma[k], c] for k, c in cont.most_common(limite)]


# ---------------------------------------------------------------------------
# carga
# ---------------------------------------------------------------------------

def _carregar(caminho: str) -> dict:
    x = pd.read_excel(caminho, sheet_name=None, dtype=object)

    frentes = {_txt(r["ID"]): _txt(r["Frente"]) for _, r in x["Frentes"].iterrows() if _txt(r["ID"])}
    atividades = {_txt(r["ID_Atividade"]): _txt(r["Atividade"])
                  for _, r in x["Atividades"].iterrows() if _txt(r["ID_Atividade"])}

    # --- Entregas ---------------------------------------------------------
    entregas = []
    for _, r in x["Entregas"].iterrows():
        eid = _txt(r["ID_Entrega"])
        if not eid:
            continue
        fid, aid = _txt(r["Frente"]), _txt(r["Atividade"])
        entregas.append({
            "id": eid,
            "frente": frentes.get(fid, fid),
            "atividade": atividades.get(aid, aid),
            "descricao": _txt(r["Descrição"]),
            "data": _texto_data(r["Data"]),
            "status": _txt(r["Status"]),
            "solicitante": _txt(r["Solicitante"]),
            "relatorio": _txt(r["Relatório"]),
            "link": _link(r["Link"]) or _txt(r["Link"]),
        })
    entregas_por_id = {e["id"]: e for e in entregas}

    # --- Oficinas ---------------------------------------------------------
    oficinas = []
    for _, r in x["Oficinas"].iterrows():
        oid = _txt(r["ID_Oficina"])
        if not oid:
            continue
        d0 = _primeira_data(r["Data de Realização"])
        oficinas.append({
            "id": oid,
            "frente": frentes.get(_txt(r["ID_Frente"]), _txt(r["ID_Frente"])),
            "nome": _txt(r["Oficina Realizada"]),
            "formato": _txt(r["Formato"]),
            "data": _texto_data(r["Data de Realização"]),
            "ordem": d0.strftime("%Y-%m-%d") if d0 is not None else "",
            "objetivos": _txt(r["Objetivos"]),
            "servico": _txt(r["Serviço estruturante"]),
            "participantes": _num(r["Qtde de Participantes (externos UnB)"]),
            "dias": _num(r["Dias Totais da Oficina"]),
            "horas": _num(r["Horas Totais da Oficina"]),
            "prototipos": _num(r["Qtde de Protótipos Desenvolvidos"]),
            "testes": _num(r["Qtde de Testes com Usuários Realizados"]),
            "teasers": _num(r["Qtde de Teasers Produzidos"]),
            "processos": _num(r["Qtde de Processos Transformados"]),
        })
    oficinas_por_id = {o["id"]: o for o in oficinas}

    # --- Entregas por oficina --------------------------------------------
    ent_of = []
    for _, r in x["Entregas_por_Oficinas"].iterrows():
        oid, eid = _txt(r["ID_Oficina"]), _txt(r["ID_Entrega"])
        if not oid or not eid:
            continue
        o, e = oficinas_por_id.get(oid, {}), entregas_por_id.get(eid, {})
        ent_of.append({
            "id_oficina": oid,
            "oficina": o.get("nome", ""),
            "servico": o.get("servico", ""),
            "descricao": e.get("descricao", ""),
            "link": e.get("link", ""),
        })

    # --- Avaliação de reação ---------------------------------------------
    reacao = {"questoes": [], "respostas": []}
    if "Avaliacao_Reacao" in x:
        df = x["Avaliacao_Reacao"]
        qs = [c for c in df.columns if c != "ID_Oficina"]
        reacao["questoes"] = qs
        for _, r in df.iterrows():
            oid = _txt(r["ID_Oficina"])
            if not oid:
                continue
            reacao["respostas"].append({
                "oficina": oid,
                "notas": {q: int(_num(r[q])) for q in qs if _num(r[q]) is not None},
            })

    # --- Avaliação de impacto (formato largo -> longo) -------------------
    impacto = []
    if "Avaliacao_Impacto" in x:
        df = x["Avaliacao_Impacto"]
        n = max((int(m.group(1)) for c in df.columns if (m := re.match(r"Dimensao_(\d+)", str(c)))), default=0)
        for _, r in df.iterrows():
            proj = _txt(r["Projeto"])
            if not proj:
                continue
            for i in range(1, n + 1):
                dim = _txt(r.get(f"Dimensao_{i}"))
                if dim:
                    impacto.append({
                        "projeto": proj,
                        "dimensao": dim,
                        "achados": _txt(r.get(f"Achados_{i}")),
                        "avaliacao": _txt(r.get(f"Avaliacao_{i}")),
                    })

    return {
        "atualizado_em": datetime.fromtimestamp(os.path.getmtime(caminho)).strftime("%d/%m/%Y %H:%M:%S"),
        "entregas": entregas,
        "oficinas": oficinas,
        "entregas_oficinas": ent_of,
        "atividades_lista": list(atividades.values()),
        "reacao": reacao,
        "impacto": impacto,
        "nuvem": nuvem_palavras([o["objetivos"] for o in oficinas]),
    }


# ---------------------------------------------------------------------------
# download pelo link de compartilhamento (SharePoint/OneDrive)
# ---------------------------------------------------------------------------

status_link = {"verificado_em": 0.0, "erro": ""}


def _url_download(url: str) -> str:
    """Troca a visualização do Excel Online pelo download direto do arquivo."""
    url = re.sub(r"([?&])nav=[^&]*&?", r"\1", url).rstrip("?&")
    if "download=1" not in url:
        url += ("&" if "?" in url else "?") + "download=1"
    return url


def baixar_planilha(url: str, destino: str, intervalo: int = 300, forcar: bool = False) -> None:
    """Baixa a planilha do link para `destino`, no máximo a cada `intervalo` segundos.

    Em caso de falha, mantém o arquivo local existente e registra o erro em
    `status_link`, para o painel continuar funcionando com a última cópia.
    """
    import time
    import urllib.request

    agora = time.time()
    if not forcar and agora - status_link["verificado_em"] < intervalo:
        return
    status_link["verificado_em"] = agora
    tmp = destino + ".tmp"
    try:
        req = urllib.request.Request(_url_download(url), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            conteudo = r.read()
        if not conteudo.startswith(b"PK"):  # .xlsx é um zip; HTML costuma ser a tela de login
            raise ValueError("o link não devolveu uma planilha (provavelmente exige login)")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        atual = open(destino, "rb").read() if os.path.exists(destino) else None
        if conteudo != atual:  # só regrava se mudou, preservando a data de atualização
            with open(tmp, "wb") as f:
                f.write(conteudo)
            _carregar(tmp)  # valida antes de substituir
            os.replace(tmp, destino)
        status_link["erro"] = ""
    except Exception as e:  # noqa: BLE001 - rede, login, arquivo inválido
        status_link["erro"] = str(e)
        if os.path.exists(tmp):
            os.remove(tmp)


def obter(caminho: str) -> dict:
    mtime = os.path.getmtime(caminho)
    with _lock:
        if _cache["mtime"] != mtime:
            _cache["dados"] = _carregar(caminho)
            _cache["mtime"] = mtime
        return _cache["dados"]
