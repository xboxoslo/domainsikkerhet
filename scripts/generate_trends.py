"""
Generate trends page based on snapshot diffs + sector breakdown + leaderboards.

Sammenligner siste snapshot med snapshot fra 7 dager siden, finner domener
som har forbedret/forverret seg, parser sektorer fra watchlist, og genererer
/trender/index.html + /trender/data.csv.
"""
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
SNAPSHOTS_DIR = ROOT / '_data' / 'snapshots'
WATCHLIST = ROOT / '_data' / 'domains-watchlist.txt'
TRENDS_DIR = ROOT / 'trender'
TRENDS_DIR.mkdir(exist_ok=True)

GRADE_COLOR = {'A+': '#16a34a', 'A': '#22c55e', 'B': '#84cc16',
               'C': '#eab308', 'D': '#f97316', 'F': '#dc2626'}


def load_latest_snapshots() -> tuple[dict | None, dict | None, list]:
    """Returns (latest, ~7-day-old, all_snapshots_sorted)."""
    files = sorted(SNAPSHOTS_DIR.glob('*.json'))
    if not files:
        return None, None, []
    all_snaps = [json.loads(f.read_text(encoding='utf-8')) for f in files]
    latest = all_snaps[-1]
    target = datetime.fromisoformat(latest['timestamp']) - timedelta(days=7)
    older = None
    for snap in reversed(all_snaps[:-1]):
        snap_ts = datetime.fromisoformat(snap['timestamp'])
        if snap_ts <= target:
            older = snap
            break
    if older is None and len(all_snaps) >= 2:
        older = all_snaps[0]
    return latest, older, all_snaps


def parse_sectors() -> dict[str, str]:
    """Parse watchlist for sector grouping based on '# Sector'-comments."""
    sectors = {}
    current_sector = 'Annet'
    if not WATCHLIST.exists():
        return sectors
    for line in WATCHLIST.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('# Domener') or line.startswith('# Format') or line.startswith('# Domenet'):
            continue
        if line.startswith('#'):
            current_sector = line.lstrip('# ').strip()
            # forenkle parenteser
            if '(' in current_sector:
                current_sector = current_sector.split('(')[0].strip()
            continue
        sectors[line.lower()] = current_sector
    return sectors


def find_changes(latest: dict, older: dict) -> dict:
    old_scores = {r['domain']: r.get('score', 0) for r in older.get('results', [])}
    old_grades = {r['domain']: r.get('grade', '?') for r in older.get('results', [])}

    improvements, regressions, new_reject = [], [], []

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

    improvements.sort(key=lambda x: -x['diff'])
    regressions.sort(key=lambda x: x['diff'])
    return {'improvements': improvements[:20], 'regressions': regressions[:20],
            'new_reject': new_reject}


