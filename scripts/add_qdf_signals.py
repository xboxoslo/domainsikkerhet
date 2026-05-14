#!/usr/bin/env python3
"""
Add QDF (Query Deserves Freshness) signals to all blog posts:
- article:published_time + article:modified_time OG-tags
- Wrap visible "Publisert ... mai 2026" date in <time datetime="...">
- Change schema-type Article -> NewsArticle for rapport-style posts
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
BLOG = ROOT / 'blogg'

NEWS_POSTS = {
    'offentlige-etater-dmarc-overvaking-2026',
    'equinor-hydro-og-yara-tre-industrigiganter-uten-e-postsikker',
    'norske-storselskaper-uten-grunnleggende-e-postsikkerhet',
}


def iso_date(yyyy_mm_dd: str) -> str:
    return f'{yyyy_mm_dd}T09:00:00+00:00'


def update_post(post_dir: Path):
    f = post_dir / 'index.html'
    if not f.exists():
        return False
    s = f.read_text(encoding='utf-8')
    original = s

    m = re.search(r'"datePublished":"([0-9-]+)"', s)
    if not m:
        print(f'  SKIP {post_dir.name} — no datePublished')
        return False
    pub_iso = iso_date(m.group(1))

    m2 = re.search(r'"dateModified":"([0-9-]+)"', s)
    mod_iso = iso_date(m2.group(1)) if m2 else pub_iso

    if 'article:published_time' not in s:
        og_block_end = re.search(
            r'(<meta property="og:url"[^>]*>\n)',
            s
        )
        if og_block_end:
            insert = (
                f'<meta property="article:published_time" content="{pub_iso}">\n'
                f'<meta property="article:modified_time" content="{mod_iso}">\n'
            )
            s = s[:og_block_end.end()] + insert + s[og_block_end.end():]

    s = re.sub(
        r'<p class="meta">Publisert ([0-9]+\. \w+ [0-9]{4})',
        lambda mm: f'<p class="meta">Publisert <time datetime="{pub_iso[:10]}">{mm.group(1)}</time>',
        s
    )

    if post_dir.name in NEWS_POSTS:
        s = s.replace('"@type":"Article"', '"@type":"NewsArticle"', 1)

    if s != original:
        f.write_text(s, encoding='utf-8')
        return True
    return False


def main():
    changed = []
    for d in sorted(BLOG.iterdir()):
        if not d.is_dir():
            continue
        if d.name.startswith('_'):
            continue
        if update_post(d):
            changed.append(d.name)
            print(f'  OK   {d.name}')
        else:
            print(f'  (no changes) {d.name}')
    print(f'\nUpdated {len(changed)} posts.')


if __name__ == '__main__':
    main()
