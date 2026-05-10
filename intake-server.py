"""
Lokal intake-backend for domain-analyzer.

Kjører på http://localhost:3001 — mottar POST fra HTML-skjemaet,
sender HTML-rapport via Mailgun og oppretter ticket i Halo PSA.

Kjør:
    1. Lag intake-secrets.env i samme mappe (se intake-secrets.env.example)
    2. python intake-server.py
    3. I domain-analyzer.html — sett:
         const INTAKE_ENDPOINT = 'http://localhost:3001/intake';

Krever kun Python 3.8+ (ingen pip install).
"""
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ─────── Config ───────
HALO_BASE        = 'https://service.micronet.no'
HALO_TOKEN_URL   = f'{HALO_BASE}/auth/token'
HALO_API_URL     = f'{HALO_BASE}/api'
HALO_TICKET_TYPE = 'EasyDMARC'

MAILGUN_DOMAIN = 'micronet.no'
MAILGUN_REGION = 'eu'
MAILGUN_FROM   = 'DomainSikkerhet <noreply@micronet.no>'

ALLOWED_ORIGINS = {
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://data1.no',
    'https://data1.no',
    'http://www.data1.no',
    'https://www.data1.no',
}

PORT = int(os.environ.get('PORT', 3001))

# ─────── Stats logging ───────
STATS_LOG_PATH = os.environ.get('STATS_LOG_PATH', '/tmp/data1-stats.jsonl')
ADMIN_TOKEN    = os.environ.get('ADMIN_TOKEN', '')
IP_SALT        = os.environ.get('IP_SALT', 'data1-default-salt-change-me')

def _hash_ip(ip):
    if not ip:
        return ''
    return hashlib.sha256((IP_SALT + ip).encode()).hexdigest()[:12]

