"""
Generate weekly blog post via Claude API based on snapshot trends.

Kjøres ukentlig av GitHub Actions. Analyserer siste snapshot vs forrige uke,
og kaller Claude API for å skrive en bloggpost basert på funnene.

Krever ANTHROPIC_API_KEY som miljøvariabel.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
SNAPSHOTS_DIR = ROOT / '_data' / 'snapshots'
BLOG_DIR = ROOT / 'blogg'
DRAFTS_DIR = ROOT / '_drafts'
DRAFTS_DIR.mkdir(exist_ok=True)

API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not API_KEY:
    print('FEIL: ANTHROPIC_API_KEY ikke satt. Avbryter.')
    sys.exit(1)

MODEL = 'claude-sonnet-4-6'
MAX_TOKENS = 4000
API_URL = 'https://api.anthropic.com/v1/messages'


def call_claude(system_prompt: str, user_prompt: str) -> str:
    """Kall Claude API og returner tekst-svar."""
    payload = {
        'model': MODEL,
        'max_tokens': MAX_TOKENS,
        'system': system_prompt,
        'messages': [{'role': 'user', 'content': user_prompt}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={
            'Content-Type': 'application/json',
            'x-api-key': API_KEY,
            'anthropic-version': '2023-06-01',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data['content'][0]['text']


def load_snapshots() -> tuple[dict | None, dict | None]:
    files = sorted(SNAPSHOTS_DIR.glob('*.json'))
    if len(files) < 2:
        return (json.loads(files[0].read_text(encoding='utf-8')) if files else None, None)
    latest = json.loads(files[-1].read_text(encoding='utf-8'))
    target = datetime.fromisoformat(latest['timestamp']) - timedelta(days=7)
    older = None
    for f in reversed(files[:-1]):
        s = json.loads(f.read_text(encoding='utf-8'))
        if datetime.fromisoformat(s['timestamp']) <= target:
            older = s
            break
    if older is None:
        older = json.loads(files[0].read_text(encoding='utf-8'))
    return latest, older


def build_data_summary(latest: dict, older: dict | None) -> str:
    """Bygg en kompakt tekst-oppsummering av dataen som Claude kan jobbe ut fra."""
    s = latest['summary']
    summary = f"""## Ukens DMARC-status — {latest['date']}

Totalt analysert: {len(latest['results'])} norske domener
Snitt-score: {s.get('avg_score', 0):.1f}/100
Med p=reject (full beskyttelse): {s.get('has_dmarc_reject', 0)}
Mangler DMARC: {s.get('no_dmarc', 0)}
Karakter-fordeling: {s.get('grade_distribution', {})}

## Topp 10 best beskyttede:
"""
    sorted_results = sorted([r for r in latest['results'] if 'score' in r],
                            key=lambda x: -x['score'])
    for r in sorted_results[:10]:
        summary += f"  - {r['domain']:30s} {r['grade']:3s} ({r['score']}p)\n"

    summary += "\n## Bunn 10 (verst):\n"
    for r in sorted_results[-10:]:
        summary += f"  - {r['domain']:30s} {r['grade']:3s} ({r['score']}p)\n"

    if older:
        old_scores = {r['domain']: r.get('score', 0) for r in older.get('results', [])}
        improvements = []
        regressions = []
        for r in latest['results']:
            old_s = old_scores.get(r['domain'], r.get('score', 0))
            diff = r.get('score', 0) - old_s
            if diff >= 5:
                improvements.append((r['domain'], old_s, r['score'], r['grade'], diff))
            elif diff <= -5:
                regressions.append((r['domain'], old_s, r['score'], r['grade'], diff))

        improvements.sort(key=lambda x: -x[4])
        regressions.sort(key=lambda x: x[4])

        if improvements:
            summary += f"\n## Største forbedringer ({len(improvements)} totalt):\n"
            for d, o, n, g, diff in improvements[:10]:
                summary += f"  - {d:30s} {o} → {n} (+{diff}p, karakter {g})\n"
        if regressions:
            summary += f"\n## Største forverringer ({len(regressions)} totalt):\n"
            for d, o, n, g, diff in regressions[:10]:
                summary += f"  - {d:30s} {o} → {n} ({diff}p, karakter {g})\n"

    return summary


SYSTEM_PROMPT = """Du er en norsk fagskribent for data1.no, et gratis verktøy som analyserer e-postsikkerhet
(SPF, DMARC, DKIM, MTA-STS, TLS-RPT, BIMI) for norske domener. Drevet av Micronet AS.

