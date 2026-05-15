# data1 — Domeneanalyse-intake

Backend for [data1.no](https://data1.no) (`domain-analyzer.html`). Mottar POST fra skjemaet,
sender pent designet HTML-rapport via Mailgun (med 3D-skjold som inline PNG),
og oppretter draft quote i HaloPSA.

## Arkitektur

```
domain-analyzer.html  ──POST /intake──▶  intake-server.py  ──┬─▶  Mailgun (e-post m/skjold-PNG)
(brukerens nettleser)                    (lokal Python)        └─▶  HaloPSA (/api/Quotation)
```

## Komponenter

| Fil | Rolle |
|---|---|
| `intake-server.py` | Lokal Python HTTP-server (port 3001). Sender Mailgun-mail + oppretter Halo-quote. |
| `domain-analyzer.html` | Frontend-skjema. Kjører lokalt (port 3000) eller på `domeneanalyse.micronet.no`. |
| `intake-worker.js` | Cloudflare Worker-versjon (ikke deployet — beholdes som alternativ). |
| `intake-secrets.env.example` | Mal for `.env`-fila med API-nøkler (kopier til `intake-secrets.env`). |
| `scripts/` | Engangs-oppslag for å finne Halo-IDer (item, agent, template). |

## Oppsett (lokal dev, anbefalt — Azure Key Vault)

```powershell
# 1. Klon repoet
git clone https://github.com/xboxoslo/data1.git C:\dev\data1
cd C:\dev\data1

# 2. Installer avhengigheter
pip install -r requirements.txt

# 3. Logg inn på Azure (én gang per PC)
az login

# 4. Kjør serveren — secrets hentes automatisk fra micronet-data1-kv + micronet-shared-kv
python intake-server.py
```

Krever Python 3.8+ og [Azure CLI](https://aka.ms/installazurecliwindows). Ingen `.env`-fil
trengs — Halo, Mailgun og Turnstile-secrets hentes via `az login`-credentialene dine.

Vault-mapping (definert i `AZURE_SECRETS` i `intake-server.py`):

| Env var | Vault | Secret |
|---|---|---|
| `HALO_CLIENT_ID` | `micronet-data1-kv` | `Halo-Client-Id` |
| `HALO_CLIENT_SECRET` | `micronet-data1-kv` | `Halo-Client-Secret` |
| `TURNSTILE_SECRET` | `micronet-data1-kv` | `Turnstile-Secret` |
| `MAILGUN_API_KEY` | `micronet-shared-kv` | `Mailgun-Api-Key` |

### Alternativ: lokal .env-fil

Hvis du ikke vil bruke Azure (eller vil overstyre én verdi midlertidig):

```powershell
cp intake-secrets.env.example intake-secrets.env
# rediger og fyll inn — env vars vinner over .env, .env vinner over Azure
python intake-server.py
```

### Railway-prod

Secrets settes som env vars i Railway-prosjektets *Variables*-fane. Koden prøver env
vars FØRST, så prod bruker aldri Azure (ingen `az login` i container).

Server lytter på `http://localhost:3001/intake`.

Frontend må peke `INTAKE_ENDPOINT` til denne URL-en (eller en publisert variant
hvis serveren deployes utad).

## Halo-konfigurasjon (Micronet-tenant)

Default IDs som brukes i `intake-server.py`:

- **Item** `516` (`MAI001`) — Mail (SPF-DKIM-DMARC), kr 295/mnd
- **Item** `735` (`EST003`) — Estimert Service Bedrift, kr 1990 etablering (engangs)
- **PDF Template** `29` — Tilbud Micronet
- **Agent (eier)** `23` — API-bruker
- **Agent (assigned)** `3` — Terje Otterlei (review)

## E-post-design

- Inline PNG-skjold rendret med Pillow (drop-shadow, halo, hake-badge på A+/A/B)
- Karakterskala (F→A+) med aktiv karakter ringet inn
- Komponent-liste (DMARC, SPF, DKIM, MTA-STS, TLS-RPT, BIMI) med beskrivelser
- Pris kr 295/mnd vist inline
- Personlig signatur

Bygger full RFC822 MIME via `email.mime` og sender via Mailgun
`/messages.mime`-endepunktet for korrekt `Content-ID:` på inline-bilde.

## Sikkerhet

`intake-secrets.env` er gitignore'd. **Aldri commit** API-nøkler.