def compute_aggregates(latest: dict, sectors: dict[str, str]) -> dict:
    """Top/bottom leaderboards, DMARC pyramid, feature adoption, sector breakdown."""
    results = latest.get('results', [])
    total = len(results)

    # DMARC policy pyramid
    policy_count = {'reject': 0, 'quarantine': 0, 'none': 0, 'mangler': 0}
    for r in results:
        d = r.get('checks', {}).get('dmarc', {})
        if not d.get('present'):
            policy_count['mangler'] += 1
        else:
            p = d.get('policy', 'none')
            policy_count[p] = policy_count.get(p, 0) + 1

    # Feature adoption
    features = {'spf': 0, 'dmarc': 0, 'dkim': 0, 'mta_sts': 0, 'tls_rpt': 0, 'bimi': 0}
    for r in results:
        for f in features:
            if r.get('checks', {}).get(f, {}).get('present'):
                features[f] += 1

    # Top 10 / bottom 10
    sorted_by_score = sorted(results, key=lambda r: -r.get('score', 0))
    top10 = sorted_by_score[:10]
    bottom10 = list(reversed(sorted_by_score[-10:]))

    # Sector aggregates
    by_sector: dict[str, list] = {}
    for r in results:
        sector = sectors.get(r['domain'].lower(), 'Annet')
        by_sector.setdefault(sector, []).append(r)
    sector_stats = []
    for sector, rs in by_sector.items():
        avg = sum(r.get('score', 0) for r in rs) / len(rs) if rs else 0
        n_reject = sum(1 for r in rs if r.get('checks', {}).get('dmarc', {}).get('policy') == 'reject')
        sector_stats.append({'sector': sector, 'count': len(rs), 'avg': avg, 'reject': n_reject,
                              'reject_pct': n_reject / len(rs) * 100 if rs else 0})
    sector_stats.sort(key=lambda s: -s['avg'])

    # Grade distribution
    grade_dist = {'A+': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
    for r in results:
        g = r.get('grade', 'F')
        if g in grade_dist:
            grade_dist[g] += 1

    return {'total': total, 'policy_count': policy_count, 'features': features,
            'top10': top10, 'bottom10': bottom10, 'sector_stats': sector_stats,
            'grade_dist': grade_dist}


def grade_pill(grade: str) -> str:
    color = GRADE_COLOR.get(grade, '#94a3b8')
    return f'<span class="grade" style="background:{color}">{grade}</span>'


def render_grade_bars(grade_dist: dict, total: int) -> str:
    max_count = max(grade_dist.values()) or 1
    rows = []
    for g in ('A+', 'A', 'B', 'C', 'D', 'F'):
        n = grade_dist.get(g, 0)
        pct = n / total * 100 if total else 0
        bar_pct = n / max_count * 100
        color = GRADE_COLOR.get(g, '#94a3b8')
        rows.append(f'''<div class="gd-row">
            <div class="gd-label" style="color:{color}">{g}</div>
            <div class="gd-bar-bg"><div class="gd-bar" style="width:{bar_pct:.1f}%;background:{color}"></div></div>
            <div class="gd-count">{n}</div>
            <div class="gd-pct">{pct:.1f}%</div>
        </div>''')
    return '\n'.join(rows)


def render_pyramid(policy_count: dict, total: int) -> str:
    order = [('reject', 'p=reject — full beskyttelse', '#16a34a'),
             ('quarantine', 'p=quarantine — karantene', '#eab308'),
             ('none', 'p=none — kun overvåking', '#f97316'),
             ('mangler', 'ingen DMARC', '#dc2626')]
    rows = []
    for key, label, color in order:
        n = policy_count.get(key, 0)
        pct = n / total * 100 if total else 0
        rows.append(f'''<div class="py-row">
            <div class="py-label">{label}</div>
            <div class="py-bar-bg"><div class="py-bar" style="width:{pct:.1f}%;background:{color}"></div></div>
            <div class="py-count">{n} ({pct:.0f}%)</div>
        </div>''')
    return '\n'.join(rows)


def render_features(features: dict, total: int) -> str:
    labels = {'spf': 'SPF', 'dmarc': 'DMARC', 'dkim': 'DKIM',
              'mta_sts': 'MTA-STS', 'tls_rpt': 'TLS-RPT', 'bimi': 'BIMI'}
    cells = []
    for key, label in labels.items():
        n = features.get(key, 0)
        pct = n / total * 100 if total else 0
        cells.append(f'''<div class="feat">
            <div class="feat-pct">{pct:.0f}%</div>
            <div class="feat-label">{label}</div>
            <div class="feat-detail">{n} av {total}</div>
        </div>''')
    return '\n'.join(cells)


def render_sector_table(sector_stats: list) -> str:
    rows = []
    for s in sector_stats:
        rows.append(f'''<tr>
            <td>{s["sector"]}</td>
            <td style="text-align:right">{s["count"]}</td>
            <td style="text-align:right;font-weight:700">{s["avg"]:.1f}</td>
            <td style="text-align:right">{s["reject"]} ({s["reject_pct"]:.0f}%)</td>
        </tr>''')
    return '\n'.join(rows)


def render_leaderboard(rows: list, kind: str) -> str:
    items = []
    for r in rows:
        d = r['domain']
        items.append(f'''<tr>
            <td><a href="/?d={d}">{d}</a></td>
            <td>{grade_pill(r.get('grade', '?'))}</td>
            <td style="text-align:right;font-weight:700">{r.get('score', 0)}</td>
        </tr>''')
    return '\n'.join(items)


def render_change_row(c: dict, kind: str) -> str:
    arrow = '↑' if kind == 'improvement' else '↓'
    color = '#16a34a' if kind == 'improvement' else '#dc2626'
    return f'''<tr>
        <td><a href="/?d={c['domain']}">{c['domain']}</a></td>
        <td>{grade_pill(c['old_grade'])} → {grade_pill(c['new_grade'])}</td>
        <td>{c['old']} → {c['new']}</td>
        <td style="color:{color};font-weight:700">{arrow} {abs(c['diff'])}p</td>
    </tr>'''


def render_history_sparkline(all_snaps: list) -> str:
    """Mini chart over avg score over time. Returns inline SVG."""
    if len(all_snaps) < 2:
        return ''
    points = []
    for s in all_snaps[-30:]:  # max 30 days
        avg = s.get('summary', {}).get('avg_score', 0)
        points.append((s['date'], avg))
    if not points:
        return ''
    min_v = min(p[1] for p in points)
    max_v = max(p[1] for p in points)
    span = max(max_v - min_v, 1)
    w, h = 600, 80
    coords = []
    for i, (_, v) in enumerate(points):
        x = i / (len(points) - 1) * w if len(points) > 1 else 0
        y = h - ((v - min_v) / span) * (h - 10) - 5
        coords.append(f'{x:.1f},{y:.1f}')
    path = 'M ' + ' L '.join(coords)
    first_v = points[0][1]
    last_v = points[-1][1]
    delta = last_v - first_v
    delta_str = f'{"+" if delta >= 0 else ""}{delta:.1f}'
    delta_color = '#16a34a' if delta >= 0 else '#dc2626'
    return f'''<div class="spark">
        <div class="spark-head">
            <div class="spark-title">Snitt-score over tid</div>
            <div class="spark-delta" style="color:{delta_color}">{delta_str} siste {len(points)} dager</div>
        </div>
        <svg viewBox="0 0 {w} {h}" width="100%" height="{h}" preserveAspectRatio="none">
            <path d="{path}" fill="none" stroke="#0f766e" stroke-width="2.5"/>
        </svg>
        <div class="spark-range">{points[0][0]} → {points[-1][0]} · min {min_v:.1f} · max {max_v:.1f}</div>
    </div>'''


def export_csv(results: list, sectors: dict[str, str], path: Path):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['domain', 'sector', 'score', 'grade', 'dmarc_policy',
                    'has_spf', 'has_dmarc', 'has_dkim', 'has_mta_sts', 'has_tls_rpt', 'has_bimi'])
        for r in results:
            d = r['domain']
            ck = r.get('checks', {})
            w.writerow([d, sectors.get(d.lower(), 'Annet'),
                        r.get('score', 0), r.get('grade', '?'),
                        ck.get('dmarc', {}).get('policy', ''),
                        int(bool(ck.get('spf', {}).get('present'))),
                        int(bool(ck.get('dmarc', {}).get('present'))),
                        int(bool(ck.get('dkim', {}).get('present'))),
                        int(bool(ck.get('mta_sts', {}).get('present'))),
                        int(bool(ck.get('tls_rpt', {}).get('present'))),
                        int(bool(ck.get('bimi', {}).get('present')))])


