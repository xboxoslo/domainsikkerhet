"""
Auto-update sitemap.xml — sørger for at alle HTML-sider er listet og at lastmod stemmer.
Kjøres etter daglig scan så /trender/ alltid har dagens dato.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
SITEMAP = ROOT / 'sitemap.xml'

today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

# Sider som skal alltid finnes i sitemap (path -> priority)
PAGES = {
    '/': 1.0,
    '/om/': 0.7,
    '/trender/': 0.95,
    '/sammenligning/': 0.85,
    '/ordbok/': 0.85,
    '/sertifikat/': 0.6,
    '/blogg/': 0.7,
    '/blogg/dmarc/': 0.85,
    '/blogg/spf/': 0.8,
    '/blogg/dkim/': 0.8,
    '/blogg/dmarc-microsoft-365/': 0.85,
    '/blogg/dmarc-google-workspace/': 0.85,
    '/blogg/spf-microsoft-365/': 0.85,
    '/verktoy/dmarc-generator/': 0.9,
    '/verktoy/spf-generator/': 0.9,
    '/rapport-2026/': 0.9,
    '/rapport-2026/banker/': 0.85,
    '/rapport-2026/kommuner/': 0.85,
    '/rapport-2026/e-handel/': 0.85,
    '/rapport-2026/medier/': 0.85,
}


def lastmod_for(path: str) -> str:
    """Bruk filsystemets mtime, eller dagens dato hvis filen ikke finnes."""
    if path == '/':
        f = ROOT / 'index.html'
    else:
        f = ROOT / path.strip('/') / 'index.html'
    if f.exists():
        ts = f.stat().st_mtime
        return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d')
    return today


def main():
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, prio in PAGES.items():
        url = f'https://data1.no{path}'
        lm = lastmod_for(path)
        # Trender-siden oppdateres daglig
        if path == '/trender/':
            lm = today
            freq = 'daily'
        elif 'rapport' in path:
            freq = 'weekly'
        elif 'blogg' in path or 'verktoy' in path:
            freq = 'monthly'
        else:
            freq = 'monthly'
        lines.append(f'  <url>')
        lines.append(f'    <loc>{url}</loc>')
        lines.append(f'    <lastmod>{lm}</lastmod>')
        lines.append(f'    <changefreq>{freq}</changefreq>')
        lines.append(f'    <priority>{prio}</priority>')
        lines.append(f'  </url>')
    lines.append('</urlset>')

    SITEMAP.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Sitemap oppdatert: {len(PAGES)} URL-er, lastmod for /trender/ = {today}')


if __name__ == '__main__':
    main()
