"""Generer dashboard-data/email.json fra eksisterende daglige DNS-skann.

Leser:
  _data/snapshots/<i dag>.json     (siste daily_scan.py-output)
  _data/snapshots/<i dag - 7d>.json (for uke-endringer)

Skriver:
  dashboard-data/email.json

Idempotent. Kjør:
  python scripts/dashboard_email_sync.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS_DIR = ROOT / '_data' / 'snapshots'
OUT_FILE = ROOT / 'dashboard-data' / 'email.json'

OWN_DOMAINS = ['data1.no', 'micronet.no']

# Last inn daily_scan-modulen for å gjenbruke scan_domain() til egne domener.
# (daily_scan.py er ikke en pakke, så vi importerer via importlib)
_ds_path = ROOT / 'scripts' / 'daily_scan.py'
_spec = importlib.util.spec_from_file_location('daily_scan', _ds_path)
_daily_scan = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(ROOT / 'scripts'))
_spec.loader.exec_module(_daily_scan)


def latest_snapshot_path() -> Path | None:
    files = sorted(SNAPSHOTS_DIR.glob('20*.json'))
    return files[-1] if files else None


def load_snapshot(d: str | datetime) -> dict | None:
    if isinstance(d, datetime):
        d = d.strftime('%Y-%m-%d')
    p = SNAPSHOTS_DIR / f'{d}.json'
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding='utf-8'))


def policy_of(result: dict) -> str:
    dmarc = result.get('checks', {}).get('dmarc', {})
    if not dmarc.get('present'):
        return 'missing'
    return dmarc.get('policy') or 'none'


def score_of(result: dict) -> int:
    return result.get('score', 0)


def aggregate_tracked(results: list[dict]) -> dict:
    total = len(results)
    counters = {'missing': 0, 'none': 0, 'quarantine': 0, 'reject': 0}
    for r in results:
        p = policy_of(r)
        if p in counters:
            counters[p] += 1
        else:
            counters['none'] += 1  # unknown -> none-bucket
    return {
        'total': total,
        'withReject': counters['reject'],
        'withQuarantine': counters['quarantine'],
        'withNone': counters['none'],
        'missing': counters['missing'],
        'rejectPercent': round((counters['reject'] / total) * 100, 1) if total else 0.0,
    }


def own_domain_card(domain: str) -> dict:
    """Egne domener er ikke i daily_scan-listen — kjør live scan via DoH."""
    r = _daily_scan.scan_domain(domain)
    c = r.get('checks', {})
    dmarc = c.get('dmarc', {})
    spf = c.get('spf', {})
    dkim = c.get('dkim', {})
    mta = c.get('mta_sts', {})
    tls = c.get('tls_rpt', {})
    bimi = c.get('bimi', {})
    return {
        'domain': domain,
        'score': r.get('score', 0),
        'grade': r.get('grade', '—'),
        'dmarc': dmarc.get('record'),
        'spf': spf.get('record'),
        'dkim': ', '.join(dkim.get('selectors', [])) if dkim.get('selectors') else None,
        'mtaSts': bool(mta.get('present')),
        'tlsRpt': bool(tls.get('present')),
        'bimi': bool(bimi.get('present')),
        'lastChecked': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }


def weekly_changes(today: dict, last_week: dict | None) -> dict:
    if not last_week:
        return {'improved': [], 'regressed': []}
    by_domain_today = {r['domain']: r for r in today['results']}
    by_domain_lw = {r['domain']: r for r in last_week['results']}
    improved, regressed = [], []
    for domain, r_today in by_domain_today.items():
        r_lw = by_domain_lw.get(domain)
        if not r_lw:
            continue
        score_today = r_today.get('score', 0)
        score_lw = r_lw.get('score', 0)
        delta = score_today - score_lw
        if delta == 0:
            continue
        policy_today = f"p={policy_of(r_today)}"
        policy_lw = f"p={policy_of(r_lw)}"
        entry = {
            'domain': domain,
            'from': policy_lw,
            'to': policy_today,
            'scoreDelta': delta,
        }
        if delta > 0:
            improved.append(entry)
        else:
            regressed.append(entry)
    improved.sort(key=lambda x: -x['scoreDelta'])
    regressed.sort(key=lambda x: x['scoreDelta'])
    return {
        'improved': improved[:10],
        'regressed': regressed[:10],
    }


def build_timeline() -> list[dict]:
    """% p=reject de siste 12 ukene basert på ukens siste snapshot."""
    out = []
    today = datetime.now(timezone.utc).date()
    seen_weeks = set()
    for weeks_back in range(0, 12):
        target = today - timedelta(weeks=weeks_back)
        # Finn ukens fredag/siste tilgjengelige snapshot
        for offset in range(0, 7):
            d = target - timedelta(days=offset)
            snap = load_snapshot(d)
            if snap is None:
                continue
            iso_year, iso_week, _ = d.isocalendar()
            week_key = f'{iso_year}-W{iso_week:02d}'
            if week_key in seen_weeks:
                break
            seen_weeks.add(week_key)
            agg = aggregate_tracked(snap['results'])
            out.append({'week': week_key, 'rejectPercent': agg['rejectPercent']})
            break
    return list(reversed(out))


def main():
    latest = latest_snapshot_path()
    if latest is None:
        raise SystemExit('Ingen snapshots funnet i _data/snapshots/')
    today = json.loads(latest.read_text(encoding='utf-8'))
    today_date = datetime.fromisoformat(today.get('date') or today.get('timestamp', '').replace('Z', '+00:00').split('T')[0])
    last_week_date = (today_date - timedelta(days=7)).strftime('%Y-%m-%d')
    last_week = load_snapshot(last_week_date)

    payload = {
        'lastUpdated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'ownDomains': [own_domain_card(d) for d in OWN_DOMAINS],
        'trackedDomains': aggregate_tracked(today['results']),
        'weeklyChanges': weekly_changes(today, last_week),
        'timeline': build_timeline(),
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

    print(f'OK — skrev {OUT_FILE.relative_to(ROOT)} ({OUT_FILE.stat().st_size} bytes)')
    print(f'  Egne domener: {len(payload["ownDomains"])}')
    print(f'  Sporet:        {payload["trackedDomains"]["total"]}')
    print(f'  p=reject:      {payload["trackedDomains"]["rejectPercent"]}%')
    print(f'  Forbedret:     {len(payload["weeklyChanges"]["improved"])}')
    print(f'  Forverret:     {len(payload["weeklyChanges"]["regressed"])}')
    print(f'  Tidslinje:     {len(payload["timeline"])} uker')


if __name__ == '__main__':
    main()
