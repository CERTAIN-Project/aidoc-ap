(async function(){

  // --- helpers --------------------------------------------------------------
  const $ = sel => document.querySelector(sel);
  const byId = id => document.getElementById(id);
  const esc = s => (s||'').replace(/[&<>"]/g,c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;' }[c]));

  const coverageClass = score => {
    if (score >= 0.9) return 'high';
    if (score >= 0.8) return 'medium';
    return 'low';
  };

  // --- load data: load from TTL ----------------------------
  async function loadFromTTL(){
    await loadScript('https://unpkg.com/n3@1.17.4/browser/n3.min.js');
    const ttlUrl = window.COVERAGE_TTL || 'resources/semantic_mapping.ttl';
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
    const DQV  = 'http://www.w3.org/ns/dqv#';
    const COV  = 'https://w3id.org/aidoc-ap/coverage#';
    const PROV = 'http://www.w3.org/ns/prov#';

    // Collect runs
    const runMap = {};
    for (const [s,qs] of byS) {
      if (qs.some(q => q.predicate.id===RDF && q.object.id===PROV+'Activity')) {
        const started = obj(byS, s, PROV+'startedAtTime');
        const ended   = obj(byS, s, PROV+'endedAtTime');
        const label   = obj(byS, s, RDFS+'label');
        runMap[s] = { 
          id: s, 
          startedAt: lit(started), 
          endedAt: lit(ended),
          label: lit(label) || s.split('/').pop()
        };
      }
    }

    // Collect measurements
    const measurements = [];
    for (const [s,qs] of byS) {
      if (qs.some(q => q.predicate.id===RDF && q.object.id===DQV+'QualityMeasurement')) {
        const reqUri = val(obj(byS, s, COV+'forRequirement'));
        const reqId = reqUri ? reqUri.split('#')[1] : null;
        const score = obj(byS, s, DQV+'value');
        const reasoning = lit(obj(byS, s, COV+'reasoning'));
        const run = val(obj(byS, s, PROV+'wasGeneratedBy'));
        const agent = val(obj(byS, s, PROV+'wasAttributedTo'));

        // Collect matched terms
        const matchedTerms = [];
        for (const q of qs) {
          if (q.predicate.id === COV+'matchedTerm') {
            const termUri = q.object.id;
            const termLabel = termUri.includes('#') ? termUri.split('#')[1] : termUri.split('/').pop();
            matchedTerms.push(termLabel);
          }
        }

        // Collect missing labels
        const missing = [];
        for (const q of qs) {
          if (q.predicate.id === COV+'missingLabel') {
            missing.push(q.object.value);
          }
        }

        measurements.push({
          measurementUri: s, // Keep the unique measurement URI
          requirement_id: reqId,
          requirement: null, // will load from requirements TTL
          coverage_score: score ? Number(score.object.value) : 0,
          matched_terms: matchedTerms,
          missing: missing,
          reasoning: reasoning || '',
          run: run,
          agent: agent
        });
      }
    }

    return { measurements, runs: Object.values(runMap) };

    // TTL helpers
    function obj(byS, s, p){
      const qs = byS.get(s) || [];
      return qs.find(q => q.predicate.id===p);
    }
    function val(q){ return q ? (q.object.id || q.object.value) : null; }
    function lit(q){ return q ? q.object.value : null; }
  }

  async function loadRequirements(){
    // Load requirement labels from annex_4.ttl
    try {
      await loadScript('https://unpkg.com/n3@1.17.4/browser/n3.min.js');
      const ttlUrl = window.REQUIREMENTS_TTL || 'annex_4.ttl';
      const txt = await (await fetch(ttlUrl, {cache:'no-store'})).text();
      const parser = new N3.Parser();
      const quads = parser.parse(txt);

      const reqMap = {};
      const byS = new Map();
      for (const q of quads) {
        const k = q.subject.id;
        if(!byS.has(k)) byS.set(k, []);
        byS.get(k).push(q);
      }

      const RDFS = 'http://www.w3.org/2000/01/rdf-schema#';
      const DCTERMS = 'http://purl.org/dc/terms/';

      for (const [s,qs] of byS) {
        if (s.includes('#req')) {
          const reqId = s.split('#')[1];
          const label = qs.find(q => q.predicate.id===RDFS+'label');
          const desc = qs.find(q => q.predicate.id===DCTERMS+'description');
          reqMap[reqId] = {
            id: reqId,
            label: label ? label.object.value : reqId,
            description: desc ? desc.object.value : ''
          };
        }
      }
      return reqMap;
    } catch(e) {
      console.error('Failed to load requirements:', e);
      return {};
    }
  }

  async function loadScript(src){
    return new Promise((ok,ko)=>{
      const s=document.createElement('script'); s.src=src; s.onload=ok; s.onerror=ko; document.head.appendChild(s);
    });
  }

  // --- render ---------------------------------------------------------------
  const [coverageData, reqMap] = await Promise.all([loadFromTTL(), loadRequirements()]);
  const {measurements, runs} = coverageData;

  // Enrich measurements with requirement labels
  measurements.forEach(m => {
    if (reqMap[m.requirement_id]) {
      m.requirement = reqMap[m.requirement_id].label;
      m.requirement_description = reqMap[m.requirement_id].description;
    } else {
      m.requirement = m.requirement_id;
    }
  });

  // Group measurements by run - if no run filter selected, use the most recent for each requirement
  const measurementsByRun = {};
  const latestMeasurements = {};
  
  measurements.forEach(m => {
    if (!measurementsByRun[m.run]) {
      measurementsByRun[m.run] = [];
    }
    measurementsByRun[m.run].push(m);
    
    // Track latest measurement per requirement (for default view)
    if (!latestMeasurements[m.requirement_id] || 
        (m.run > latestMeasurements[m.requirement_id].run)) {
      latestMeasurements[m.requirement_id] = m;
    }
  });

  // Sort runs by date (newest first)
  runs.sort((a, b) => {
    const dateA = a.startedAt || a.id;
    const dateB = b.startedAt || b.id;
    return dateB.localeCompare(dateA);
  });

  // Sort runs by date (newest first)
  runs.sort((a, b) => {
    const dateA = a.startedAt || a.id;
    const dateB = b.startedAt || b.id;
    return dateB.localeCompare(dateA);
  });

  // Populate run filter
  runs.forEach(r => { 
    const o=document.createElement('option'); 
    o.value=r.id; 
    const date = r.startedAt ? r.startedAt.split('T')[0] : '';
    const agentLabel = r.label ? r.label.replace('LLM Coverage Analysis using ', '') : r.id.split('/').pop();
    o.textContent = date ? `${date} (${agentLabel})` : agentLabel; 
    byId('runSel').appendChild(o); 
  });

  // Get active measurement set based on selected run
  function getActiveMeasurements() {
    if (state.run) {
      // Filter by selected run
      return measurements.filter(m => m.run === state.run);
    } else {
      // Use latest measurement for each requirement
      return Object.values(latestMeasurements);
    }
  }

  // Calculate stats based on active measurements
  const activeMeasurements = getActiveMeasurements();
  const totalReqs = activeMeasurements.length;
  // Calculate stats based on active measurements
  const activeMeasurements = getActiveMeasurements();
  const totalReqs = activeMeasurements.length;
  const avgCoverage = activeMeasurements.reduce((sum, m) => sum + m.coverage_score, 0) / totalReqs;
  const excellentCount = activeMeasurements.filter(m => m.coverage_score >= 0.9).length;
  const goodCount = activeMeasurements.filter(m => m.coverage_score >= 0.85 && m.coverage_score < 0.9).length;

  function updateStats() {
    const active = getActiveMeasurements();
    const total = active.length;
    const avg = active.reduce((sum, m) => sum + m.coverage_score, 0) / total;
    const excellent = active.filter(m => m.coverage_score >= 0.9).length;
    const good = active.filter(m => m.coverage_score >= 0.85 && m.coverage_score < 0.9).length;

    byId('stats').innerHTML = `
      <div class="stat-card">
        <h3>${total}</h3>
        <p>Total Requirements</p>
      </div>
      <div class="stat-card">
        <h3>${(avg * 100).toFixed(1)}%</h3>
        <p>Average Coverage</p>
      </div>
      <div class="stat-card">
        <h3>${excellent}</h3>
        <p>Excellent (≥ 0.90)</p>
      </div>
      <div class="stat-card">
        <h3>${good}</h3>
        <p>Good (0.85-0.89)</p>
      </div>
    `;

    // Overall coverage bar
    const overallClass = coverageClass(avg);
    byId('overallBar').className = `coverage-fill ${overallClass}`;
    byId('overallBar').style.width = `${avg * 100}%`;
    byId('overallText').textContent = `${(avg * 100).toFixed(1)}%`;
  }

  updateStats();

  // State management
  const state = { q:'', coverage:'', run:'' };
  byId('q').oninput = e => { state.q = e.target.value.toLowerCase(); draw(); };
  byId('coverageSel').onchange = e => { state.coverage = e.target.value; draw(); };
  byId('runSel').onchange = e => { 
    state.run = e.target.value; 
    updateStats(); 
    draw(); 
  };
  byId('closeDetails').onclick = () => byId('details').classList.add('hidden');

  function filter(list){
    return list.filter(m => {
      if (state.coverage) {
        const threshold = parseFloat(state.coverage);
        if (state.coverage === '0.5') {
          if (m.coverage_score >= 0.85) return false;
        } else {
          if (m.coverage_score < threshold) return false;
        }
      }
      if (state.q) {
        const hay = [
          m.requirement, 
          m.requirement_id,
          m.reasoning,
          ...(m.matched_terms || []),
          ...(m.missing || [])
        ].join(' ').toLowerCase();
        if (!hay.includes(state.q)) return false;
      }
      return true;
    });
  }

  function draw(){
    const active = getActiveMeasurements();
    const list = filter(active);
    const totalInView = active.length;
    $('#summary').innerHTML = `<p>${list.length} of ${totalInView} requirement(s) shown.</p>`;
    
    // Sort by requirement number
    list.sort((a, b) => {
      const numA = parseInt(a.requirement_id.replace('req', ''));
      const numB = parseInt(b.requirement_id.replace('req', ''));
      return numA - numB;
    });
    
    $('#rows').innerHTML = list.map((m, idx) => {
      const reqNum = parseInt(m.requirement_id.replace('req', ''));
      const scoreClass = coverageClass(m.coverage_score);
      const matchedPreview = (m.matched_terms || []).slice(0, 3).map(t => 
        `<span class="term-badge">${esc(t)}</span>`
      ).join('');
      const matchedMore = (m.matched_terms || []).length > 3 ? 
        ` <span class="term-badge">+${(m.matched_terms || []).length - 3} more</span>` : '';
      
      const missingPreview = (m.missing || []).slice(0, 2).map(t => 
        `<span class="missing-badge">${esc(t)}</span>`
      ).join('');
      const missingMore = (m.missing || []).length > 2 ? 
        ` <span class="missing-badge">+${(m.missing || []).length - 2} more</span>` : '';

      return `
        <tr class="requirement-row" data-measurementid="${esc(m.measurementUri)}">
          <td>${reqNum}</td>
          <td><strong>${esc(m.requirement || m.requirement_id)}</strong></td>
          <td>
            <span class="coverage-score ${scoreClass}">${(m.coverage_score * 100).toFixed(0)}%</span>
            <div class="coverage-bar" style="margin-top:4px; height:6px;">
              <div class="coverage-fill ${scoreClass}" style="width:${m.coverage_score * 100}%"></div>
            </div>
          </td>
          <td>${matchedPreview}${matchedMore}</td>
          <td>${missingPreview}${missingMore}</td>
        </tr>
      `;
    }).join('');

    // Row click => open details
    document.querySelectorAll('tbody tr').forEach(tr=>{
      tr.onclick = () => showDetails(tr.getAttribute('data-measurementid'));
    });
  }

  function showDetails(measurementUri){
    const m = measurements.find(x => x.measurementUri === measurementUri);
    if(!m) return;

    const run = m.run ? runs.find(r => r.id === m.run) : null;
    const scoreClass = coverageClass(m.coverage_score);

    const matchedHtml = (m.matched_terms || []).map(t => {
      // Try to link to ontology term
      const termUri = `https://w3id.org/aidoc-ap#${t.replace(/ /g, '_')}`;
      return `<span class="term-badge"><a href="${esc(termUri)}" style="color:inherit">${esc(t)}</a></span>`;
    }).join(' ');

    const missingHtml = (m.missing || []).map(t => 
      `<span class="missing-badge">${esc(t)}</span>`
    ).join(' ');

    byId('detailsBody').innerHTML = `
      <h3>${esc(m.requirement || m.requirement_id)}</h3>
      ${m.requirement_description ? `<p style="color: var(--muted); font-style: italic;">${esc(m.requirement_description)}</p>` : ''}
      
      <div style="margin: 20px 0;">
        <h4>Coverage Score</h4>
        <div class="coverage-bar">
          <div class="coverage-fill ${scoreClass}" style="width:${m.coverage_score * 100}%"></div>
          <div class="coverage-text">${(m.coverage_score * 100).toFixed(1)}%</div>
        </div>
      </div>

      <div style="margin: 20px 0;">
        <h4>Reasoning</h4>
        <p>${m.reasoning ? esc(m.reasoning) : '—'}</p>
      </div>

      <div style="margin: 20px 0;">
        <h4>Matched AIDOC Terms (${(m.matched_terms || []).length})</h4>
        <div>${matchedHtml || '<p style="color: var(--muted);">No matched terms</p>'}</div>
      </div>

      <div style="margin: 20px 0;">
        <h4>Missing Concepts (${(m.missing || []).length})</h4>
        <div>${missingHtml || '<p style="color: var(--muted);">No missing concepts identified</p>'}</div>
      </div>

      <hr>
      <h4>Provenance (PROV‑O)</h4>
      ${m.agent ? `<p><strong>Agent:</strong> ${esc(m.agent)}</p>` : ''}
      ${m.run ? `<p><strong>Run:</strong> ${esc(m.run)}</p>` : ''}
      ${run ? `
        <ul>
          <li><strong>Started:</strong> ${esc(run.startedAt||'—')}</li>
          <li><strong>Ended:</strong> ${esc(run.endedAt||'—')}</li>
          <li><strong>Label:</strong> ${esc(run.label||'—')}</li>
        </ul>
      ` : ''}
    `;
    byId('details').classList.remove('hidden');
  }

  draw();
})();
