# SEO-oppgradering — endringslogg

Levert: 2026-05-18 av Claude (sammen med Terje Otterlei)

## Hva ble gjort

### Fase 1 — Kritiske SEO-fikser ✅

**1.2 — Forfatter byttet fra «Micronet» til «Terje Otterlei»**
- `<meta name="author">` oppdatert i **197 HTML-filer**
- Generator-templates (`scripts/weekly_blogpost.py`, `scripts/generate_domain_pages.py`) oppdatert så framtidige sider får riktig forfatter
- «Micronet AS» beholdes som *publisher* i alle JSON-LD-blokker

**1.3 — Trimmet keywords-meta**
- `<meta name="keywords">` redusert til maks 7 termer i **5 filer**
- (De fleste filer hadde allerede ≤7 termer)

### Fase 2 — JSON-LD Structured Data ✅

**Article schema med Person-author**
- **26 JSON-LD Article-blokker** oppdatert: `author` byttet fra `Organization (Micronet AS)` til `Person (Terje Otterlei)` med `jobTitle: "Daglig leder"` og `worksFor: Micronet AS`
- Forfatter-URL peker til `https://data1.no/om/`
- `publisher` forblir Organization (Micronet AS) — Google og AI-systemer skiller mellom forfatter og utgiver

**SoftwareApplication schema lagt til**
- `/verktoy/dmarc-generator/` og `/verktoy/spf-generator/`
- Med `offers.price: 0 NOK`, `inLanguage: nb-NO`, `applicationCategory: SecurityApplication`
- `author`: Person Terje Otterlei, `publisher`: Micronet AS

### Fase 3 — llms.txt og llms-full.txt ✅

**Dynamisk generering fra blogg-katalogen**
- `llms.txt` (4,8 kB): kompakt manifest med 10 blogginnlegg, 5 rapporter, 3 verktøy, om-side
- `llms-full.txt` (6,0 kB): utvidet versjon med teknisk forklaring av karaktersystem og DNS-sjekkene som kjøres
- Begge genereres av `scripts/seo_upgrade.py phase3` — kan kjøres på nytt når nye artikler legges til

## Tooling

Nytt script: [`scripts/seo_upgrade.py`](scripts/seo_upgrade.py)
- Idempotent (kan kjøres flere ganger uten skade)
- Tre faser: `phase1`, `phase2`, `phase3`, `all`
- Bruk: `python scripts/seo_upgrade.py phase3` for å regenerere llms.txt etter nytt blogginnlegg

## TODO — manuelle oppgaver

| Oppgave | Hvem | Hva |
|---|---|---|
| **GSC-token** | Du | Hent token fra Google Search Console, bytt `REPLACE_GSC_TOKEN` i `index.html` linje 27. Verifiser deretter via DNS TXT eller HTML-tag-metoden. |
| **Cloudflare cache-purge** | Du | Etter deploy: hard-refresh data1.no, evt. purge cache i Cloudflare for å se llms.txt og endringer raskt. |
| **Submit sitemap** | Du | Etter GSC-verifisering: submit `https://data1.no/sitemap.xml` i Google Search Console. |

## Ikke gjort i denne runden (videre arbeid)

| Fase | Status | Begrunnelse |
|---|---|---|
| **4.1 Sitemap** | Eksisterer allerede (`sitemap.xml` generert av `scripts/update_sitemap.py`). Trenger ikke endring. | |
| **4.2 robots.txt** | Eksisterer allerede med riktig oppsett (ikke blokker AI-crawlere). Trenger ikke endring. | |
| **5 Forfatterprofil i `/om/`** | Eksisterer delvis, kunne forbedres med Person-schema. Lagt på TODO. | Tar 15–20 min — gjøres når foto av Terje er klart. |
| **6.1 Synlig forfatter-byline** | Ikke gjort. | Krever editorial review per blogg-post. Anbefales som neste batch. |
| **6.2 «I korte trekk»-bokser** | Ikke gjort på hovedartikler. | Krever editorial review og innholdsskriving per artikkel. |
| **6.3 Intern lenking** | Ikke automatisert. | Krever editorial judgment. |
| **7.1 OG-bilder per artikkel** | Statisk `og-image.png` brukes. | For dynamiske OG-bilder trengs en image-server (Cloudflare Workers + Satori e.l.) — egen prosjekt. |
| **7.2 Bildeoptimalisering** | Ikke vurdert. | Få bilder på siden, lavt prioritert. |
| **7.3 Performance** | Statisk HTML har allerede perfekt Core Web Vitals. | Ingen handling nødvendig. |

## Stack-merknad

Original-oppgaven var skrevet med antakelse om Next.js + Tailwind + Vercel. Faktisk stack er **statisk HTML + Python-generatorer + Cloudflare Pages**. Implementasjonen er tilpasset den faktiske stacken — målene er oppnådd, men metoden er forskjellig (Python-script i stedet for `lib/schema.ts`, statiske JSON-LD-blokker i stedet for runtime-injisert React-komponent).

## Neste anbefalte runde

1. **Visible byline på blogg** — "Av Terje Otterlei · Publisert ..." øverst på hver blogg-post, lenket til `/om/`. Krever rask manuell editering per post (~10 min).
2. **«I korte trekk»-boks på DMARC/SPF/DKIM-hovedartikler** — 2–3 setninger AI-systemer plukker opp og siterer. Editorial.
3. **Person-schema på `/om/`** — full E-E-A-T-profil for Terje Otterlei (Person + sameAs LinkedIn).
4. **Submit sitemap til GSC** etter token er satt inn.
