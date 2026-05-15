# Konkurrentanalyse — DMARC-aktører i Norge (mai 2026)

## Sammendrag

data1.no har ingen direkte konkurrenter i den norske språkmarked-nisjen. Globale aktører dominerer internasjonalt men ingen oversetter til norsk eller tilbyr norsk-spesifikk data. De norske spillerne som finnes er konsulent-/MSP-baserte, ikke SaaS-baserte verktøy.

## Marked-segmentering

| Segment | Aktører | Hvor er de? |
|---|---|---|
| Globale SaaS-verktøy (engelsk) | mxtoolbox, dmarcian, EasyDMARC, Valimail | Internasjonalt, EN |
| Norske MSP-er som tilbyr DMARC | Micronet, Microsoft 365-partnere | Konsulent + drift, ikke verktøy |
| Norske spesialiserte sikkerhetsfirmaer | Mnemonic, Watchcom, KPMG Cyber | Enterprise-konsulent |
| Norske myndighet | NSM, NorSIS, Datatilsynet | Anbefalere, ikke leverandører |
| **data1.no** | — | **Eneste norske SaaS-verktøy** |

## Detaljanalyse av 6 antatte konkurrenter

### 1. mxtoolbox.com

**Hva de er:** Verdens største SaaS for DNS / e-post-sjekk. Diagnostiserer SPF, DMARC, DKIM, MX, blacklist osv.

**Modell:** Freemium. Free tier limited til ~10 sjekker/dag. Pro $129+/mnd, Enterprise $400+/mnd.

**Styrker:**
- Massiv database, 25+ år erfaring
- Mest brukt blant amerikanske IT-folk
- Robust API

**Svakheter (mot data1.no):**
- Kun engelsk
- Ingen Norge-spesifikk data
- Ingen kontekst om norske banker, kommuner, NSM-anbefalinger
- Krever registrering for full rapport
- Sporing/cookies

**Konkurrerer på:** Power-users som vet hva mxtoolbox er. Ikke menigmann/IT-sjefer som søker "DMARC norge".

---

### 2. dmarcian.com

**Hva de er:** DMARC-spesialist, opprinnelig grunnlagt av folk fra DMARC-protokoll-spesifikasjonen. Tilbyr DMARC-overvåking + verktøy.

**Modell:** Free for små org. Premium $1500+/år. Enterprise mye mer.

**Styrker:**
- Dyp DMARC-ekspertise
- Brukt av offentlig sektor i Europa
- DMARC-aggregering rapporter er god

**Svakheter:**
- Kun engelsk
- Pris-modell skaler raskt for store oppsett
- Krever konto for å se rapporter
- Mer komplekst UI enn data1.no

**Konkurrerer på:** Store norske bedrifter som allerede har DMARC-prosjekter. Sjeldent vurderes for SMB.

---

### 3. easydmarc.com

**Hva de er:** Yngre konkurrent, fokus på enkelhet og pris. Polert UI.

**Modell:** Free for 1 domene. Pro $39/mnd per domene. Enterprise tilpasset.

**Styrker:**
- Best i klassen på UX
- Aggressiv pris-modell
- AI-genererte tiltaksforslag

**Svakheter:**
- Kun engelsk
- Ingen Norge-data
- Yngre selskap, mindre etablert

**Konkurrerer på:** SMB internasjonalt. Lite penetrasjon i Norge.

---

### 4. valimail.com

**Hva de er:** Enterprise DMARC-løsning. Mer compliance/governance-fokus enn verktøy.

**Modell:** Enterprise-only, $25 000+/år.

**Styrker:**
- Brand authority — selger til Fortune 500
- BIMI-spesialist
- Kompletteler DMARC + BIMI + brand-impersonation

**Svakheter:**
- Bare for store enterprise
- Ikke relevant for SMB-/kommunesegment
- Kun engelsk

**Konkurrerer på:** Norges aller største (DnB, Equinor) som allerede har Valimail eller lignende. Resten av markedet — nei.

---

### 5. Micronet AS (din egen)

**Hva dere er:** Norsk IT-leverandør / Microsoft 365-konsulent + drift. Driver data1.no.

**Modell:** Etablering 1 990 kr + 295 kr/mnd løpende.

**Styrker:**
- Norsk, lokalt, kjøpsmessig enkelt
- Pris er konkurrent (under SaaS-engelske priser i NOK)
- 20+ års Microsoft 365-erfaring
- HaloPSA-distributør

**Posisjon:** Komplementær til data1.no — verktøyet er gratis discovery-engine, Micronet selger oppsett/drift.

---

### 6. Norske MSP-er generelt (Crayon, ATEA, Conscia, Sopra Steria, lokale partnere)

**Hva de er:** Store norske IT-leverandører som tilbyr DMARC som del av sikkerhetspakker.

**Modell:** Konsulentprosjekt 50-200 000 kr + drift.

**Styrker:**
- Etablert kunderelasjon
- Pakket sammen med M365-lisenser

**Svakheter:**
- Dyrt for SMB
- DMARC er ofte ettertanke, ikke spesialitet
- Ingen offentlig diagnose-verktøy

**Konkurrerer på:** Existing kundeforhold. Sjeldent valgt for ren DMARC-tjeneste alene.

---

## Markeds-mulighet for data1.no

### Hvor du eier (eller kan eie) markedet

1. **Norsk språk-SEO** for DMARC/SPF/DKIM-relaterte søk — ingen reell konkurranse
2. **Norske domener i datasettet** — Altinn, NRK, kommuner — nisje ingen andre kan kopiere uten å bygge skannings-infrastruktur
3. **Gratis selv-betjent diagnose** — globale konkurrenter krever registrering
4. **Trust + lokal kontekst** — Norges egne tall, ikke amerikanske referanser

### Hvor du IKKE bør konkurrere

1. **Enterprise compliance** (Valimail-segmentet) — for stor / for komplisert investering
2. **DMARC aggregat-rapport-aggregering** (dmarcian/easydmarc) — krever XML-parsing-infra over tid + e-postservere
3. **Generelle MX-tools** (mxtoolbox-segmentet) — for stort scope, ikke spesialitet

### Strategisk anbefaling

**Doble ned på:**
- Norsk innhold (du har 8 blogger, 158 sjekk-sider, 10 feil-sider — fortsett)
- Live-data fra norske domener (du er den eneste som har dette)
- Forfatter-autoritet (Terje Otterlei + Micronet)
- Backlinks fra norske kilder (Digi, Kode24, NRKbeta, Wikipedia)

**Ikke kast bort tid på:**
- Bygge full DMARC-aggregat-tjeneste (dmarcian gjør det allerede bedre)
- Ekspandere utenfor Norge i 2026 (du eier ikke segmentet enda)
- Konkurrere på pris med globale freemium

**Realistisk markedsstørrelse i Norge:**
- Norske bedrifter med eget domene som søker DMARC-hjelp: ~5 000-15 000
- Faktisk betalende konsulent-segment (Micronet-modell): 200-1000 kunder
- Trafikk-mål: 10 000-50 000 organiske besøk/mnd om 12 mnd
- Lead-mål: 50-200 kvalifiserte leads/mnd via Micronet

## Konklusjon

data1.no har ingen direkte konkurrent i sin nisje (norsk-språk, .no-fokus, gratis, ingen registrering). De fleste norske bedrifter googler "DMARC" og lander på engelske sites. Når du etablerer SEO-autoritet på norske termer, eier du discovery-funnel-en for hele segmentet.

Micronet selger oppfølgingen — det er forretningsmodellen, ikke verktøyet i seg selv.
