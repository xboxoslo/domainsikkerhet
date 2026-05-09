"""
Generate trends page based on snapshot diffs.

Sammenligner siste snapshot med snapshot fra 7 dager siden, finner domener
som har forbedret/forverret seg, og genererer /trender/index.html.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
SNAPSHOTS_DIR = ROOT / '_data' / 'snapshots'
TRENDS_DIR = ROOT / 'trender'
TRENDS_DIR.mkdir(exist_ok=True)


def load_latest_snapshots() -> tuple[dict | None, dict | None]:
    files = sorted(SNAPSHOTS_DIR.glob('*.json'))
    if not files:
        return None, None
    latest = json.loads(files[-1].read_text(encoding='utf-8'))

    # Finn snapshot ca 7 dager tilbake
    target = datetime.fromisoformat(latest['timestamp']) - timedelta(days=7)
    older = None
    for f in reversed(files[:-1]):
        snap = json.loads(f.read_text(encoding='utf-8'))
        snap_ts = datetime.fromisoformat(snap['timestamp'])
        if snap_ts <= target:
            older = snap
            break
    if older is None and len(files) >= 2:
        older = json.loads(files[0].read_text(encoding='utf-8'))
    return latest, older


def find_changes(latest: dict, older: dict) -> dict:
    old_scores = {r['domain']: r.get('score', 0) for r in older.get('results', [])}
    old_grades = {r['domain']: r.get('grade', '?') for r in older.get('results', [])}

    improvements = []
    regressions = []
    new_reject = []
    new_no_dmarc = []

    for r in latest.get('results', []):
        d = r['domain']
        new_score = r.get('score', 0)
        old_score = old_scores.get(d, new_score)
        new_grade = r.get('grade', '?')
        old_grade = old_grades.get(d, new_grade)

        diff = new_score - old_score
        if diff >= 5:
            improvements.append({'domain': d, 'old': old_score, 'new': new_score,
                                 'old_grade': old_grade, 'new_grade': new_grade, 'diff': diff})
        elif diff <= -5:
            regressions.append({'domain': d, 'old': old_score, 'new': new_score,
                                'old_grade': old_grade, 'new_grade': new_grade, 'diff': diff})

        new_policy = r.get('checks', {}).get('dmarc', {}).get('policy')
        old_data = next((o for o in older.get('results', []) if o['domain'] == d), None)
        old_policy = old_data.get('checks', {}).get('dmarc', {}).get('policy') if old_data else None
        if new_policy == 'reject' and old_policy != 'reject':
            new_reject.append({'domain': d, 'old_policy': old_policy or 'ingen'})
        if not r.get('checks', {}).get('dmarc', {}).get('present') and old_data and old_data.get('checks', {}).get('dmarc', {}).get('present'):
            new_no_dmarc.append({'domain': d})

    improvements.sort(key=lambda x: -x['diff'])
    regressions.sort(key=lambda x: x['diff'])
    return {
        'improvements': improvements[:20],
        'regressions': regressions[:20],
        'new_reject': new_reject,
        'new_no_dmarc': new_no_dmarc,
    }


def grade_color(g: str) -> str:
    return {'A+': '#16a34a', 'A': '#22c55e', 'B': '#84cc16',
            'C': '#eab308', 'D': '#f97316', 'F': '#dc2626'}.get(g, '#94a3b8')


def render_change_row(c: dict, kind: str) -> str:
    arrow = '↑' if kind == 'improvement' else '↓'
    color = '#16a34a' if kind == 'improvement' else '#dc2626'
    return f'''<tr>
        <td><a href="/?d={c['domain']}">{c['domain']}</a></td>
        <td><span class="grade" style="background:{grade_color(c['old_grade'])}">{c['old_grade']}</span> → <span class="grade" style="background:{grade_color(c['new_grade'])}">{c['new_grade']}</span></td>
        <td>{c['old']} → {c['new']}</td>
        <td style="color:{color};font-weight:700">{arrow} {abs(c['diff'])}p</td>
    </tr>'''


def main():
    latest, older = load_latest_snapshots()
    if not latest:
        print('Ingen snapshots funnet.')
        return
    if not older:
        print('Bare ett snapshot — kan ikke beregne trender ennå.')
        # Generer minimal side
        changes = {'improvements': [], 'regressions': [], 'new_reject': [], 'new_no_dmarc': []}
    else:
        changes = find_changes(latest, older)

    today = latest['date']
    older_date = older['date'] if older else 'i dag (kun ett snapshot)'

    summary = latest['summary']

    html = f'''<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Daglig oppdaterte trender for norske domeners e-postsikkerhet. Hvilke domener har forbedret eller forverret SPF, DMARC, DKIM siste uke?">
<meta name="keywords" content="dmarc trender, e-post sikkerhet norge, dmarc statistikk daglig, norske domener dmarc">
<meta name="theme-color" content="#1a202c">
<link rel="canonical" href="https://data1.no/trender/">
<meta property="og:type" content="article">
<meta property="og:title" content="DMARC-trender for norske domener — oppdatert {today}">
<meta property="og:description" content="Live oversikt: hvilke norske domener forbedret eller forverret e-postsikkerheten siden {older_date}.">
<meta property="og:image" content="https://data1.no/og-image.png">
<title>DMARC-trender for norske domener — {today} | data1.no</title>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Dataset","name":"Daglige DMARC-trender for norske domener","description":"Daglige målinger av SPF, DMARC, DKIM, MTA-STS, TLS-RPT og BIMI for {summary.get("grade_distribution", {}).get("A+", 0) + summary.get("grade_distribution", {}).get("A", 0) + summary.get("grade_distribution", {}).get("B", 0) + summary.get("grade_distribution", {}).get("C", 0) + summary.get("grade_distribution", {}).get("D", 0) + summary.get("grade_distribution", {}).get("F", 0)} norske domener.","url":"https://data1.no/trender/","dateModified":"{today}","creator":{{"@type":"Organization","name":"Micronet","url":"https://micronet.no"}},"license":"https://creativecommons.org/licenses/by/4.0/","keywords":["DMARC","SPF","DKIM","e-postsikkerhet","Norge"]}}</script>
<style>
@font-face{{font-family:"Inter";font-weight:400 900;font-display:optional;src:url(/fonts/inter-latin.woff2)format("woff2");unicode-range:U+0000-00FF}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"Inter",-apple-system,sans-serif;background:#f1f5f9;color:#1e293b;line-height:1.6}}
.header{{background:#1a202c;padding:14px 28px;display:flex;align-items:center;gap:18px}}
.logo{{color:#fff;font-size:19px;font-weight:800;text-decoration:none}}.logo span{{color:#4fd1c5}}
.spacer{{flex:1}}.nav-link{{color:#cbd5e0;text-decoration:none;font-size:14px}}
main{{max-width:920px;margin:0 auto;padding:36px 22px 80px}}
.crumbs{{font-size:13px;color:#94a3b8;margin-bottom:16px}}.crumbs a{{color:#0f766e;text-decoration:none}}
h1{{font-size:34px;font-weight:900;color:#0f172a;letter-spacing:-.025em;margin-bottom:8px}}
.lead{{font-size:16px;color:#475569;margin-bottom:6px}}
.meta{{font-size:13px;color:#64748b;margin-bottom:28px}}
.summary-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:24px 0}}
.stat{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px;text-align:center}}
.stat-num{{font-size:28px;font-weight:900;color:#0f766e}}
.stat-label{{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.04em;margin-top:4px}}
h2{{font-size:22px;font-weight:800;color:#0f172a;margin:32px 0 12px;letter-spacing:-.015em}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;margin:14px 0;font-size:14px;box-shadow:0 1px 3px rgba(0,0,0,.05)}}
th{{background:#0f172a;color:#fff;text-align:left;padding:10px 14px;font-size:12px;letter-spacing:.04em;text-transform:uppercase}}
td{{padding:12px 14px;border-bottom:1px solid #f1f5f9}}
tr:last-child td{{border-bottom:none}}
.grade{{display:inline-block;color:#fff;padding:2px 8px;border-radius:6px;font-size:12px;font-weight:700;min-width:30px;text-align:center}}
a{{color:#0f766e;text-decoration:none}}a:hover{{text-decoration:underline}}
.empty{{background:#f8fafc;padding:20px;text-align:center;color:#94a3b8;border-radius:10px;font-size:14px}}
.callout{{background:#f0fdfa;border-left:4px solid #14b8a6;padding:14px 18px;border-radius:0 10px 10px 0;margin:20px 0;font-size:14px;color:#134e4a}}
</style>
</head>
<body>
<header class="header">
<a href="/" class="logo">data1<span>.no</span></a>
<div class="spacer"></div>
<a href="/" class="nav-link">Sjekk eget domene →</a>
</header>
<main>
<nav class="crumbs"><a href="/">Hjem</a> › Daglige trender</nav>
<h1>Daglige DMARC-trender</h1>
<p class="lead">Hvilke norske domener forbedret eller forverret e-postsikkerheten siste 7 dager?</p>
<p class="meta">Oppdatert {today} · sammenligner med {older_date} · automatisk daglig skanning av {len(latest.get("results", []))} domener</p>

<div class="summary-grid">
<div class="stat"><div class="stat-num">{summary.get("avg_score", 0):.1f}</div><div class="stat-label">Snitt-score (av 100)</div></div>
<div class="stat"><div class="stat-num">{summary.get("has_dmarc_reject", 0)}</div><div class="stat-label">Med p=reject</div></div>
<div class="stat"><div class="stat-num">{summary.get("no_dmarc", 0)}</div><div class="stat-label">Uten DMARC</div></div>
<div class="stat"><div class="stat-num">{len(changes["improvements"])}</div><div class="stat-label">Forbedret siste uke</div></div>
</div>

<h2>📈 Domener som forbedret seg ({len(changes["improvements"])})</h2>
'''

    if changes['improvements']:
        html += '<table><thead><tr><th>Domene</th><th>Karakter</th><th>Score</th><th>Endring</th></tr></thead><tbody>'
        for c in changes['improvements']:
            html += render_change_row(c, 'improvement')
        html += '</tbody></table>'
    else:
        html += '<div class="empty">Ingen domener har forbedret seg betydelig siste uke.</div>'

    html += f'<h2>📉 Domener som forverret seg ({len(changes["regressions"])})</h2>'
    if changes['regressions']:
        html += '<table><thead><tr><th>Domene</th><th>Karakter</th><th>Score</th><th>Endring</th></tr></thead><tbody>'
        for c in changes['regressions']:
            html += render_change_row(c, 'regression')
        html += '</tbody></table>'
    else:
        html += '<div class="empty">Ingen domener har forverret seg betydelig siste uke.</div>'

    if changes['new_reject']:
        html += f'<h2>✅ Nye domener med p=reject ({len(changes["new_reject"])})</h2>'
        html += '<table><thead><tr><th>Domene</th><th>Tidligere policy</th></tr></thead><tbody>'
        for c in changes['new_reject']:
            html += f'<tr><td><a href="/?d={c["domain"]}">{c["domain"]}</a></td><td>{c["old_policy"]}</td></tr>'
        html += '</tbody></table>'

    html += '''<div class="callout">
<strong>Hva betyr dette?</strong> p=reject er den eneste DMARC-policyen som faktisk blokkerer e-post-forfalskning. Domener som går fra «none» eller «quarantine» til «reject» har tatt det viktige siste steget mot full beskyttelse.
</div>

<h2>Sjekk ditt domene</h2>
<p style="margin-bottom:24px">Vil du vite hvor ditt domene står på samme rangering? <a href="/" style="font-weight:700">Kjør gratis analyse →</a></p>

<p style="font-size:13px;color:#94a3b8;margin-top:40px;border-top:1px solid #e2e8f0;padding-top:18px">Data oppdateres daglig kl 06:00 UTC av automatisk skanner. Karakterskala: A+ (90+), A (80-89), B (70-79), C (55-69), D (35-54), F (0-34).</p>
</main>
</body>
</html>
'''

    out = TRENDS_DIR / 'index.html'
    out.write_text(html, encoding='utf-8')
    print(f'Trends-side generert: {out.relative_to(ROOT)}')
    print(f'  Forbedringer: {len(changes["improvements"])}')
    print(f'  Forverring:   {len(changes["regressions"])}')
    print(f'  Nye p=reject: {len(changes["new_reject"])}')


if __name__ == '__main__':
    main()
