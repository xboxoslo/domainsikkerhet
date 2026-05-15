"""
Auto-genererer blogg-index ved å lese metadata fra alle index.html i /blogg/.

Kjøres etter weekly_blogpost.py så nye AI-genererte poster automatisk
dukker opp i blog-listingen.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
BLOG_DIR = ROOT / 'blogg'
INDEX_FILE = BLOG_DIR / 'index.html'

# Tags basert på slug-mønstre
TAG_RULES = [
    (r'microsoft-365$', 'Microsoft 365', '#0078d4'),
    (r'google-workspace$', 'Google Workspace', '#34a853'),
    (r'^dmarc-', 'DMARC', '#14b8a6'),
    (r'^spf-', 'SPF', '#0ea5e9'),
    (r'^dmarc$', 'DMARC', '#14b8a6'),
    (r'^spf$', 'SPF', '#0ea5e9'),
    (r'^dkim$', 'DKIM', '#8b5cf6'),
    (r'mta-?sts', 'MTA-STS', '#f59e0b'),
    (r'bimi', 'BIMI', '#ec4899'),
]

NORWEGIAN_MONTHS = {
    1: 'januar', 2: 'februar', 3: 'mars', 4: 'april', 5: 'mai', 6: 'juni',
    7: 'juli', 8: 'august', 9: 'september', 10: 'oktober', 11: 'november', 12: 'desember',
}


def detect_tag(slug: str) -> tuple[str, str]:
    for pattern, tag, color in TAG_RULES:
        if re.search(pattern, slug, re.I):
            return tag, color
    # Default for AI-genererte ukerapporter
    if any(w in slug.lower() for w in ['uke', 'rapport', 'analyse']):
        return 'Ukerapport', '#dc2626'
    return 'Analyse', '#64748b'


def parse_post(post_dir: Path) -> dict | None:
    f = post_dir / 'index.html'
    if not f.exists():
        return None
    html = f.read_text(encoding='utf-8', errors='replace')

    title_m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
    desc_m = re.search(r'<meta property="og:description" content="([^"]+)"', html)
    if not desc_m:
        desc_m = re.search(r'<meta name="description" content="([^"]+)"', html)
    date_m = re.search(r'"datePublished":"([^"]+)"', html)

    if not title_m:
        return None

    title = title_m.group(1).strip()
    desc = desc_m.group(1).strip() if desc_m else ''
    if len(desc) > 180:
        desc = desc[:177] + '…'

    date_str = date_m.group(1) if date_m else None
    try:
        date = datetime.fromisoformat(date_str) if date_str else None
    except Exception:
        date = None

    # Anslå lesetid (1 min per ~250 ord)
    text = re.sub(r'<[^>]+>', ' ', html)
    word_count = len(text.split())
    read_min = max(2, word_count // 250)

    tag, color = detect_tag(post_dir.name)

    return {
        'slug': post_dir.name,
        'title': title,
        'desc': desc,
        'date': date,
        'tag': tag,
        'tag_color': color,
        'read_min': read_min,
    }


def format_date(d: datetime | None) -> str:
    if not d:
        return 'Nylig'
    return f'{d.day}. {NORWEGIAN_MONTHS[d.month]} {d.year}'


def main():
    posts = []
    for sub in BLOG_DIR.iterdir():
        if sub.is_dir() and not sub.name.startswith('_'):
            p = parse_post(sub)
            if p:
                posts.append(p)

    def _sort_key(p):
        d = p['date']
        if d is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if d.tzinfo is None:
            return d.replace(tzinfo=timezone.utc)
        return d
    posts.sort(key=_sort_key, reverse=True)

    # Bygg HTML-fragmenter for postene
    posts_html = []
    for p in posts:
        date_str = format_date(p['date'])
        posts_html.append(f'''    <a href="/blogg/{p["slug"]}/" class="post">
      <span class="post-tag" style="background:{p["tag_color"]};color:#fff">{p["tag"]}</span>
      <h2>{p["title"]}</h2>
      <p>{p["desc"]}</p>
      <div class="post-meta">{date_str} · {p["read_min"]} min lesetid</div>
    </a>''')

    # Les eksisterende index.html og bytt ut posts-blokken
    if INDEX_FILE.exists():
        existing = INDEX_FILE.read_text(encoding='utf-8')
        new_posts_block = '<div class="posts">\n' + '\n'.join(posts_html) + '\n  </div>'
        # Match fra <div class="posts"> til neste </div> som er på samme indent
        new_html = re.sub(
            r'<div class="posts">.*?</div>(\s*</main>)',
            new_posts_block + r'\1',
            existing,
            count=1,
            flags=re.DOTALL,
        )
        if new_html == existing:
            print('ADVARSEL: Fant ikke <div class="posts"> i index.html, ingen oppdatering gjort.')
            return
        INDEX_FILE.write_text(new_html, encoding='utf-8')
        print(f'Blogg-index oppdatert: {len(posts)} poster listet.')
        for p in posts[:5]:
            print(f'  - {p["title"][:60]}  ({format_date(p["date"])})')
    else:
        print('FEIL: blogg/index.html finnes ikke.')


if __name__ == '__main__':
    main()

