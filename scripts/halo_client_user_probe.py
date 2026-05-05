"""Probe Halo Client/Users API for å finne riktige feltnavn for orgnr-søk og bruker-oppslag."""
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

# Hent én eksisterende klient og se på alle felter
print('=== Eksempel-klient (felter) ===')
s, c = get('/Client?count=1&pageinate=false')
items = c if isinstance(c, list) else c.get('clients') or c.get('value') or []
if items:
    sample = items[0]
    print(f'  Total felter: {len(sample.keys())}')
    org_candidates = []
    for k in sorted(sample.keys()):
        v = sample[k]
        # Find candidate orgnr fields
        if any(x in k.lower() for x in ['org', 'company_no', 'companynumber', 'reg', 'tax', 'vat', 'cvr', 'business']):
            org_candidates.append((k, v))
        # Print only short scalar fields, ikke arrays/objects
        if not isinstance(v, (list, dict)):
            vstr = str(v)[:50]
            print(f'    {k}: {vstr}')
    print(f'\n  Sannsynlige orgnr-felt:')
    for k, v in org_candidates:
        print(f'    {k}: {v}')

# Hent én bruker og se på felter
print('\n=== Eksempel-bruker (felter) ===')
s, u = get('/Users?count=1&pageinate=false')
items = u if isinstance(u, list) else u.get('users') or u.get('value') or []
if items:
    sample = items[0]
    print(f'  Total felter: {len(sample.keys())}')
    for k in sorted(sample.keys()):
        v = sample[k]
        if not isinstance(v, (list, dict)):
            print(f'    {k}: {str(v)[:50]}')

# Test: kan vi søke på orgnr direkte?
print('\n=== Search-test ===')
for q in ['?search=micronet', '?search=914777654', '?companynumber=914777654']:
    s, r = get(f'/Client{q}')
    items = r if isinstance(r, list) else (r.get('clients') if isinstance(r, dict) else [])
    cnt = len(items) if isinstance(items, list) else 0
    print(f'  /Client{q}: HTTP {s}, {cnt} treff')
    if isinstance(items, list) and items:
        for it in items[:3]:
            print(f'      id={it.get("id")} name={it.get("name")} orgnr_like={it.get("companynumber") or it.get("orgnr") or it.get("inactive")}')