Du skriver ukentlige bloggposter basert på faktiske DMARC-data fra norske domener. Skrivestil:
- Norsk bokmål
- Klart, direkte språk uten unødvendige tekniske detaljer
- Konkrete tall og funn — siter alltid spesifikke domener fra dataen
- Praktisk og handlingsrettet
- Ikke bruk "vi" om data1.no — skriv i 3. person eller bruk passiv form
- Hvis du nevner en bedrift som scorer dårlig, gjør det faktabasert (ingen hån)

Format på output: REN HTML-fragmenter (ikke full HTML-side, bare innholdet i <main>). Bruk:
- <h1> for tittel
- <p class="lead"> for ingress (1 setning)
- <p class="meta"> for "Publisert DD. mmm YYYY · Av Micronet · X min lesetid"
- <h2 id="..."> for seksjonsoverskrifter
- <h3> for underseksjoner
- <p>, <ul>, <ol>, <strong>, <code> som vanlig
- <table> for sammenligninger (med class="data-table")
- <div class="callout warn"> for advarsler eller viktige tall
- Lenker: <a href="/?d=domene.no">domene.no</a> for å lenke til analyse av et spesifikt domene
- Lenker til /trender/ og /sammenligning/ der relevant

IKKE inkluder <html>, <head>, <body>, <header>, <nav>, eller <footer>. Bare innhold som går inn i <main>.

Lengde: 600-1000 ord. Inkluder konkrete handlingsråd til lesere.
"""


def main():
    latest, older = load_snapshots()
    if not latest:
        print('Ingen snapshots tilgjengelig — kan ikke generere bloggpost.')
        sys.exit(0)

    data_summary = build_data_summary(latest, older)
    print('=== Data-oppsummering sendt til Claude: ===')
    print(data_summary)
    print('=' * 60)

    today = datetime.fromisoformat(latest['timestamp'])
    week_num = today.isocalendar()[1]
    year = today.year

    user_prompt = f"""Skriv ukens bloggpost for data1.no basert på dataen under.

Tittelforslag (velg det som passer best, eller foreslå eget):
- "Ukens DMARC-rapport: Slik står det til med norsk e-postsikkerhet i uke {week_num}"
- "[Topptema fra dataen] — uke {week_num}-rapport"
- "Disse norske domenene forbedret seg mest siste uke"

Velg en vinkel basert på det mest interessante du ser i dataen — kan være:
- En bransje (f.eks. banker, kommuner, e-handel) som peker seg ut
- Et spesifikt domene som har gjort store endringer
- En generell trend (flere/færre med p=reject)
- En bestemt protokoll (f.eks. økning i MTA-STS)

DATA:

{data_summary}

