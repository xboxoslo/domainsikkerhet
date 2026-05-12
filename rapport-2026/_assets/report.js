'use strict';
/* Shared analyzer for all /rapport-2026/* sub-reports.
 * Page must define window.REPORT_CONFIG = { slug, domains: [...] }
 * before this script runs.
 */
(function () {
  const cfg = window.REPORT_CONFIG;
  if (!cfg || !Array.isArray(cfg.domains) || !cfg.slug) {
    console.error('Missing REPORT_CONFIG');
    return;
  }
  const DKIM_SELECTORS = ["selector1","selector2","google","k1","k2","mail","default","dkim","s1","s2","mxvault","fm1","fm2","fm3"];
  const DOH = 'https://cloudflare-dns.com/dns-query';
  const CACHE_KEY = 'data1-' + cfg.slug + '-v1';
  const CACHE_HOURS = 6;

  async function dohQuery(name, type) {
    try {
      const r = await fetch(DOH + '?name=' + encodeURIComponent(name) + '&type=' + type, {
        headers: { Accept: 'application/dns-json' }, signal: AbortSignal.timeout(7000)
      });
      if (!r.ok) return [];
      return (await r.json()).Answer || [];
    } catch { return []; }
  }
  const clean = s => (s||'').replace(/^"|"$/g,'').replace(/"\s*"/g,'').trim();
  function findRec(arr, prefix) {
    for (const a of arr) {
      const d = clean(a.data);
      if (d.toLowerCase().startsWith(prefix.toLowerCase())) return d;
    }
    return null;
  }
  async function findDkim(domain) {
    const probes = DKIM_SELECTORS.map(sel => dohQuery(sel + '._domainkey.' + domain, 'TXT').then(ans => {
      for (const a of ans) {
        if (clean(a.data).toLowerCase().startsWith('v=dkim1')) return sel;
      }
      return null;
    }));
    const out = await Promise.all(probes);
    return out.find(Boolean) || null;
  }
  async function analyze(domain) {
    const [txt, dmarcA, mtaA, tlsA, bimiA] = await Promise.all([
      dohQuery(domain, 'TXT'),
      dohQuery('_dmarc.' + domain, 'TXT'),
      dohQuery('_mta-sts.' + domain, 'TXT'),
      dohQuery('_smtp._tls.' + domain, 'TXT'),
      dohQuery('default._bimi.' + domain, 'TXT'),
    ]);
    const spf = findRec(txt, 'v=spf1');
    const dmarc = findRec(dmarcA, 'v=DMARC1');
    const mta = findRec(mtaA, 'v=STSv1');
    const tls = findRec(tlsA, 'v=TLSRPTv1');
    const bimi = findRec(bimiA, 'v=BIMI1');
    const dkim = await findDkim(domain);

    let score = 0, dmarc_p = null;
    if (dmarc) {
      const m = dmarc.match(/p=([a-z]+)/i);
      if (m) dmarc_p = m[1].toLowerCase();
      if (dmarc_p === 'reject') score += 35;
      else if (dmarc_p === 'quarantine') score += 22;
      else if (dmarc_p === 'none') score += 8;
    }
    if (spf) score += /[-~]all\b/.test(spf) ? 25 : 10;
    if (dkim) score += 20;
    if (mta) score += 12;
    if (tls) score += 5;
    if (bimi) score += 3;
    let grade;
    if (score >= 90) grade='A+'; else if (score>=80) grade='A'; else if (score>=70) grade='B';
    else if (score>=55) grade='C'; else if (score>=35) grade='D'; else grade='F';
    return { domain, score, grade, dmarc:!!dmarc, dmarc_p, spf:!!spf, dkim:!!dkim, mta_sts:!!mta, tls_rpt:!!tls, bimi:!!bimi };
  }

  function loadCache() {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      const obj = JSON.parse(raw);
      if ((Date.now() - obj.savedAt) / 1000 / 3600 > CACHE_HOURS) return null;
      return obj.results;
    } catch { return null; }
  }
  function saveCache(results) {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify({ savedAt: Date.now(), results })); } catch {}
  }

  function gradeClass(g) { return ({'A+':'gl-ap','A':'gl-a','B':'gl-b','C':'gl-c','D':'gl-d','F':'gl-f'})[g] || 'gl-f'; }
  function check(v) { return v ? '<span class="check">✓</span>' : '<span class="cross">✗</span>'; }
  function htmlEscape(s) { return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

  let currentResults = null;
  let currentFilter = 'all';

  async function runAll() {
    const cached = loadCache();
    if (cached) { renderAll(cached); return; }
    const results = [];
    let done = 0;
    const queue = [...cfg.domains];
    const updateProg = current => {
      const pct = (done / cfg.domains.length) * 100;
      document.getElementById('progressFill').style.width = pct + '%';
      document.getElementById('progressMeta').textContent =
        done + ' av ' + cfg.domains.length + ' ferdig' + (current ? ' · sjekker ' + current : '');
    };
    updateProg();
    const workers = Array(8).fill(0).map(async () => {
      while (queue.length) {
        const d = queue.shift();
        if (!d) break;
        try { results.push(await analyze(d)); }
        catch { results.push({ domain: d, score: 0, grade: 'F', dmarc:false, dmarc_p:null, spf:false, dkim:false, mta_sts:false, tls_rpt:false, bimi:false }); }
        done++;
        updateProg(d);
      }
    });
    await Promise.all(workers);
    saveCache(results);
    renderAll(results);
  }

  function renderAll(results) {
    currentResults = results;
    document.getElementById('progressCard').hidden = true;
    document.getElementById('summary').hidden = false;
    document.getElementById('gradeBars').hidden = false;
    document.getElementById('controls').hidden = false;
    document.getElementById('rankWrap').hidden = false;
    const upd = document.getElementById('lastUpdate');
    if (upd) upd.textContent = new Date().toLocaleString('no-NO');
    renderSummary(results);
    renderGradeBars(results);
    renderTable(results);
  }

  function renderSummary(results) {
    const total = results.length;
    const avg = Math.round(results.reduce((s, r) => s + r.score, 0) / total);
    const noDmarc = results.filter(r => !r.dmarc).length;
    const weakDmarc = results.filter(r => r.dmarc_p === 'none').length;
    const enforce = results.filter(r => r.dmarc_p === 'reject' || r.dmarc_p === 'quarantine').length;
    const failing = results.filter(r => r.grade === 'F').length;
    const aGrade = results.filter(r => r.grade === 'A+' || r.grade === 'A').length;
    const stats = [
      [avg + '%', 'Snittscore'],
      [noDmarc, 'Uten DMARC'],
      [weakDmarc, 'DMARC p=none (kun overvåking)'],
      [enforce, 'Håndhever DMARC'],
      [failing, 'Karakter F'],
      [aGrade, 'Karakter A / A+'],
    ];
    document.getElementById('summary').innerHTML = stats.map(([n, l]) =>
      '<div class="stat"><div class="stat-num">' + n + '</div><div class="stat-label">' + l + '</div></div>'
    ).join('');
  }

  function renderGradeBars(results) {
    const total = results.length;
    const counts = { 'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0 };
    results.forEach(r => counts[r.grade]++);
    const html = ['A+', 'A', 'B', 'C', 'D', 'F'].map(g => {
      const pct = (counts[g] / total) * 100;
      return '<div class="gb-row"><span class="gb-label">' + g + '</span><div class="gb-bar"><div class="gb-fill ' + gradeClass(g) + '" style="width:' + pct.toFixed(1) + '%"></div></div><span class="gb-count">' + counts[g] + ' (' + pct.toFixed(0) + '%)</span></div>';
    }).join('');
    document.getElementById('gradeBars').innerHTML = '<h2>Karakterfordeling</h2>' + html;
    const allBtn = document.querySelector('.controls button[data-filter="all"]');
    const enforceBtn = document.querySelector('.controls button[data-filter="enforce"]');
    const failingBtn = document.querySelector('.controls button[data-filter="failing"]');
    const missBtn = document.querySelector('.controls button[data-filter="missing-dmarc"]');
    if (allBtn) allBtn.textContent = 'Alle (' + total + ')';
    if (enforceBtn) enforceBtn.textContent = 'Håndhever DMARC (' + results.filter(r => r.dmarc_p === 'reject' || r.dmarc_p === 'quarantine').length + ')';
    if (failingBtn) failingBtn.textContent = 'Karakter F (' + counts['F'] + ')';
    if (missBtn) missBtn.textContent = 'Mangler DMARC (' + results.filter(r => !r.dmarc).length + ')';
  }

  function renderTable(results) {
    let filtered = results.slice();
    if (currentFilter === 'enforce') filtered = filtered.filter(r => r.dmarc_p === 'reject' || r.dmarc_p === 'quarantine');
    else if (currentFilter === 'failing') filtered = filtered.filter(r => r.grade === 'F');
    else if (currentFilter === 'missing-dmarc') filtered = filtered.filter(r => !r.dmarc);
    filtered.sort((a, b) => b.score - a.score || a.domain.localeCompare(b.domain));
    document.getElementById('rankBody').innerHTML = filtered.map((r, i) =>
      '<tr><td class="rank">' + (i + 1) + '</td>' +
      '<td><a href="/sjekk/' + encodeURIComponent(r.domain) + '/">' + htmlEscape(r.domain) + '</a></td>' +
      '<td><span class="grade-pill ' + gradeClass(r.grade) + '">' + r.grade + '</span></td>' +
      '<td class="score">' + r.score + '%</td>' +
      '<td>' + check(r.dmarc) + '<span class="muted">' + (r.dmarc_p || '') + '</span></td>' +
      '<td>' + check(r.spf) + '</td>' +
      '<td>' + check(r.dkim) + '</td>' +
      '<td>' + check(r.mta_sts) + '</td>' +
      '<td>' + check(r.tls_rpt) + '</td>' +
      '<td>' + check(r.bimi) + '</td></tr>'
    ).join('');
  }

  document.querySelectorAll('.controls button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.controls button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      if (currentResults) renderTable(currentResults);
    });
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runAll);
  } else {
    runAll();
  }
})();
