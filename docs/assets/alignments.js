(async function(){

  // --- helpers --------------------------------------------------------------
  const $ = sel => document.querySelector(sel);
  const byId = id => document.getElementById(id);
  const esc = s => (s||'').replace(/[&<>"]/g,c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c]));
  const localName = iri => (iri||'').split('#')[1] || (iri||'').split('/').pop();

  const pref = iri => (iri||'')
    .replace('http://www.w3.org/2004/02/skos/core#','skos:')
    .replace('http://www.w3.org/2002/07/owl#','owl:');

  const pillFor = rel => {
    if(!rel) return '';
    if(rel.endsWith('exactMatch')) return `<span class="pill exact">exact</span>`;
    if(rel.endsWith('closeMatch')) return `<span class="pill close">close</span>`;
    if(rel.endsWith('broadMatch')) return `<span class="pill broad">broad</span>`;
    if(rel.endsWith('narrowMatch')) return `<span class="pill narrow">narrow</span>`;
    return `<span class="pill related">related</span>`;
  };

  // vocabulary display name from a "<bucket>-alignments.ttl" file path
  const VOCAB_LABELS = {
    'airo':'AIRO','vair':'VAIR','rains':'RAINS','dpv':'DPV','dpv-ai':'DPV-AI',
    'dpv-aiact':'DPV-AIAct','dpv-tech':'DPV-TECH','mlschema':'MLSchema',
    'ml-onto':'ML-Onto','mex-core':'MEX-Core','prov-o':'PROV-O','mcro':'MCRO'
  };
  const vocabOf = file => {
    const b = file.split('/').pop().replace('-alignments.ttl','');
    return VOCAB_LABELS[b] || b.toUpperCase();
  };

  // --- load data: prefer JSON (build-time), else TTL via manifest -----------
  async function loadJSONorTTL(){
    try {
      const res = await fetch('alignments.json');
      if (res.ok) return await res.json();
    } catch(e){ /* fall through to TTL */ }

    // TTL fallback with N3.js (load lazily); file list from the manifest
    await loadScript('https://unpkg.com/n3@1.17.4/browser/n3.min.js');
    let files = [];
    try {
      const res = await fetch('resources/alignments-manifest.json');
      files = (await res.json()).files || [];
    } catch(e){
      console.error('Could not load resources/alignments-manifest.json');
      return [];
    }

    const RDFT = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type';
    const PROV = 'http://www.w3.org/ns/prov#';
    const ALIGN= 'https://w3id.org/aidoc-ap/alignment#';
    const maps = [];

    for (const file of files) {
      const txt = await (await fetch(file)).text();
      const byS = new Map();
      for (const q of new N3.Parser().parse(txt)) {
        if(!byS.has(q.subject.id)) byS.set(q.subject.id, []);
        byS.get(q.subject.id).push(q);
      }
      const obj = (s,p) => (byS.get(s)||[]).find(q => q.predicate.id===p);
      const val = q => q ? (q.object.id || q.object.value) : null;
      const lit = q => q ? q.object.value : null;

      const started = {};
      for (const [s,qs] of byS)
        if (qs.some(q => q.predicate.id===RDFT && q.object.id===PROV+'Activity'))
          started[s] = lit(obj(s, PROV+'startedAtTime'));

      for (const [s,qs] of byS) {
        if (!qs.some(q => q.predicate.id===RDFT && q.object.id===ALIGN+'Mapping')) continue;
        maps.push({
          mapping: s,
          source: val(obj(s, ALIGN+'source')),
          relation: val(obj(s, ALIGN+'relation')),
          target: val(obj(s, ALIGN+'target')),
          vocab: vocabOf(file),
          outcome: lit(obj(s, ALIGN+'curationOutcome')),
          llm_relation: lit(obj(s, ALIGN+'llmSuggestedRelation')),
          editorial_note: lit(obj(s, ALIGN+'editorialNote')),
          agent: val(obj(s, PROV+'wasAttributedTo')),
          generated_at: started[val(obj(s, PROV+'wasGeneratedBy'))] || null,
          file
        });
      }
    }
    maps.sort((a,b) => (a.vocab+a.source).localeCompare(b.vocab+b.source));
    return maps;
  }
  async function loadScript(src){
    return new Promise((ok,ko)=>{
      const s=document.createElement('script'); s.src=src; s.onload=ok; s.onerror=ko; document.head.appendChild(s);
    });
  }

  // --- render ---------------------------------------------------------------
  const maps = await loadJSONorTTL();

  // stats strip (computed from the loaded data)
  const vocabs = [...new Set(maps.map(m=>m.vocab))].sort();
  const nAccept = maps.filter(m=>m.outcome==='accept').length;
  const nModify = maps.filter(m=>m.outcome==='modify').length;
  $('#stats').innerHTML = `
    <div class="stat"><strong>${maps.length}</strong><span>curated mappings</span></div>
    <div class="stat"><strong>${vocabs.length}</strong><span>target vocabularies</span></div>
    <div class="stat"><strong>${nAccept}</strong><span>accepted as proposed</span></div>
    <div class="stat"><strong>${nModify}</strong><span>relation corrected by curators</span></div>
  `;

  // per-vocabulary TTL download list
  const filesByVocab = new Map();
  maps.forEach(m => filesByVocab.set(m.vocab, m.file));
  byId('ttlList').innerHTML = 'Per vocabulary: ' + [...filesByVocab.entries()]
    .sort((a,b)=>a[0].localeCompare(b[0]))
    .map(([v,f]) => `<a href="${esc(f)}" download>${esc(v)}</a>`)
    .join(' · ');

  // filters
  vocabs.forEach(v => { const o=document.createElement('option'); o.value=v; o.textContent=v; byId('vocabSel').appendChild(o); });

  const state = { q:'', vocab:'', relation:'', outcome:'' };
  byId('q').oninput = e => { state.q = e.target.value.toLowerCase(); draw(); };
  byId('vocabSel').onchange = e => { state.vocab = e.target.value; draw(); };
  byId('relationSel').onchange = e => { state.relation = e.target.value; draw(); };
  byId('outcomeSel').onchange = e => { state.outcome = e.target.value; draw(); };
  byId('closeDetails').onclick = () => byId('details').classList.add('hidden');

  function filter(list){
    return list.filter(m => {
      if (state.vocab && m.vocab!==state.vocab) return false;
      if (state.relation && pref(m.relation)!==state.relation) return false;
      if (state.outcome && m.outcome!==state.outcome) return false;
      if (state.q) {
        const hay = [m.source,m.target,m.relation,m.llm_relation,m.vocab].join(' ').toLowerCase();
        if (!hay.includes(state.q)) return false;
      }
      return true;
    });
  }

  function relationCell(m){
    let html = `${pillFor(m.relation)} <code>${esc(pref(m.relation))}</code>`;
    if (m.outcome==='modify' && m.llm_relation && m.llm_relation!==pref(m.relation))
      html += `<br><span class="muted">corrected from <code>${esc(m.llm_relation)}</code></span>`;
    return html;
  }

  function draw(){
    const list = filter(maps);
    $('#summary').innerHTML = `<p>${list.length} of ${maps.length} mapping(s) shown.${
      state.vocab?` <span class="badge ns">${esc(state.vocab)}</span>`:''}</p>`;
    $('#rows').innerHTML = list.map(m => `
      <tr data-mid="${esc(m.mapping)}">
        <td><a href="${esc(m.source)}">${esc(localName(m.source))}</a></td>
        <td>${relationCell(m)}</td>
        <td><a target="_blank" href="${esc(m.target)}">${esc(m.target)}</a>
            <span class="badge ns">${esc(m.vocab)}</span></td>
        <td><a href="${esc(m.file)}" download title="Curated alignment file (Turtle)">TTL</a></td>
      </tr>
    `).join('');

    // row click => open details drawer (but not when a link was clicked)
    document.querySelectorAll('tbody tr').forEach(tr=>{
      tr.onclick = ev => { if (ev.target.tagName!=='A') showDetails(tr.getAttribute('data-mid')); };
    });
  }

  function showDetails(mid){
    const m = maps.find(x=>x.mapping===mid);
    if(!m) return;
    $('#detailsBody').innerHTML = `
      <p><strong>Source (AIDOC):</strong> <a href="${esc(m.source)}">${esc(m.source)}</a></p>
      <p><strong>Curated relation:</strong> <code>${esc(pref(m.relation))}</code> ${pillFor(m.relation)}</p>
      <p><strong>Target:</strong> <a target="_blank" href="${esc(m.target)}">${esc(m.target)}</a>
         <span class="badge ns">${esc(m.vocab)}</span></p>
      <hr>
      <h3>Curation</h3>
      <p><strong>Outcome:</strong> ${m.outcome==='modify' ? 'relation corrected by curators' : 'accepted as proposed'}</p>
      <p><strong>LLM‑suggested relation:</strong> <code>${esc(m.llm_relation||'—')}</code></p>
      ${m.editorial_note ? `<p class="note"><strong>Editorial note:</strong> ${esc(m.editorial_note)}</p>` : ''}
      <hr>
      <h3>Provenance (PROV‑O)</h3>
      <p><strong>Agent:</strong> ${esc(m.agent||'—')} (prov:wasAttributedTo)</p>
      <p><strong>Generated:</strong> ${m.generated_at ? esc(m.generated_at.slice(0,19).replace('T',' ')) : '—'} (prov:wasGeneratedBy)</p>
      <p><strong>Source file:</strong> <a href="${esc(m.file)}" download>${esc(m.file)}</a></p>
    `;
    byId('details').classList.remove('hidden');
  }

  draw();
})();