Husk: Skriv som ren HTML-fragmenter (uten <html>/<head>/<body>). Tittel som <h1>, ingress som <p class="lead">, meta som <p class="meta">.
Lenk til konkrete domener med <a href="/?d=DOMENE">DOMENE</a>. Lenk til /trender/ og /sammenligning/ der det passer.
"""

    print('Kaller Claude API...')
    body_html = call_claude(SYSTEM_PROMPT, user_prompt)
    print(f'Mottok {len(body_html)} tegn med HTML.')

    # Lag slug fra første <h1>
    h1_match = re.search(r'<h1[^>]*>(.+?)</h1>', body_html)
    title = h1_match.group(1).strip() if h1_match else f'Ukerapport {week_num}'
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:60]

    # Pakk inn i full HTML-template
    date_iso = today.strftime('%Y-%m-%d')
    full_html = f'''<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<meta name="description" content="{title} — ukentlig DMARC-analyse fra data1.no.">
<meta name="author" content="Terje Otterlei">
<meta name="theme-color" content="#1a202c">
<link rel="canonical" href="https://data1.no/blogg/{slug}/">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:image" content="https://data1.no/og-image.png">
<title>{title} | data1.no</title>
<link rel="stylesheet" href="/blogg/_assets/post.css">
<style>
.data-table{{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05)}}
.data-table th{{background:#0f172a;color:#fff;text-align:left;padding:10px 12px;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}
.data-table td{{padding:10px 12px;border-bottom:1px solid #f1f5f9}}
.callout{{background:#f0fdfa;border-left:4px solid #14b8a6;padding:14px 18px;border-radius:0 10px 10px 0;margin:18px 0}}
.callout.warn{{background:#fff7ed;border-left-color:#f97316;color:#7c2d12}}
.meta{{font-size:13px;color:#64748b;margin-bottom:22px}}
.lead{{font-size:18px;color:#475569;margin-bottom:24px;line-height:1.7}}
</style>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":"{title}","datePublished":"{date_iso}","dateModified":"{date_iso}","author":{{"@type":"Organization","name":"Micronet","url":"https://micronet.no/"}},"publisher":{{"@type":"Organization","name":"data1.no","logo":{{"@type":"ImageObject","url":"https://data1.no/og-image.png"}}}},"description":"{title}","image":"https://data1.no/og-image.png","mainEntityOfPage":"https://data1.no/blogg/{slug}/","inLanguage":"nb-NO"}}</script>
</head>
<body>
<header class="header">
<a href="/" class="logo">data1<span>.no</span></a>
<div class="spacer"></div>
<a href="/" class="nav-link">Sjekk eget domene →</a>
</header>
<main>
<nav class="crumbs"><a href="/">Hjem</a> › <a href="/blogg/">Blogg</a> › Ukerapport {week_num}</nav>
{body_html}

<div style="margin-top:40px;padding:20px;background:#f0fdfa;border-radius:12px;border:1px solid #99f6e4">
<h3 style="margin-bottom:8px">Sjekk ditt eget domene</h3>
<p style="margin-bottom:14px">Få samme analyse for ditt domene på 10 sekunder, helt gratis.</p>
<a href="/" style="display:inline-block;background:#14b8a6;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;font-weight:700">Kjør analyse →</a>
</div>
</main>
</body>
</html>
'''

    target = BLOG_DIR / slug
    target.mkdir(exist_ok=True)
    out = target / 'index.html'
    out.write_text(full_html, encoding='utf-8')
    print(f'Bloggpost lagret: {out.relative_to(ROOT)}')
    print(f'Tittel: {title}')

    # Generer LinkedIn-utkast
    print('\nGenererer LinkedIn-utkast...')
    li_prompt = f"""Basert på bloggposten under, skriv en LinkedIn-post (300-500 tegn) som leder lesere til artikkelen.
Bruk emojier sparsomt, ha ett konkret tall fra dataen, og avslutt med spørsmål eller call-to-action.
Lenke å bruke: https://data1.no/blogg/{slug}/

BLOGGPOST:
{body_html[:3000]}
"""
    li_text = call_claude(
        "Du skriver konsise, engasjerende LinkedIn-poster på norsk for B2B-publikum. Maks 500 tegn.",
        li_prompt,
    )
    li_file = DRAFTS_DIR / f'linkedin-{date_iso}.txt'
    li_file.write_text(li_text, encoding='utf-8')
    print(f'LinkedIn-utkast: {li_file.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
