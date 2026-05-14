# Intake-arkitektur for data1.no

Når en bruker klikker "Send rapport på e-post" sender frontend en POST mot
`https://intake.data1.no/intake`. Bak denne URL-en kjører `intake-server.py`
på Railway.

## Frontend → Backend

```
data1.no (Cloudflare Pages, statisk HTML)
   └─► POST https://intake.data1.no/intake (JSON-payload)
         │
         └─► CNAME → web-production-1681.up.railway.app
                       │
                       └─► intake-server.py (Python HTTPServer)
                             ├─► Cloudflare Turnstile-verifisering
                             ├─► Halo PSA — opprett ticket + (eventuelt) quote
                             └─► Mailgun — send PNG-shield-rapport som vedlegg
```

## DNS-oppsett (kreves)

CNAME-record i Cloudflare:
| Type  | Name   | Target                                  | Proxy |
|-------|--------|-----------------------------------------|-------|
| CNAME | intake | web-production-1681.up.railway.app      | Av    |

Custom domain i Railway-dashbordet:
- Settings → Networking → "Custom Domain" → `intake.data1.no`
- Railway provisioner Let's Encrypt-sertifikat automatisk

## Hvorfor custom domain

- **Vendor-lock-in unngås:** Hvis intake-server.py flyttes vekk fra Railway (f.eks. til
  Fly.io, en VPS, eller Cloudflare Worker med feature-parity), endrer du bare CNAME —
  ingen frontend-endring trengs.
- **Bedre branding:** `intake.data1.no` ser proff ut, `web-production-1681.up.railway.app`
  ser ut som en debug-URL.
- **CORS er upåvirket:** server'n sjekker `Origin`-header (data1.no), ikke target-host.

## Historisk: intake-worker.js (Cloudflare Worker)

Tidligere fantes `intake-worker.js` — en Cloudflare Worker som var en forenklet
JS-variant av intake-server.py (Halo ticket + Mailgun-mail, men uten Halo
quote og uten PIL-rendret PNG-vedlegg). Worker'en ble aldri deployet til prod
og ble fjernet i denne PR-en. Hvis migrasjon fra Railway til Workers blir
aktuell senere, må PIL-shield-rendering portes (vurder Cloudflare Images,
@vercel/og, eller bare SVG i e-posten istedenfor PNG).
