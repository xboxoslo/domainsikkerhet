# Dashboard data-sync — GitHub Actions

Dashboardet på [data1.no/dashboard](https://data1.no/dashboard/) leser fire JSON-filer fra `/dashboard-data/`. Disse oppdateres automatisk av GitHub Actions-workflowen [`.github/workflows/dashboard-sync.yml`](../.github/workflows/dashboard-sync.yml), som kjører Python-script i `scripts/dashboard_*_sync.py`.

> **Hvorfor GitHub Actions og ikke n8n?** Hele dette repoet kjører allerede 6 workflows som committer data tilbake (`daily-content.yml` osv.). Å holde alt ett sted (i Git, versionskontrollert, med samme auth-mønster via `BOT_PAT`) er enklere enn å koble inn en separat n8n-instans med egne credentials, secrets-styring og webhook-deploy.

## Oversikt

| Sync | Script | Cron | Krever |
|---|---|---|---|
| **Email** | `dashboard_email_sync.py` | Daglig 06:30 UTC | Ingen (bruker eksisterende `_data/snapshots/`) |
| **Konkurrenter** | `dashboard_competitors_sync.py` | Daglig 06:30 UTC | Ingen (skraper offentlig `sitemap.xml`) |
| **SEO** | `dashboard_seo_sync.py` | Daglig 06:30 UTC | GSC OAuth refresh-token (engangs-oppsett, se under) |
| **AI-synlighet** | `dashboard_ai_sync.py` | Ukentlig mandag 07:00 UTC | LLM-API-nøkler (se under) |

Alle scriptene er **idempotente** — kan kjøres flere ganger uten skade, og hopper over jobben uten å feile hvis credentials mangler. Det betyr workflowen ikke krasjer før secrets er på plass.

## 1. Email-sync (klar)

Leser siste snapshot fra `_data/snapshots/<dato>.json` (generert av `daily_scan.py`) og:
- Live-skanner `data1.no` og `micronet.no` via DNS-over-HTTPS (de er ikke i tracking-listen på 158 norske bedrifter)
- Aggregerer policy-fordeling, ukentlige endringer (vs. snapshot 7 dager tilbake)
- Bygger 12-ukers tidslinje med `%p=reject`

**Trenger ingen ekstra konfig** — kjører nå.

## 2. Konkurrent-sync (delvis klar)

Henter `sitemap.xml` fra hver konkurrent og teller `<loc>`-noder:
- ✓ data1.no, mxtoolbox.com, easydmarc.com, powerdmarc.com, dmarcian.com, valimail.com
- ⚠️ sjekk.email, dmarcstatus.no — sitemap utilgjengelig, beholder eksisterende verdi

**Domain Rating + backlinks** krever Ahrefs/SEMrush. Per nå manuelt vedlikeholdt i `dashboard-data/competitors.json`. Hvis SEMrush MCP-tilkobling konfigureres, kan scriptet utvides til å hente disse automatisk.

## 3. SEO-sync (krever engangs-oppsett)

Bruker Google Search Console v1 API for å hente:
- Klikk + visninger siste 90 dager (tidslinje)
- Topp 50 søkeord siste 28 dager
- Topp 25 sider siste 28 dager
- Sammendrag (totale klikk, visninger, CTR, snittposisjon)

**Engangs-oppsett av OAuth:**

1. Gå til <https://console.cloud.google.com/apis/credentials>
2. Velg eksisterende prosjekt eller opprett nytt ("data1-dashboard")
3. **Enable APIs** → søk "Search Console API" → aktiver
4. **Create credentials** → OAuth client ID → "Desktop app"
5. Last ned JSON, noter `client_id` og `client_secret`
6. Få refresh-token én gang via:
   ```bash
   # Bytt CLIENT_ID til verdi fra steg 5:
   open "https://accounts.google.com/o/oauth2/v2/auth?client_id=CLIENT_ID&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/webmasters.readonly&access_type=offline&prompt=consent"
   ```
   Logg inn som eier av data1.no Search Console-property, kopier `code`-verdien fra URL.
   ```bash
   # Bytt CLIENT_ID, CLIENT_SECRET, CODE:
   curl -X POST https://oauth2.googleapis.com/token \
     -d "client_id=CLIENT_ID&client_secret=CLIENT_SECRET&code=CODE&grant_type=authorization_code&redirect_uri=urn:ietf:wg:oauth:2.0:oob"
   ```
   Svaret inneholder `refresh_token` — kopier den.
7. Sett som GitHub Secrets:
   ```bash
   gh secret set GSC_CLIENT_ID --body "<client-id>"
   gh secret set GSC_CLIENT_SECRET --body "<client-secret>"
   gh secret set GSC_REFRESH_TOKEN --body "<refresh-token>"
   ```

Etter dette kjører SEO-sync automatisk daglig.

## 4. AI-synlighet-sync (krever API-nøkler)

Sender 20 norske prompts om DMARC/SPF/e-postsikkerhet mot 4 LLM-er og teller treff på `data1.no`, `Micronet`, samt konkurrenter (sjekk.email, dmarcstatus.no, mxtoolbox, easydmarc, powerdmarc, dmarcian).

**Engangs-oppsett av nøkler:**

```bash
gh secret set ANTHROPIC_API_KEY --body "sk-ant-..."   # https://console.anthropic.com/settings/keys
gh secret set OPENAI_API_KEY --body "sk-..."          # https://platform.openai.com/api-keys
gh secret set PERPLEXITY_API_KEY --body "pplx-..."    # https://www.perplexity.ai/settings/api
gh secret set GEMINI_API_KEY --body "AI..."           # https://aistudio.google.com/apikey
```

**Estimert kost per kjøring** (20 prompts × ~500 tokens utdata):
- Claude Sonnet 4.7: ~$0.20
- GPT-4o: ~$0.15
- Perplexity sonar: ~$0.10
- Gemini: gratis-tier dekker
- **Totalt ~$0.45/uke = ~$24/år**

Hvis bare *noen* nøkler er satt, kjøres kun de modellene. Manglende modeller telles som "ikke nevnt" i resultatene.

## Manuell trigging

```bash
# Alt:
gh workflow run dashboard-sync.yml

# Bare AI-sync:
gh workflow run dashboard-sync.yml -f jobs=ai
```

Eller via GitHub UI: Actions → Dashboard data sync → Run workflow.

## Feilsøking

- **Workflow logger "Ingen endringer"** — sync kjørte men data var identisk med forrige. Vanlig hvis ingen nye DMARC-endringer eller GSC-data.
- **Sync feiler med "401 Unauthorized"** — refresh-token utløpt eller tilbakekalt. Generer ny via OAuth-flyten over.
- **Egne domener viser F-grade** — DNS-cache. Vent 1 time, kjør på nytt.
- **`data1.no` viser score 0 i email-tab** — sjekk at SPF/DMARC faktisk er publisert. Sjekk-verktøyet til data1.no kan kjøres mot eget domene.

## Cloudflare Access (auth — manuell)

Dashboardet skal beskyttes av Cloudflare Access så bare innloggede brukere ser det. Settes opp manuelt i Cloudflare-dashbordet:

1. Cloudflare Dashboard → `data1.no` → **Zero Trust** → Access → Applications → **Add an application** → "Self-hosted"
2. **Application name:** `data1.no Dashboard`
3. **Session duration:** `24 hours`
4. **Application domain:** Legg til to oppføringer:
   - `data1.no` + path `/dashboard*`
   - `data1.no` + path `/dashboard-data*`
5. **Identity providers:** Velg One-time PIN (e-post OTP) som minimum. Legg til Google Workspace IdP om tilgjengelig.
6. **Policy → Action: Allow → Include: Emails:**
   - `terje@micronet.no`
   - (legg til andre etter behov)
7. Save.

Etter dette returnerer `curl -I https://data1.no/dashboard/` en 302-redirect til `<team>.cloudflareaccess.com/cdn-cgi/access/login/...`.

Programmatisk oppsett via Cloudflare API krever en token med scopes `Account → Access: Apps and Policies → Edit`. Eksisterende token i Key Vault (`Cloudflare-Api-Token`) mangler disse scopes per 18. mai 2026 — regenerer hvis automatisering er ønskelig.
