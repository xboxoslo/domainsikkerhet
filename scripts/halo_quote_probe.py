"""Probe Halo Quotation API for å finne riktig payload-struktur."""
import json, os, urllib.parse, urllib.request, urllib.error
from pathlib import Path

env = Path(__file__).parent / 'intake-secrets.env'
for line in env.read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

BASE = 'https://service.micronet.no'
req = urllib.request.Request(f'{BASE}/auth/token',
    data=urllib.parse.urlencode({'grant_type':'client_credentials',
        'client_id':os.environ['HALO_CLIENT_ID'],
        'client_secret':os.environ['HALO_CLIENT_SECRET'],
        'scope':'all'}).encode(),
    headers={'Content-Type':'application/x-www-form-urlencoded'}, method='POST')
with urllib.request.urlopen(req, timeout=15) as r:
    token = json.loads(r.read())['access_token']
H = {'Authorization': f'Bearer {token}'}

def get(path):
    try:
        r = urllib.request.urlopen(urllib.request.Request(f'{BASE}/api{path}', headers=H), timeout=20)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')

def post(path, payload):
    body = json.dumps(payload).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            f'{BASE}/api{path}', data=body,
            headers={**H, 'Content-Type':'application/json'}, method='POST'), timeout=20)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')

# 1. Hent ticket #34430 for å få client_id
print('=== Ticket 34430 (klient/bruker-info) ===')
s, t = get('/Tickets/34430')
if s == 200:
    if isinstance(t, dict):
        for k in ['id', 'client_id', 'client_name', 'user_id', 'user_name', 'site_id', 'site_name']:
            if k in t: print(f'  {k}: {t[k]}')
    client_id = t.get('client_id') if isinstance(t, dict) else None
else:
    print(f'  Feilet: {s}'); client_id = None

# 2. Probe Quotation endpoint - GET et eksisterende quote for å se feltnavn
print('\n=== Eksisterende quotes (1 stk) ===')
s, q = get('/Quotation?count=1')
if s == 200:
    items = q if isinstance(q, list) else q.get('quotations') or q.get('value') or []
    if items:
        sample = items[0]
        print(f'  Felt på Quotation:')
        for k in sorted(sample.keys()):
            v = sample[k]
            vstr = str(v)[:60] if not isinstance(v, (list, dict)) else f'<{type(v).__name__}>'
            print(f'    {k}: {vstr}')
else:
    print(f'  Feilet: {s} {str(q)[:200]}')

# 3. Forsøk minimal create (tomt body) for å se hvilke felt som er required
print('\n=== POST /Quotation med tom payload (lærer required fields) ===')
s, r = post('/Quotation', [{}])
print(f'  HTTP {s}: {str(r)[:400]}')

if client_id:
    print(f'\n=== POST /Quotation med ticket-link (client_id={client_id}) ===')
    payload = [{
        'client_id': client_id,
        'ticket_id': 34430,
        'agent_id': 3,
        'pdftemplate_id': 29,
        'title': 'Tilbud: Domenesikkerhet — micronet.no',
        'lines': [{'item_id': 516, 'quantity': 1}],
    }]
    s, r = post('/Quotation', payload)
    print(f'  HTTP {s}')
    if isinstance(r, list) and r:
        for k in ['id', 'quote_status_id', 'quote_status', 'status', 'title', 'agent_id', 'pdftemplate_id', 'ticket_id']:
            if k in r[0]: print(f'    {k}: {r[0][k]}')
    else:
        print(f'  body: {str(r)[:500]}')
