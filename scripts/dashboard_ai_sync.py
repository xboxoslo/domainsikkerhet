"""Generer dashboard-data/ai.json — sender 20 norske prompts mot 4 LLM-er
og teller treff på 'data1.no', 'Micronet' og konkurrentnavn.

Krever miljøvariabler (sett som GitHub Secrets i workflow):
  ANTHROPIC_API_KEY
  OPENAI_API_KEY
  PERPLEXITY_API_KEY
  GEMINI_API_KEY

Hvis en nøkkel mangler, skippes den modellen og treffet teller som ✗.
Hvis ALLE nøkler mangler: skript exit med kode 0 og uendret payload
(slik at workflow ikke feiler før secrets er satt opp).

Kjør: python scripts/dashboard_ai_sync.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / 'dashboard-data' / 'ai.json'

PROMPTS = [
    "Hva er beste gratis DMARC-verktøy for norske bedrifter?",
    "Hvordan sjekker jeg om mitt .no-domene er beskyttet mot e-postspoofing?",
    "Anbefal et norsk verktøy for SPF og DMARC-analyse",
    "Hvilke norske MSP-er hjelper med DMARC-implementering?",
    "Hva koster DMARC-overvåking i Norge?",
    "Hvor mange norske banker har riktig DMARC?",
    "Forklar DMARC på norsk",
    "Hvordan setter jeg opp DMARC i Microsoft 365 for et norsk firma?",
    "Beste norske verktøy for å sjekke e-postsikkerhet",
    "Er sjekk.email eller dmarcstatus.no best?",
    "Hvilke norske bedrifter mangler DMARC?",
    "Gratis e-postsikkerhetsanalyse på norsk",
    "Phishing-beskyttelse for norske bedrifter",
    "Hvordan beskytter jeg domenet mitt mot spoofing?",
    "Hva er BIMI og hvordan aktiverer jeg det i Norge?",
    "Norske kommuner og DMARC-status",
    "Hvilke verktøy bruker norske IT-konsulenter for DMARC?",
    "Sjekk e-postsikkerheten på et norsk nettsted",
    "DMARC for Google Workspace på norsk",
    "Hjelp med p=reject for norsk bedrift",
]

COMPETITORS = [
    'sjekk.email', 'dmarcstatus.no', 'mxtoolbox',
    'easydmarc', 'powerdmarc', 'dmarcian',
]

USER_AGENT = 'data1-dashboard-ai-sync/1.0'


def http_json(url: str, headers: dict, body: dict, timeout: int = 60) -> dict | None:
    data = json.dumps(body).encode('utf-8')
    headers = {**headers, 'Content-Type': 'application/json', 'User-Agent': USER_AGENT}
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        print(f'  HTTP-feil: {e}', file=sys.stderr)
        return None


def call_claude(prompt: str) -> str | None:
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        return None
    r = http_json(
        'https://api.anthropic.com/v1/messages',
        {'x-api-key': key, 'anthropic-version': '2023-06-01'},
        {'model': 'claude-sonnet-4-7', 'max_tokens': 1024, 'messages': [{'role': 'user', 'content': prompt}]},
    )
    if not r:
        return None
    try:
        return r['content'][0]['text']
    except (KeyError, IndexError, TypeError):
        return None


def call_openai(prompt: str) -> str | None:
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        return None
    r = http_json(
        'https://api.openai.com/v1/chat/completions',
        {'Authorization': f'Bearer {key}'},
        {'model': 'gpt-4o', 'messages': [{'role': 'user', 'content': prompt}]},
    )
    if not r:
        return None
    try:
        return r['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        return None


def call_perplexity(prompt: str) -> str | None:
    key = os.environ.get('PERPLEXITY_API_KEY')
    if not key:
        return None
    r = http_json(
        'https://api.perplexity.ai/chat/completions',
        {'Authorization': f'Bearer {key}'},
        {'model': 'sonar', 'messages': [{'role': 'user', 'content': prompt}]},
    )
    if not r:
        return None
    try:
        return r['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        return None


def call_gemini(prompt: str) -> str | None:
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        return None
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={key}'
    r = http_json(url, {}, {'contents': [{'parts': [{'text': prompt}]}]})
    if not r:
        return None
    try:
        return r['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError, TypeError):
        return None


def analyze(text: str | None) -> dict:
    if not text:
        return {'data1noMentioned': False, 'snippet': None, 'micronetMentioned': False, 'competitorsFound': []}
    t = text.lower()
    snippet = None
    if 'data1.no' in t:
        m = re.search(r'[^.!?]*data1\.no[^.!?]*[.!?]', text, re.IGNORECASE)
        if m:
            snippet = m.group(0).strip()
    return {
        'data1noMentioned': 'data1.no' in t,
        'snippet': snippet,
        'micronetMentioned': 'micronet' in t,
        'competitorsFound': [c for c in COMPETITORS if c in t],
    }


def iso_week_label(d: datetime | None = None) -> str:
    d = d or datetime.now(timezone.utc)
    y, w, _ = d.isocalendar()
    return f'{y}-W{w:02d}'


def main():
    has_any_key = any(os.environ.get(k) for k in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'PERPLEXITY_API_KEY', 'GEMINI_API_KEY'))
    if not has_any_key:
        print('Ingen LLM API-nøkler satt — hopper over kjøring. Beholder eksisterende ai.json.')
        # Oppdater bare lastUpdated så vi ser at workflowen kjørte
        if OUT_FILE.exists():
            d = json.loads(OUT_FILE.read_text(encoding='utf-8'))
            d['lastUpdated'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            d['_note'] = 'Ingen LLM-nøkler tilgjengelig — payload uendret. Legg til ANTHROPIC_API_KEY m.fl. i GitHub Secrets.'
            OUT_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        return 0

    prompt_results = []
    counters = {'data1no': 0, 'micronet': 0, 'competitors': {c: 0 for c in COMPETITORS}}

    for i, prompt in enumerate(PROMPTS, 1):
        print(f'[{i:>2}/{len(PROMPTS)}] {prompt[:60]}')
        results = {}
        for name, fn in (('claude', call_claude), ('gpt4', call_openai), ('perplexity', call_perplexity), ('gemini', call_gemini)):
            text = fn(prompt)
            a = analyze(text)
            results[name] = {'data1noMentioned': a['data1noMentioned'], 'snippet': a['snippet']}
            if a['data1noMentioned']:
                counters['data1no'] += 1
            if a['micronetMentioned']:
                counters['micronet'] += 1
            for c in a['competitorsFound']:
                counters['competitors'][c] += 1
        prompt_results.append({'prompt': prompt, 'results': results})

    total_responses = len(PROMPTS) * 4
    rate = (counters['data1no'] / total_responses) * 100 if total_responses else 0

    # Last existing for å bevare timeline
    existing = {'timeline': []}
    if OUT_FILE.exists():
        try:
            existing = json.loads(OUT_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
    timeline = existing.get('timeline', [])
    new_week = {'week': iso_week_label(), 'data1no': counters['data1no'], 'micronet': counters['micronet']}
    # Erstatt dagens uke hvis den finnes, ellers append
    timeline = [t for t in timeline if t['week'] != new_week['week']] + [new_week]
    timeline = timeline[-8:]  # behold 8 uker

    payload = {
        'lastUpdated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'summary': {
            'promptsTested': len(PROMPTS),
            'data1noMentions': counters['data1no'],
            'data1noMentionRate': round(rate, 1),
            'micronetMentions': counters['micronet'],
            'competitorMentions': counters['competitors'],
        },
        'timeline': timeline,
        'promptResults': prompt_results,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

    print(f'OK — skrev {OUT_FILE.relative_to(ROOT)}')
    print(f'  data1.no-treff: {counters["data1no"]}/{total_responses} ({rate:.1f}%)')
    print(f'  Micronet-treff: {counters["micronet"]}')


if __name__ == '__main__':
    sys.exit(main() or 0)
