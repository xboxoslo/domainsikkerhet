# DomainSikkerhet — Domeneanalyse-intake

Lokal intake-backend for `domain-analyzer.html`. Mottar POST fra skjemaet,
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

## Oppsett

```bash
# 1. Klon repoet
git clone https://github.com/<bruker>/domeneanalyse-intake.git
cd domeneanalyse-intake

# 2. Installer avhengigheter
pip install -r requirements.txt

# 3. Kopier hemmelighets-malen og fyll inn nøkler
cp intake-secrets.env.example intake-secrets.env
# Rediger intake-secrets.env med:
#   HALO_CLIENT_ID, HALO_CLIENT_SECRET, MAILGUN_API_KEY

# 4. Kjør serveren
python intake-server.py
```

Server lytter på `http://localhost:3001/intake`.

Frontend må peke `INTAKE_ENDPOINT` til denne URL-en (eller en publisert variant
hvis serveren deployes utad).

## Halo-konfigurasjon (Micronet-tenant)

Default IDs som brukes i `intake-server.py`:

- **Item** `516` (`MAI001`) — Mail (SPF-DKIM-DMARC), kr 295/mnd
- **Item** `735` (`EST003`) — Estimert Service Bedrift, kr 2080 engangs
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
