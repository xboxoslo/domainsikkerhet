#!/usr/bin/env python3
"""
Generer /blogg/feed.xml RSS 2.0 fra alle blogg-poster.

Leser hver blogg/<slug>/index.html, plukker ut headline,
datePublished, description og bygger en RSS-feed sortert
nyeste først (siste 10).
"""
import html
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
BLOG = ROOT / 'blogg'
OUT = BLOG / 'feed.xml'

SITE = 'https://data1.no'


def extract(s: str, pattern: str) -> str | None:
    m = re.search(pattern, s)
    return m.group(1) if m else None


def read_post(d: Path) -> dict | None:
    f = d / 'index.html'
    if not f.exists():
        return None
    s = f.read_text(encoding='utf-8')

    headline = extract(s, r'"headline":"([^"]+)"')
    if not headline:
        m_howto = re.search(r'"@type":"HowTo"[^}]*?"name":"([^"]+)"', s)
        if m_howto:
            headline = m_howto.group(1)
    pub = extract(s, r'"datePublished":"([0-9-]+)"')
    desc = extract(s, r'<meta name="description" content="([^"]+)"')
    if not (headline and pub):
        return None

    try:
        pub_dt = datetime.strptime(pub, '%Y-%m-%d').replace(
            hour=9, minute=0, tzinfo=timezone.utc
        )
    except ValueError:
        return None

    return {
        'slug': d.name,
        'title': headline,
        'pub_dt': pub_dt,
        'description': desc or '',
        'url': f'{SITE}/blogg/{d.name}/',
    }


def main():
    posts = []
    for d in sorted(BLOG.iterdir()):
        if not d.is_dir() or d.name.startswith('_'):
            continue
        p = read_post(d)
        if p:
            posts.append(p)
    posts.sort(key=lambda p: p['pub_dt'], reverse=True)
    posts = posts[:10]

    now_rfc = format_datetime(datetime.now(timezone.utc))

    items = []
    for p in posts:
        items.append(f'''    <item>
      <title>{html.escape(p['title'])}</title>
      <link>{p['url']}</link>
      <guid isPermaLink="true">{p['url']}</guid>
      <pubDate>{format_datetime(p['pub_dt'])}</pubDate>
      <description>{html.escape(p['description'])}</description>
    </item>''')

    feed = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>data1.no — blogg om e-postsikkerhet</title>
    <link>{SITE}/blogg/</link>
    <atom:link href="{SITE}/blogg/feed.xml" rel="self" type="application/rss+xml" />
    <description>Praktiske guider på norsk om hvordan du beskytter e-post-domenet ditt mot phishing, spoofing og misbruk.</description>
    <language>nb-NO</language>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <generator>scripts/generate_rss.py</generator>
{chr(10).join(items)}
  </channel>
</rss>
'''

    OUT.write_text(feed, encoding='utf-8')
    print(f'Wrote {OUT} with {len(posts)} items')


if __name__ == '__main__':
    main()
