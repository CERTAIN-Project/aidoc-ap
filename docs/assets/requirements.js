(async function(){

  // --- helpers --------------------------------------------------------------
  const $ = sel => document.querySelector(sel);
  const byId = id => document.getElementById(id);
  const esc = s => (s||'').replace(/[&<>"]/g,c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c]));

  // --- load data ------------------------------------------------------------
  async function loadRequirements(){
    await loadScript('https://unpkg.com/n3@1.17.4/browser/n3.min.js');
    const ttlUrl = window.REQUIREMENTS_TTL || 'annex_4.ttl';
    const txt = await (await fetch(ttlUrl, {cache:'no-store'})).text();
    const parser = new N3.Parser();
    const quads = parser.parse(txt);

    // Index quads by subject
    const byS = new Map();
    for (const q of quads) {
      const k = q.subject.id;
      if(!byS.has(k)) byS.set(k, []);
      byS.get(k).push(q);
    }

    const RDF  = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type';
    const RDFS = 'http://www.w3.org/2000/01/rdf-schema#';
    const DCTERMS = 'http://purl.org/dc/terms/';
    const AIACT = 'https://w3id.org/aidoc-ap/requirements#';

    const requirements = [];
    const cqMap = new Map(); // map CQ URIs to labels

    // First pass: collect all competency questions
    for (const [s,qs] of byS) {
      if (qs.some(q => q.predicate.id===RDF && q.object.id===AIACT+'CompetencyQuestion')) {
        const label = obj(byS, s, RDFS+'label');
        if (label) {
          cqMap.set(s, lit(label));
        }
      }
    }

    // Second pass: collect requirements
    for (const [s,qs] of byS) {
      if (qs.some(q => q.predicate.id===RDF && q.object.id===AIACT+'Requirement')) {
        const reqId = s.split('#')[1];
        if (!reqId || !reqId.startsWith('req')) continue; // skip non-req URIs
        
        const label = lit(obj(byS, s, RDFS+'label'));
        const desc = lit(obj(byS, s, DCTERMS+'description'));
        const stage = lit(obj(byS, s, AIACT+'aiLifecycleStage'));
        const source = lit(obj(byS, s, DCTERMS+'source'));
        
        // Collect all competency questions
        const cqs = [];
        for (const q of qs) {
          if (q.predicate.id === AIACT+'hasCompetencyQuestion') {
            const cqUri = q.object.id;
            const cqLabel = cqMap.get(cqUri);
            if (cqLabel) {
              cqs.push(cqLabel);
            }
          }
        }

        requirements.push({
          id: reqId,
          uri: s,
          label: label || reqId,
          description: desc || '',
          lifecycleStage: stage || 'Not specified',
          source: source || '',
          competencyQuestions: cqs
        });
      }
    }

    // Sort by requirement number
    requirements.sort((a, b) => {
      const numA = parseInt(a.id.replace('req', ''));
      const numB = parseInt(b.id.replace('req', ''));
      return numA - numB;
    });

    return requirements;

    // TTL helpers
    function obj(byS, s, p){
      const qs = byS.get(s) || [];
      return qs.find(q => q.predicate.id===p);
    }
    function lit(q){ return q ? q.object.value : null; }
  }

  async function loadScript(src){
    return new Promise((ok,ko)=>{
      const s=document.createElement('script'); s.src=src; s.onload=ok; s.onerror=ko; document.head.appendChild(s);
    });
  }

  // --- render ---------------------------------------------------------------
  const requirements = await loadRequirements();

  // Populate lifecycle stage filter
  const stages = [...new Set(requirements.map(r => r.lifecycleStage))].sort();
  stages.forEach(stage => { 
    const o=document.createElement('option'); 
    o.value=stage; 
    o.textContent=stage; 
    byId('stageSel').appendChild(o); 
  });

  // State management
  const state = { q:'', stage:'' };
  byId('q').oninput = e => { state.q = e.target.value.toLowerCase(); draw(); };
  byId('stageSel').onchange = e => { state.stage = e.target.value; draw(); };
  byId('closeDetails').onclick = () => byId('details').classList.add('hidden');

  function filter(list){
    return list.filter(r => {
      if (state.stage && r.lifecycleStage !== state.stage) return false;
      if (state.q) {
        const hay = [
          r.label, 
          r.description, 
          r.lifecycleStage,
          ...(r.competencyQuestions || [])
        ].join(' ').toLowerCase();
        if (!hay.includes(state.q)) return false;
      }
      return true;
    });
  }

  function draw(){
    const list = filter(requirements);
    const totalReqs = requirements.length;
    
    $('#summary').innerHTML = `<p>${list.length} of ${totalReqs} requirement(s) shown.</p>`;
    
    $('#rows').innerHTML = list.map(r => {
      const reqNum = parseInt(r.id.replace('req', ''));
      const cqCount = (r.competencyQuestions || []).length;
      const stageShort = r.lifecycleStage.length > 40 
        ? r.lifecycleStage.substring(0, 37) + '…' 
        : r.lifecycleStage;

      return `
        <tr class="requirement-row" data-reqid="${esc(r.id)}">
          <td><strong>${reqNum}</strong></td>
          <td>${esc(r.label)}</td>
          <td>${esc(r.description.substring(0, 150))}${r.description.length > 150 ? '…' : ''}</td>
          <td><span class="badge ns">${esc(stageShort)}</span></td>
          <td>${cqCount}</td>
        </tr>
      `;
    }).join('');

    // Row click => open details
    document.querySelectorAll('tbody tr').forEach(tr=>{
      tr.onclick = () => showDetails(tr.getAttribute('data-reqid'));
    });
  }

  function showDetails(reqId){
    const r = requirements.find(x => x.id === reqId);
    if(!r) return;

    const reqNum = parseInt(r.id.replace('req', ''));
    const euActUrl = 'https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-4';

    const cqsHtml = (r.competencyQuestions || []).map(cq => 
      `<li>${esc(cq)}</li>`
    ).join('');

    byId('detailsBody').innerHTML = `
      <h3>${reqNum}. ${esc(r.label)}</h3>
      
      <div style="margin: 20px 0;">
        <h4>Description</h4>
        <p>${esc(r.description)}</p>
      </div>

      <div style="margin: 20px 0;">
        <h4>AI Lifecycle Stage</h4>
        <p><span class="badge ns">${esc(r.lifecycleStage)}</span></p>
      </div>

      <div style="margin: 20px 0;">
        <h4>Competency Questions (${(r.competencyQuestions || []).length})</h4>
        ${cqsHtml ? `<ul>${cqsHtml}</ul>` : '<p style="color: var(--muted);">No competency questions defined</p>'}
      </div>

      <hr>
      <h4>Source</h4>
      <p><strong>URI:</strong> <code>${esc(r.uri)}</code></p>
      ${r.source ? `<p><strong>Reference:</strong> ${esc(r.source)}</p>` : ''}
      <p><strong>Official Text:</strong> <a target="_blank" href="${euActUrl}">EU AI Act 2024/1689, Annex IV →</a></p>
    `;
    byId('details').classList.remove('hidden');
  }

  draw();
})();
