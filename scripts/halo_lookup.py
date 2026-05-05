"""Engangs-oppslag for å finne interne Halo-IDer (item, template, agent) til quote-koden."""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

env = Path(__file__).parent / 'intake-secrets.env'
for line in env.read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    os.environ[k.strip()] = v.strip().strip('"').strip("'")

CID = os.environ['HALO_CLIENT_ID']
CS  = os.environ['HALO_CLIENT_SECRET']
BASE = 'https://service.micronet.no'

token_req = urllib.request.Request(
    f'{BASE}/auth/token',
    data=urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': CID, 'client_secret': CS, 'scope': 'all',
    }).encode(),
    headers={'Content-Type': 'application/x-www-form-urlencoded'},
    method='POST',
)
with urllib.request.urlopen(token_req, timeout=15) as r:
    token = json.loads(r.read())['access_token']

H = {'Authorization': f'Bearer {token}'}

def get(path):
    req = urllib.request.Request(f'{BASE}/api{path}', headers=H)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def show(label, data, name_keys=('name','description','third_party_name')):
    items = data if isinstance(data, list) else (
        data.get('items') or data.get('templates') or data.get('agents')
        or data.get('value') or data.get('record') or []
    )
    print(f'\n=== {label} ({len(items)} treff) ===')
    for it in items[:25]:
        nm = next((it.get(k) for k in name_keys if it.get(k)), '?')
        print(f"  id={it.get('id'):<6}  {nm}")

show('Item search "Mail"', get('/Item?search=Mail&pageinate=false'))
show('Item search "DMARC"', get('/Item?search=DMARC&pageinate=false'))
print()
print('--- Quote PDF templates ---')
try:
    show('QuotationTemplate', get('/QuotationTemplate'))
except Exception as e:
    print(f'  /QuotationTemplate feilet: {e}')
try:
    show('PDFQuoteTemplate', get('/PDFQuoteTemplate'))
except Exception as e:
    print(f'  /PDFQuoteTemplate feilet: {e}')

print()
print('--- Agents (Terje) ---')
show('Agent search "Terje"', get('/Agent?search=Terje'))
