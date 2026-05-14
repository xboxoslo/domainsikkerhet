# Migrasjonsplan: intake-server.py (Railway) → Cloudflare Worker

**Status:** Planlagt, ikke startet.
**Estimat:** 4–8 timers reelt arbeid + 1–2 dager observasjon i prod-parallell.
**Avklaring kreves før start:** se "Beslutninger" nedenfor.

---

## Hvorfor vurdere migrasjon

| Aspekt                 | Railway (dagens)                | Cloudflare Worker                                |
|------------------------|---------------------------------|--------------------------------------------------|
| Pris                   | $5/mnd minimum                  | Gratis (10M req/mnd) eller $5/mnd (unlimited)    |
| Kaldstart              | 5–30 sek etter idle             | < 50 ms (Workers er always-warm)                 |
| Geo-distribusjon       | Ett US-datasenter               | 300+ datasenter globalt                          |
| Drift                  | Egen prosess, log-konfig, OOM   | Stateless, auto-skalering, ingen serverdrift     |
| Samme infra som Pages  | Nei                             | Ja — én leverandør for hele stacken              |
| Kompatibilitet Python  | Native                          | JS/TS (Python via Pyodide finnes men er stort)   |
| PIL-rendering          | Native (PIL kjører ut av boksen)| Krever omskriving — kjernekomplikasjonen         |

Hovedmotivasjonen er kostnadsreduksjon, ytelse og infra-konsolidering.
**Hovedhindringen er PIL-portering** — alt det andre er rett-frem JS-skriving.

---

## Komponentanalyse av intake-server.py (1238 linjer)

### 1. CORS + HTTP-håndtering (lett, ~50 LOC)

`BaseHTTPRequestHandler`, `ALLOWED_ORIGINS`, OPTIONS preflight, JSON-parsing.
**Worker-port:** trivielt. Bruk `request.headers.get('Origin')` og `Response`.

### 2. Cloudflare Turnstile (lett, ~30 LOC)

POST til `challenges.cloudflare.com/turnstile/v0/siteverify` med `secret`,
`response`, `remoteip`.
**Worker-port:** trivielt. Samme API-kall fra Worker, ingen Python-spesifikt.

### 3. Halo PSA — ticket creation (middels, ~150 LOC)

Auth via OAuth2 client_credentials → `service.micronet.no/auth/token`,
deretter POST til `/api/Tickets` med `userlookup`, `tags`, `tickettype_id`.
**Worker-port:** middels. Krever caching av access_token (use `caches.default`
eller `KV` namespace for ticket-type-ID som er statisk).

### 4. Halo PSA — quote creation (komplekst, ~180 LOC)

`halo_find_or_create_customer` + `halo_item_line` + `create_halo_quote`.
Slår opp item-ID, beregner pris, oppretter quote i Halo PSA.
**Worker-port:** middels — én lang chain av API-kall. Bør være rett-frem.

### 5. Mailgun-utsendelse med HTML + PNG-vedlegg (komplekst, ~120 LOC)

Bygger MIME multipart-message med:
- HTML-mailbody (rikt design, embeddede grafikkelementer)
- PNG-vedlegg generert med PIL (skjold med karakter)
- `multipart_form()`-funksjon for å lage form-encoding

**Worker-port:** middels. `FormData` i Workers støtter binær attach via Blob.
Sending HTTPS-request til `api.eu.mailgun.net/v3/.../messages` er trivielt.
HTML-genereringen er bare string-templating.

### 6. PIL-skjold-PNG-rendering (HARD, ~250 LOC) ⚠️

Dette er knockerout. `intake-server.py` genererer en PNG av et "skjold"
med karakter A+/A/B/C/D/F basert på score, med fargegradient, drop-shadow,
custom-tegnete Bezier-kurver. PNG vedlegges hver e-post.

Worker-port-alternativer (rangert):

1. **Bruk SVG i e-posten istedet for PNG** (anbefalt)
   - Bytt PNG-attachment til inline SVG (Mailgun støtter inline SVG i HTML-body)
   - SVG er enkelt å generere som streng i JS (samme matte som det vi allerede
     bruker i `renderResults()` frontend!)
   - Mister Outlook-kompatibilitet (Outlook strippet SVG) — men SVG kan
     fallback'es til `<img src="data:image/svg+xml;base64,...">` for bredere
     støtte, eller en serverside-rendret PNG-fallback fra
     `og-image-generator`-tjeneste.
   - **Arbeid:** ~2 timer

2. **Bruk Cloudflare's @vercel/og eller satori-html i Worker**
   - Tar SVG-string, returnerer PNG
   - Krever å lære deres template-API
   - **Arbeid:** ~4 timer

3. **Eget rendering-service via Cloudflare Images**
   - Lag PNG manuelt, upload via Workers API til Images
   - Bruk Image-URL i mail
   - **Arbeid:** ~3 timer, men avhengig av Cloudflare Images-plan

