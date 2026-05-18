#!/usr/bin/env python3
"""
Generer /sjekk/{domain}/index.html for hvert domene i siste daily scan.

Programmatisk SEO: hver overvåket bedrift får sin egen indekserbare side.
Innholdet er unikt fordi vi inkluderer den faktiske DNS-recorden + kontekstuelle
norske forklaringer basert på status. Auto-oppdateres når daily_scan.py kjører.
"""
import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
SNAPSHOTS_DIR = ROOT / '_data' / 'snapshots'
OUT_DIR = ROOT / 'sjekk'

GRADE_COLORS = {
    'A+': '#10b981', 'A': '#22c55e', 'B': '#3b82f6',
    'C': '#eab308', 'D': '#f97316', 'F': '#7f1d1d',
}


def latest_snapshot() -> dict:
    files = sorted(SNAPSHOTS_DIR.glob('*.json'))
    if not files:
        raise SystemExit('Ingen snapshots funnet i _data/snapshots/')
    return json.loads(files[-1].read_text(encoding='utf-8'))


def grade_verdict(grade: str, score: int, domain: str) -> str:
    v = {
        'A+': f'{score}/100 — full beskyttelse. DMARC håndhever (p=reject), SPF og DKIM er på plass, og avanserte standarder som MTA-STS er aktive. Phishing-angrep som utgir seg for å komme fra @{domain} blir avvist av mottakende e-postservere.',
        'A': f'{score}/100 — sterk beskyttelse. DMARC er aktivt med håndhevende policy, og grunnleggende SPF/DKIM er på plass. Noen avanserte standarder (MTA-STS, TLS-RPT eller BIMI) mangler.',
        'B': f'{score}/100 — god beskyttelse, men ikke optimal. Konfigurasjonen er på plass men noen kritiske mangler gjør at angripere fortsatt har en del muligheter.',
        'C': f'{score}/100 — middels beskyttelse. Grunnleggende oppsett finnes, men det er tydelige hull som kan utnyttes av phishing-kampanjer.',
        'D': f'{score}/100 — svak beskyttelse. Kritiske mangler i SPF eller DMARC betyr at e-poster som utgir seg for å komme fra @{domain} ofte havner i innboksen til mottakerne.',
        'F': f'{score}/100 — praktisk talt ubeskyttet. Domenet mangler grunnleggende e-postsikkerhets-records og er åpent for spoofing. En kriminell kan sende e-post som ser ut som den kommer fra @{domain} uten å bli stoppet.',
    }
    return v.get(grade, f'{score}/100 — karakter {grade}.')


def spf_section(spf: dict, domain: str) -> tuple:
    if not spf.get('present'):
        return ('SPF (Sender Policy Framework)', 'missing', 'MANGLER', None,
                f'{domain} har ingen SPF-record. Det betyr at mottakende e-postservere ikke har noen instruks om hvilke avsendere som er legitime — alle kan teknisk sett utgi seg for å sende fra @{domain}.')
    record = spf.get('record', '')
    qual = spf.get('all_qualifier', '')
    if qual == '-':
        return ('SPF (Sender Policy Framework)', 'ok', 'OK (strict)', record,
                f'Strict SPF (-all). E-post fra ikke-autoriserte servere skal avvises. Dette er anbefalt oppsett kombinert med DMARC p=reject.')
    if qual == '~':
        return ('SPF (Sender Policy Framework)', 'warn', 'SOFTFAIL', record,
                'Softfail (~all). E-post fra ikke-autoriserte servere markeres som mistenkelig men ikke avvist. Akseptabelt, men strict (-all) gir sterkere beskyttelse.')
    return ('SPF (Sender Policy Framework)', 'warn', 'KONFIG', record,
            'SPF mangler korrekt all-mekanisme på slutten. Bør avsluttes med -all (anbefalt) eller ~all.')


def dmarc_section(dmarc: dict, domain: str) -> tuple:
    if not dmarc.get('present'):
        return ('DMARC', 'missing', 'MANGLER', None,
                f'{domain} har ingen DMARC-record. Phishing-mailer som spoofer @{domain} har stor sjanse for å havne i mottakerens innboks. DMARC er den viktigste enkeltstandarden mot e-post-svindel.')
    record = dmarc.get('record', '')
    policy = dmarc.get('policy', 'none')
    if policy == 'reject':
        return ('DMARC', 'ok', 'p=reject', record,
                f'p=reject — strengeste policy. Mottakere instrueres om å avvise e-post fra @{domain} som ikke består SPF/DKIM-autentisering. Dette er gullstandarden.')
    if policy == 'quarantine':
        return ('DMARC', 'warn', 'p=quarantine', record,
                f'p=quarantine — ikke-autentisert e-post sendes til spam-mappen. Bedre enn ingenting, men gir ikke samme beskyttelse som p=reject. Bør skjerpes etter en overvåkingsperiode.')
    return ('DMARC', 'warn', 'p=none', record,
            f'p=none — kun overvåking, ingen håndheving. {domain} mottar DMARC-rapporter, men angripere kan fortsatt nå mottakerens innboks. Bør strammes til p=reject etter 4-8 uker.')


