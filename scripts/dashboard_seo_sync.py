"""Generer dashboard-data/seo.json fra Google Search Console API.

Krever miljøvariabler (sett som GitHub Secrets / lokal env):
  GSC_CLIENT_ID          OAuth2 client ID
  GSC_CLIENT_SECRET      OAuth2 client secret
  GSC_REFRESH_TOKEN      Refresh-token (engangs-oppsett, se docs/)
  GSC_SITE_URL           https://data1.no/  (default)

Hvis nøklene mangler: oppdater bare lastUpdated og _note, ikke feil.
Det betyr workflow ikke krasjer før OAuth er satt opp.

Kjør: python scripts/dashboard_seo_sync.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / 'dashboard-data' / 'seo.json'

SITE_URL = os.environ.get('GSC_SITE_URL', 'https://data1.no/')
USER_AGENT = 'data1-dashboard-seo-sync/1.0'


def http_json(url: str, headers: dict, body: dict | None = None, method: str = 'GET', timeout: int = 30) -> dict | None:
    data = json.dumps(body).encode('utf-8') if body else None
    headers = {**headers, 'User-Agent': USER_AGENT}
    if body:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print(f'  HTTP-feil ({method} {url}): {e}', file=sys.stderr)
        return None


def get_access_token() -> str | None:
    client_id = os.environ.get('GSC_CLIENT_ID')
    client_secret = os.environ.get('GSC_CLIENT_SECRET')
    refresh = os.environ.get('GSC_REFRESH_TOKEN')
    if not all([client_id, client_secret, refresh]):
        return None
    body = urllib.parse.urlencode({
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh,
        'grant_type': 'refresh_token',
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://oauth2.googleapis.com/token',
        data=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': USER_AGENT},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode('utf-8'))['access_token']
    except Exception as e:
        print(f'OAuth token-refresh feilet: {e}', file=sys.stderr)
        return None


def query_gsc(access_token: str, body: dict) -> dict | None:
    encoded_site = urllib.parse.quote(SITE_URL, safe='')
    url = f'https://searchconsole.googleapis.com/v1/sites/{encoded_site}/searchAnalytics/query'
    return http_json(url, {'Authorization': f'Bearer {access_token}'}, body=body, method='POST')


def fetch_seo_data(token: str) -> dict | None:
    today = datetime.now(timezone.utc).date()
    last_28 = today - timedelta(days=28)
    last_90 = today - timedelta(days=90)

    timeline_resp = query_gsc(token, {
        'startDate': str(last_90), 'endDate': str(today),
        'dimensions': ['date'], 'rowLimit': 200,
    })
    queries_resp = query_gsc(token, {
        'startDate': str(last_28), 'endDate': str(today),
        'dimensions': ['query'], 'rowLimit': 50,
    })
    pages_resp = query_gsc(token, {
        'startDate': str(last_28), 'endDate': str(today),
        'dimensions': ['page'], 'rowLimit': 25,
    })
    summary_resp = query_gsc(token, {
        'startDate': str(last_28), 'endDate': str(today),
        'dimensions': [], 'rowLimit': 1,
    })
    if not all([timeline_resp, queries_resp, pages_resp, summary_resp]):
        return None

    s = summary_resp.get('rows', [{}])[0] if summary_resp.get('rows') else {}
    timeline = [
        {'date': r['keys'][0], 'clicks': r.get('clicks', 0), 'impressions': r.get('impressions', 0)}
        for r in (timeline_resp.get('rows') or [])
    ]
    top_queries = [
        {'query': r['keys'][0], 'clicks': r.get('clicks', 0), 'impressions': r.get('impressions', 0), 'position': r.get('position', 0)}
        for r in (queries_resp.get('rows') or [])
    ]
    top_pages = [
        {'url': urllib.parse.urlparse(r['keys'][0]).path or '/', 'clicks': r.get('clicks', 0), 'impressions': r.get('impressions', 0)}
        for r in (pages_resp.get('rows') or [])
    ]

    # Sitemap-størrelse for totalPages
    total_pages = 0
    try:
        sitemap = (ROOT / 'sitemap.xml').read_text(encoding='utf-8')
        total_pages = sitemap.count('<loc>')
    except Exception:
        pass

    return {
        'lastUpdated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'summary': {
            'indexedPages': len(top_pages),  # heuristisk — sider med klikk/visning er indeksert
            'totalPages': total_pages or 200,
            'clicks28d': int(s.get('clicks', 0)),
            'impressions28d': int(s.get('impressions', 0)),
            'avgPosition': round(s.get('position', 0), 1),
            'ctr': round(s.get('ctr', 0) * 100, 2),
        },
        'timeline': timeline,
        'topQueries': top_queries,
        'topPages': top_pages,
        'indexingStatus': [],  # urlInspection-API krever separat per-URL-kall; hopper i v1
    }


def main():
    token = get_access_token()
    if not token:
        print('GSC OAuth ikke konfigurert (mangler GSC_CLIENT_ID/SECRET/REFRESH_TOKEN). Beholder eksisterende seo.json.')
        if OUT_FILE.exists():
            d = json.loads(OUT_FILE.read_text(encoding='utf-8'))
            d['lastUpdated'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            d['_note'] = 'GSC OAuth ikke konfigurert. Se docs/dashboard-n8n-setup.md for engangs-oppsett.'
            OUT_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        return 0

    data = fetch_seo_data(token)
    if not data:
        print('GSC-spørringer feilet. Beholder eksisterende fil.', file=sys.stderr)
        return 1

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'OK — skrev {OUT_FILE.relative_to(ROOT)}')
    print(f'  Klikk 28d:     {data["summary"]["clicks28d"]}')
    print(f'  Visninger 28d: {data["summary"]["impressions28d"]}')
    print(f'  Søkeord:        {len(data["topQueries"])}')


if __name__ == '__main__':
    sys.exit(main() or 0)
