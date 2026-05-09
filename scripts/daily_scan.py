"""
Daily DNS scan — kjøres av GitHub Actions hver morgen.

Skanner alle domener i _data/domains-watchlist.txt for SPF, DMARC, DKIM, MTA-STS,
TLS-RPT og BIMI via Cloudflare DoH. Lagrer snapshot i _data/snapshots/YYYY-MM-DD.json.
"""
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Tillat SSL-bypass for lokal testing på Windows (sett DAILY_SCAN_INSECURE=1)
SSL_CTX = None
if os.environ.get('DAILY_SCAN_INSECURE') == '1':
    SSL_CTX = ssl.create_default_context()
    SSL_CTX.check_hostname = False
    SSL_CTX.verify_mode = ssl.CERT_NONE

ROOT = Path(__file__).parent.parent
DOMAINS_FILE = ROOT / '_data' / 'domains-watchlist.txt'
SNAPSHOTS_DIR = ROOT / '_data' / 'snapshots'
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

DOH_URL = 'https://cloudflare-dns.com/dns-query'
HEADERS = {'Accept': 'application/dns-json', 'User-Agent': 'data1.no-bot/1.0'}

DKIM_SELECTORS = [
    'selector1', 'selector2', 'google', 'k1', 'k2', 'mandrill', 'mxvault',
    'default', 'dkim', 's1', 's2', 'mail', 'protonmail', 'mailo',
]


def doh_query(name: str, qtype: str = 'TXT', timeout: int = 10) -> list[str]:
    """Spør Cloudflare DoH og returner liste over TXT-records (eller []."""
    try:
        url = f'{DOH_URL}?name={urllib.parse.quote(name)}&type={qtype}'
        req = urllib.request.Request(url, headers=HEADERS)
        kwargs = {'timeout': timeout}
        if SSL_CTX is not None:
            kwargs['context'] = SSL_CTX
        with urllib.request.urlopen(req, **kwargs) as r:
            data = json.loads(r.read())
        answers = data.get('Answer', [])
        return [a['data'].strip('"') for a in answers if a.get('type') == (16 if qtype == 'TXT' else 0)]
    except Exception:
        return []


def check_spf(domain: str) -> dict:
    txts = doh_query(domain, 'TXT')
    spf = next((t for t in txts if t.lower().startswith('v=spf1')), None)
    return {
        'present': bool(spf),
        'record': spf,
        'all_qualifier': re.search(r'([+\-~?])all', spf).group(1) if spf and re.search(r'([+\-~?])all', spf) else None,
    }


def check_dmarc(domain: str) -> dict:
    txts = doh_query(f'_dmarc.{domain}', 'TXT')
    dmarc = next((t for t in txts if t.lower().startswith('v=dmarc1')), None)
    policy = None
    pct = None
    if dmarc:
        m = re.search(r'p=(\w+)', dmarc, re.I)
        policy = m.group(1).lower() if m else None
        m = re.search(r'pct=(\d+)', dmarc, re.I)
        pct = int(m.group(1)) if m else 100
    return {
        'present': bool(dmarc),
        'record': dmarc,
        'policy': policy,
        'pct': pct,
    }


def check_dkim(domain: str) -> dict:
    found = []
    for selector in DKIM_SELECTORS:
        txts = doh_query(f'{selector}._domainkey.{domain}', 'TXT')
        for t in txts:
            if 'v=dkim1' in t.lower() or 'p=' in t.lower():
                found.append(selector)
                break
    return {'present': bool(found), 'selectors': found}


def check_mta_sts(domain: str) -> dict:
    txts = doh_query(f'_mta-sts.{domain}', 'TXT')
    rec = next((t for t in txts if t.lower().startswith('v=stsv1')), None)
    return {'present': bool(rec), 'record': rec}


def check_tls_rpt(domain: str) -> dict:
    txts = doh_query(f'_smtp._tls.{domain}', 'TXT')
    rec = next((t for t in txts if t.lower().startswith('v=tlsrptv1')), None)
    return {'present': bool(rec), 'record': rec}


