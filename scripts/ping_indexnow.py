#!/usr/bin/env python3
"""
Push nye / endrede URL-er til IndexNow (Bing, Yandex, Seznam).

IndexNow er en åpen protokoll der søkemotorer abonnerer på push-
notifikasjoner om innholdsendringer. Bypass-er crawl-køen.

Setup første gang:
  1. Generer en key (32 hex tegn)
  2. Lagre i miljøvariabel INDEXNOW_KEY (eller .env)
  3. Lag en verifikasjons-fil: <key>.txt i repo-rot med selve nøkkelen
     som innhold. Dette er hvordan IndexNow verifiserer at du eier domenet.
  4. Bekreft at https://data1.no/<key>.txt svarer 200 OK med nøkkelen

Bruk:
  python scripts/ping_indexnow.py                  # push siste 10 blogg-poster
  python scripts/ping_indexnow.py <url1> <url2>    # push spesifikke URL-er
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
BLOG = ROOT / 'blogg'
HOST = 'data1.no'
ENDPOINT = 'https://api.indexnow.org/indexnow'


def latest_blog_urls(limit: int = 10) -> list[str]:
    """Return URLs of N most recently published blog posts."""
    posts = []
    for d in BLOG.iterdir():
        if not d.is_dir() or d.name.startswith('_'):
            continue
        f = d / 'index.html'
        if not f.exists():
            continue
        s = f.read_text(encoding='utf-8', errors='ignore')
        m = re.search(r'"datePublished":"([0-9-]+)"', s)
        if m:
            posts.append((m.group(1), d.name))
    posts.sort(reverse=True)
    return [f'https://{HOST}/blogg/{slug}/' for _, slug in posts[:limit]]


def push(urls: list[str], key: str) -> None:
    payload = {
        'host': HOST,
        'key': key,
        'keyLocation': f'https://{HOST}/{key}.txt',
        'urlList': urls,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={'Content-Type': 'application/json; charset=utf-8'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            status = r.status
            body = r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode('utf-8', errors='replace')

    print(f'IndexNow status: {status}')
    if body:
        print(f'Body: {body}')

    if status == 200:
        print(f'OK — {len(urls)} URL-er pushet til IndexNow.')
    elif status == 202:
        print(f'Akseptert — venter på verifikasjon. Sjekk at https://{HOST}/{key}.txt svarer 200.')
    elif status == 422:
        print('FEIL — én eller flere URL-er er ugyldige eller ikke under host.')
    else:
        print('FEIL — sjekk dokumentasjon på https://www.indexnow.org')


def main():
    key = os.environ.get('INDEXNOW_KEY')
    if not key:
        sys.exit(
            'Mangler INDEXNOW_KEY. Generer med:\n'
            '  python -c "import secrets; print(secrets.token_hex(16))"\n'
            'Lagre i environment, lag <key>.txt i repo-rot med nøkkelen, '
            'commit den, og kjør på nytt.'
        )

    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    else:
        urls = latest_blog_urls(limit=10)

    if not urls:
        sys.exit('Ingen URL-er å pushe.')

    print(f'Pusher {len(urls)} URL-er:')
    for u in urls:
        print(f'  {u}')
    push(urls, key)


if __name__ == '__main__':
    main()
