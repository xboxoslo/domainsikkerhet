"""Oppdater pris på item 516 (Mail SPF-DKIM-DMARC) fra 195 til 295 kr/mnd."""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

env = Path(r'C:\Users\TerjeOtterlei\Claude\intake-secrets.env')
for line in env.read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    os.environ[k.strip()] = v.strip().strip('"').strip("'")

CID = os.environ['HALO_CLIENT_ID']
CS  = os.environ['HALO_CLIENT_SECRET']
BASE = 'https://service.micronet.no'

# 1) Auth
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

H = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# 2) GET item 516
print('=== Item 516 før oppdatering ===')
req = urllib.request.Request(f'{BASE}/api/Item/516', headers=H)
with urllib.request.urlopen(req, timeout=20) as r:
    item = json.loads(r.read())

# Vis pris-relaterte felter
price_fields = ['baseprice', 'price', 'cost', 'unitprice', 'sellprice', 'recurringprice',
                'recurring_price', 'monthly_price', 'msrp', 'list_price', 'discounted_price']
print(f"id={item.get('id')}  name={item.get('name')}")
for k, v in item.items():
    if any(p in k.lower() for p in ['price', 'cost', 'baseprice', 'recurr', 'monthly']):
        print(f"  {k} = {v!r}")

# 3) PUT med oppdatert pris
print('\n=== Forsøker oppdatering: 195 -> 295 ===')

# Sett alle felter som tidligere var 195 til 295
updates = {}
for k, v in item.items():
    if isinstance(v, (int, float)) and v == 195:
        updates[k] = 295
        print(f"  Endrer {k}: 195 -> 295")

if not updates:
    print('  Ingen 195-verdier funnet i item 516. Skriver ut hele item-objektet:')
    print(json.dumps(item, indent=2, ensure_ascii=False)[:2000])
else:
    # Halo POST tar liste med ett objekt for update.
    # Prøver flere mønstre for å bekrefte "Ikke oppdater eksisterende fakturaer"
    attempts = [
        # Bekreft konflikt med "0" (No) — flere mønstre
        ('', [{'id': 516, **updates, 'update_recurring_invoice_price': '0', 'update_recurring_invoice_cost': '0'}]),
        ('', [{'id': 516, **updates, 'update_recurring_invoice_price': 0, 'update_recurring_invoice_cost': 0}]),
        # Med "i"-prefiks som er ekte db-felt (kan være rene numbers)
        ('', [{'id': 516, 'irecurringprice': 295.0, 'irecurringcost': 295.0, 'use': 'item'}]),
        # Send som dictionary (ikke liste) - kanskje feilen er strukturen
        ('', {'id': 516, **updates, 'update_recurring_invoice_price': False, 'update_recurring_invoice_cost': False}),
        # Endepunkt /Item/516 (single, ikke /Item)
        ('|/Item/516', [{'id': 516, **updates}]),
        # Bruk PUT i stedet for POST
        ('|PUT', [{'id': 516, **updates}]),
    ]

    for query, payload in attempts:
        method = 'POST'
        endpoint = '/api/Item'
        if '|PUT' in query:
            method = 'PUT'
            query = query.replace('|PUT', '')
        if '|/Item/516' in query:
            endpoint = '/api/Item/516'
            query = query.replace('|/Item/516', '')
        url = f'{BASE}{endpoint}{query}'
        put_req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), headers=H, method=method,
        )
        keys_desc = list(payload[0].keys()) if isinstance(payload, list) else list(payload.keys())
        try:
            with urllib.request.urlopen(put_req, timeout=20) as r:
                resp = json.loads(r.read())
            print(f'  OK {method} {endpoint}{query} / keys={keys_desc} -> {str(resp)[:300]}')
            break
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')[:300]
            print(f'  FAIL {method} {endpoint}{query} / keys={keys_desc} -> HTTP {e.code}: {body[:150]}')

# 4) Verifiser
print('\n=== Item 516 etter oppdatering ===')
req = urllib.request.Request(f'{BASE}/api/Item/516', headers=H)
with urllib.request.urlopen(req, timeout=20) as r:
    item2 = json.loads(r.read())
for k, v in item2.items():
    if any(p in k.lower() for p in ['price', 'cost', 'baseprice', 'recurr', 'monthly']):
        marker = '  OK' if v == 295 else '   '
        print(f"{marker} {k} = {v!r}")