def check_bimi(domain: str) -> dict:
    txts = doh_query(f'default._bimi.{domain}', 'TXT')
    rec = next((t for t in txts if t.lower().startswith('v=bimi1')), None)
    return {'present': bool(rec), 'record': rec}


def compute_score(checks: dict) -> tuple[int, str]:
    """Vekter: DMARC 35, SPF 25, DKIM 20, MTA-STS 12, TLS-RPT 5, BIMI 3."""
    score = 0
    spf = checks['spf']
    if spf['present']:
        if spf['all_qualifier'] == '-':
            score += 25
        elif spf['all_qualifier'] == '~':
            score += 20
        elif spf['all_qualifier'] == '?':
            score += 10
        else:
            score += 5

    dmarc = checks['dmarc']
    if dmarc['present']:
        if dmarc['policy'] == 'reject' and dmarc['pct'] == 100:
            score += 35
        elif dmarc['policy'] == 'reject':
            score += 28
        elif dmarc['policy'] == 'quarantine':
            score += 20
        else:
            score += 8

    if checks['dkim']['present']:
        score += 20
    if checks['mta_sts']['present']:
        score += 12
    if checks['tls_rpt']['present']:
        score += 5
    if checks['bimi']['present']:
        score += 3

    if score >= 90:
        grade = 'A+'
    elif score >= 80:
        grade = 'A'
    elif score >= 70:
        grade = 'B'
    elif score >= 55:
        grade = 'C'
    elif score >= 35:
        grade = 'D'
    else:
        grade = 'F'

    return score, grade


def scan_domain(domain: str) -> dict:
    checks = {
        'spf': check_spf(domain),
        'dmarc': check_dmarc(domain),
        'dkim': check_dkim(domain),
        'mta_sts': check_mta_sts(domain),
        'tls_rpt': check_tls_rpt(domain),
        'bimi': check_bimi(domain),
    }
    score, grade = compute_score(checks)
    return {
        'domain': domain,
        'score': score,
        'grade': grade,
        'checks': checks,
    }


def load_domains() -> list[str]:
    out = []
    for line in DOMAINS_FILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        out.append(line.lower())
    return list(dict.fromkeys(out))  # dedupe


def main():
    domains = load_domains()
    print(f'Skanner {len(domains)} domener…')

    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    output_file = SNAPSHOTS_DIR / f'{today}.json'

    results = []
    for i, d in enumerate(domains, 1):
        try:
            r = scan_domain(d)
            results.append(r)
            print(f'  [{i:3d}/{len(domains)}] {d:30s}  {r["grade"]:3s}  ({r["score"]}p)')
        except Exception as e:
            print(f'  [{i:3d}/{len(domains)}] {d:30s}  FEIL: {e}')
            results.append({'domain': d, 'error': str(e)})
        time.sleep(0.1)  # vær snill med Cloudflare

    snapshot = {
        'date': today,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'domain_count': len(domains),
        'results': results,
        'summary': {
            'avg_score': sum(r.get('score', 0) for r in results) / len(results) if results else 0,
            'grade_distribution': {g: sum(1 for r in results if r.get('grade') == g)
                                   for g in ['A+', 'A', 'B', 'C', 'D', 'F']},
            'has_dmarc_reject': sum(1 for r in results
                                    if r.get('checks', {}).get('dmarc', {}).get('policy') == 'reject'),
            'no_dmarc': sum(1 for r in results
                            if not r.get('checks', {}).get('dmarc', {}).get('present')),
        }
    }

    output_file.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\nSnapshot lagret: {output_file.relative_to(ROOT)}')
    print(f'Gjennomsnittlig score: {snapshot["summary"]["avg_score"]:.1f}')
    print(f'Karakter-fordeling: {snapshot["summary"]["grade_distribution"]}')
    print(f'Med p=reject: {snapshot["summary"]["has_dmarc_reject"]} av {len(results)}')
    print(f'Mangler DMARC: {snapshot["summary"]["no_dmarc"]} av {len(results)}')


if __name__ == '__main__':
    main()