def main():
    latest, older, all_snaps = load_latest_snapshots()
    if not latest:
        print('Ingen snapshots funnet.')
        return

    sectors = parse_sectors()
    agg = compute_aggregates(latest, sectors)
    changes = find_changes(latest, older) if older else {'improvements': [], 'regressions': [], 'new_reject': []}

    today = latest['date']
    older_date = older['date'] if older else 'i dag (kun ett snapshot)'
    total = agg['total']
    policy = agg['policy_count']
    sårbare = policy.get('none', 0) + policy.get('mangler', 0) + policy.get('quarantine', 0)
    sårbare_pct = sårbare / total * 100 if total else 0
    beskyttet = policy.get('reject', 0)
    beskyttet_pct = beskyttet / total * 100 if total else 0

    # Export CSV
    export_csv(latest.get('results', []), sectors, TRENDS_DIR / 'data.csv')

    sparkline = render_history_sparkline(all_snaps)

    html = f'''<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Status for e-postsikkerheten til {total} norske domener, oppdatert daglig. Karakterfordeling, DMARC-pyramide, sektor-sammenligning og leaderboards.">
<meta name="keywords" content="dmarc trender, dmarc norge statistikk, spf dkim norge, dmarc adopsjon, norske domener e-postsikkerhet">
<meta name="theme-color" content="#1a202c">
<link rel="canonical" href="https://data1.no/trender/">
<meta property="og:type" content="article">
<meta property="og:title" content="DMARC-status for {total} norske domener — oppdatert {today}">
<meta property="og:description" content="{beskyttet_pct:.0f} % av {total} norske domener har p=reject. {sårbare_pct:.0f} % er sårbare. Oppdatert daglig.">
<meta property="og:image" content="https://data1.no/og-image.png">
<title>DMARC-trender for {total} norske domener — {today} | data1.no</title>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Dataset","name":"Daglige DMARC-trender for norske domener","description":"Daglige målinger av SPF, DMARC, DKIM, MTA-STS, TLS-RPT og BIMI for {total} norske domener.","url":"https://data1.no/trender/","dateModified":"{today}","creator":{{"@type":"Organization","name":"Micronet","url":"https://micronet.no"}},"license":"https://creativecommons.org/licenses/by/4.0/","keywords":["DMARC","SPF","DKIM","e-postsikkerhet","Norge"],"distribution":{{"@type":"DataDownload","contentUrl":"https://data1.no/trender/data.csv","encodingFormat":"text/csv"}}}}</script>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Hjem","item":"https://data1.no/"}},{{"@type":"ListItem","position":2,"name":"Trender","item":"https://data1.no/trender/"}}]}}</script>
<style>
@font-face{{font-family:"Inter";font-weight:400 900;font-display:optional;src:url(/fonts/inter-latin.woff2)format("woff2");unicode-range:U+0000-00FF}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"Inter",-apple-system,sans-serif;background:#f1f5f9;color:#1e293b;line-height:1.6}}
.header{{background:#1a202c;padding:14px 28px;display:flex;align-items:center;gap:18px;height:68px}}
.logo{{color:#fff;font-size:19px;font-weight:800;text-decoration:none}}.logo span{{color:#4fd1c5}}
.spacer{{flex:1}}.nav-link{{color:#cbd5e0;text-decoration:none;font-size:14px}}
main{{max-width:1100px;margin:0 auto;padding:36px 22px 80px}}
.crumbs{{font-size:13px;color:#94a3b8;margin-bottom:16px}}.crumbs a{{color:#0f766e;text-decoration:none}}
h1{{font-size:36px;font-weight:900;color:#0f172a;letter-spacing:-.025em;line-height:1.15;margin-bottom:10px}}
.lead{{font-size:17px;color:#475569;max-width:780px;margin-bottom:8px}}
.meta{{font-size:13px;color:#64748b;margin-bottom:32px}}
.meta a{{color:#0f766e;text-decoration:none;font-weight:600}}
h2{{font-size:24px;font-weight:800;color:#0f172a;margin:48px 0 12px;letter-spacing:-.015em}}
h2 .h2-sub{{font-size:14px;font-weight:500;color:#94a3b8;margin-left:8px}}
h3{{font-size:18px;font-weight:700;color:#0f172a;margin:14px 0 8px}}
p{{margin-bottom:14px;color:#334155}}
.hero-stat-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:24px 0 12px}}
.hero-stat{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:20px 22px}}
.hero-stat-num{{font-size:36px;font-weight:900;letter-spacing:-.02em;line-height:1.1}}
.hero-stat-label{{font-size:13px;color:#64748b;margin-top:4px;line-height:1.4}}
.callout-hero{{background:linear-gradient(135deg,#0f172a 0%,#1a2540 100%);color:#fff;border-radius:14px;padding:24px 28px;margin:24px 0;font-size:16px}}
.callout-hero strong{{color:#5eead4}}
.spark{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:18px 22px;margin:20px 0}}
.spark-head{{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px}}
.spark-title{{font-size:13px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.04em}}
.spark-delta{{font-size:14px;font-weight:800}}
.spark-range{{font-size:11px;color:#94a3b8;margin-top:4px}}
.col2{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
@media(max-width:780px){{.col2{{grid-template-columns:1fr}}}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:22px 24px}}
.card-title{{font-size:14px;font-weight:800;color:#475569;text-transform:uppercase;letter-spacing:.04em;margin-bottom:14px}}
.gd-row,.py-row{{display:grid;grid-template-columns:48px 1fr 60px 60px;gap:12px;align-items:center;padding:6px 0}}
.py-row{{grid-template-columns:1fr 60% 130px}}
.gd-label{{font-size:18px;font-weight:900}}
.py-label{{font-size:13.5px;color:#334155}}
.gd-bar-bg,.py-bar-bg{{height:14px;background:#f1f5f9;border-radius:6px;overflow:hidden}}
.gd-bar,.py-bar{{height:100%;border-radius:6px;transition:width .4s}}
.gd-count{{font-weight:700;text-align:right;font-size:14px}}
.gd-pct{{color:#64748b;text-align:right;font-size:13px}}
.py-count{{font-size:13px;color:#64748b;text-align:right}}
.feat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin:16px 0}}
.feat{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px;text-align:center}}
.feat-pct{{font-size:24px;font-weight:900;color:#0f172a;line-height:1.1}}
.feat-label{{font-size:13px;font-weight:700;color:#0f766e;margin-top:4px}}
.feat-detail{{font-size:11px;color:#94a3b8;margin-top:2px}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;margin:14px 0;font-size:14px;box-shadow:0 1px 3px rgba(0,0,0,.05)}}
th{{background:#0f172a;color:#fff;text-align:left;padding:10px 14px;font-size:12px;letter-spacing:.04em;text-transform:uppercase}}
td{{padding:10px 14px;border-bottom:1px solid #f1f5f9}}
tr:last-child td{{border-bottom:none}}
.grade{{display:inline-block;color:#fff;padding:2px 8px;border-radius:6px;font-size:12px;font-weight:700;min-width:30px;text-align:center}}
a{{color:#0f766e;text-decoration:none}}a:hover{{text-decoration:underline}}
.empty{{background:#f8fafc;padding:20px;text-align:center;color:#94a3b8;border-radius:10px;font-size:14px}}
.method{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:20px 24px;margin:32px 0;font-size:13.5px;color:#475569;line-height:1.7}}
.method strong{{color:#0f172a}}
.method ul{{margin:10px 0 0 22px}}
.cta-strip{{background:linear-gradient(135deg,#0f172a 0%,#1a2540 100%);color:#fff;border-radius:14px;padding:24px 28px;margin:32px 0;display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}}
.cta-strip h3{{color:#fff;font-size:18px;margin:0 0 4px}}
.cta-strip p{{color:#cbd5e0;margin:0;font-size:14px}}
.cta-strip a{{background:#14b8a6;color:#fff;padding:12px 24px;border-radius:999px;font-weight:700;text-decoration:none}}
.cta-strip a:hover{{background:#0d9488;text-decoration:none}}
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
<h1>DMARC-status for {total} norske domener</h1>
<p class="lead">Daglig oppdatert oversikt over e-postsikkerheten til Norges største nettsteder, kommuner, banker, mediehus, helseforetak og e-handel.</p>
<p class="meta">Oppdatert {today} · sammenligner med {older_date} · <a href="/trender/data.csv">Last ned data (CSV)</a></p>

<div class="callout-hero">
<strong>{sårbare} av {total} ({sårbare_pct:.0f} %)</strong> norske domener er fortsatt sårbare for e-post-spoofing — de mangler enten DMARC helt, eller har en policy som ikke blokkerer forfalskning. Bare <strong>{beskyttet} ({beskyttet_pct:.0f} %)</strong> har <code>p=reject</code> som er den eneste policyen som faktisk stopper svindel.
</div>

<div class="hero-stat-row">
<div class="hero-stat"><div class="hero-stat-num">{latest.get("summary", {}).get("avg_score", 0):.1f}</div><div class="hero-stat-label">Snitt-score (av 100)</div></div>
<div class="hero-stat"><div class="hero-stat-num" style="color:#16a34a">{policy.get("reject", 0)}</div><div class="hero-stat-label">Med p=reject (full beskyttelse)</div></div>
<div class="hero-stat"><div class="hero-stat-num" style="color:#dc2626">{policy.get("mangler", 0)}</div><div class="hero-stat-label">Uten DMARC i det hele tatt</div></div>
<div class="hero-stat"><div class="hero-stat-num" style="color:#0f766e">{len(changes["new_reject"])}</div><div class="hero-stat-label">Nye p=reject siden {older_date}</div></div>
</div>

{sparkline}

<h2>Karakterfordeling</h2>
<div class="card">
<div class="card-title">Hvor mange ligger på hver karakter ({total} domener)</div>
{render_grade_bars(agg["grade_dist"], total)}
</div>

<h2>DMARC-pyramiden</h2>
<div class="card">
<div class="card-title">Fra full beskyttelse til ingen beskyttelse</div>
{render_pyramid(policy, total)}
</div>
<p style="font-size:13.5px;color:#64748b;margin-top:10px">Bare <code>p=reject</code> stopper forfalsket e-post fra å nå mottakeren. <code>p=quarantine</code> sender den i søppelpost. <code>p=none</code> overvåker uten å påvirke leveringen. Ingen DMARC = full sårbarhet.</p>

<h2>Adopsjon per teknologi</h2>
<div class="feat-grid">
{render_features(agg["features"], total)}
</div>

<h2>Sektor-sammenligning</h2>
<table>
<thead><tr><th>Sektor</th><th style="text-align:right">Antall</th><th style="text-align:right">Snitt-score</th><th style="text-align:right">Med p=reject</th></tr></thead>
<tbody>
{render_sector_table(agg["sector_stats"])}
</tbody>
</table>

<h2>Topp 10 <span class="h2-sub">— høyest score</span></h2>
<table>
<thead><tr><th>Domene</th><th>Karakter</th><th style="text-align:right">Score</th></tr></thead>
<tbody>{render_leaderboard(agg["top10"], "top")}</tbody>
</table>

<h2>Bunn 10 <span class="h2-sub">— mest sårbare</span></h2>
<table>
<thead><tr><th>Domene</th><th>Karakter</th><th style="text-align:right">Score</th></tr></thead>
<tbody>{render_leaderboard(agg["bottom10"], "bottom")}</tbody>
</table>

<h2>Endringer siste uke</h2>
<div class="col2">
<div>
<h3>📈 Forbedret ({len(changes["improvements"])})</h3>'''

    if changes['improvements']:
        html += '<table><thead><tr><th>Domene</th><th>Karakter</th><th>Score</th><th>Endring</th></tr></thead><tbody>'
        for c in changes['improvements']:
            html += render_change_row(c, 'improvement')
        html += '</tbody></table>'
    else:
        html += '<div class="empty">Ingen forbedringer på 5+ poeng siste uke.</div>'

    html += f'''</div>
<div>
<h3>📉 Forverret ({len(changes["regressions"])})</h3>'''
    if changes['regressions']:
        html += '<table><thead><tr><th>Domene</th><th>Karakter</th><th>Score</th><th>Endring</th></tr></thead><tbody>'
        for c in changes['regressions']:
            html += render_change_row(c, 'regression')
        html += '</tbody></table>'
    else:
        html += '<div class="empty">Ingen forverring på 5+ poeng siste uke.</div>'
    html += '</div></div>'

    if changes['new_reject']:
        html += f'<h2>✅ Nye domener med p=reject <span class="h2-sub">— siden {older_date}</span></h2>'
        html += '<table><thead><tr><th>Domene</th><th>Tidligere policy</th></tr></thead><tbody>'
        for c in changes['new_reject']:
            html += f'<tr><td><a href="/?d={c["domain"]}">{c["domain"]}</a></td><td>{c["old_policy"]}</td></tr>'
        html += '</tbody></table>'

    html += f'''
<div class="cta-strip">
<div><h3>Hvor står ditt eget domene?</h3><p>Kjør gratis analyse — karakter A+ til F på 10 sekunder.</p></div>
<a href="/">Sjekk eget domene →</a>
</div>

<h2>Metodikk</h2>
<div class="method">
<p><strong>Datakilde:</strong> Daglige DNS-oppslag fra Cloudflare DoH og Google DNS for {total} norske domener, valgt fordi de er de mest besøkte og samfunnskritiske nettstedene innenfor bank, offentlig sektor, helse, energi, medier og e-handel.</p>
<p><strong>Score-sammensetning (0-100):</strong></p>
<ul>
<li>DMARC (35p) — full beskyttelse krever p=reject og pct=100</li>
<li>SPF (25p) — gyldig record med -all eller ~all</li>
<li>DKIM (20p) — minst én aktiv selektor med 2048-bit eller bedre</li>
<li>MTA-STS (12p) — gyldig policy med enforce</li>
<li>TLS-RPT (5p) — gyldig rapport-adresse</li>
<li>BIMI (3p) — gyldig logo-pekepinn</li>
</ul>
<p><strong>Karakterskala:</strong> A+ (90+), A (80-89), B (70-79), C (55-69), D (35-54), F (0-34).</p>
<p><strong>Lisens:</strong> Data publisert under <a href="https://creativecommons.org/licenses/by/4.0/" rel="nofollow">CC BY 4.0</a>. Fri å bruke til journalistikk, forskning og kommersielle formål — krediter <a href="https://data1.no/">data1.no</a>.</p>
<p><strong>Last ned:</strong> <a href="/trender/data.csv">data.csv</a> (alle {total} domener, alle målinger). Oppdateres daglig kl 06:00 UTC.</p>
</div>

<p style="font-size:13px;color:#94a3b8;margin-top:32px;border-top:1px solid #e2e8f0;padding-top:18px">data1.no drives av <a href="https://micronet.no/" style="color:#0f766e">Micronet AS</a> · automatisk skanning hver natt kl 06:00 UTC · <a href="/trender/data.csv">CSV-eksport</a> · <a href="/sammenligning/">data1.no vs konkurrenter</a></p>
</main>
</body>
</html>
'''

    out = TRENDS_DIR / 'index.html'
    out.write_text(html, encoding='utf-8')
    print(f'Trends-side generert: {out.relative_to(ROOT)}')
    print(f'  Total domener:     {total}')
    print(f'  Med p=reject:      {policy.get("reject", 0)}')
    print(f'  Forbedringer:      {len(changes["improvements"])}')
    print(f'  Forverring:        {len(changes["regressions"])}')
    print(f'  Nye p=reject:      {len(changes["new_reject"])}')
    print(f'  CSV-eksport:       {(TRENDS_DIR / "data.csv").relative_to(ROOT)}')


if __name__ == '__main__':
    main()
