/**
 * Cloudflare Worker — Domain Analyzer Intake
 *
 * Mottar POST fra domain-analyzer.html med kontaktinfo + score,
 * 1) sender HTML-rapport via Mailgun
 * 2) oppretter ticket i Halo PSA (service.micronet.no) tagget med domene
 *
 * Deploy:
 *   1. wrangler init  (eller bruk Cloudflare-dashboardet > Workers > Create)
 *   2. Sett secrets:
 *        wrangler secret put MAILGUN_API_KEY
 *        wrangler secret put HALO_CLIENT_ID
 *        wrangler secret put HALO_CLIENT_SECRET
 *   3. Deploy:  wrangler deploy
 *   4. Sett INTAKE_ENDPOINT i domain-analyzer.html til Worker-URL-en
 */

const HALO_BASE         = 'https://service.micronet.no';
const HALO_TOKEN_URL    = `${HALO_BASE}/auth/token`;
const HALO_API_URL      = `${HALO_BASE}/api`;
const HALO_TICKET_TYPE  = 'EasyDMARC';      // navn — ID slås opp + caches

let _ticketTypeId = null;                   // cache mellom requests innen samme isolate

const MAILGUN_DOMAIN  = 'micronet.no';
const MAILGUN_REGION  = 'eu';
const MAILGUN_FROM    = 'DomainSikkerhet <noreply@micronet.no>';

const ALLOWED_ORIGINS = [
    'https://data1.no',                              // ← prod-domene (Cloudflare Pages)
    'https://www.data1.no',                          // ← med www-subdomene
    'https://domain-analyzer.micronet.no',           // ← legacy prod-domene (DigitalOcean)
    'https://domeneanalyse.micronet.no',             // alt navn
    'http://localhost:3000',                         // dev (lokal preview)
    'http://127.0.0.1:3000',
];

const CORS_HEADERS = origin => ({
    'Access-Control-Allow-Origin': ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0],
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
});

export default {
    async fetch(request, env) {
        const origin = request.headers.get('Origin') || '';
        const cors = CORS_HEADERS(origin);

        if (request.method === 'OPTIONS') return new Response(null, { headers: cors });
        if (request.method !== 'POST')    return new Response('Method not allowed', { status: 405, headers: cors });

        let body;
        try { body = await request.json(); }
        catch { return json({ error: 'Invalid JSON' }, 400, cors); }

        // Validate required fields
        const { name, email, domain } = body;
        if (!name || !email || !domain) return json({ error: 'Mangler navn/email/domain' }, 400, cors);
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return json({ error: 'Ugyldig e-post' }, 400, cors);

        const clientIp = request.headers.get('CF-Connecting-IP')
            || (request.headers.get('X-Forwarded-For') || '').split(',')[0].trim()
            || '';
        const ts = await verifyTurnstile(body.turnstileToken, clientIp, env);
        if (!ts.ok) return json({ error: 'Bot-beskyttelse feilet. Last siden på nytt og prøv igjen.' }, 403, cors);

        try {
            const [haloResult, mailResult] = await Promise.allSettled([
                createHaloTicket(body, env),
                sendMailgunReport(body, env),
            ]);

            return json({
                ok: true,
                halo: haloResult.status === 'fulfilled' ? haloResult.value : { error: String(haloResult.reason) },
                mail: mailResult.status === 'fulfilled' ? mailResult.value : { error: String(mailResult.reason) },
            }, 200, cors);
        } catch (err) {
            return json({ error: err.message }, 500, cors);
        }
    },
};

/* ─────── Cloudflare Turnstile ─────── */
async function verifyTurnstile(token, remoteIp, env) {
    if (!env.TURNSTILE_SECRET) return { ok: true, reason: 'turnstile-disabled' };
    if (!token) return { ok: false, reason: 'missing-token' };
    const form = new URLSearchParams({ secret: env.TURNSTILE_SECRET, response: token });
    if (remoteIp) form.set('remoteip', remoteIp);
    try {
        const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: form,
        });
        if (!r.ok) return { ok: false, reason: `siteverify-http-${r.status}` };
        const data = await r.json();
        if (data.success) return { ok: true, reason: 'ok' };
        return { ok: false, reason: (data['error-codes'] || ['unknown']).join(',') };
    } catch (e) {
        return { ok: false, reason: `siteverify-error-${e.message}` };
    }
}

/* ─────── Halo PSA ─────── */
async function getHaloToken(env) {
    const params = new URLSearchParams({
        grant_type:    'client_credentials',
        client_id:     env.HALO_CLIENT_ID,
        client_secret: env.HALO_CLIENT_SECRET,
        scope:         'all',
    });
    const res = await fetch(HALO_TOKEN_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params,
    });
    if (!res.ok) throw new Error(`Halo auth feilet: ${res.status} ${await res.text()}`);
    const json = await res.json();
    return json.access_token;
}

