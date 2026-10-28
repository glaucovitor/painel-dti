/* Funções compartilhadas pelas páginas do painel. */
const COR = { azul: "#118dff", escuro: "#12239e", laranja: "#e66c37", texto: "#252423", suave: "#605e5c" };
const FONTE = '"Segoe UI", "Helvetica Neue", Arial, sans-serif';
const CONFIG = { displayModeBar: false, responsive: true, locale: "pt-BR" };
const VAZIO = "(Em branco)";

const fmt = (v, casas = 0) =>
  v == null || isNaN(v) ? "–" : Number(v).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

const soma = (arr, f) => arr.reduce((s, x) => s + (Number(f(x)) || 0), 0);
const media = (arr, f) => {
  const v = arr.map(f).filter(x => x != null && !isNaN(x));
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
};
const contar = (arr, f) => {
  const m = new Map();
  arr.forEach(x => { const k = f(x) || VAZIO; m.set(k, (m.get(k) || 0) + 1); });
  return m;
};
const ordenarDesc = m => [...m.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "pt-BR"));
const truncar = (s, n) => (s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function kpis(el, itens) {
  el.innerHTML = itens.map(([v, l]) =>
    `<div class="kpi"><div class="valor">${v}</div><div class="legenda" title="${esc(l)}">${esc(l)}</div></div>`).join("");
}

/* Barras horizontais no estilo Power BI. pares = [[rótulo, valor], ...] */
function barraH(el, pares, o = {}) {
  const alt = o.altBarra || 30;
  const nChars = o.nChars || 32;
  const sel = o.selecionados || new Set();
  const rot = pares.map(p => p[0]);
  const val = pares.map(p => p[1]);
  const cores = rot.map(r => (sel.size && !sel.has(r) ? "rgba(17,141,255,.35)" : (o.cor || COR.azul)));
  const altura = Math.max(o.minAltura || 0, pares.length * alt + (o.titX ? 60 : 24));
  el.style.height = (o.fixo ? "100%" : altura + "px");
  const maxV = Math.max(1, ...val);
  Plotly.react(el, [{
    type: "bar", orientation: "h",
    y: rot.map(r => truncar(r, nChars)), x: val,
    customdata: rot,
    text: val.map(v => fmt(v)), textposition: "outside", cliponaxis: false,
    textfont: { size: 13, color: COR.suave },
    marker: { color: cores },
    hovertemplate: "%{customdata}<br><b>%{x}</b><extra></extra>",
    width: o.espessura || 0.62,
  }], {
    margin: { l: o.margemEsq || 250, r: 46, t: 6, b: o.titX ? 48 : 6 },
    font: { family: FONTE, size: 13, color: COR.suave },
    paper_bgcolor: "#fff", plot_bgcolor: "#fff",
    xaxis: {
      visible: !!o.eixoX, range: [0, maxV * 1.08], fixedrange: true,
      title: o.titX ? { text: o.titX, font: { size: 12, color: COR.texto } } : undefined,
      gridcolor: "#e6e6e6", zeroline: false, tickfont: { size: 12 },
      dtick: o.dtick,
    },
    yaxis: {
      autorange: "reversed", fixedrange: true, automargin: false,
      ticksuffix: "  ", tickfont: { size: o.fonteRotulo || 13, color: COR.suave },
      title: o.titY ? { text: o.titY, font: { size: 12, color: COR.texto }, standoff: 4 } : undefined,
    },
    bargap: 0.3,
    hoverlabel: { font: { family: FONTE } },
  }, CONFIG);
  if (o.onClick && !el._clique) {
    el._clique = true;
    el.on("plotly_click", ev => o.onClick(ev.points[0].customdata));
  }
}

/* Segmentação (slicer) com caixas de seleção múltipla. */
function slicer(el, valores, onChange, limparEl) {
  const sel = new Set();
  el.innerHTML = valores.map((v, i) =>
    `<label title="${esc(v)}"><input type="checkbox" data-i="${i}">${esc(v)}</label>`).join("");
  const sync = () => {
    el.querySelectorAll("input").forEach(c => { c.checked = sel.has(valores[c.dataset.i]); });
    if (limparEl) limparEl.classList.toggle("visivel", sel.size > 0);
  };
  el.addEventListener("change", ev => {
    const v = valores[ev.target.dataset.i];
    ev.target.checked ? sel.add(v) : sel.delete(v);
    sync(); onChange(sel);
  });
  if (limparEl) limparEl.addEventListener("click", () => { sel.clear(); sync(); onChange(sel); });
  return {
    sel,
    alternar(v) { sel.has(v) ? sel.delete(v) : sel.add(v); sync(); onChange(sel); },
  };
}

/* Tabela com ordenação por clique no cabeçalho.
   colunas: [{campo, titulo, tipo: 'num'|'link'|'texto', largura, ordenarPor}] */
function tabela(el, colunas, ordemInicial) {
  let linhas = [];
  let ordem = ordemInicial || { campo: colunas[0].campo, dir: 1 };
  const cab = colunas.map(c =>
    `<th data-c="${c.campo}" style="${c.largura ? "width:" + c.largura : ""}">${esc(c.titulo)}</th>`).join("");
  el.innerHTML = `<table class="tabela"><thead><tr>${cab}</tr></thead><tbody></tbody></table>`;
  const tb = el.querySelector("tbody");
  const ths = el.querySelectorAll("th");

  function desenhar() {
    const col = colunas.find(c => c.campo === ordem.campo) || colunas[0];
    const chave = col.ordenarPor || col.campo;
    const ord = [...linhas].sort((a, b) => {
      const x = a[chave], y = b[chave];
      if (typeof x === "number" || typeof y === "number") return ((x ?? -Infinity) - (y ?? -Infinity)) * ordem.dir;
      return String(x ?? "").localeCompare(String(y ?? ""), "pt-BR", { numeric: true }) * ordem.dir;
    });
    ths.forEach(t => t.className = t.dataset.c === ordem.campo ? (ordem.dir > 0 ? "ord-asc" : "ord-desc") : "");
    if (!ord.length) { tb.innerHTML = `<tr><td class="vazio" colspan="${colunas.length}">Nenhum registro para a seleção atual.</td></tr>`; return; }
    tb.innerHTML = ord.map(l => "<tr>" + colunas.map(c => {
      const v = l[c.campo];
      if (c.tipo === "link") {
        return /^https?:/i.test(v || "")
          ? `<td class="link"><a href="${esc(v)}" target="_blank" rel="noopener" title="${esc(v)}">${esc(v)}</a></td>`
          : `<td class="link">${esc(v)}</td>`;
      }
      if (c.tipo === "num") return `<td class="num">${v == null ? "" : fmt(v)}</td>`;
      return `<td>${esc(v)}</td>`;
    }).join("") + "</tr>").join("");
  }
  ths.forEach(t => t.addEventListener("click", () => {
    ordem = { campo: t.dataset.c, dir: ordem.campo === t.dataset.c ? -ordem.dir : 1 };
    desenhar();
  }));
  return { atualizar(novas) { linhas = novas; desenhar(); } };
}

/* Valores únicos ordenados, com "(Em branco)" no topo quando houver vazios. */
function unicos(arr, f, extra = []) {
  const s = new Set(extra);
  let temVazio = false;
  arr.forEach(x => { const v = f(x); v ? s.add(v) : (temVazio = true); });
  const lista = [...s].sort((a, b) => a.localeCompare(b, "pt-BR"));
  return temVazio ? [VAZIO, ...lista] : lista;
}
const passa = (sel, v) => !sel.size || sel.has(v || VAZIO);