def log_event(kind, **fields):
    """Append a JSON event to STATS_LOG_PATH. Best-effort, never raises."""
    try:
        rec = {'t': datetime.now(timezone.utc).isoformat(), 'kind': kind, **fields}
        with open(STATS_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    except Exception as e:
        sys.stderr.write(f'  [stats log fail] {e}\n')

# ─────── Load secrets from intake-secrets.env ───────
def load_env():
    env_path = Path(__file__).parent / 'intake-secrets.env'
    if not env_path.exists():
        return  # Railway: secrets are already in environment variables
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

load_env()
HALO_CLIENT_ID     = os.environ.get('HALO_CLIENT_ID', '')
HALO_CLIENT_SECRET = os.environ.get('HALO_CLIENT_SECRET', '')
MAILGUN_API_KEY    = os.environ.get('MAILGUN_API_KEY', '')
TURNSTILE_SECRET   = os.environ.get('TURNSTILE_SECRET', '')

for key in ('HALO_CLIENT_ID', 'HALO_CLIENT_SECRET', 'MAILGUN_API_KEY'):
    if not os.environ.get(key):
        print(f'  [WARN] {key} mangler i intake-secrets.env')

if not TURNSTILE_SECRET:
    print('  [WARN] TURNSTILE_SECRET mangler — Turnstile-verifisering er deaktivert')

_ticket_type_id = None


# ─────── HTTP helpers ───────
def http_post(url, data=None, headers=None, json_body=None):
    if json_body is not None:
        body = json.dumps(json_body).encode('utf-8')
        headers = {**(headers or {}), 'Content-Type': 'application/json'}
    elif isinstance(data, dict):
        body = urllib.parse.urlencode(data).encode('utf-8')
        headers = {**(headers or {}), 'Content-Type': 'application/x-www-form-urlencoded'}
    else:
        body = data
    req = urllib.request.Request(url, data=body, headers=headers or {}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')

def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {}, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')


def verify_turnstile(token: str, remote_ip: str = '') -> tuple[bool, str]:
    """Verify a Cloudflare Turnstile token. Returns (ok, reason)."""
    if not TURNSTILE_SECRET:
        return True, 'turnstile-disabled'
    if not token:
        return False, 'missing-token'
    payload = {'secret': TURNSTILE_SECRET, 'response': token}
    if remote_ip:
        payload['remoteip'] = remote_ip
    status, text = http_post(
        'https://challenges.cloudflare.com/turnstile/v0/siteverify',
        data=payload,
    )
    if status != 200:
        return False, f'siteverify-http-{status}'
    try:
        data = json.loads(text)
    except Exception:
        return False, 'invalid-response'
    if data.get('success'):
        return True, 'ok'
    return False, ','.join(data.get('error-codes') or ['unknown'])

def multipart_form(fields):
    """Lag multipart/form-data body for Mailgun.
    Tekstfelter: ('navn', 'verdi'). Filfelter: ('navn', ('filnavn', 'content-type', bytes))."""
    boundary = '----intake' + uuid.uuid4().hex
    parts = []
    for name, value in fields:
        parts.append(f'--{boundary}'.encode())
        if isinstance(value, tuple) and len(value) == 3:
            filename, ctype, data = value
            parts.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode())
            parts.append(f'Content-Type: {ctype}'.encode())
            parts.append(b'')
            parts.append(data if isinstance(data, (bytes, bytearray)) else str(data).encode('utf-8'))
        else:
            parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
            parts.append(b'')
            parts.append(str(value).encode('utf-8'))
    parts.append(f'--{boundary}--'.encode())
    parts.append(b'')
    body = b'\r\n'.join(parts)
    return body, f'multipart/form-data; boundary={boundary}'


# ─────── Halo ───────
def halo_token():
    status, text = http_post(HALO_TOKEN_URL, data={
        'grant_type':    'client_credentials',
        'client_id':     HALO_CLIENT_ID,
        'client_secret': HALO_CLIENT_SECRET,
        'scope':         'all',
    })
    if status >= 300:
        raise RuntimeError(f'Halo auth feilet ({status}): {text[:200]}')
    return json.loads(text)['access_token']

def halo_ticket_type_id(token):
    global _ticket_type_id
    if _ticket_type_id:
        return _ticket_type_id
    status, text = http_get(f'{HALO_API_URL}/TicketType',
                            headers={'Authorization': f'Bearer {token}'})
    if status >= 300:
        raise RuntimeError(f'Halo TicketType feilet ({status}): {text[:200]}')
    data = json.loads(text)
    items = data if isinstance(data, list) else data.get('tickettypes') or data.get('value') or []
    for t in items:
        if (t.get('name') or '').lower() == HALO_TICKET_TYPE.lower():
            _ticket_type_id = t['id']
            return _ticket_type_id
    raise RuntimeError(f'Ticket-type "{HALO_TICKET_TYPE}" ikke funnet i Halo')

def create_halo_ticket(b):
    token = halo_token()
    tt_id = halo_ticket_type_id(token)
    quote_id = b.get('_quoteId')
    client_id = b.get('_clientId')
    quote_link = (f"{HALO_BASE}/orders?mainview=quotes&selid=-1&sellevel=1&selparentid=0&quoteid={quote_id}"
                  if quote_id else None)

    summary = f"Domeneanalyse: {b.get('domain')} ({b.get('grade') or '?'} / {b.get('score') or '?'}%)"

    # Halo bruker HTML for ticket-details (ren tekst kollapser til én linje)
    name = b.get('name', '') or '(ikke oppgitt)'
    company = b.get('company') or '(ikke oppgitt)'
    orgnr = b.get('orgnr') or '(ikke oppgitt)'
    email = b.get('email', '') or '(ikke oppgitt)'
    phone = b.get('phone') or '(ikke oppgitt)'
    domain = b.get('domain', '')
    score = b.get('score') or '?'
    grade = b.get('grade') or '?'
    report_url = b.get('reportUrl', '')
    message = (b.get('message') or '').strip() or '<em>(ingen melding)</em>'

    # Karakter-fargekode
    grade_color = {'A+': '#16a34a', 'A': '#22c55e', 'B': '#84cc16',
                   'C': '#eab308', 'D': '#f97316', 'F': '#dc2626'}.get(grade, '#64748b')

    quote_block = ''
    if quote_id:
        quote_block = (
            f'<h3 style="font-size:14px;color:#0f172a;margin:18px 0 8px;'
            f'border-top:1px solid #e2e8f0;padding-top:14px">Tilbud</h3>'
            f'<p style="margin:0 0 4px"><strong>Tilbuds-ID:</strong> #{quote_id}</p>'
            f'<p style="margin:0"><strong>Lenke:</strong> <a href="{quote_link}">{quote_link}</a></p>'
        )

    details = (
        '<div style="font-family:-apple-system,Segoe UI,sans-serif;font-size:14px;line-height:1.6;color:#0f172a">'

        f'<h3 style="font-size:14px;color:#0f172a;margin:0 0 8px">Kontaktinformasjon</h3>'
        f'<table cellpadding="3" cellspacing="0" style="border-collapse:collapse;font-size:13px">'
        f'<tr><td style="color:#64748b;padding-right:12px">Navn:</td><td><strong>{name}</strong></td></tr>'
        f'<tr><td style="color:#64748b;padding-right:12px">Firma:</td><td><strong>{company}</strong></td></tr>'
        f'<tr><td style="color:#64748b;padding-right:12px">Org.nr:</td><td>{orgnr}</td></tr>'
        f'<tr><td style="color:#64748b;padding-right:12px">E-post:</td>'
        f'<td><a href="mailto:{email}">{email}</a></td></tr>'
        f'<tr><td style="color:#64748b;padding-right:12px">Telefon:</td>'
        f'<td><a href="tel:{phone}">{phone}</a></td></tr>'
        f'</table>'

        f'<h3 style="font-size:14px;color:#0f172a;margin:18px 0 8px;'
        f'border-top:1px solid #e2e8f0;padding-top:14px">Analyseresultat</h3>'
        f'<table cellpadding="3" cellspacing="0" style="border-collapse:collapse;font-size:13px">'
        f'<tr><td style="color:#64748b;padding-right:12px">Domene:</td>'
        f'<td><strong>{domain}</strong></td></tr>'
        f'<tr><td style="color:#64748b;padding-right:12px">Karakter:</td>'
        f'<td><span style="display:inline-block;background:{grade_color};color:#fff;'
        f'padding:2px 10px;border-radius:6px;font-weight:700">{grade}</span> &nbsp; ({score}%)</td></tr>'
        f'<tr><td style="color:#64748b;padding-right:12px">Rapport:</td>'
        f'<td><a href="{report_url}">{report_url}</a></td></tr>'
        f'</table>'

        f'{quote_block}'

        f'<h3 style="font-size:14px;color:#0f172a;margin:18px 0 8px;'
        f'border-top:1px solid #e2e8f0;padding-top:14px">Melding fra kunde</h3>'
        f'<div style="background:#f8fafc;border-left:3px solid #cbd5e0;'
        f'padding:10px 14px;border-radius:4px;color:#334155">{message}</div>'

        '</div>'
    )

    tags = [
        {'text': 'domeneanalyse'},
        {'text': f"domene:{b.get('domain','')}"},
        {'text': f"score:{b.get('score') or 'na'}"},
        {'text': f"karakter:{b.get('grade') or 'na'}"},
        {'text': 'kilde:domain-analyzer'},
    ]
    if b.get('orgnr'):
        tags.append({'text': f"orgnr:{b['orgnr']}"})
    if quote_id:
        tags.append({'text': f"quote:{quote_id}"})

    payload_item = {
        'summary': summary,
        'details': details,
        'tickettype_id': tt_id,
        'category_1': 'Domeneanalyse',
        'tags': tags,
        'userlookup': {
            'email': b.get('email',''),
            'name':  b.get('name',''),
            'phone': b.get('phone',''),
        },
    }
    # Lenk ticketen direkte til client og quote hvis vi har dem
    if client_id:
        payload_item['client_id'] = client_id
    if quote_id:
        payload_item['quote_id'] = quote_id

    payload = [payload_item]
    status, text = http_post(f'{HALO_API_URL}/Tickets',
                             json_body=payload,
                             headers={'Authorization': f'Bearer {token}'})
    if status >= 300:
        raise RuntimeError(f'Halo ticket feilet ({status}): {text[:300]}')
    res = json.loads(text)
    tid = res[0]['id'] if isinstance(res, list) and res else res.get('id')
    return {'ticketId': tid}


def halo_find_or_create_customer(b, token):
    """Returner (client_id, user_id). Søkerekkefølge: e-post → company-navn → opprett ny."""
    H = {'Authorization': f'Bearer {token}'}
    email   = (b.get('email') or '').strip()
    company = (b.get('company') or '').strip()
    name    = (b.get('name') or email or 'Ukjent').strip()

    if email:
        s, t = http_get(f'{HALO_API_URL}/Users?search={urllib.parse.quote(email)}&pageinate=false',
                        headers=H)
        if s == 200:
            data = json.loads(t)
            users = data if isinstance(data, list) else data.get('users') or []
            exact = [u for u in users if (u.get('emailaddress') or '').lower() == email.lower()]
            if exact:
                u = max(exact, key=lambda x: x.get('id', 0))
                return u['client_id'], u['id']

    client_id = None
    if company:
        s, t = http_get(f'{HALO_API_URL}/Client?search={urllib.parse.quote(company)}&pageinate=false',
                        headers=H)
        if s == 200:
            data = json.loads(t)
            clients = data if isinstance(data, list) else data.get('clients') or []
            exact = [c for c in clients if (c.get('name') or '').strip().lower() == company.lower()]
            if exact:
                client_id = exact[0]['id']

    if not client_id:
        client_name = company or b.get('domain') or name
        s, t = http_post(f'{HALO_API_URL}/Client',
                         json_body=[{'name': client_name}],
                         headers=H)
        if s >= 300:
            raise RuntimeError(f'Halo client-opprett feilet ({s}): {t[:300]}')
        res = json.loads(t)
        client_id = res[0]['id'] if isinstance(res, list) and res else res.get('id')

    parts = name.split(' ', 1)
    firstname = parts[0]
    surname   = parts[1] if len(parts) > 1 else ''
    s, t = http_post(f'{HALO_API_URL}/Users',
                     json_body=[{
                         'name': name,
                         'firstname': firstname,
                         'surname': surname,
                         'emailaddress': email,
                         'phonenumber': b.get('phone', ''),
                         'client_id': client_id,
                     }],
                     headers=H)
    if s >= 300:
        raise RuntimeError(f'Halo user-opprett feilet ({s}): {t[:300]}')
    res = json.loads(t)
    user_id = res[0]['id'] if isinstance(res, list) and res else res.get('id')
    return client_id, user_id


def halo_item_line(item_id, quantity, token):
    """Hent item-defaults og bygg quote-linje med pris/navn fylt inn (Halo auto-kopierer ikke via API)."""
    s, t = http_get(f'{HALO_API_URL}/Item/{item_id}',
                    headers={'Authorization': f'Bearer {token}'})
    if s >= 300:
        raise RuntimeError(f'Halo item-oppslag feilet ({s}): {t[:200]}')
    it = json.loads(t)
    is_recurring = bool(it.get('isrecurringitem'))
    price = it.get('recurringprice') if is_recurring else it.get('baseprice')
    cost  = it.get('recurringcost')  if is_recurring else it.get('costprice')
    return {
        'item_id':      item_id,
        'quantity':     quantity,
        'name':         it.get('name', ''),
        'description':  it.get('user_description') or it.get('name', ''),
        'price':        price or 0,
        'baseprice':    price or 0,
        'costprice':    cost  or 0,
        'item_recurring': is_recurring,
        'billingperiod': 1 if is_recurring else 0,  # 1 = månedlig
        'item_taxable': bool(it.get('taxable', True)),
        'item_tax_code': it.get('taxcode'),
    }


def create_halo_quote(b):
    """Opprett draft quote i Halo med item 516 (Mail SPF-DKIM-DMARC), template 29 (Tilbud Micronet).

    Hvis b['orderType'] == 'dmarc-service-package' tilpasses tittel og notat for direkte
    DMARC-tjenestebestillinger (uten domeneanalyse-score)."""
    token = halo_token()
    client_id, user_id = halo_find_or_create_customer(b, token)
    # Bygg adresse-linje fra BRREG-data hvis tilgjengelig
    addr_parts = []
    if b.get('address'): addr_parts.append(b['address'])
    pc_city = ' '.join(filter(None, [b.get('postcode',''), b.get('city','')]))
    if pc_city: addr_parts.append(pc_city)
    if b.get('country') and b.get('country') != 'Norge': addr_parts.append(b['country'])
    address_line = ', '.join(addr_parts) if addr_parts else '(ikke oppgitt)'

    ehf_status = '✓ Ja (PEPPOL/EHF-mottak)' if b.get('ehf') else '✗ Nei (manuell faktura)' if 'ehf' in b else '(ikke sjekket)'
    nace_line = f"{b.get('nace_code','')} {b.get('nace_text','')}".strip() or '(ikke oppgitt)'

    is_service_order = (b.get('orderType') or '').strip() == 'dmarc-service-package'
    if is_service_order:
        title = f"DMARC-pakke — {b.get('domain','')}"
        header_block = [
            f"=== Direkte bestilling: DMARC-pakke ===",
            f"  Domene:         {b.get('domain','')}",
            f"  Pakke:          1 990 kr engangs + 295 kr/mnd",
            f"  Kilde:          data1.no — \"Bestill nå\"-knapp",
        ]
    else:
        title = f"Domenesikkerhet — {b.get('domain','')}"
        header_block = [
            f"=== Domeneanalyse for {b.get('domain','')} ===",
            f"  Score: {b.get('score') or '?'}% ({b.get('grade') or '?'})",
            f"  Rapport: {b.get('reportUrl','')}",
        ]

    note = '\n'.join(header_block + [
        '',
        '=== Firma (auto-hentet fra BRREG) ===',
        f"  Navn:           {b.get('company') or '(ikke oppgitt)'}",
        f"  Org.nr:         {b.get('orgnr') or '(ikke oppgitt)'}",
        f"  Daglig leder:   {b.get('daglig_leder') or '(ikke oppgitt)'}",
        f"  Adresse:        {address_line}",
        f"  Antall ansatte: {b.get('employees') if b.get('employees') is not None else '(ikke oppgitt)'}",
        f"  NACE-bransje:   {nace_line}",
        f"  EHF-mottak:     {ehf_status}",
        '',
        '=== Kontaktperson ===',
        f"  Navn:    {b.get('name','')}",
        f"  E-post:  {b.get('email','')}",
        f"  Telefon: {b.get('phone') or '(ikke oppgitt)'}",
        '',
        '=== Melding fra kunde ===',
        b.get('message') or '(ingen)',
    ])
    payload = [{
        'title':          title,
        'client_id':      client_id,
        'user_id':        user_id,
        'agent_id':       23,    # API-bruker (eier)
        'assigned_agent': 3,     # Terje Otterlei (review)
        'pdftemplate_id': 29,    # Tilbud Micronet
        'note':           note,
        'lines': [
            halo_item_line(516, 1, token),  # Mail (SPF-DKIM-DMARC) — recurring kr 295/mnd
            halo_item_line(735, 1, token),  # Estimert Service Bedrift — etablering kr 1990 (engangs)
        ],
    }]
    s, t = http_post(f'{HALO_API_URL}/Quotation',
                     json_body=payload,
                     headers={'Authorization': f'Bearer {token}'})
    if s >= 300:
        raise RuntimeError(f'Halo quote feilet ({s}): {t[:300]}')
    res = json.loads(t)
    qid = res[0]['id'] if isinstance(res, list) and res else res.get('id')
    return {'quoteId': qid, 'clientId': client_id, 'userId': user_id}


# ─────── Mailgun ───────
def esc(s):
    return (str(s or '')
            .replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            .replace('"','&quot;').replace("'",'&#39;'))

def grade_palette(s):
    """Returnerer (grade, gradeColor, gradeColorLight) — samme mapping som domain-analyzer.html."""
    if s >= 90: return 'A+', '#2f855a', '#9ae6b4'
    if s >= 80: return 'A',  '#38a169', '#b9e8c7'
    if s >= 70: return 'B',  '#48916b', '#bfe3cb'
    if s >= 55: return 'C',  '#c79144', '#f6d28a'
    if s >= 35: return 'D',  '#c05621', '#f6b58a'
    return 'F', '#c53030', '#f6a8a8'

def score_card_bg(s):
    """Score-card bakgrunn (matcher .sc-* klassene i portalen — start-fargen i gradient)."""
    if s >= 90: return '#e2faf6'   # sc-aplus
    if s >= 80: return '#e8f8f0'   # sc-a
    if s >= 70: return '#eef6ff'   # sc-b
    if s >= 55: return '#fffbeb'   # sc-c
    if s >= 35: return '#fff7ed'   # sc-d
    return '#fef2f2'                # sc-f

# Karakterskala (matcher portalens design — pale bg, mørk tekst, aktiv har grønn ring)
GRADE_SCALE = [
    ('F',  '0–34',   '#c53030', '#fef2f2'),
    ('D',  '35–54',  '#c05621', '#fff7ed'),
    ('C',  '55–69',  '#c79144', '#fefce8'),
    ('B',  '70–79',  '#48916b', '#f0fdf4'),
    ('A',  '80–89',  '#38a169', '#ecfdf5'),
    ('A+', '90–100', '#2f855a', '#ecfdf5'),
]

def render_grade_cells(active_grade):
    """6 fargede karakterboxer (F→A+) med gjeldende karakter fremhevet med grønn ring."""
    cells = []
    for g, rng, color, bg in GRADE_SCALE:
        is_active = (g == active_grade)
        border = f'2px solid #2f855a' if is_active else f'1px solid {bg}'
        cells.append(
            f'<td bgcolor="{bg}" align="center" width="16%" '
            f'style="background:{bg};border:{border};border-radius:8px;'
            f'padding:12px 4px;font-family:Helvetica,Arial,sans-serif">'
            f'<div style="font-size:20px;font-weight:900;color:{color};line-height:1">{esc(g)}</div>'
            f'<div style="font-size:11px;color:{color};font-weight:700;margin-top:4px">{esc(rng)}%</div>'
            f'</td>'
        )
    return ''.join(cells)

# Komponent-beskrivelser (samme tekst som i portalen)
COMPONENTS = [
    ('#dc2626', 'DMARC',   '35p', 'p=reject gir full poengsum'),
    ('#eab308', 'SPF',     '25p', '~all og -all godkjent'),
    ('#16a34a', 'DKIM',    '20p', 'gyldig nøkkel funnet'),
    ('#2563eb', 'MTA-STS', '12p', 'kryptert innlevering'),
    ('#9333ea', 'TLS-RPT', '5p',  'TLS-feilrapportering'),
    ('#ca8a04', 'BIMI',    '3p',  'firmalogo i e-post'),
]

def render_components_html():
    rows = []
    for color, name, pts, desc in COMPONENTS:
        rows.append(
            f'<tr><td style="padding:4px 0;font-family:Helvetica,Arial,sans-serif;font-size:13px;color:#334155;line-height:1.5">'
            f'<span style="display:inline-block;width:11px;height:11px;background:{color};border-radius:50%;margin-right:8px;vertical-align:middle"></span>'
            f'<strong style="color:#0f172a">{esc(name)} ({esc(pts)})</strong> '
            f'<span style="color:#64748b">— {esc(desc)}</span>'
            f'</td></tr>'
        )
    return ''.join(rows)

def _hex_to_rgb(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def _cubic_bezier(p0, p1, p2, p3, n=24):
    """Sample n points langs en kubisk bezier, returner liste av (x,y)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0]
        y = u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1]
        pts.append((x, y))
    return pts

def _shield_polygon(scale=1.0, ox=0, oy=0):
    """Returner punktene som danner skjold-formen fra portalen (viewBox 120x130)."""
    s = scale
    sx = lambda x: x * s + ox
    sy = lambda y: y * s + oy
    P = lambda x, y: (sx(x), sy(y))
    pts = []
    pts.append(P(60, 8))
    pts += [(P(p[0], p[1])) for p in _cubic_bezier((60,8),(60,8),(90,12),(102,20))[1:]]
    pts += [(P(p[0], p[1])) for p in _cubic_bezier((102,20),(103,21),(104,22),(104,24))[1:]]
    pts.append(P(104, 62))
    pts += [(P(p[0], p[1])) for p in _cubic_bezier((104,62),(104,88),(86,110),(60,120))[1:]]
    pts += [(P(p[0], p[1])) for p in _cubic_bezier((60,120),(34,110),(16,88),(16,62))[1:]]
    pts.append(P(16, 24))
    pts += [(P(p[0], p[1])) for p in _cubic_bezier((16,24),(16,22),(17,21),(18,20))[1:]]
    pts += [(P(p[0], p[1])) for p in _cubic_bezier((18,20),(30,12),(60,8),(60,8))[1:]]
    return pts

def render_shield_png(grade, gc, gc_light):
    """Rendrer 3D-skjold-PNG: drop-shadow, gradient-halvdeler, hake-badge på A+/A. 240x260 @ 2x."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    SCALE = 4
    W, H = 120, 130
    iw, ih = W * SCALE, H * SCALE
    img = Image.new('RGBA', (iw, ih), (0, 0, 0, 0))
    shield_pts = _shield_polygon(scale=SCALE)

    # 1. Drop shadow (mørk skjold-form, blurret, offset litt ned)
    shadow = Image.new('RGBA', (iw, ih), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    shadow_pts = [(p[0], p[1] + 3*SCALE) for p in shield_pts]
    sd.polygon(shadow_pts, fill=(15, 23, 42, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=4*SCALE))
    img = Image.alpha_composite(img, shadow)

    # 2. Halo (myk sirkel bak skjoldet)
    halo = Image.new('RGBA', (iw, ih), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse((2*SCALE, 7*SCALE, 118*SCALE, 123*SCALE),
               fill=_hex_to_rgb(gc_light) + (76,))
    img = Image.alpha_composite(img, halo)

    # 3. Skjoldet (lys farge basis + mørk høyre halvdel)
    base = Image.new('RGBA', (iw, ih), (0, 0, 0, 0))
    bd = ImageDraw.Draw(base)
    bd.polygon(shield_pts, fill=_hex_to_rgb(gc_light))
    mask = Image.new('L', (iw, ih), 0)
    md = ImageDraw.Draw(mask)
    md.polygon(shield_pts, fill=255)
    right = Image.new('RGBA', (iw, ih), (0, 0, 0, 0))
    rd = ImageDraw.Draw(right)
    rd.rectangle((60*SCALE, 0, iw, ih), fill=_hex_to_rgb(gc) + (255,))
    base.paste(right, (0, 0), mask)

    img = Image.alpha_composite(img, base)
    draw = ImageDraw.Draw(img)

    # 6. Hvit sirkel med myk drop-shadow (gir letter-badge løftet 3D-følelse)
    cx, cy, r = 60*SCALE, 58*SCALE, 24*SCALE
    circle_shadow = Image.new('RGBA', (iw, ih), (0, 0, 0, 0))
    csd = ImageDraw.Draw(circle_shadow)
    csd.ellipse((cx-r, cy-r+2*SCALE, cx+r, cy+r+2*SCALE), fill=(0, 0, 0, 60))
    circle_shadow = circle_shadow.filter(ImageFilter.GaussianBlur(radius=2*SCALE))
    img = Image.alpha_composite(img, circle_shadow)
    draw = ImageDraw.Draw(img)
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(255, 255, 255, 255))

    # 7. Grade-bokstaven
    font_size = 36*SCALE if len(grade) == 1 else 28*SCALE
    font = None
    for path in [
        str(Path(__file__).parent / 'fonts' / 'DejaVuSans-Bold.ttf'),
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf',
        '/System/Library/Fonts/Helvetica.ttc',
        r'C:\Windows\Fonts\arialbd.ttf', r'C:\Windows\Fonts\arial.ttf',
        r'C:\Windows\Fonts\segoeuib.ttf']:
        try: font = ImageFont.truetype(path, font_size); break
        except Exception: continue
    if font is None: font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), grade, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = cx - tw / 2 - bbox[0]
    ty = cy - th / 2 - bbox[1]
    draw.text((tx, ty), grade, fill=_hex_to_rgb(gc) + (255,), font=font)

    # 8. Hake-badge i øvre høyre hjørne (kun på høye grades, slik portalen har)
    if grade in ('A+', 'A', 'B'):
        bcx, bcy = 99*SCALE, 18*SCALE
        br = 11*SCALE
        # Hvit ring-skygge bak
        bs2 = Image.new('RGBA', (iw, ih), (0, 0, 0, 0))
        bs2d = ImageDraw.Draw(bs2)
        bs2d.ellipse((bcx-br-2*SCALE, bcy-br+SCALE, bcx+br+2*SCALE, bcy+br+3*SCALE), fill=(0, 0, 0, 80))
        bs2 = bs2.filter(ImageFilter.GaussianBlur(radius=SCALE))
        img = Image.alpha_composite(img, bs2)
        draw = ImageDraw.Draw(img)
        # Hvit ring
        draw.ellipse((bcx-br-2*SCALE, bcy-br-2*SCALE, bcx+br+2*SCALE, bcy+br+2*SCALE),
                     fill=(255, 255, 255, 255))
        # Mørk indre sirkel
        draw.ellipse((bcx-br, bcy-br, bcx+br, bcy+br), fill=(15, 23, 42, 255))
        # Hake (3-punkts polyline)
        cw = max(2, int(2.5 * SCALE))
        draw.line(
            [(bcx - 5*SCALE, bcy + 0.5*SCALE),
             (bcx - 1.5*SCALE, bcy + 4*SCALE),
             (bcx + 5*SCALE, bcy - 3*SCALE)],
            fill=(255, 255, 255, 255), width=cw, joint='curve')

    # Downsample
    img = img.resize((W * 2, H * 2), Image.LANCZOS)
    import io
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()

def render_email_html(b):
    score = b.get('score') or 0
    try: s = int(score)
    except: s = 0
    grade, gc, gc_light = grade_palette(s)
    grade_e = esc(grade)
    bar_pct = max(0, min(100, s))

    if s >= 90:
        verdict_title = 'Sterk e-postsikkerhet'
        verdict_text = ('Domenet har et solid grunnlag. Vi anbefaler kontinuerlig overvåking '
                        'av DMARC-rapporter for å fange opp endringer og forsøk på misbruk.')
    elif s >= 70:
        verdict_title = 'God, men ikke optimal'
        verdict_text = ('Hovedmekanismene er på plass, men det finnes konkrete forbedringer som '
                        'reduserer risikoen for at noen kan sende falske e-poster i deres navn.')
    elif s >= 35:
        verdict_title = 'Vesentlige svakheter'
        verdict_text = ('Domenet er sårbart for spoofing. Det betyr at en angriper kan sende '
                        'e-poster som ser ut til å komme fra dere, og kunder/partnere har ingen '
                        'sikker måte å oppdage at det er falskt på.')
    else:
        verdict_title = 'Domenet er åpent for misbruk'
        verdict_text = ('Det er i praksis ingenting som hindrer en angriper i å utgi seg for å '
                        'være dere på e-post. Dette utnyttes daglig i målrettede phishing-angrep '
                        'mot ansatte, kunder og leverandører.')
    color = gc

    msg_block = (f'<tr><td style="padding:0 28px 24px"><div style="padding:14px 16px;background:#f0fdfa;'
                 f'border-left:3px solid #14b8a6;border-radius:6px;color:#0f172a;font-size:14px;line-height:1.55">'
                 f'<strong style="color:#0f766e">Din melding til oss:</strong><br>{esc(b.get("message"))}</div></td></tr>'
                 ) if b.get('message') else ''

    return f'''<!doctype html><html><body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#0f172a">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 12px">
  <tr><td align="center">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:white;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(15,23,42,0.06)">

      <tr><td style="background:#0f172a;padding:22px 28px">
        <div style="color:white;font-size:18px;font-weight:800;letter-spacing:-.01em">Domain<span style="color:#4fd1c5">Sikkerhet</span></div>
        <div style="color:#94a3b8;font-size:12px;margin-top:2px">en tjeneste fra Micronet AS</div>
      </td></tr>

      <tr><td style="padding:32px 28px 8px">
        <h1 style="font-size:24px;margin:0 0 12px;letter-spacing:-.02em">Hei {esc(b.get('name'))},</h1>
        <p style="color:#334155;margin:0 0 8px;line-height:1.6;font-size:15px">
          Takk for at du bestilte en gratis sikkerhetsanalyse av <strong>{esc(b.get('domain'))}</strong>.
          Vi har sjekket hvordan domenet er beskyttet mot spoofing og phishing —
          her er resultatet.
        </p>
      </td></tr>

      <tr><td style="padding:16px 28px" bgcolor="#ffffff">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" bgcolor="{score_card_bg(s)}"
               style="background:{score_card_bg(s)};border-radius:16px">
          <tr>
            <td valign="middle" align="center" width="140" style="padding:14px 6px 14px 14px">
              <img src="cid:shield" width="120" height="130" alt="Karakter {grade_e}"
                   style="display:block;border:0;outline:none;text-decoration:none;width:120px;height:130px">
            </td>
            <td valign="middle" style="padding:18px 18px 18px 8px;font-family:Helvetica,Arial,sans-serif">
              <div style="font-size:11px;color:#475569;text-transform:uppercase;letter-spacing:.08em;font-weight:700">Score</div>
              <div style="font-size:44px;font-weight:900;color:#1a202c;line-height:1.05;margin-top:2px">{s}%</div>
              <div style="font-size:14px;color:#4a5568;margin-top:4px">{esc(b.get('domain',''))}</div>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
                     style="margin-top:10px;border-collapse:separate;border-radius:4px;overflow:hidden" bgcolor="#ffffff">
                <tr>
                  <td bgcolor="{color}" height="8" width="{bar_pct}%" style="background:{color};font-size:0;line-height:0">&nbsp;</td>
                  <td bgcolor="#ffffff" height="8" style="background:#ffffff;font-size:0;line-height:0">&nbsp;</td>
                </tr>
              </table>
              <div style="font-size:14px;color:{color};font-weight:700;margin-top:12px">{esc(verdict_title)}</div>
            </td>
          </tr>
        </table>
        <p style="color:#475569;font-size:14px;line-height:1.6;margin:14px 2px 0">{esc(verdict_text)}</p>
      </td></tr>

      <tr><td style="padding:18px 28px 4px">
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:10px">Karakterskala — hvordan bestemmes scoren?</div>
        <table role="presentation" cellpadding="0" cellspacing="6" border="0" width="100%" style="border-collapse:separate">
          <tr>
            {render_grade_cells(grade)}
          </tr>
        </table>
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top:14px">
          {render_components_html()}
        </table>
      </td></tr>

      <tr><td style="padding:8px 28px">
        <p><a href="{esc(b.get('reportUrl'))}" style="display:inline-block;background:#0f172a;color:white;padding:13px 28px;border-radius:999px;text-decoration:none;font-weight:600;font-size:14px">Åpne full rapport &rarr;</a></p>
        <p style="color:#64748b;font-size:13px;line-height:1.55;margin:0 0 8px">
          Den interaktive rapporten viser alle DNS-poster, DKIM-selektorer og en prioritert liste
          over hva som bør rettes opp.
        </p>
      </td></tr>

      <tr><td style="padding:16px 28px;border-top:1px solid #e2e8f0">
        <h2 style="font-size:17px;margin:0 0 10px;letter-spacing:-.01em">Hvorfor dette er viktig</h2>
        <p style="color:#334155;font-size:14px;line-height:1.65;margin:0 0 10px">
          Spoofing og phishing er den vanligste innfallsvinkelen i moderne dataangrep — også
          mot småbedrifter. Når SPF, DKIM og DMARC ikke er korrekt satt opp, kan en angriper
          sende e-poster som ser ut til å komme fra dere, til kunder, leverandører og ansatte.
          Resultatet er ofte fakturasvindel, kompromitterte kontoer eller tap av tillit.
        </p>
        <p style="color:#334155;font-size:14px;line-height:1.65;margin:0">
          Dette er ikke teoretisk — vi ser angrep mot norske bedrifter ukentlig, og kostnadene
          ved ett enkelt vellykket angrep overstiger som regel mange års sikkerhetsbudsjett.
        </p>
      </td></tr>

      <tr><td style="padding:18px 28px;border-top:1px solid #e2e8f0;background:#fafbfc">
        <h2 style="font-size:17px;margin:0 0 12px;letter-spacing:-.01em">Vi kan hjelpe dere</h2>
        <p style="color:#334155;font-size:14px;line-height:1.65;margin:0 0 12px">
          Micronet er Microsoft Solutions Partner med spisskompetanse på e-postsikkerhet.
          Vi setter opp og vedlikeholder SPF, DKIM og DMARC for dere, og overvåker domenet
          kontinuerlig så små endringer ikke får utvikle seg til reelle åpninger.
        </p>
        <table cellpadding="0" cellspacing="0" style="width:100%;margin:8px 0 14px">
          <tr><td style="font-size:14px;color:#0f172a;padding:4px 0">✓ &nbsp;Fullstendig oppsett av SPF, DKIM og DMARC</td></tr>
          <tr><td style="font-size:14px;color:#0f172a;padding:4px 0">✓ &nbsp;Kontinuerlig overvåking av rapportstrøm fra ekstern post</td></tr>
          <tr><td style="font-size:14px;color:#0f172a;padding:4px 0">✓ &nbsp;Månedlig statusrapport — så dere vet det virker</td></tr>
          <tr><td style="font-size:14px;color:#0f172a;padding:4px 0">✓ &nbsp;Direkte kontakt når noe oppstår — ingen anonym helpdesk</td></tr>
        </table>
        <table cellpadding="0" cellspacing="0" style="background:white;border:1px solid #cbd5e1;border-radius:10px;width:100%">
          <tr>
            <td style="padding:16px 18px">
              <div style="font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.06em;font-weight:700">Pris</div>
              <div style="font-size:24px;font-weight:900;color:#0f172a;margin-top:2px">kr 295 / mnd</div>
              <div style="font-size:13px;color:#64748b;margin-top:2px">eks. mva &middot; etablering kr 1990</div>
            </td>
          </tr>
        </table>
      </td></tr>

      {msg_block}

      <tr><td style="padding:20px 28px;border-top:1px solid #e2e8f0">
        <h2 style="font-size:17px;margin:0 0 10px;letter-spacing:-.01em">Vil du ta en prat?</h2>
        <p style="color:#334155;font-size:14px;line-height:1.65;margin:0 0 14px">
          Svar på denne mailen, eller ring oss direkte på <strong>22 80 20 40</strong>.
          Vi tar gjerne et 15-minutters uforpliktende møte på Teams der vi går gjennom
          rapporten sammen og viser hva som faktisk er åpent for misbruk.
        </p>
        <p style="margin:16px 0 0;color:#0f172a;font-size:14px;line-height:1.5">
          <strong>Med vennlig hilsen,</strong><br>
          <strong style="font-size:15px">Terje Otterlei</strong><br>
          <span style="color:#64748b">Micronet AS</span><br>
          <a href="tel:+4722802040" style="color:#0f766e;text-decoration:none">22 80 20 40</a> &nbsp;&middot;&nbsp;
          <a href="mailto:terje@micronet.no" style="color:#0f766e;text-decoration:none">terje@micronet.no</a>
        </p>
      </td></tr>

      <tr><td style="background:#f8fafc;padding:16px 28px;border-top:1px solid #e2e8f0;font-size:11px;color:#94a3b8;line-height:1.6">
        Micronet AS &middot; <a href="mailto:hjelp@micronet.no" style="color:#0f766e;text-decoration:none">hjelp@micronet.no</a> &middot; 22 80 20 40<br>
        Du fikk denne mailen fordi du bestilte en sikkerhetsanalyse på domeneanalyse.micronet.no
      </td></tr>

    </table>
  </td></tr>
</table>
</body></html>'''

def build_mime_message(b, shield_png):
    """Bygg full MIME-melding (multipart/related → alternative + inline image) med eksplisitt Content-ID."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    score = b.get('score') or 0
    try: s_int = int(score)
    except: s_int = 0
    grade, _, _ = grade_palette(s_int)

    text_body = (f"Hei {b.get('name','')},\n\n"
                 f"Din domeneanalyse for {b.get('domain','')}:\n"
                 f"Score: {b.get('score') or '?'}% ({grade})\n\n"
                 f"Full rapport: {b.get('reportUrl','')}\n\nMicronet")

    related = MIMEMultipart('related')
    related['From'] = MAILGUN_FROM
    related['To'] = f"{b.get('name','')} <{b.get('email','')}>"
    related['Subject'] = f"Domeneanalyse: {b.get('domain','')} — {grade}"
    related['Reply-To'] = 'hjelp@micronet.no'

    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText(text_body, 'plain', 'utf-8'))
    alt.attach(MIMEText(render_email_html(b), 'html', 'utf-8'))
    related.attach(alt)

    img = MIMEImage(shield_png, _subtype='png')
    img.add_header('Content-ID', '<shield>')
    img.add_header('Content-Disposition', 'inline', filename='shield.png')
    related.attach(img)

    return related.as_bytes()

def send_mailgun(b):
    endpoint = (f'https://api.eu.mailgun.net/v3/{MAILGUN_DOMAIN}/messages.mime'
                if MAILGUN_REGION == 'eu'
                else f'https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages.mime')
    score = b.get('score') or 0
    try: s_int = int(score)
    except: s_int = 0
    grade, gc, gc_light = grade_palette(s_int)

    shield_png = render_shield_png(grade, gc, gc_light)
    mime_bytes = build_mime_message(b, shield_png)

    body, ct = multipart_form([
        ('to',      f"{b.get('name','')} <{b.get('email','')}>"),
        ('message', ('message.eml', 'message/rfc822', mime_bytes)),
    ])
    import base64
    auth = base64.b64encode(f'api:{MAILGUN_API_KEY}'.encode()).decode()
    req = urllib.request.Request(endpoint, data=body, method='POST',
                                 headers={'Content-Type': ct, 'Authorization': f'Basic {auth}'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Mailgun feilet ({e.code}): {e.read().decode("utf-8", "replace")[:300]}')


# ─────── HTTP server ───────
class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get('Origin', '')
        allowed = origin if origin in ALLOWED_ORIGINS else next(iter(ALLOWED_ORIGINS))
        self.send_header('Access-Control-Allow-Origin', allowed)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _client_ip(self):
        return (self.headers.get('CF-Connecting-IP')
                or self.headers.get('X-Forwarded-For', '').split(',')[0].strip()
                or self.client_address[0])

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/track':
            self._handle_track_get(parsed.query)
            return
        if parsed.path == '/admin/stats':
            qs = urllib.parse.parse_qs(parsed.query)
            token = (qs.get('token') or [''])[0]
            if not ADMIN_TOKEN or token != ADMIN_TOKEN:
                self.send_response(401); self._cors()
                self.send_header('Content-Type', 'text/plain'); self.end_headers()
                self.wfile.write(b'Unauthorized')
                return
            self._render_stats()
            return
        if parsed.path == '/admin/preview-email':
            qs = urllib.parse.parse_qs(parsed.query)
            token = (qs.get('token') or [''])[0]
            if not ADMIN_TOKEN or token != ADMIN_TOKEN:
                self.send_response(401); self._cors()
                self.send_header('Content-Type', 'text/plain'); self.end_headers()
                self.wfile.write(b'Unauthorized')
                return
            to_email = (qs.get('to') or [''])[0]
            if not to_email or '@' not in to_email:
                self.send_response(400); self._cors()
                self.send_header('Content-Type', 'text/plain'); self.end_headers()
                self.wfile.write(b'Missing or invalid ?to=email@example.com')
                return
            try:
                self._send_shield_preview(to_email)
                self.send_response(200); self._cors()
                self.send_header('Content-Type', 'text/plain'); self.end_headers()
                self.wfile.write(f'Sent preview to {to_email}'.encode('utf-8'))
            except Exception as e:
                self.send_response(500); self._cors()
                self.send_header('Content-Type', 'text/plain'); self.end_headers()
                self.wfile.write(f'Error: {e}'.encode('utf-8'))
            return
        if parsed.path == '/healthz':
            self.send_response(200); self._cors()
            self.send_header('Content-Type', 'text/plain'); self.end_headers()
            self.wfile.write(b'ok')
            return
        self.send_response(404); self._cors(); self.end_headers()

    def _send_shield_preview(self, to_email):
        """Send a test email with all 6 shields (A+, A, B, C, D, F) inline."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.image import MIMEImage
        import base64

        grades = [(95, 'A+'), (85, 'A'), (75, 'B'), (62, 'C'), (45, 'D'), (15, 'F')]
        related = MIMEMultipart('related')
        related['From'] = MAILGUN_FROM
        related['To'] = to_email
        related['Subject'] = 'Skjold-preview — alle 6 karakterer (A+ til F)'

        rows = []
        for s, expected_grade in grades:
            grade, gc, gc_light = grade_palette(s)
            png = render_shield_png(grade, gc, gc_light)
            cid = f'shield-{grade.replace("+","p").lower()}'
            img = MIMEImage(png, _subtype='png')
            img.add_header('Content-ID', f'<{cid}>')
            img.add_header('Content-Disposition', 'inline', filename=f'{cid}.png')
            related.attach(img)
            rows.append(f'''
              <tr>
                <td style="padding:18px;background:{score_card_bg(s)};border-radius:14px" valign="middle" align="center">
                  <img src="cid:{cid}" width="120" height="130" alt="{grade}" style="display:block;border:0">
                  <div style="margin-top:10px;font-family:Helvetica,Arial,sans-serif;font-size:13px;color:#475569">
                    <strong style="color:{gc};font-size:18px">{grade}</strong> &middot; score {s}
                  </div>
                </td>
              </tr>''')

        html = f'''<!doctype html><html><body style="margin:0;padding:24px;background:#f1f5f9;font-family:Helvetica,Arial,sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.06)">
  <tr><td>
    <h1 style="font-size:22px;margin:0 0 8px;color:#0f172a">Skjold-preview</h1>
    <p style="font-size:14px;color:#475569;margin:0 0 18px">Alle 6 karakter-skjold som brukes i e-postrapporter fra data1.no. Bekreft at fargene og hake-badge-en gjengis riktig hos deg.</p>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="14">{''.join(rows)}</table>
    <p style="font-size:12px;color:#94a3b8;margin:18px 0 0">Test-e-post fra /admin/preview-email · {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</p>
  </td></tr>
</table>
</body></html>'''

        text = 'Skjold-preview: ' + ', '.join(f'{g} (score {s})' for s, g in grades)

        alt = MIMEMultipart('alternative')
        alt.attach(MIMEText(text, 'plain', 'utf-8'))
        alt.attach(MIMEText(html, 'html', 'utf-8'))
        related.attach(alt)

        endpoint = (f'https://api.eu.mailgun.net/v3/{MAILGUN_DOMAIN}/messages.mime'
                    if MAILGUN_REGION == 'eu'
                    else f'https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages.mime')
        body, ct = multipart_form([
            ('to', to_email),
            ('message', ('message.eml', 'message/rfc822', related.as_bytes())),
        ])
        auth = base64.b64encode(f'api:{MAILGUN_API_KEY}'.encode()).decode()
        req = urllib.request.Request(endpoint, data=body, method='POST',
                                     headers={'Content-Type': ct, 'Authorization': f'Basic {auth}'})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))

    def _handle_track_get(self, query):
        qs = urllib.parse.parse_qs(query)
        log_event('pageview',
                  path=(qs.get('p') or [''])[0][:200],
                  referrer=(qs.get('r') or [''])[0][:200],
                  utm_source=(qs.get('s') or [''])[0][:40],
                  utm_medium=(qs.get('m') or [''])[0][:40],
                  utm_campaign=(qs.get('c') or [''])[0][:40],
                  ua_short=(self.headers.get('User-Agent','')[:80]),
                  iph=_hash_ip(self._client_ip()))
        gif = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        self.send_response(200); self._cors()
        self.send_header('Content-Type', 'image/gif')
        self.send_header('Cache-Control', 'no-store, max-age=0')
        self.send_header('Content-Length', str(len(gif)))
        self.end_headers()
        self.wfile.write(gif)

    def do_POST(self):
        if self.path == '/track':
            self._handle_track()
            return
        if self.path != '/intake':
            self.send_response(404); self._cors(); self.end_headers()
            return
        length = int(self.headers.get('Content-Length') or 0)
        try:
            body = json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception:
            self._send_json({'error': 'Invalid JSON'}, 400); return

        for f in ('name', 'email', 'domain'):
            if not body.get(f):
                self._send_json({'error': f'Mangler felt: {f}'}, 400); return

        client_ip = self._client_ip()
        ts_ok, ts_reason = verify_turnstile(body.get('turnstileToken', ''), client_ip)
        if not ts_ok:
            print(f'  [BLOCKED] Turnstile failed for {client_ip}: {ts_reason}')
            self._send_json({'error': 'Bot-beskyttelse feilet. Last siden på nytt og prøv igjen.'}, 403); return

        result = {'ok': True}
        is_service_order = (body.get('orderType') or '').strip() == 'dmarc-service-package'

        if is_service_order:
            print(f'  --> Service-bestilling (DMARC-pakke) for {body.get("domain")} — hopper over rapport-mail')
            result['mail'] = {'skipped': 'service-order'}
        else:
            try:
                print(f'  --> Sender mail til {body.get("email")} for {body.get("domain")}')
                result['mail'] = send_mailgun(body)
                print(f'    [OK] Mailgun OK')
            except Exception as e:
                print(f'    [FAIL] Mailgun: {e}')
                result['mail'] = {'error': str(e)}

        try:
            print(f'  --> Oppretter Halo-quote for {body.get("domain")}')
            result['halo'] = create_halo_quote(body)
            print(f'    [OK] Halo OK (quote {result["halo"].get("quoteId")}, '
                  f'client {result["halo"].get("clientId")}, user {result["halo"].get("userId")})')
            # Beriker body med quote-info så ticketen kan referere til den
            body['_quoteId'] = result['halo'].get('quoteId')
            body['_clientId'] = result['halo'].get('clientId')
        except Exception as e:
            print(f'    [FAIL] Halo: {e}')
            result['halo'] = {'error': str(e)}

        try:
            print(f'  --> Oppretter Halo-ticket for {body.get("domain")}')
            result['ticket'] = create_halo_ticket(body)
            print(f'    [OK] Ticket OK (id {result["ticket"].get("ticketId")})')
        except Exception as e:
            print(f'    [FAIL] Ticket: {e}')
            result['ticket'] = {'error': str(e)}

        log_event('conversion',
                  domain=(body.get('domain') or '').lower()[:80],
                  utm_source=(body.get('utm_source') or '')[:40],
                  utm_medium=(body.get('utm_medium') or '')[:40],
                  utm_campaign=(body.get('utm_campaign') or '')[:40],
                  referrer=(body.get('referrer') or '')[:140],
                  iph=_hash_ip(client_ip))
        self._send_json(result, 200)

    def _handle_track(self):
        length = int(self.headers.get('Content-Length') or 0)
        if length > 4096:
            self.send_response(413); self._cors(); self.end_headers(); return
        try:
            body = json.loads(self.rfile.read(length).decode('utf-8')) if length else {}
        except Exception:
            body = {}
        log_event('pageview',
                  path=(body.get('path') or '')[:200],
                  referrer=(body.get('referrer') or '')[:200],
                  utm_source=(body.get('utm_source') or '')[:40],
                  utm_medium=(body.get('utm_medium') or '')[:40],
                  utm_campaign=(body.get('utm_campaign') or '')[:40],
                  ua_short=(self.headers.get('User-Agent','')[:80]),
                  iph=_hash_ip(self._client_ip()))
        self.send_response(204); self._cors(); self.end_headers()

    def _render_stats(self):
        events = []
        try:
            with open(STATS_LOG_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    try: events.append(json.loads(line))
                    except: pass
        except FileNotFoundError:
            pass

        now_ts = time.time()
        def within(ev, hours):
            try:
                t = datetime.fromisoformat(ev['t'].replace('Z','+00:00')).timestamp()
                return (now_ts - t) <= hours*3600
            except: return False

        def bucket(events, hours):
            evs = [e for e in events if within(e, hours)]
            return {
                'pageviews': sum(1 for e in evs if e.get('kind')=='pageview'),
                'unique_visitors': len({e.get('iph') for e in evs if e.get('kind')=='pageview' and e.get('iph')}),
                'conversions': sum(1 for e in evs if e.get('kind')=='conversion'),
                'top_paths': Counter(e.get('path','') for e in evs if e.get('kind')=='pageview').most_common(15),
                'top_sources': Counter((e.get('utm_source') or '(direct)') for e in evs).most_common(15),
                'top_referrers': Counter((e.get('referrer') or '(none)')[:60] for e in evs if e.get('kind')=='pageview').most_common(15),
                'conversion_by_source': Counter((e.get('utm_source') or '(direct)') for e in evs if e.get('kind')=='conversion').most_common(15),
                'top_domains': Counter(e.get('domain','') for e in evs if e.get('kind')=='conversion').most_common(15),
            }

        d24 = bucket(events, 24)
        d7  = bucket(events, 24*7)
        d30 = bucket(events, 24*30)

        def fmt_table(title, rows):
            if not rows:
                return f'<h3>{title}</h3><p style="color:#94a3b8">(ingen data)</p>'
            tr = ''.join(f'<tr><td>{esc(k)}</td><td style="text-align:right">{v}</td></tr>' for k,v in rows)
            return f'<h3>{title}</h3><table>{tr}</table>'

        def section(label, b):
            return f'''
<section>
  <h2>{label}</h2>
  <div class="kpis">
    <div class="kpi"><div class="n">{b["pageviews"]}</div><div class="l">Pageviews</div></div>
    <div class="kpi"><div class="n">{b["unique_visitors"]}</div><div class="l">Unike (hashet IP)</div></div>
    <div class="kpi"><div class="n">{b["conversions"]}</div><div class="l">Konverteringer</div></div>
  </div>
  <div class="grid">
    {fmt_table('Top sider', b['top_paths'])}
    {fmt_table('Top kilder (utm_source)', b['top_sources'])}
    {fmt_table('Top referrers', b['top_referrers'])}
    {fmt_table('Konverteringer per kilde', b['conversion_by_source'])}
    {fmt_table('Top domener (sjekket)', b['top_domains'])}
  </div>
</section>'''

        html = f'''<!doctype html>
<html lang="no"><head><meta charset="utf-8"><title>data1.no — stats</title>
<meta name="robots" content="noindex">
<style>
*{{box-sizing:border-box}}body{{font:14px/1.5 -apple-system,BlinkMacSystemFont,sans-serif;background:#f1f5f9;color:#1e293b;margin:0;padding:24px}}
h1{{font-size:24px;margin:0 0 18px;color:#0f172a}}
h2{{font-size:18px;margin:28px 0 12px;color:#0f172a}}
h3{{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#64748b;margin:14px 0 6px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}}
.kpi{{background:#fff;border-radius:10px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kpi .n{{font-size:24px;font-weight:800;color:#0f172a}}
.kpi .l{{font-size:12px;color:#64748b}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}}
.grid > *{{background:#fff;border-radius:10px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
td{{padding:5px 0;border-bottom:1px solid #f1f5f9;word-break:break-all}}
section{{background:#fafbfc;padding:16px 20px;border-radius:14px;margin-bottom:18px}}
.meta{{color:#64748b;font-size:13px;margin-bottom:18px}}
</style></head><body>
<h1>data1.no — analytics</h1>
<p class="meta">Logfile: {esc(STATS_LOG_PATH)} · {len(events)} events totalt · oppdatert {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</p>
{section("Siste 24 timer", d24)}
{section("Siste 7 dager", d7)}
{section("Siste 30 dager", d30)}
</body></html>'''

        self.send_response(200); self._cors()
        self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _send_json(self, obj, status):
        self.send_response(status)
        self._cors()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode('utf-8'))

    def log_message(self, fmt, *args):
        sys.stderr.write(f'[{self.log_date_time_string()}] {fmt % args}\n')


if __name__ == '__main__':
    print(f'Intake-server kjører på http://localhost:{PORT}/intake')
    print(f'  Halo:    {HALO_BASE}  (ticket-type: {HALO_TICKET_TYPE})')
    print(f'  Mailgun: {MAILGUN_DOMAIN}  ({MAILGUN_REGION.upper()})')
    print(f'  Tillater CORS fra: {", ".join(ALLOWED_ORIGINS)}')
    print('  Trykk Ctrl+C for å stoppe.\n')
    HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
