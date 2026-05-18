"""Generer dashboard-data/competitors.json.

V1: skraper offentlig sitemap.xml fra hver konkurrent for å telle indekserte sider,
og oppdaterer lastUpdated. Domain Rating og backlinks krever Ahrefs/SEMrush
og legges inn manuelt eller via MCP-tool senere.

Kjør: python scripts/dashboard_competitors_sync.py
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / 'dashboard-data' / 'competitors.json'

USER_AGENT = 'data1-dashboard-competitors-sync/1.0'
SITEMAP_CANDIDATES = [
    '/sitemap.xml', '/sitemap_index.xml', '/sitemap-index.xml', '/post-sitemap.xml',
]


def fetch_text(url: str, timeout: int = 15) -> str | None:
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception:
        return None


def count_sitemap_locs(domain: str) -> int | None:
    base = f'https://{domain}'
    for path in SITEMAP_CANDIDATES:
        txt = fetch_text(base + path)
        if txt:
            # Tell <loc>...</loc> som peker tilbake til domenet
            locs = re.findall(r'<loc>([^<]+)</loc>', txt)
            same_domain = [u for u in locs if domain in u]
            return len(same_domain) if same_domain else len(locs)
    return None


def last_modified(domain: str) -> str | None:
    """Hent siste <lastmod> fra sitemap (best-effort)."""
    base = f'https://{domain}'
    for path in SITEMAP_CANDIDATES:
        txt = fetch_text(base + path)
        if not txt:
            continue
        dates = re.findall(r'<lastmod>([^<]+)</lastmod>', txt)
        if dates:
            try:
                ds = sorted(dates, reverse=True)
                d = datetime.fromisoformat(ds[0].rstrip('Z').replace('Z', ''))
                return d.strftime('%d. %B %Y').lower()
            except Exception:
                return ds[0][:10]
    return None


def main():
    existing = {'competitors': []}
    if OUT_FILE.exists():
        try:
            existing = json.loads(OUT_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass

    competitors = existing.get('competitors', [])
    domain_map = {
        'data1.no': 'data1.no',
        'sjekk.email': 'sjekk.email',
        'dmarcstatus.no': 'dmarcstatus.no',
        'mxtoolbox.com': 'mxtoolbox.com',
        'easydmarc.com': 'easydmarc.com',
        'powerdmarc.com': 'powerdmarc.com',
        'dmarcian.com': 'dmarcian.com',
        'valimail.com': 'valimail.com',
    }

    updated = []
    for c in competitors:
        domain = domain_map.get(c.get('name'))
        if domain:
            count = count_sitemap_locs(domain)
            if count is not None:
                c['indexedPages'] = count
                print(f'  {domain:25} {count:>5} indekserte sider')
            else:
                print(f'  {domain:25} (sitemap utilgjengelig — beholder eksisterende verdi)')
            lm = last_modified(domain)
            if lm:
                c['lastArticle'] = lm
        updated.append(c)

    payload = {
        'lastUpdated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'competitors': updated,
        'note': existing.get('note', 'Domain Rating fra Ahrefs/SEMrush — manuell oppdatering i v1.'),
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'OK — skrev {OUT_FILE.relative_to(ROOT)}')


if __name__ == '__main__':
    sys.exit(main() or 0)
