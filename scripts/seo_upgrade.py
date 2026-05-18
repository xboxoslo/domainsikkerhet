"""SEO + AI-synlighet-oppgradering for data1.no.

Fase 1: forfatter (Micronet -> Terje Otterlei), trim keywords til <= 7
Fase 2: Article-schema med Person-author, SoftwareApplication på verktøy/
Fase 3: Generer /llms.txt og /llms-full.txt fra blogg-katalogen

Idempotent. Kjor:
  python scripts/seo_upgrade.py phase1
  python scripts/seo_upgrade.py phase2
  python scripts/seo_upgrade.py phase3
  python scripts/seo_upgrade.py all
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW_AUTHOR_NAME = "Terje Otterlei"

PERSON_AUTHOR = {
    "@type": "Person",
    "name": "Terje Otterlei",
    "jobTitle": "Daglig leder",
    "worksFor": {
        "@type": "Organization",
        "name": "Micronet AS",
        "url": "https://micronet.no/",
    },
    "url": "https://data1.no/om/",
}

# ----- Filtrering -----

EXCLUDE_DIRS = {'.git', '.claude', '.tmp', '_data', 'node_modules', 'fonts',
                '__pycache__', '.venv', 'venv'}


def html_files() -> list[Path]:
    out = []
    for p in ROOT.rglob('*.html'):
        rel_parts = p.relative_to(ROOT).parts
        if any(part in EXCLUDE_DIRS for part in rel_parts):
            continue
        out.append(p)
    return sorted(out)


# ----- Fase 1 -----

def phase1():
    """Forfatter + keywords."""
    changed_author = 0
    changed_keywords = 0
    for fp in html_files():
        txt = fp.read_text(encoding='utf-8')
        orig = txt

        # 1.2 Forfatter — kun <meta name="author" ...>
        # Micronet, Micronet AS -> Terje Otterlei
        txt, n = re.subn(
            r'(<meta\s+name="author"\s+content=")(?:Micronet(?:\s+AS)?)(")',
            rf'\1{NEW_AUTHOR_NAME}\2',
            txt,
        )
        if n:
            changed_author += 1

        # 1.3 Trim keywords til max 7 termer
        def _trim(m):
            terms = [t.strip() for t in m.group(2).split(',') if t.strip()]
            if len(terms) <= 7:
                return m.group(0)
            return m.group(1) + ', '.join(terms[:7]) + m.group(3)

        new_txt, n = re.subn(
            r'(<meta\s+name="keywords"\s+content=")([^"]+)(")',
            _trim, txt,
        )
        if n and new_txt != txt:
            changed_keywords += 1
            txt = new_txt

        if txt != orig:
            fp.write_text(txt, encoding='utf-8', newline='\n')

    # Oppdater Python-generatorer
    gen_changed = 0
    for sp in [ROOT / 'scripts' / s for s in
               ('generate_domain_pages.py', 'weekly_blogpost.py', 'generate_trends.py')]:
        if not sp.exists():
            continue
        t = sp.read_text(encoding='utf-8')
        orig = t
        # Forfatter-strenger i Python-templates
        t = re.sub(r'(<meta\s+name="author"\s+content=")Micronet(?:\s+AS)?(")',
                   rf'\1{NEW_AUTHOR_NAME}\2', t)
        if t != orig:
            sp.write_text(t, encoding='utf-8', newline='\n')
            gen_changed += 1

    print(f'Fase 1 ferdig:')
    print(f'  Forfatter oppdatert i {changed_author} HTML-filer')
    print(f'  Keywords trimmet i {changed_keywords} HTML-filer')
    print(f'  Generatorer oppdatert: {gen_changed}')


# ----- Fase 2 -----

JSON_LD_RE = re.compile(
    r'<script\s+type="application/ld\+json">(.*?)</script>',
    re.DOTALL,
)


def _modify_jsonld_in_html(html: str, modifier) -> tuple[str, int]:
    """Finn alle JSON-LD-blokker, parse, send til modifier(data), serialize tilbake.
    Modifier returnerer ny data (eller samme). Returner (ny html, antall endringer).
    """
    changes = 0

    def _repl(m):
        nonlocal changes
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return m.group(0)
        new_data = modifier(data)
        if new_data == data:
            return m.group(0)
        changes += 1
        return f'<script type="application/ld+json">{json.dumps(new_data, ensure_ascii=False, separators=(",", ":"))}</script>'

    return JSON_LD_RE.sub(_repl, html), changes


def _set_person_author_in_article(data):
    """Hvis data inneholder @type=Article med Organization-author, bytt til Person."""
    if not isinstance(data, dict):
        return data
    types = data.get('@type')
    if types == 'Article' or (isinstance(types, list) and 'Article' in types):
        author = data.get('author')
        if isinstance(author, dict) and author.get('@type') == 'Organization':
            # Erstatt med Person, men behold koblingen til Micronet AS via worksFor
            data = {**data, 'author': dict(PERSON_AUTHOR)}
    # Rekurser inn i nested objects og lister
    if isinstance(data, dict):
        for k, v in list(data.items()):
            if k in ('publisher', 'parentOrganization'):
                continue  # publisher skal forbli Organization
            data[k] = _set_person_author_in_article(v)
    elif isinstance(data, list):
        return [_set_person_author_in_article(x) for x in data]
    return data


SOFTWAREAPP_TEMPLATES = {
    'verktoy/dmarc-generator/index.html': {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "DMARC-generator",
        "description": "Gratis verktøy for å generere DMARC DNS-record på norsk.",
        "applicationCategory": "SecurityApplication",
        "operatingSystem": "Web",
        "url": "https://data1.no/verktoy/dmarc-generator/",
        "inLanguage": "nb-NO",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "NOK"},
        "publisher": {"@type": "Organization", "name": "Micronet AS", "url": "https://micronet.no/"},
        "author": dict(PERSON_AUTHOR),
    },
    'verktoy/spf-generator/index.html': {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "SPF-generator",
        "description": "Gratis verktøy for å generere SPF DNS-record på norsk.",
        "applicationCategory": "SecurityApplication",
        "operatingSystem": "Web",
        "url": "https://data1.no/verktoy/spf-generator/",
        "inLanguage": "nb-NO",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "NOK"},
        "publisher": {"@type": "Organization", "name": "Micronet AS", "url": "https://micronet.no/"},
        "author": dict(PERSON_AUTHOR),
    },
}


def _add_softwareapp_if_missing(fp: Path) -> bool:
    rel = fp.relative_to(ROOT).as_posix()
    if rel not in SOFTWAREAPP_TEMPLATES:
        return False
    txt = fp.read_text(encoding='utf-8')
    # Sjekk om SoftwareApplication allerede finnes for denne URL-en
    if '"@type":"SoftwareApplication"' in txt and 'verktoy' in txt:
        return False
    schema = SOFTWAREAPP_TEMPLATES[rel]
    inject = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}</script>\n'
    # Sett inn rett foer </head>
    new_txt, n = re.subn(r'</head>', inject + '</head>', txt, count=1, flags=re.I)
    if n:
        fp.write_text(new_txt, encoding='utf-8', newline='\n')
        return True
    return False


def phase2():
    """Article author -> Person, SoftwareApplication på verktøy."""
    article_changes = 0
    softapp_added = 0

    for fp in html_files():
        txt = fp.read_text(encoding='utf-8')
        new_txt, n = _modify_jsonld_in_html(txt, _set_person_author_in_article)
        if n:
            article_changes += n
            fp.write_text(new_txt, encoding='utf-8', newline='\n')

    for fp in [ROOT / k for k in SOFTWAREAPP_TEMPLATES.keys()]:
        if fp.exists() and _add_softwareapp_if_missing(fp):
            softapp_added += 1

    # Oppdater Python-generatorer slik at nye blogginnlegg faar Person-author
    wp = ROOT / 'scripts' / 'weekly_blogpost.py'
    if wp.exists():
        t = wp.read_text(encoding='utf-8')
        # Find old author Organization block and replace with Person
        # Antar at templates kun har en Article-schema
        new_t = re.sub(
            r'"author":\s*\{\s*"@type":\s*"Organization"[^{}]*?"Micronet AS"[^{}]*?\}',
            f'"author": {json.dumps(PERSON_AUTHOR, ensure_ascii=False)}',
            t, count=1,
        )
        if new_t != t:
            wp.write_text(new_t, encoding='utf-8', newline='\n')

    print(f'Fase 2 ferdig:')
    print(f'  Article-author bytttet til Person i {article_changes} JSON-LD blokker')
    print(f'  SoftwareApplication lagt til på {softapp_added} verktøy-sider')


# ----- Fase 3 -----

def _list_blog_posts():
    """Returner liste over (path, title, description, modified)."""
    posts = []
    for fp in (ROOT / 'blogg').glob('*/index.html'):
        txt = fp.read_text(encoding='utf-8')
        m_title = re.search(r'<title>([^<|]+?)(?:\s*\|\s*data1\.no)?</title>', txt)
        m_desc = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', txt)
        m_url = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', txt)
        slug = fp.parent.name
        posts.append({
            'slug': slug,
            'title': m_title.group(1).strip() if m_title else slug,
            'description': m_desc.group(1).strip() if m_desc else '',
            'url': m_url.group(1).strip() if m_url else f'https://data1.no/blogg/{slug}/',
        })
    return posts


def _list_report_pages():
    out = []
    for sub in ('rapport-2026/index.html', 'rapport-2026/banker/index.html',
                'rapport-2026/kommuner/index.html', 'rapport-2026/e-handel/index.html',
                'rapport-2026/medier/index.html'):
        fp = ROOT / sub
        if not fp.exists():
            continue
        txt = fp.read_text(encoding='utf-8')
        m_title = re.search(r'<title>([^<|]+?)(?:\s*\|\s*data1\.no)?</title>', txt)
        m_desc = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', txt)
        m_url = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', txt)
        out.append({
            'title': m_title.group(1).strip() if m_title else sub,
            'description': m_desc.group(1).strip() if m_desc else '',
            'url': m_url.group(1).strip() if m_url else f'https://data1.no/{sub.replace("/index.html","/")}',
        })
    return out


def phase3():
    """Generer /llms.txt og /llms-full.txt."""
    posts = _list_blog_posts()
    reports = _list_report_pages()

    # Sorter blogginnlegg pedagogisk: forklaringer først, deretter implementasjon, deretter rapporter
    priority_slugs = ['dmarc', 'spf', 'dkim',
                      'dmarc-microsoft-365', 'dmarc-google-workspace',
                      'spf-microsoft-365']
    pri = {s: i for i, s in enumerate(priority_slugs)}
    posts.sort(key=lambda p: (pri.get(p['slug'], 999), p['slug']))

    lines = ['# data1.no', '']
    lines.append('> Gratis norsk verktøy for analyse av e-postsikkerhet — spesialisert på .no-domener. Test SPF, DMARC, DKIM, MTA-STS, TLS-RPT og BIMI på sekunder. Karakter A+ til F med konkrete tiltak. Drives av Micronet AS.')
    lines.append('')

    lines.append('## Om e-postsikkerhet (guider)')
    lines.append('')
    for p in posts:
        if p['slug'] in priority_slugs:
            lines.append(f"- [{p['title']}]({p['url']}): {p['description']}")
    lines.append('')

    other = [p for p in posts if p['slug'] not in priority_slugs]
    if other:
        lines.append('## Andre artikler')
        lines.append('')
        for p in other:
            lines.append(f"- [{p['title']}]({p['url']}): {p['description']}")
        lines.append('')

    if reports:
        lines.append('## Rapporter og data')
        lines.append('')
        for r in reports:
            lines.append(f"- [{r['title']}]({r['url']}): {r['description']}")
        lines.append('')

    lines.append('## Verktoy')
    lines.append('')
    lines.append('- [DMARC-generator](https://data1.no/verktoy/dmarc-generator/): Gratis verktøy for å generere DMARC DNS-record på norsk.')
    lines.append('- [SPF-generator](https://data1.no/verktoy/spf-generator/): Gratis verktøy for å generere SPF DNS-record på norsk.')
    lines.append('- [Sjekk alle skannede domener](https://data1.no/sjekk/): Katalog over alle overvåkede norske domener.')
    lines.append('')

    lines.append('## Om')
    lines.append('')
    lines.append('- [Om data1.no](https://data1.no/om/): Bakgrunn, hvem som drifter siden (Micronet AS, Lørenskog), kontaktinformasjon.')
    lines.append('- [Micronet AS](https://micronet.no): Norsk IT-konsulentselskap som drifter data1.no. Daglig leder: Terje Otterlei.')
    lines.append('')

    out = '\n'.join(lines)
    (ROOT / 'llms.txt').write_text(out, encoding='utf-8', newline='\n')

    # llms-full.txt: kort versjon + ekstra-snippets med hovedfunksjoner
    full = list(lines)
    full.append('## Hva data1.no gjor teknisk')
    full.append('')
    full.append('data1.no kjorer en serie DNS-baserte sjekker på et domene:')
    full.append('')
    full.append('- **SPF**: Henter TXT-record på apex (`domene.no`), parser `v=spf1`-streng, teller DNS-oppslag (10-grense), validerer `-all`/`~all`-policy.')
    full.append('- **DMARC**: Henter TXT-record på `_dmarc.domene.no`, parser policy (`p=`, `sp=`, `pct=`, `rua=`, `ruf=`, `aspf=`, `adkim=`).')
    full.append('- **DKIM**: Forsøker vanlige selectorer (`selector1`, `selector2`, `s1`, `google`, m.fl.) og henter TXT-record på `_domainkey`. Validerer nøkkellengde (min 2048 bit anbefalt per RFC 8301).')
    full.append('- **MTA-STS**: Henter TXT-record på `_mta-sts.domene.no` og policy-fil på `https://mta-sts.domene.no/.well-known/mta-sts.txt`.')
    full.append('- **TLS-RPT**: Henter TXT-record på `_smtp._tls.domene.no`.')
    full.append('- **BIMI**: Henter TXT-record på `default._bimi.domene.no`, lastet ned logo-SVG, sjekker om VMC-sertifikat er angitt.')
    full.append('')
    full.append('## Karaktersystem')
    full.append('')
    full.append('Vekting per kategori (sum 100 poeng): DMARC 35, SPF 25, DKIM 20, MTA-STS 12, TLS-RPT 5, BIMI 3.')
    full.append('')
    full.append('| Karakter | Poeng | Tolkning |')
    full.append('|---|---|---|')
    full.append('| A+ | 90–100 | Full beskyttelse, p=reject |')
    full.append('| A  | 80–89 | Sterk beskyttelse |')
    full.append('| B  | 70–79 | God, men ikke optimal |')
    full.append('| C  | 55–69 | Middels |')
    full.append('| D  | 35–54 | Svak |')
    full.append('| F  |  0–34 | Praktisk talt ubeskyttet |')
    full.append('')

    (ROOT / 'llms-full.txt').write_text('\n'.join(full), encoding='utf-8', newline='\n')

    print(f'Fase 3 ferdig:')
    print(f'  llms.txt:      {(ROOT / "llms.txt").stat().st_size} bytes ({len(posts)} blogginnlegg, {len(reports)} rapporter)')
    print(f'  llms-full.txt: {(ROOT / "llms-full.txt").stat().st_size} bytes')


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if cmd in ('phase1', 'all'):
        phase1()
    if cmd in ('phase2', 'all'):
        phase2()
    if cmd in ('phase3', 'all'):
        phase3()


if __name__ == '__main__':
    main()
