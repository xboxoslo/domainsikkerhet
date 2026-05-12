#!/usr/bin/env python3
"""
Sjekk sp= subdomain-policy i DMARC-record for de 12 offentlige etatene
i bloggposten 2026-05-12. Brukes til å verifisere LinkedIn-claim om at
"ingen av de 12 har sp= subdomain-policy satt".

Output: _data/sp-verification-YYYY-MM-DD.md
"""
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / '_data'
DOH = 'https://cloudflare-dns.com/dns-query'

DOMAINS = [
    'altinn.no',
    'nrk.no',
    'forsvaret.no',
    'uio.no',
    'ntnu.no',
    'nmbu.no',
    'hvl.no',
    'khio.no',
    'oslo.kommune.no',
    'baerum.kommune.no',
    'tromso.kommune.no',
    'ks.no',
]


def doh(name: str, qtype: str) -> dict:
    url = f'{DOH}?name={urllib.parse.quote(name)}&type={qtype}'
    req = urllib.request.Request(url, headers={'Accept': 'application/dns-json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def get_dmarc(domain: str) -> str | None:
    try:
        r = doh(f'_dmarc.{domain}', 'TXT')
    except Exception as e:
        return f'ERROR: {e}'
    if r.get('Status') != 0:
        return None
    for a in r.get('Answer', []):
        data = a.get('data', '').replace('"', '').strip()
        if data.lower().startswith('v=dmarc1'):
            return data
    return None


def parse_tags(record: str) -> dict:
    tags = {}
    for part in record.split(';'):
        part = part.strip()
        if '=' in part:
            k, v = part.split('=', 1)
            tags[k.strip().lower()] = v.strip()
    return tags


def main():
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    rows = []
    for d in DOMAINS:
        rec = get_dmarc(d)
        if not rec:
            rows.append({'domain': d, 'dmarc': None, 'p': None, 'sp': None, 'pct': None, 'rua': None, 'raw': None})
            print(f'  {d:<22} NO DMARC')
            continue
        if rec.startswith('ERROR'):
            rows.append({'domain': d, 'dmarc': None, 'p': None, 'sp': None, 'pct': None, 'rua': None, 'raw': rec})
            print(f'  {d:<22} {rec}')
            continue
        tags = parse_tags(rec)
        row = {
            'domain': d,
            'dmarc': True,
            'p': tags.get('p'),
            'sp': tags.get('sp'),
            'pct': tags.get('pct'),
            'rua': tags.get('rua'),
            'raw': rec,
        }
        rows.append(row)
        sp_str = row['sp'] or '(arving fra p)'
        print(f'  {d:<22} p={row["p"]} sp={sp_str}')

    n_total = len(rows)
    n_with_sp = sum(1 for r in rows if r['sp'])
    n_without_sp = n_total - n_with_sp

    lines = []
    lines.append(f'# sp= subdomain-policy verifikasjon — {today}')
    lines.append('')
    lines.append(f'Sjekket {n_total} offentlige etater fra bloggposten 2026-05-12.')
    lines.append('')
    lines.append(f'- **{n_without_sp} av {n_total}** har INGEN sp= satt (subdomains arver p=none)')
    lines.append(f'- **{n_with_sp} av {n_total}** har sp= eksplisitt satt')
    lines.append('')
    lines.append('| # | Domene | p= | sp= | pct= | rua= |')
    lines.append('|---|---|---|---|---|---|')
    for i, r in enumerate(rows, 1):
        sp_disp = r['sp'] or '_(mangler — arver p=)_'
        rua_disp = (r['rua'] or '_(ingen)_')
        if rua_disp != '_(ingen)_' and len(rua_disp) > 50:
            rua_disp = rua_disp[:50] + '…'
        lines.append(f'| {i} | `{r["domain"]}` | {r["p"] or "_n/a_"} | {sp_disp} | {r["pct"] or "100"} | `{rua_disp}` |')

    lines.append('')
    lines.append('## Råverifikasjons-data')
    lines.append('')
    lines.append('```json')
    lines.append(json.dumps(rows, ensure_ascii=False, indent=2))
    lines.append('```')

    out = OUT_DIR / f'sp-verification-{today}.md'
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'\nRapport: {out}')
    print(f'Uten sp=: {n_without_sp}/{n_total}')


if __name__ == '__main__':
    main()
