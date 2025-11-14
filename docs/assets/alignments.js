(async function(){

  // --- helpers --------------------------------------------------------------
  const $ = sel => document.querySelector(sel);
  const byId = id => document.getElementById(id);
  const esc = s => (s||'').replace(/[&<>"]/g,c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c]));
  const short = iri => iri.replace(/^https?:\/\//,'').replace(/#.*$/,'').replace(/\/$/,'').split('/').slice(0,2).join('/') + '…';

  const pillFor = rel => {
    if(!rel) return '';
    if(rel.endsWith('equivalentClass')) return `<span class="pill eqv">equivalent</span>`;
    if(rel.endsWith('exactMatch')) return `<span class="pill exact">exact</span>`;
    if(rel.endsWith('closeMatch')) return `<span class="pill close">close</span>`;
    if(rel.endsWith('broadMatch')) return `<span class="pill broad">broad</span>`;
    if(rel.endsWith('narrowMatch')) return `<span class="pill narrow">narrow</span>`;
    return `<span class="pill related">related</span>`;
  };

  const aidocAnchor = iri => {
    // try #localName first
    const id = iri.includes('#') ? iri.split('#')[1] : iri.split('/').pop();
    return `/#${encodeURIComponent(id)}`;
  };

  // --- load data: prefer JSON (build-time), else TTL (client-side) ----------
  async function loadJSONorTTL(){
    try {
      const [mapsRes, runsRes] = await Promise.all([
        fetch('alignments.json', {cache:'no-store'}),
        fetch('runs.json', {cache:'no-store'})
      ]);
      if (mapsRes.ok) {
        const maps = await mapsRes.json();
        const runs = runsRes.ok ? (await runsRes.json()).runs : [];
        return {maps, runs};
      }
    } catch(e){ /* fall through */ }

    // TTL fallback with N3.js (load lazily)
    await loadScript('https://unpkg.com/n3@1.17.4/browser/n3.min.js');
    const ttlFiles = (window.ALIGNMENT_TTLS || []);
    const maps = [];
    const runMap = {};

    for (const ttl of ttlFiles) {
      const txt = await (await fetch(ttl, {cache:'no-store'})).text();
      const parser = new N3.Parser();
      const quads = parser.parse(txt);

      // Index quads by subject for quick access
      const byS = new Map();
      for (const q of quads) {
        const k = q.subject.id;
        if(!byS.has(k)) byS.set(k, []);
        byS.get(k).push(q);
      }
      const RDF  = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type';
      const PROV = 'http://www.w3.org/ns/prov#';
      const ALIGN= 'https://w3id.org/aidoc-ap/alignment#';

      // collect PROV activities
      for (const [s,qs] of byS) {
        if (qs.some(q => q.predicate.id===RDF && q.object.id===PROV+'Activity')) {
          const started = obj(byS, s, PROV+'startedAtTime');
          const ended   = obj(byS, s, PROV+'endedAtTime');
          const used    = obj(byS, s, PROV+'used');
          runMap[s] = { id:s, startedAt: lit(started), endedAt: lit(ended), used: val(used) };
        }
      }
      // collect mappings
      for (const [s,qs] of byS) {
        if (qs.some(q => q.predicate.id===RDF && q.object.id===ALIGN+'Mapping')) {
          const rel  = val(obj(byS, s, ALIGN+'relation'));
          const src  = val(obj(byS, s, ALIGN+'source'));
          const tgt  = val(obj(byS, s, ALIGN+'target'));
          const conf = obj(byS, s, ALIGN+'confidence'); // literal
          const rat  = lit(obj(byS, s, ALIGN+'rationale'));
          const who  = val(obj(byS, s, PROV+'wasAttributedTo'));
          const run  = val(obj(byS, s, PROV+'wasGeneratedBy'));
          const ns   = tgt ? (tgt.includes('#') ? tgt.split('#')[0] : tgt.substring(0, tgt.lastIndexOf('/'))) : '';
          maps.push({
            mapping: s, source: src, relation: rel, target: tgt, target_ns: ns,
            confidence: conf ? Number(conf.object.value) : null,
            rationale: rat || null, agent: who || null, run: run || null
          });
        }
      }
    }
    return {maps, runs: Object.values(runMap)};

    // helpers for TTL parsing
    function obj(byS, s, p){
      const qs = byS.get(s) || [];
      return qs.find(q => q.predicate.id===p);
    }
    function val(q){ return q ? (q.object.id || q.object.value) : null; }
    function lit(q){ return q ? q.object.value : null; }
  }
  async function loadScript(src){
    return new Promise((ok,ko)=>{
      const s=document.createElement('script'); s.src=src; s.onload=ok; s.onerror=ko; document.head.appendChild(s);
    });
  }

  // --- render ---------------------------------------------------------------
  const {maps, runs} = await loadJSONorTTL();

  // populate filters
  const ontos = [...new Set(maps.map(m=>m.target_ns).filter(Boolean))].sort();
  ontos.forEach(ns => { const o=document.createElement('option'); o.value=ns; o.textContent=ns; byId('ontologySel').appendChild(o); });
  runs.forEach(r => { const o=document.createElement('option'); o.value=r.id; o.textContent = runLabel(r); byId('runSel').appendChild(o); });

  const state = { q:'', ns:'', relation:'', run:'', conf:0 };
  byId('q').oninput = e => { state.q = e.target.value.toLowerCase(); draw(); };
  byId('ontologySel').onchange = e => { state.ns = e.target.value; draw(); };
  byId('relationSel').onchange = e => { state.relation = e.target.value; draw(); };
  byId('runSel').onchange = e => { state.run = e.target.value; draw(); };
  byId('confSel').onchange = e => { state.conf = parseFloat(e.target.value||'0'); draw(); };
  byId('closeDetails').onclick = () => byId('details').classList.add('hidden');

  function runLabel(r){
    const t = r.startedAt || r.endedAt || '';
    const when = t ? new Date(t).toISOString().slice(0,19).replace('T',' ') : r.id.split('/').pop();
    const tool = r.used ? (r.used.split('/').pop()) : 'run';
    return `${tool} @ ${when}`;
  }

  function filter(list){
    return list.filter(m => {
      if (state.ns && m.target_ns!==state.ns) return false;
      if (state.relation && pref(m.relation)!==state.relation) return false;
      if (state.run && m.run!==state.run) return false;
      if (state.conf && (m.confidence||0) < state.conf) return false;
      if (state.q) {
        const hay = [m.source,m.target,m.relation,m.rationale].join(' ').toLowerCase();
        if (!hay.includes(state.q)) return false;
      }
      return true;
    });
  }

  function draw(){
    const list = filter(maps);
    $('#summary').innerHTML = `<p>${list.length} mapping(s) shown. ${
      state.ns?`<span class="badge ns">${esc(state.ns)}</span>`:''} ${
      state.run?`<span class="badge run">${esc(runLabel(runs.find(r=>r.id===state.run)||{id:state.run}))}</span>`:''}
    </p>`;
    $('#rows').innerHTML = list.map(m => `
      <tr data-mid="${esc(m.mapping)}">
        <td><a href="${aidocAnchor(m.source)}">${esc(m.source.split('#')[1]||m.source.split('/').pop())}</a></td>
        <td>${pillFor(m.relation)} <code>${esc(pref(m.relation))}</code></td>
        <td><a target="_blank" href="${esc(m.target)}">${esc(m.target)}</a><br>
            <span class="badge ns">${esc(m.target_ns||short(m.target||''))}</span></td>
        <td>${m.confidence!=null ? (m.confidence.toFixed(2)) : '—'}</td>
        <td>${m.run ? esc(runLabel(runs.find(r=>r.id===m.run)||{id:m.run})) : '—'}</td>
      </tr>
    `).join('');

    // row click => open details drawer
    document.querySelectorAll('tbody tr').forEach(tr=>{
      tr.onclick = () => showDetails(tr.getAttribute('data-mid'));
    });
  }

  function pref(iri){
    if (!iri) return '';
    return iri.replace('http://www.w3.org/2004/02/skos/core#','skos:')
              .replace('http://www.w3.org/2002/07/owl#','owl:');
  }

  function showDetails(mid){
    const m = maps.find(x=>x.mapping===mid);
    if(!m) return;
    const run = m.run ? runs.find(r=>r.id===m.run) : null;
    $('#detailsBody').innerHTML = `
      <p><strong>Source (AIDOC):</strong> <a href="${aidocAnchor(m.source)}">${esc(m.source)}</a></p>
      <p><strong>Relation:</strong> <code>${esc(pref(m.relation))}</code> ${pillFor(m.relation)}</p>
      <p><strong>Target:</strong> <a target="_blank" href="${esc(m.target)}">${esc(m.target)}</a></p>
      <p><strong>Confidence:</strong> ${m.confidence!=null?m.confidence:'—'}</p>
      <p><strong>Rationale:</strong><br>${m.rationale?esc(m.rationale):'—'}</p>
      <hr>
      <h3>Provenance (PROV‑O)</h3>
      <p><strong>Agent:</strong> ${m.agent?esc(m.agent):'—'} (prov:wasAttributedTo)</p>
      <p><strong>Run:</strong> ${m.run?esc(m.run):'—'} (prov:wasGeneratedBy)</p>
      ${run?`
        <ul>
          <li><strong>startedAtTime:</strong> ${esc(run.startedAt||'')}</li>
          <li><strong>endedAtTime:</strong> ${esc(run.endedAt||'')}</li>
          <li><strong>used:</strong> ${run.used?`<a target="_blank" href="${esc(run.used)}">${esc(run.used)}</a>`:'—'}</li>
        </ul>
      `:''}
    `;
    byId('details').classList.remove('hidden');
  }

  draw();
})();