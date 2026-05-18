"""Wikipedia (no.wikipedia.org) CRUD-klient mot MediaWiki Action API.

Henter bot-credentials fra Azure Key Vault (vault: micronet-data1-kv).
Fallback til intake-secrets.env eller miljøvariabler WIKI_BOT_USERNAME / WIKI_BOT_PASSWORD.

Bruk:
  python scripts/wiki_edit.py whoami
  python scripts/wiki_edit.py read "Sidetittel" [--section N]
  python scripts/wiki_edit.py history "Sidetittel" [--limit 10]
  python scripts/wiki_edit.py edit "Sidetittel" --text "..." [--summary "..."] [--minor] [--dry-run]
  python scripts/wiki_edit.py append "Sidetittel" --text "..." [--summary "..."] [--dry-run]
  python scripts/wiki_edit.py prepend "Sidetittel" --text "..." [--summary "..."] [--dry-run]
  python scripts/wiki_edit.py replace-section "Sidetittel" --section N --text "..." [--summary "..."]
  python scripts/wiki_edit.py create "Sidetittel" --text "..." [--summary "..."] [--dry-run]

Sikkerhet:
  - Alle skrive-operasjoner krever --yes for å faktisk publisere, ellers dry-run.
  - Edit summary får automatisk prefiks "(via wiki_edit.py)" for sporbarhet.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

API = 'https://no.wikipedia.org/w/api.php'
USER_AGENT = 'data1-wiki-edit/1.0 (https://no.wikipedia.org/wiki/Bruker:Terje_Otterlei)'

AZURE_SECRETS = {
    'WIKI_BOT_USERNAME': ('micronet-data1-kv', 'Wikipedia-Bot-Username'),
    'WIKI_BOT_PASSWORD': ('micronet-data1-kv', 'Wikipedia-Bot-Password'),
}


def _find_az_cli():
    import shutil
    path = shutil.which('az') or shutil.which('az.cmd')
    if path:
        return path
    windows_default = r'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'
    if os.name == 'nt' and Path(windows_default).exists():
        return windows_default
    return None


def load_credentials() -> tuple[str, str]:
    # 1. .env fallback
    env_path = Path(__file__).resolve().parent.parent / 'intake-secrets.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            if k in AZURE_SECRETS and not os.environ.get(k):
                os.environ[k] = v.strip().strip('"').strip("'")

    # 2. Azure Key Vault for det som mangler
    missing = [k for k in AZURE_SECRETS if not os.environ.get(k)]
    if missing:
        az = _find_az_cli()
        if az:
            for key in missing:
                vault, secret = AZURE_SECRETS[key]
                try:
                    r = subprocess.run(
                        [az, 'keyvault', 'secret', 'show',
                         '--vault-name', vault, '--name', secret,
                         '--query', 'value', '-o', 'tsv'],
                        capture_output=True, text=True, timeout=10, check=False,
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        os.environ[key] = r.stdout.strip()
                except Exception:
                    pass

    user = os.environ.get('WIKI_BOT_USERNAME', '').strip()
    pwd = os.environ.get('WIKI_BOT_PASSWORD', '').strip()
    if not user or not pwd:
        sys.exit('FEIL: WIKI_BOT_USERNAME/WIKI_BOT_PASSWORD ikke satt. Se scripts/wiki_setup.md.')
    return user, pwd


class WikiSession:
    def __init__(self) -> None:
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies),
        )
        self.opener.addheaders = [('User-Agent', USER_AGENT)]

    def _request(self, method: str, params: dict) -> dict:
        params = {**params, 'format': 'json', 'formatversion': '2'}
        if method == 'GET':
            url = f'{API}?{urllib.parse.urlencode(params)}'
            req = urllib.request.Request(url, method='GET')
        else:
            data = urllib.parse.urlencode(params).encode('utf-8')
            req = urllib.request.Request(API, data=data, method='POST')
        with self.opener.open(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise RuntimeError(f'Ikke-JSON svar: {body[:200]}')

    def get(self, **params) -> dict:
        return self._request('GET', params)

    def post(self, **params) -> dict:
        return self._request('POST', params)

    def login(self, username: str, password: str) -> None:
        tok = self.get(action='query', meta='tokens', type='login')
        login_token = tok['query']['tokens']['logintoken']
        r = self.post(action='login', lgname=username, lgpassword=password, lgtoken=login_token)
        result = r.get('login', {}).get('result')
        if result != 'Success':
            raise RuntimeError(f'Innlogging feilet: {r}')

    def csrf_token(self) -> str:
        r = self.get(action='query', meta='tokens')
        return r['query']['tokens']['csrftoken']

    def whoami(self) -> dict:
        return self.get(action='query', meta='userinfo', uiprop='groups|rights')['query']['userinfo']

    def read_page(self, title: str, section: int | None = None) -> str:
        params = dict(action='parse', page=title, prop='wikitext')
        if section is not None:
            params['section'] = str(section)
        r = self.get(**params)
        if 'error' in r:
            raise RuntimeError(r['error'].get('info', str(r['error'])))
        return r['parse']['wikitext']

    def history(self, title: str, limit: int = 10) -> list[dict]:
        r = self.get(action='query', prop='revisions', titles=title,
                     rvprop='timestamp|user|comment|size', rvlimit=str(limit))
        pages = r.get('query', {}).get('pages', [])
        if not pages:
            return []
        return pages[0].get('revisions', [])

    def edit(self, *, title: str, text: str | None = None,
             appendtext: str | None = None, prependtext: str | None = None,
             section: int | None = None, summary: str = '',
             minor: bool = False, createonly: bool = False) -> dict:
        token = self.csrf_token()
        params = dict(action='edit', title=title, token=token, bot='', summary=summary)
        if text is not None:
            params['text'] = text
        if appendtext is not None:
            params['appendtext'] = appendtext
        if prependtext is not None:
            params['prependtext'] = prependtext
        if section is not None:
            params['section'] = str(section)
        if minor:
            params['minor'] = ''
        if createonly:
            params['createonly'] = ''
        r = self.post(**params)
        if 'error' in r:
            raise RuntimeError(r['error'].get('info', str(r['error'])))
        return r.get('edit', r)


def _confirm_write(args, action: str, title: str, preview: str) -> bool:
    print(f'\n=== {action}: {title} ===')
    print(f'(antall tegn: {len(preview)})')
    print('--- innhold ---')
    print(preview)
    print('--- slutt ---')
    if not args.yes:
        print('\nDry-run (ingen endringer publisert). Kjør på nytt med --yes for å publisere.')
        return False
    return True


def _stamp_summary(summary: str) -> str:
    suffix = ' (via wiki_edit.py)'
    if not summary:
        return 'Oppdatering' + suffix
    return summary if suffix in summary else summary + suffix


def main():
    p = argparse.ArgumentParser(description='no.wikipedia.org CRUD')
    sp = p.add_subparsers(dest='cmd', required=True)

    sp.add_parser('whoami')

    pr = sp.add_parser('read')
    pr.add_argument('title')
    pr.add_argument('--section', type=int)

    ph = sp.add_parser('history')
    ph.add_argument('title')
    ph.add_argument('--limit', type=int, default=10)

    for name in ('edit', 'append', 'prepend', 'create'):
        s = sp.add_parser(name)
        s.add_argument('title')
        g = s.add_mutually_exclusive_group(required=True)
        g.add_argument('--text', help='Tekstinnhold direkte')
        g.add_argument('--text-file', help='Les tekstinnhold fra fil (UTF-8)')
        s.add_argument('--summary', default='')
        s.add_argument('--minor', action='store_true')
        s.add_argument('--yes', action='store_true', help='Faktisk publiser (ellers dry-run)')

    s = sp.add_parser('replace-section')
    s.add_argument('title')
    s.add_argument('--section', type=int, required=True)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument('--text', help='Tekstinnhold direkte')
    g.add_argument('--text-file', help='Les tekstinnhold fra fil (UTF-8)')
    s.add_argument('--summary', default='')
    s.add_argument('--minor', action='store_true')
    s.add_argument('--yes', action='store_true')

    args = p.parse_args()

    # Hvis et skrive-cmd har --text-file, les inn innholdet til args.text
    if hasattr(args, 'text_file') and args.text_file:
        args.text = Path(args.text_file).read_text(encoding='utf-8')

    user, pwd = load_credentials()
    s = WikiSession()
    s.login(user, pwd)

    if args.cmd == 'whoami':
        info = s.whoami()
        print(f'Innlogget som: {info.get("name")}')
        print(f'Grupper:       {", ".join(info.get("groups", []))}')
        print(f'ID:            {info.get("id")}')
        return

    if args.cmd == 'read':
        print(s.read_page(args.title, section=args.section))
        return

    if args.cmd == 'history':
        for rev in s.history(args.title, limit=args.limit):
            print(f'{rev.get("timestamp")}  {rev.get("user"):20s}  {rev.get("comment", "")[:80]}')
        return

    summary = _stamp_summary(args.summary)

    if args.cmd in ('edit', 'replace-section'):
        if not _confirm_write(args, args.cmd, args.title, args.text):
            return
        section = getattr(args, 'section', None)
        r = s.edit(title=args.title, text=args.text, section=section,
                   summary=summary, minor=args.minor)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    if args.cmd == 'append':
        if not _confirm_write(args, 'append', args.title, args.text):
            return
        r = s.edit(title=args.title, appendtext=args.text, summary=summary, minor=args.minor)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    if args.cmd == 'prepend':
        if not _confirm_write(args, 'prepend', args.title, args.text):
            return
        r = s.edit(title=args.title, prependtext=args.text, summary=summary, minor=args.minor)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return

    if args.cmd == 'create':
        if not _confirm_write(args, 'create', args.title, args.text):
            return
        r = s.edit(title=args.title, text=args.text, summary=summary,
                   minor=args.minor, createonly=True)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return


if __name__ == '__main__':
    main()