def dkim_section(dkim: dict, domain: str) -> tuple:
    if not dkim.get('present'):
        return ('DKIM', 'missing', 'MANGLER', None,
                f'Vi fant ingen DKIM-selektorer for {domain} blant standard-navnene (selector1, selector2, k1-k4, google, mail, default …). Det betyr enten at DKIM ikke brukes, eller at selektoren har et uvanlig navn vi ikke prøver. Uten DKIM kan DMARC feile alignment selv for ekte e-post.')
    selectors = dkim.get('selectors', [])
    sel_str = ', '.join(selectors)
    n = len(selectors)
    plural_e = 'e' if n != 1 else ''
    plural_er = 'er' if n != 1 else ''
    return ('DKIM', 'ok', f'{n} selektor{plural_er}', f'Selektorer funnet: {sel_str}',
            f'DKIM signerer e-post kryptografisk så mottakeren kan verifisere at innholdet ikke er endret. {domain} har {n} aktiv{plural_e} selektor{plural_er} ({sel_str}) som mottakere kan slå opp og verifisere mot.')


def mta_sts_section(mta_sts: dict, domain: str) -> tuple:
    if not mta_sts.get('present'):
        return ('MTA-STS', 'missing', 'MANGLER', None,
                f'MTA-STS er en moderne standard som tvinger inngående e-post til {domain} å bruke TLS-kryptering. Uten den er TLS-stripping-angrep teoretisk mulig på e-post i transit.')
    return ('MTA-STS', 'ok', 'OK', mta_sts.get('record', ''),
            f'MTA-STS er aktivt. {domain} krever at all innkommende e-post bruker TLS-kryptering, og avviser leveringsforsøk uten TLS.')


def tls_rpt_section(tls_rpt: dict, domain: str) -> tuple:
    if not tls_rpt.get('present'):
        return ('TLS-RPT', 'missing', 'MANGLER', None,
                'TLS-RPT (TLS Reporting) gir daglige rapporter når andre servere ikke klarer å levere e-post med TLS. Ikke kritisk, men nyttig for å oppdage konfigurasjonsproblemer.')
    return ('TLS-RPT', 'ok', 'OK', tls_rpt.get('record', ''),
            f'TLS-RPT er aktivt. {domain} mottar daglige rapporter om TLS-leveringsfeil fra andre e-postservere.')


def bimi_section(bimi: dict, domain: str) -> tuple:
    if not bimi.get('present'):
        return ('BIMI', 'missing', 'MANGLER', None,
                f'BIMI viser logoen din i innbokser hos mottakere som støtter det (Gmail, Yahoo, Apple Mail). {domain} har ingen BIMI-record — logoen vises ikke ved siden av e-poster.')
    return ('BIMI', 'ok', 'OK', bimi.get('record', ''),
            f'BIMI er konfigurert. Logoen til {domain} vises ved siden av e-poster i innbokser hos BIMI-støttende klienter.')


