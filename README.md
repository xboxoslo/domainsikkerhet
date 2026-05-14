# data1.no

Gratis norsk verktøy for e-postsikkerhetsanalyse — spesialisert på .no-domener.
Sjekker SPF, DMARC, DKIM, MTA-STS, TLS-RPT og BIMI på sekunder, gir karakter
A+ til F og konkrete tiltak.

Drives av Micronet AS (org.nr 990 661 766). Live på https://data1.no.

## Arkitektur

```
data1.no                                   intake.data1.no
(Cloudflare Pages, statisk HTML)            (CNAME → Railway)
   │                                              │
   ├─► /index.html                                ▼
   │     analyser-domene (DNS-lookup i browser)   intake-server.py
   │     viser score + tiltak                       ├─► Cloudflare Turnstile (anti-bot)
   │                                                ├─► Halo PSA (ticket + quote)
   └─► "Send rapport på e-post"-knapp              └─► Mailgun (HTML-mail + skjold-PNG)
         POST → intake.data1.no/intake
```

| Fil / katalog            | Rolle                                                            |
|--------------------------|------------------------------------------------------------------|
| `index.html`             | Hovedfrontend (DNS-analyse, score, rapport-knapp)                |
| `intake-server.py`       | Backend (Halo + Mailgun + Turnstile + stats), kjører på Railway  |
| `Procfile`               | Railway prosess-konfig (`web: python intake-server.py`)          |
| `intake-secrets.env.example` | Eksempel-konfig for secrets                                  |
| `blogg/`                 | Bloggartikler (DMARC, SPF, DKIM, Microsoft 365, Google Workspace)|
| `rapport-2026/`          | Ukentlige rapporter (topp 100, banker, kommuner, e-handel, medier) |
| `verktoy/`               | DMARC- og SPF-generatorer                                        |
| `feil/`                  | Feilsøking-sider (SPF PermError, DKIM, m.m.)                     |
| `ordbok/`                | Definisjoner (DefinedTermSet schema for AI-ekstraksjon)          |
| `_data/`                 | Watchlist (158 domener), ukentlige rapport-data                  |
| `_assets/`               | Tracker-script, fonter                                           |
| `scripts/`               | Daily scan, sitemap-builder, IndexNow-ping, rapport-generator    |
| `docs/`                  | Intern arkitektur-dokumentasjon                                  |

## Lokal utvikling

Frontend er ren statisk HTML — server hvilken som helst HTTP-server fra repo-rot:

```sh
python3 -m http.server 3000
# Åpne http://localhost:3000
```

Backend (kun nødvendig hvis du skal teste "Send rapport"-flyten lokalt):

```sh
cp intake-secrets.env.example intake-secrets.env
# Fyll inn MAILGUN_API_KEY, HALO_CLIENT_ID, HALO_CLIENT_SECRET m.m.
python3 intake-server.py
# Lytter på http://localhost:3001
```

Frontend bruker automatisk `http://localhost:3001/intake` når den åpnes på
`localhost` eller `127.0.0.1`, og `https://intake.data1.no/intake` ellers.

## Deploy

| Komponent       | Hvor                                | Hvordan                              |
|-----------------|-------------------------------------|--------------------------------------|
| Frontend        | Cloudflare Pages                    | Auto-deploy på push til `main`       |
| Backend         | Railway                             | Auto-deploy på push til `main`       |
| DNS for `data1.no` | Cloudflare                       | Manuelt via CF-dashbordet            |

Se `docs/intake-architecture.md` for detaljer om DNS- og custom-domain-oppsett.

## Lisens

© Micronet AS. Alle rettigheter forbeholdt.
