"""Finn quote PDF-template ID for 'Tilbud Micronet'."""
import json, os, urllib.parse, urllib.request
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

def try_endpoint(path):
    try:
        r = urllib.request.urlopen(urllib.request.Request(f'{BASE}/api{path}', headers=H), timeout=20)
        data = json.loads(r.read())
        items = data if isinstance(data, list) else (
            data.get('templates') or data.get('items') or data.get('record') or data.get('value') or [data]
        )
        print(f'  {path}: HTTP 200, {len(items) if isinstance(items, list) else 1} record(s)')
        for it in (items if isinstance(items, list) else [items])[:30]:
            if isinstance(it, dict):
                nm = it.get('name') or it.get('title') or it.get('description') or '?'
                print(f"      id={it.get('id'):<6}  {nm}")
        return True
    except urllib.error.HTTPError as e:
        print(f'  {path}: HTTP {e.code}')
    except Exception as e:
        print(f'  {path}: {e}')
    return False

print('Prøver template-endepunkter:')
for p in ['/PDFTemplate', '/Template', '/QuoteTemplate', '/PdfTemplate',
          '/Quote/Templates', '/Lookup?lookupid=151', '/Lookup?lookupid=152',
          '/Lookup?lookupid=153', '/CannedText', '/PdfTemplates',
          '/EmailTemplate', '/QuoteTemplates']:
    try_endpoint(p)

print('\nLeter etter "Tilbud" i alle Lookup-typer 100..200:')
for lid in range(100, 201):
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(f'{BASE}/api/Lookup?lookupid={lid}', headers=H), timeout=10)
        data = json.loads(r.read())
        items = data if isinstance(data, list) else data.get('record') or []
        for it in items:
            nm = (it.get('name') or '') if isinstance(it, dict) else ''
            if 'tilbud' in nm.lower() or 'micronet' in nm.lower():
                print(f"  Lookup {lid}: id={it.get('id')}  {nm}")
    except Exception:
        pass
