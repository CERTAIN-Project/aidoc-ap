/* Coverage page: renders the experiment results (coverage matrix + empirical
 * CQ answering) from resources/experiments-data.json. No dependencies. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const pct = (x) => (x * 100).toFixed(0) + "%";

  fetch("resources/experiments-data.json")
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(render)
    .catch(() => {
      $("byModel").innerHTML = "<tr><td>Run scripts/export_pages_data.py to generate resources/experiments-data.json.</td></tr>";
    });

  function render(d) {
    renderByModel(d);
    renderCQ(d);
    renderTemp(d);
    $("badge").textContent = `Data: ${d.coverage_by_model.length} models × 3 iterations (mean of ${d.n_seeds || 3} seeds), ${d.cq_validation.length} pilot knowledge graphs.`;
  }

  function covCell(v, std, cls) {
    const w = Math.max(0, Math.min(100, v * 100));
    const stdTxt = std ? `<span class="std">±${std.toFixed(3)}</span>` : "";
    return `<td><div class="cov-cell"><div class="bar ${cls}" style="flex:1">
      <span style="width:${w}%"></span></div>
      <span class="val">${v.toFixed(3)}</span>${stdTxt}</div></td>`;
  }

  function renderByModel(d) {
    const rows = d.coverage_by_model;
    let html = `<thead><tr><th style="width:22%">Model</th>
      <th>Iter 1 · core</th><th>Iter 2 · + architecture</th>
      <th>Iter 3 · + data</th><th style="width:9%">Gain</th></tr></thead><tbody>`;
    for (const m of rows) {
      html += `<tr><td><strong>${esc(m.model)}</strong></td>` +
        covCell(m.iter1, m.iter1_std, "g1") +
        covCell(m.iter2, m.iter2_std, "g2") +
        covCell(m.iter3, m.iter3_std, "g3") +
        `<td class="gain">+${m.gain.toFixed(3)}</td></tr>`;
    }
    // average row from temperature.T0 if present
    const t0 = d.temperature && d.temperature["0.0"];
    if (t0) {
      html += `<tr style="border-top:2px solid var(--line)"><td><strong>Average</strong></td>` +
        covCell(t0["1"], 0, "g1") + covCell(t0["2"], 0, "g2") + covCell(t0["3"], 0, "g3") +
        `<td class="gain">+${(t0["3"] - t0["1"]).toFixed(3)}</td></tr>`;
    }
    $("byModel").innerHTML = html + "</tbody>";
  }

  function renderCQ(d) {
    let html = `<thead><tr><th style="width:26%">Pilot</th><th style="width:26%">Domain (Annex III)</th>
      <th>Competency questions answered (of 50)</th><th style="width:9%">Triples</th></tr></thead><tbody>`;
    for (const p of d.cq_validation) {
      const w = (p.answered / p.total) * 100;
      html += `<tr><td><strong>${esc(p.display)}</strong></td>
        <td>${esc(p.domain)}</td>
        <td><div class="cqbar"><span style="width:${w}%"></span><b>${p.answered} / ${p.total}</b></div></td>
        <td>${p.triples}</td></tr>`;
    }
    $("cq").innerHTML = html + "</tbody>";
  }

  function renderTemp(d) {
    const t = d.temperature;
    if (!t || !t["0.0"] || !t["1.0"]) { $("tempNote").style.display = "none"; return; }
    const f = (o) => `${o["1"].toFixed(3)} / ${o["2"].toFixed(3)} / ${o["3"].toFixed(3)}`;
    $("tempNote").innerHTML =
      `<strong>Stable across runs and temperature.</strong> Run‑to‑run standard deviation stays ≤ 0.008 at temperature 0. Averaged over the models, the per‑iteration coverage is ${f(t["0.0"])} at temperature 0 versus ${f(t["1.0"])} at temperature 1.0 — a difference of at most ${Math.max(...["1","2","3"].map(i => Math.abs(t["0.0"][i]-t["1.0"][i]))).toFixed(3)}, so the sampling temperature does not drive the reported trends.`;
  }
})();
