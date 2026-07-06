/* AIDOC-AP alignment curation UI.
 * Loads resources/curation-data.json; stores decisions in localStorage per
 * curator; exports JSON for scripts/merge_curation.py. No dependencies. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  let DATA = null;          // {batch_id, items: [...]}
  let items = [];           // filtered view
  let idx = 0;              // position within filtered view
  let curator = localStorage.getItem("aidocCurator") || "";

  const storeKey = () => `aidocCuration:${curator}`;
  const loadDecisions = () =>
    curator ? JSON.parse(localStorage.getItem(storeKey()) || "{}") : {};
  const saveDecisions = (d) => localStorage.setItem(storeKey(), JSON.stringify(d));
  let decisions = {};

  // ---------- data ----------
  fetch("resources/curation-data.json")
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((d) => { DATA = d; init(); })
    .catch(() => {
      $("banner").hidden = false;
      $("banner").textContent =
        "curation-data.json not found — run scripts/export_curation_ui_data.py and redeploy.";
    });

  function init() {
    const ontos = [...new Set(DATA.items.map((i) => i.ontology))].sort();
    for (const o of ontos) {
      const opt = document.createElement("option");
      opt.value = o; opt.textContent = o;
      $("fOnto").appendChild(opt);
    }
    $("curator").value = curator;
    decisions = loadDecisions();
    refresh();
  }

  // ---------- filtering / rendering ----------
  function refresh(keepIdx) {
    const fo = $("fOnto").value, fs = $("fStatus").value;
    items = DATA.items.filter((it) => {
      if (fo && it.ontology !== fo) return false;
      const done = !!decisions[it.id];
      if (fs === "open" && done) return false;
      if (fs === "done" && !done) return false;
      return true;
    });
    if (!keepIdx) idx = 0;
    idx = Math.max(0, Math.min(idx, items.length - 1));
    renderProgress();
    renderQueue();
    renderCard();
  }

  function renderProgress() {
    const all = DATA.items.length;
    const done = DATA.items.filter((i) => decisions[i.id]).length;
    $("pbar").style.width = all ? (100 * done / all) + "%" : "0";
    $("plabel").textContent = curator
      ? `${curator}: ${done} / ${all} curated (batch ${DATA.batch_id})`
      : "→ Kürzel eingeben, dann werden Entscheidungen gespeichert";
  }

  function renderQueue() {
    const tb = $("qbody");
    tb.innerHTML = "";
    items.forEach((it, i) => {
      const d = decisions[it.id];
      const tr = document.createElement("tr");
      if (i === idx) tr.className = "current";
      tr.innerHTML =
        `<td>${i + 1}</td><td>${esc(it.aidoc_label)}</td><td>${esc(it.ref_label)}</td>` +
        `<td>${esc(it.ontology)}</td><td><code>${esc(it.llm_relation)}</code></td>` +
        `<td>${it.llm_confidence.toFixed(2)}</td>` +
        `<td class="st ${d ? d.decision : "open"}">${d ? d.decision + (d.relation ? " → " + d.relation : "") : "open"}</td>`;
      tr.onclick = () => { idx = i; renderQueue(); renderCard(); };
      tb.appendChild(tr);
    });
  }

  function renderCard() {
    const card = $("card");
    if (!items.length) { card.hidden = true; return; }
    card.hidden = false;
    const it = items[idx];
    $("posInfo").textContent = `${idx + 1} / ${items.length} (filtered)`;
    $("metaInfo").textContent = `ontology: ${it.ontology}`;
    $("aLabel").textContent = it.aidoc_label;
    $("aIri").textContent = it.aidoc_iri; $("aIri").href = it.aidoc_iri;
    $("rLabel").textContent = it.ref_label;
    $("rIri").textContent = it.ref_iri; $("rIri").href = it.ref_iri;
    $("llmRel").textContent = it.llm_relation;
    const cb = $("confBadge");
    cb.textContent = "conf " + it.llm_confidence.toFixed(2);
    cb.className = "badge " + (it.llm_confidence >= 0.75 ? "hi" : "lo");
    const lb = $("lexBadge");
    lb.textContent = "lex " + it.lexical_similarity.toFixed(2);
    lb.className = "badge " + (it.lexical_similarity >= 0.75 ? "hi" : "lo");
    $("llmRat").textContent = it.llm_rationale || "";
    const d = decisions[it.id];
    $("noteInp").value = d && d.note ? d.note : "";
    $("modifyRel").style.display = "none";
    for (const b of ["btnAccept", "btnModify", "btnReject"]) $(b).classList.remove("sel");
    if (d) {
      if (d.decision === "accept") $("btnAccept").classList.add("sel");
      if (d.decision === "reject") $("btnReject").classList.add("sel");
      if (d.decision === "modify") {
        $("btnModify").classList.add("sel");
        $("modifyRel").style.display = "";
        $("modifyRel").value = d.relation || "skos:closeMatch";
      }
    }
  }

  const esc = (s) => String(s ?? "").replace(/[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ---------- decisions ----------
  function requireCurator() {
    if (!curator) { alert("Bitte zuerst Kurator-Kürzel eingeben."); $("curator").focus(); }
    return !!curator;
  }

  function decide(decision, relation) {
    if (!requireCurator() || !items.length) return;
    const it = items[idx];
    decisions[it.id] = {
      decision,
      relation: relation || null,
      note: $("noteInp").value.trim() || null,
      curator,
      batch_id: DATA.batch_id,
      ts: new Date().toISOString(),
    };
    saveDecisions(decisions);
    // auto-advance; with "open only" filter the list shrinks in place
    if ($("fStatus").value === "open") refresh(true);
    else { if (idx < items.length - 1) idx++; refresh(true); }
  }

  $("btnAccept").onclick = () => decide("accept");
  $("btnReject").onclick = () => decide("reject");
  $("btnModify").onclick = () => {
    if (!requireCurator()) return;
    const sel = $("modifyRel");
    if (sel.style.display === "none") { sel.style.display = ""; sel.focus(); }
    else decide("modify", sel.value);
  };
  $("modifyRel").onchange = () => decide("modify", $("modifyRel").value);
  $("btnSkip").onclick = () => { if (idx < items.length - 1) { idx++; refresh(true); } };
  $("btnUndo").onclick = () => {
    if (!items.length) return;
    delete decisions[items[idx].id];
    saveDecisions(decisions);
    refresh(true);
  };
  $("btnPrev").onclick = () => { if (idx > 0) { idx--; refresh(true); } };
  $("btnNext").onclick = () => { if (idx < items.length - 1) { idx++; refresh(true); } };
  $("noteInp").onchange = () => {   // persist note edits on decided items
    const it = items[idx];
    if (it && decisions[it.id]) {
      decisions[it.id].note = $("noteInp").value.trim() || null;
      saveDecisions(decisions);
    }
  };

  $("curator").onchange = () => {
    curator = $("curator").value.trim();
    localStorage.setItem("aidocCurator", curator);
    decisions = loadDecisions();
    refresh();
  };
  $("fOnto").onchange = () => refresh();
  $("fStatus").onchange = () => refresh();

  // ---------- keyboard ----------
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
    const k = e.key.toLowerCase();
    if (k === "a") decide("accept");
    else if (k === "r") decide("reject");
    else if (k === "m") $("btnModify").onclick();
    else if (k === "s") $("btnSkip").onclick();
    else if (k === "u") $("btnUndo").onclick();
    else if (e.key === "ArrowLeft") $("btnPrev").onclick();
    else if (e.key === "ArrowRight") $("btnNext").onclick();
    else return;
    e.preventDefault();
  });

  // ---------- export / import ----------
  $("exportBtn").onclick = () => {
    if (!requireCurator()) return;
    const payload = {
      curator,
      batch_id: DATA.batch_id,
      exported: new Date().toISOString(),
      n_decisions: Object.keys(decisions).length,
      decisions,
    };
    const blob = new Blob([JSON.stringify(payload, null, 1)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `curation_${curator}_${DATA.batch_id}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  $("importBtn").onclick = () => $("importFile").click();
  $("importFile").onchange = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    f.text().then((t) => {
      const p = JSON.parse(t);
      if (p.batch_id !== DATA.batch_id &&
          !confirm(`Export stammt aus Batch ${p.batch_id}, aktuell ist ${DATA.batch_id}. Trotzdem laden?`)) return;
      if (p.curator && p.curator !== curator) {
        curator = p.curator;
        $("curator").value = curator;
        localStorage.setItem("aidocCurator", curator);
      }
      decisions = Object.assign(loadDecisions(), p.decisions);
      saveDecisions(decisions);
      refresh();
    }).catch(() => alert("Datei konnte nicht gelesen werden."));
  };
})();