4. **Behold Railway kun for PIL-rendering, alt annet i Worker**
   - Frontend POST-er til Worker
   - Worker delegerer PIL-rendering-step til Railway-mini-tjeneste
   - **Arbeid:** ~1 time, men beholder Railway-avhengighet
   - **Ikke anbefalt** — gir oss "verden av to broer"

**Anbefalt: alternativ 1** (SVG inline). Forenkler arkitekturen og lar oss
gjenbruke frontend-rendering-koden direkte.

### 7. Stats-logging (middels, ~80 LOC)

Logger til `/tmp/data1-stats.jsonl` med hashet IP, timestamp, kind, fields.
`/admin/stats` endpoint leser tilbake.

**Worker-port:** Workers har ikke filesystem. Alternativer:
- Cloudflare D1 (SQLite) — anbefalt for strukturert spørring
- KV — ikke ideelt for time-series
- Workers Analytics Engine — best for write-heavy stats
- Eksternt: Sentry, Datadog, PostHog

**Anbefalt:** Workers Analytics Engine — formålsbygget for dette,
gratis tier (10M write events/mnd).
**Arbeid:** ~2 timer å porte log_event-kallene.

### 8. Misc (lett, ~40 LOC)

- `_hash_ip` (SHA-256 med salt)
- `verify_turnstile` (omtalt over)
- `load_env` — Workers bruker `env.MY_SECRET`-objektet istedet
- Konstanter — bare bytte til JS

---

## Beslutninger som må tas før arbeid kan starte

1. **PNG-skjold: behold eller bytt til SVG?**
   - Anbefalt: SVG inline med PNG-fallback (alternativ 1 ovenfor)
   - Avgjør om Outlook-kompatibilitet er kritisk

2. **Stats-lagring: D1 eller Analytics Engine?**
   - Anbefalt: Analytics Engine
   - Avgjør om du trenger struktuerte queries (D1) eller bare aggregert telling (AE)

3. **Migrasjonsstrategi:**
   - **A. Big bang:** bytt INTAKE_ENDPOINT til Worker-URL én kveld, monitorer
   - **B. Parallell:** Worker mottar 10% av trafikken først, øk gradvis
   - Anbefalt: B med Cloudflare Workers' percentage routing

4. **Hva med Halo quote-kompleksitet?**
   - Hvis det viser seg vanskelig å replikere quote-logikken i JS,
     kan vi vurdere å beholde KUN den i intake-server.py og gjøre resten i Worker.
   - Krever løpende vurdering under porting.

---

## Implementeringsrekkefølge (når vi starter)

1. **Spike (1 time)**: lag minimal Worker som mottar POST og returnerer 200.
   Test deploy til workers.dev-URL.

2. **CORS + Turnstile (1 time)**: port-over disse to. Test end-to-end fra
   localhost-frontend.

3. **Halo ticket (2 timer)**: port OAuth + Tickets POST. Test med ekte data.

4. **SVG-skjold + Mailgun (2 timer)**: bytt PNG til SVG, send testmail.
   Verifiser visuelt i Gmail, Outlook, Apple Mail.

5. **Halo quote (2 timer)**: port quote-kjeden. Test med ekte data.

6. **Stats-logging via Analytics Engine (1 time)**: port `log_event`.

7. **Parallell-utrulling (2 dager observasjon)**: send 10% → 50% → 100% til
   Worker mens Railway fortsatt kjører som fallback.

8. **Sunset Railway**: Etter 1 uke uten Worker-feil, slett Railway-prosjektet
   og fjern Procfile/intake-server.py fra repo.

**Total:** 8–10 timers fokusert arbeid + 1 ukes observasjon.

---

## Risiko

| Risiko                                           | Sannsynlighet | Mitigering                                                |
|--------------------------------------------------|---------------|-----------------------------------------------------------|
| Mailgun støtter ikke SVG i Outlook              | Høy           | PNG-fallback via Cloudflare Images for Outlook-detektering|
| Halo OAuth-token utløper i lang-running Worker  | Lav           | Workers er stateless; token caches i `caches.default`     |
| Halo API-call-grenser overskrides ved spike     | Lav           | Workers har auto-retry med backoff. Cap req-rate per IP.  |
| Analytics Engine begrenset query-evne           | Middels       | Kombiner med D1 hvis admin-rapport krever JOIN-spørringer |
| PNG-skjold-rendering ser dårligere ut som SVG   | Middels       | Designgjennomgang før utrulling. PNG-fallback om kritisk. |

---

## Beslutning før start

Etter denne planen er klar, trenger vi at noen tar avgjørelser på:
1. PNG vs SVG (anbefaler SVG)
2. D1 vs Analytics Engine (anbefaler AE)
3. Migrasjonsstrategi (anbefaler parallell-utrulling)

Når disse er bekreftet, kan vi planlegge en konsentrert arbeidsperiode på
8–10 timer (fortrinnsvis én sammenhengende dag, eller 2 halvdager).