def render_page(result: dict, today: str) -> str:
    domain = result['domain']
    score = result['score']
    grade = result['grade']
    color = GRADE_COLORS.get(grade, '#64748b')
    verdict = grade_verdict(grade, score, domain)

    sections = [
        spf_section(result['checks']['spf'], domain),
        dmarc_section(result['checks']['dmarc'], domain),
        dkim_section(result['checks']['dkim'], domain),
        mta_sts_section(result['checks']['mta_sts'], domain),
        tls_rpt_section(result['checks']['tls_rpt'], domain),
        bimi_section(result['checks']['bimi'], domain),
    ]

    pill_colors = {'ok': '#10b981', 'warn': '#eab308', 'missing': '#ef4444'}
    sec_html_parts = []
    for name, status, label, record, explanation in sections:
        record_html = f'    <pre class="dns-record">{html.escape(record)}</pre>\n' if record else ''
        sec_html_parts.append(
            f'  <section class="check">\n'
            f'    <div class="check-head">\n'
            f'      <h2>{html.escape(name)}</h2>\n'
            f'      <span class="pill" style="background:{pill_colors[status]}">{html.escape(label)}</span>\n'
            f'    </div>\n'
            f'{record_html}'
            f'    <p>{html.escape(explanation)}</p>\n'
            f'  </section>'
        )
    sec_html = '\n'.join(sec_html_parts)

    title = f'E-postsikkerhet for {domain} — karakter {grade} | data1.no'
    desc = f'{domain} har karakter {grade} ({score}/100) på e-postsikkerhet. Se DMARC, SPF, DKIM, MTA-STS, TLS-RPT og BIMI-status, oppdatert {today}.'

    schema = {
        '@context': 'https://schema.org',
        '@type': 'WebPage',
        '@id': f'https://data1.no/sjekk/{domain}/',
        'url': f'https://data1.no/sjekk/{domain}/',
        'name': title,
        'description': desc,
        'inLanguage': 'nb-NO',
        'isPartOf': {'@id': 'https://data1.no/#website'},
        'about': {'@type': 'Thing', 'name': f'E-postsikkerhet for {domain}'},
        'dateModified': today,
        'breadcrumb': {
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Hjem', 'item': 'https://data1.no/'},
                {'@type': 'ListItem', 'position': 2, 'name': 'Sjekk domene', 'item': 'https://data1.no/sjekk/'},
                {'@type': 'ListItem', 'position': 3, 'name': domain, 'item': f'https://data1.no/sjekk/{domain}/'},
            ],
        },
    }

    return f'''<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<meta name="description" content="{html.escape(desc)}">
<meta name="author" content="Terje Otterlei">
<meta name="theme-color" content="#1a202c">
<link rel="canonical" href="https://data1.no/sjekk/{domain}/">
<meta property="og:type" content="article">
<meta property="og:site_name" content="data1.no">
<meta property="og:locale" content="nb_NO">
<meta property="og:url" content="https://data1.no/sjekk/{domain}/">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:image" content="https://data1.no/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<title>{html.escape(title)}</title>
<link rel="preload" href="/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/rapport-2026/_assets/report.css">
<style>
.grade-hero{{display:flex;align-items:center;gap:24px;background:#fff;border-radius:14px;padding:24px 28px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.07)}}
.grade-badge{{font-size:56px;font-weight:900;line-height:1;letter-spacing:-.04em;color:#fff;width:96px;height:96px;border-radius:14px;display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.grade-info h2{{font-size:13px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin:0 0 6px}}
.grade-info p{{margin:0;color:#1e293b;font-size:15px;line-height:1.55}}
.check{{background:#fff;border-radius:12px;padding:20px 24px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)}}
.check-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:12px}}
.check h2{{font-size:18px;font-weight:800;color:#0f172a;margin:0}}
.pill{{font-size:11px;font-weight:800;color:#fff;padding:4px 10px;border-radius:999px;text-transform:uppercase;letter-spacing:.05em;white-space:nowrap}}
.dns-record{{background:#0f172a;color:#7dd3fc;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;padding:11px 14px;border-radius:8px;overflow-x:auto;margin:8px 0 12px;white-space:pre-wrap;word-break:break-all;line-height:1.5}}
.check p{{color:#475569;font-size:14.5px;line-height:1.6;margin:0}}
.cta{{background:linear-gradient(135deg,#0f172a 0%,#1a2540 100%);color:#fff;border-radius:14px;padding:24px 28px;margin:28px 0 14px;text-align:center}}
.cta h2{{color:#fff;font-size:20px;font-weight:800;margin-bottom:8px}}
.cta p{{color:#94a3b8;margin-bottom:14px;font-size:15px}}
.cta a{{display:inline-block;padding:11px 22px;background:#14b8a6;color:#fff;border-radius:999px;text-decoration:none;font-weight:700}}
.cta a:hover{{background:#0d9488}}
.updated{{font-size:13px;color:#64748b;margin-top:24px;text-align:center}}
</style>
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
</head>
<body>
<header class="header">
  <a href="/" class="logo">data1<span>.no</span></a>
  <form class="header-search" action="/" method="get" role="search">
    <input type="text" name="domain" placeholder="Skriv inn domene — f.eks. micronet.no" aria-label="Sjekk domene">
    <button type="submit">Analyser →</button>
  </form>
</header>
<main class="container">
  <nav class="crumbs"><a href="/">Hjem</a> › <a href="/sjekk/">Sjekk domene</a> › {domain}</nav>
  <h1>E-postsikkerhet for {domain}</h1>

  <div class="grade-hero">
    <div class="grade-badge" style="background:{color}">{grade}</div>
    <div class="grade-info">
      <h2>Karakter — sist oppdatert {today}</h2>
      <p>{html.escape(verdict)}</p>
    </div>
  </div>

{sec_html}

  <div class="cta">
    <h2>Sjekk ditt eget domene</h2>
    <p>Få karakter, full rapport og konkrete tiltak på 10 sekunder. Gratis.</p>
    <a href="/?domain={domain}">Kjør live-analyse →</a>
  </div>

  <p class="updated">Sist oppdatert: {today}. Data hentes daglig via DNS.</p>
</main>
</body>
</html>
'''