async function getTicketTypeId(token) {
    if (_ticketTypeId) return _ticketTypeId;
    const res = await fetch(`${HALO_API_URL}/TicketType`, {
        headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`Halo TicketType lookup feilet: ${res.status}`);
    const data = await res.json();
    const list = Array.isArray(data) ? data : (data.tickettypes || data.value || []);
    const match = list.find(t => (t.name || '').toLowerCase() === HALO_TICKET_TYPE.toLowerCase());
    if (!match) throw new Error(`Fant ikke ticket-type "${HALO_TICKET_TYPE}" i Halo`);
    _ticketTypeId = match.id;
    return _ticketTypeId;
}

async function createHaloTicket(b, env) {
    const token = await getHaloToken(env);
    const tickettype_id = await getTicketTypeId(token);

    const summary = `Domeneanalyse: ${b.domain} (${b.grade ?? '?'} / ${b.score ?? '?'}%)`;
    const details = [
        `Kontakt:  ${b.name}`,
        `Firma:    ${b.company || '(ikke oppgitt)'}`,
        `Org.nr:   ${b.orgnr || '(ikke oppgitt)'}`,
        `E-post:   ${b.email}`,
        `Telefon:  ${b.phone || '(ikke oppgitt)'}`,
        `Domene:   ${b.domain}`,
        `Score:    ${b.score ?? '?'}% (${b.grade ?? '?'})`,
        `Rapport:  ${b.reportUrl || ''}`,
        '',
        '— Melding fra kunde —',
        b.message || '(ingen)',
    ].join('\n');

    const ticket = [{
        summary,
        details,
        tickettype_id,
        category_1: 'Domeneanalyse',
        tags: [
            { text: 'domeneanalyse' },
            { text: `domene:${b.domain}` },
            { text: `score:${b.score ?? 'na'}` },
            { text: `karakter:${b.grade ?? 'na'}` },
            { text: 'kilde:domain-analyzer' },
            ...(b.orgnr ? [{ text: `orgnr:${b.orgnr}` }] : []),
        ],
        // Ny kontakt opprettes hvis e-post ikke matcher eksisterende
        userlookup: { email: b.email, name: b.name, phone: b.phone || '' },
    }];

    const res = await fetch(`${HALO_API_URL}/Tickets`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type':  'application/json',
        },
        body: JSON.stringify(ticket),
    });
    if (!res.ok) throw new Error(`Halo ticket feilet: ${res.status} ${await res.text()}`);
    const result = await res.json();
    return { ticketId: result?.[0]?.id ?? result?.id ?? null };
}

/* ─────── Mailgun ─────── */
async function sendMailgunReport(b, env) {
    const endpoint = MAILGUN_REGION === 'eu'
        ? `https://api.eu.mailgun.net/v3/${MAILGUN_DOMAIN}/messages`
        : `https://api.mailgun.net/v3/${MAILGUN_DOMAIN}/messages`;

    const html = renderEmailHTML(b);
    const text = `Hei ${b.name},\n\nDin domeneanalyse for ${b.domain}:\n` +
                 `Score: ${b.score ?? '?'}% (${b.grade ?? '?'})\n\n` +
                 `Full rapport: ${b.reportUrl}\n\nMicronet`;

    const form = new FormData();
    form.append('from',    MAILGUN_FROM);
    form.append('to',      `${b.name} <${b.email}>`);
    form.append('subject', `Domeneanalyse: ${b.domain} — ${b.grade ?? ''}`);
    form.append('text',    text);
    form.append('html',    html);
    form.append('h:Reply-To', 'hjelp@micronet.no');

    const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Authorization': 'Basic ' + btoa('api:' + env.MAILGUN_API_KEY) },
        body: form,
    });
    if (!res.ok) throw new Error(`Mailgun feilet: ${res.status} ${await res.text()}`);
    return await res.json();
}

/* ─────── HTML email template ─────── */
function renderEmailHTML(b) {
    const grade = esc(b.grade ?? '?');
    const score = b.score ?? '?';
    const color = score >= 90 ? '#2f855a'
                : score >= 70 ? '#48916b'
                : score >= 35 ? '#c05621'
                : '#c53030';
    return `<!doctype html><html><body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,Segoe UI,sans-serif;color:#0f172a">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 12px">
  <tr><td align="center">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06)">
      <tr><td style="background:#0f172a;padding:22px 28px">
        <div style="color:white;font-size:18px;font-weight:800">Domain<span style="color:#4fd1c5">Sikkerhet</span></div>
      </td></tr>
      <tr><td style="padding:32px 28px">
        <h1 style="font-size:24px;margin:0 0 8px;letter-spacing:-.02em">Hei ${esc(b.name)},</h1>
        <p style="color:#475569;margin:0 0 24px;line-height:1.55">Her er e-postsikkerhetsrapporten for <strong>${esc(b.domain)}</strong>.</p>
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:20px;display:flex;align-items:center;gap:18px">
          <div style="width:64px;height:64px;border-radius:50%;background:${color};color:white;font-size:22px;font-weight:900;display:flex;align-items:center;justify-content:center;flex-shrink:0">${grade}</div>
          <div>
            <div style="font-size:13px;color:#64748b;text-transform:uppercase;letter-spacing:.04em;font-weight:700">Score</div>
            <div style="font-size:32px;font-weight:900">${score}%</div>
          </div>
        </div>
        <p style="margin:24px 0 8px;color:#475569;line-height:1.55">Se full interaktiv rapport med alle DNS-poster, DKIM-selektorer og anbefalte tiltak:</p>
        <p><a href="${esc(b.reportUrl)}" style="display:inline-block;background:#0f172a;color:white;padding:13px 26px;border-radius:999px;text-decoration:none;font-weight:600">Åpne rapport →</a></p>
        ${b.message ? `<div style="margin-top:24px;padding:14px 16px;background:#f8fafc;border-left:3px solid #14b8a6;border-radius:6px;color:#475569;font-size:14px"><strong>Din melding:</strong><br>${esc(b.message)}</div>` : ''}
      </td></tr>
      <tr><td style="background:#f8fafc;padding:18px 28px;border-top:1px solid #e2e8f0;font-size:12px;color:#94a3b8">
        Micronet · <a href="mailto:hjelp@micronet.no" style="color:#0f766e">hjelp@micronet.no</a> · 22 80 20 40
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>`;
}

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const json = (obj, status, headers) => new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json', ...headers } });