def render_index(results: list, today: str) -> str:
    by_grade = sorted(results, key=lambda r: (-r['score'], r['domain']))
    rows = []
    for r in by_grade:
        d = r['domain']
        g = r['grade']
        color = GRADE_COLORS.get(g, '#64748b')
        rows.append(
            f'  <li><a href="/sjekk/{d}/"><span class="g" style="background:{color}">{g}</span>'
            f'<span class="d">{d}</span><span class="s">{r["score"]}/100</span></a></li>'
        )
    list_html = '\n'.join(rows)

    title = f'Sjekk e-postsikkerhet for norske domener — {len(results)} bedrifter | data1.no'
    desc = f'Daglig oppdatert oversikt over e-postsikkerhet (DMARC, SPF, DKIM) hos {len(results)} norske domener. Karakterer A+ til F.'

    return f'''<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<meta name="description" content="{html.escape(desc)}">
<meta name="theme-color" content="#1a202c">
<link rel="canonical" href="https://data1.no/sjekk/">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="https://data1.no/sjekk/">
<meta property="og:image" content="https://data1.no/og-image.png">
<title>{html.escape(title)}</title>
<link rel="preload" href="/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/rapport-2026/_assets/report.css">
<style>
.domain-list{{background:#fff;border-radius:12px;padding:8px;box-shadow:0 1px 3px rgba(0,0,0,.07);list-style:none;margin:14px 0 28px}}
.domain-list li{{margin:0}}
.domain-list a{{display:flex;align-items:center;gap:14px;padding:10px 14px;text-decoration:none;color:#0f172a;border-radius:8px}}
.domain-list a:hover{{background:#f1f5f9}}
.g{{display:inline-flex;align-items:center;justify-content:center;width:42px;height:32px;border-radius:6px;color:#fff;font-weight:800;font-size:13px;letter-spacing:-.02em;flex-shrink:0}}
.d{{flex:1;font-weight:600;font-size:15px}}
.s{{color:#64748b;font-size:13px;font-variant-numeric:tabular-nums}}
.intro{{font-size:17px;color:#475569;max-width:760px;margin-bottom:14px;line-height:1.6}}
</style>
</head>
<body>
<header class="header">
  <a href="/" class="logo">data1<span>.no</span></a>
  <form class="header-search" action="/" method="get" role="search">
    <input type="text" name="domain" placeholder="Skriv inn domene — f.eks. micronet.no" aria-label="Sjekk domene">
    <button type="submit">Analyser →</button>
  </form>
</header>
<main class="container">
  <nav class="crumbs"><a href="/">Hjem</a> › Sjekk domene</nav>
  <h1>Sjekk e-postsikkerhet for norske domener</h1>
  <p class="intro">Daglig oppdatert oversikt over {len(results)} norske bedrifter, organisasjoner og institusjoner. Hver bedrift har sin egen side med karakter, faktiske DNS-records og forklaring av hva som mangler. Klikk på et domene for full rapport.</p>

  <ul class="domain-list">
{list_html}
  </ul>

  <p class="updated" style="font-size:13px;color:#64748b;text-align:center;margin-top:18px">Sist oppdatert: {today}. Data hentes daglig via DNS.</p>
</main>
</body>
</html>
'''


def main():
    snap = latest_snapshot()
    today = snap['date']
    OUT_DIR.mkdir(exist_ok=True)
    count = 0
    for result in snap['results']:
        domain = result['domain']
        if '/' in domain or '..' in domain or domain.startswith('.'):
            continue
        page_dir = OUT_DIR / domain
        page_dir.mkdir(exist_ok=True)
        (page_dir / 'index.html').write_text(render_page(result, today), encoding='utf-8')
        count += 1
    (OUT_DIR / 'index.html').write_text(render_index(snap['results'], today), encoding='utf-8')
    print(f'Genererte {count} domene-sider + 1 oversikt i /sjekk/')


if __name__ == '__main__':
    main()
