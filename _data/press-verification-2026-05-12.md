# Pressemelding-verifikasjon — 2026-05-12

Hver F- og D-grade-claim verifisert mot live DNS via Cloudflare DoH.

## Status-koder

- ✅ **VERIFIED** — Trygt å nevne. MX-records finnes, DMARC-mangel bekreftet live.
- ⚠️ **RECHECK** — Snapshot stemmer ikke med live DNS. Sjekk manuelt før bruk.
- ❌ **SKIP** — Ikke trygt å bruke i press. Enten ingen e-post-trafikk eller alternativt hoveddomene.

## ✅ VERIFIED (42)

| Domene | Karakter | MX | DMARC-policy live | Kommentar |
|---|---|---|---|---|
| `sparebanken-vest.no` | F | fangorn.primaerdata.no | p=none | MX: fangorn.primaerdata.no | Real e-post-domene + DMARC-mangel bekreftet live. |
| `sparebanken-sor.no` | F | mail15.edb.com | p=none | MX: mail15.edb.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `tryg.no` | D | dk.mx1.mailanyone.net | p=none | MX: dk.mx1.mailanyone.net | Real e-post-domene + DMARC-mangel bekreftet live. |
| `codan.no` | D | codan-no.mail.protection.outlook.com | _mangler_ | MX: codan-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `knif.no` | D | knif-no.mail.protection.outlook.com | p=none | MX: knif-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `get.no` | D | mail.cm.telia.net | p=none | MX: mail.cm.telia.net | Real e-post-domene + DMARC-mangel bekreftet live. |
| `altibox.no` | D | altibox-no.mail.protection.outlook.com | p=reject | MX: altibox-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `altinn.no` | F | altinn-no.mail.protection.outlook.com | p=none | MX: altinn-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `forsvaret.no` | D | forsvaret-no.mail.protection.outlook.com | p=none | MX: forsvaret-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `nrk.no` | D | smtp.google.com | p=none | MX: smtp.google.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `hydro.no` | F | smtp2.edelkey.net | _mangler_ | MX: smtp2.edelkey.net | Real e-post-domene + DMARC-mangel bekreftet live. |
| `statkraft.no` | F | statkraft-no.mail.protection.outlook.com | p=none | MX: statkraft-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `dagbladet.no` | D | dagbladet-no.mail.protection.outlook.com | p=none | MX: dagbladet-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `dn.no` | D | Dn-no.mail.protection.outlook.com | p=none | MX: Dn-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `itavisen.no` | D | aspmx.l.google.com | p=none | MX: aspmx.l.google.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `digi.no` | F | ASPMX.L.GOOGLE.COM | p=none | MX: ASPMX.L.GOOGLE.COM | Real e-post-domene + DMARC-mangel bekreftet live. |
| `tu.no` | D | ASPMX.L.GOOGLE.COM | p=none | MX: ASPMX.L.GOOGLE.COM | Real e-post-domene + DMARC-mangel bekreftet live. |
| `clas-ohlson.no` | F | mail.h-email.net | p=none | MX: mail.h-email.net | Real e-post-domene + DMARC-mangel bekreftet live. |
| `zalando.no` | D | aspmx.l.google.com | p=none | MX: aspmx.l.google.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `cubus.com` | D | eu.mx1.mailanyone.net | p=quarantine | MX: eu.mx1.mailanyone.net | Real e-post-domene + DMARC-mangel bekreftet live. |
| `sas.no` | D | mx1.hc63-0.eu.iphmx.com | p=quarantine | MX: mx1.hc63-0.eu.iphmx.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `norwegian.no` | D | norwegian-no.mail.protection.outlook.com | p=none | MX: norwegian-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `bring.no` | D | pos-mailgw01.posten.no | p=none | MX: pos-mailgw01.posten.no | Real e-post-domene + DMARC-mangel bekreftet live. |
| `schenker.no` | F | smtp.domainnetwork.net | _mangler_ | MX: smtp.domainnetwork.net | Real e-post-domene + DMARC-mangel bekreftet live. |
| `bilforsikring.no` | F | ASPMX.L.GOOGLE.COM | p=none | MX: ASPMX.L.GOOGLE.COM | Real e-post-domene + DMARC-mangel bekreftet live. |
| `visma.com` | D | aspmx.l.google.com | p=none | MX: aspmx.l.google.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `hjemla.no` | F | hjemla-no.mail.protection.outlook.com | p=none | MX: hjemla-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `funcom.com` | D | mailrelay-osl.funcom.com | p=none | MX: mailrelay-osl.funcom.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `uio.no` | F | smtp.uio.no | p=none | MX: smtp.uio.no | Real e-post-domene + DMARC-mangel bekreftet live. |
| `ntnu.no` | F | mx.ntnu.no | p=none | MX: mx.ntnu.no | Real e-post-domene + DMARC-mangel bekreftet live. |
| `nmbu.no` | D | nmbu-no.mail.protection.outlook.com | p=none | MX: nmbu-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `hvl.no` | D | hvl-no.mail.protection.outlook.com | p=none | MX: hvl-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `khio.no` | D | khio-no.mail.protection.outlook.com | p=none | MX: khio-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `bi.no` | D | bi-no.mail.protection.outlook.com | p=quarantine | MX: bi-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `ks.no` | D | ks-no.mail.protection.outlook.com | p=none | MX: ks-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `oslo.kommune.no` | D | oslokommune.mail.protection.outlook.com | p=none | MX: oslokommune.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `baerum.kommune.no` | D | baerum-kommune-no.mail.protection.outlook.com | p=none | MX: baerum-kommune-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `tromso.kommune.no` | D | tromso-kommune-no.mail.protection.outlook.com | p=none | MX: tromso-kommune-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `sopra-steria.no` | F | relay1.netnames.net | _mangler_ | MX: relay1.netnames.net | Real e-post-domene + DMARC-mangel bekreftet live. |
| `atea.no` | D | atea.in.tmes.trendmicro.eu | p=none | MX: atea.in.tmes.trendmicro.eu | Real e-post-domene + DMARC-mangel bekreftet live. |
| `itera.no` | D | itera-no.mail.protection.outlook.com | finnes | MX: itera-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |
| `unicef.no` | D | unicef-no.mail.protection.outlook.com | p=none | MX: unicef-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live. |

## ⚠️ RECHECK (0)

_Ingen._

## ❌ SKIP (8)

| Domene | Karakter | MX | DMARC-policy live | Kommentar |
|---|---|---|---|---|
| `sparebanken-ost.no` | F | _ingen_ | _mangler_ | Bruker sannsynligvis alternativt domene: ost.com (mx: ost-com.mail.protection.outlook.com). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare. |
| `equinor.no` | F | _ingen_ | _mangler_ | Bruker sannsynligvis alternativt domene: equinor.com (mx: equinor-com.mail.protection.outlook.com). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare. |
| `yara.no` | F | _ingen_ | _mangler_ | Bruker sannsynligvis alternativt domene: yara.com (mx: yara-com.mail.protection.outlook.com). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare. |
| `aker-solutions.no` | F | _ingen_ | _mangler_ | Bruker sannsynligvis alternativt domene: solutions.com (mx: 9bc5cba717f8fd66cf2192c9daad1cd2b8621ed6), akersolutions.com (mx: akersolutions-com.mail.protection.outlook.com). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare. |
| `nyfosse.no` | F | _ingen_ | _mangler_ | Ingen MX-records — domenet sender/mottar ikke e-post. F-grade er teknisk korrekt men ikke et reelt phishing-problem. |
| `faedrelandsvennen.no` | F | _ingen_ | _mangler_ | Ingen MX-records — domenet sender/mottar ikke e-post. F-grade er teknisk korrekt men ikke et reelt phishing-problem. |
| `scandichotels.no` | F | _ingen_ | _mangler_ | Bruker sannsynligvis alternativt domene: scandichotels.com (mx: scandichotels-com.mail.protection.outlook.com). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare. |
| `nakk.no` | F | _ingen_ | _mangler_ | Bruker sannsynligvis alternativt domene: nakk.com (mx: localhost). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare. |

## Råverifikasjons-data

```json
[
  {
    "domain": "sparebanken-vest.no",
    "grade": "F",
    "score": 8,
    "has_mx": true,
    "mx_targets": [
      "fangorn.primaerdata.no",
      "shelob.primaerdata.no"
    ],
    "dmarc_live": "v=DMARC1; p=none",
    "spf_live": null,
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: fangorn.primaerdata.no | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "sparebanken-sor.no",
    "grade": "F",
    "score": 8,
    "has_mx": true,
    "mx_targets": [
      "mail15.edb.com",
      "mail16.edb.com"
    ],
    "dmarc_live": "v=DMARC1; p=none",
    "spf_live": null,
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: mail15.edb.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "sparebanken-ost.no",
    "grade": "F",
    "score": 0,
    "has_mx": false,
    "mx_targets": [],
    "dmarc_live": null,
    "spf_live": null,
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [
      [
        "ost.com",
        "ost-com.mail.protection.outlook.com"
      ]
    ],
    "verdict": "SKIP",
    "reason": "Bruker sannsynligvis alternativt domene: ost.com (mx: ost-com.mail.protection.outlook.com). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare."
  },
  {
    "domain": "tryg.no",
    "grade": "D",
    "score": 48,
    "has_mx": true,
    "mx_targets": [
      "dk.mx1.mailanyone.net",
      "dk.mx2.mx25.net"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:0b49eff1c887658@rep.dmarcanalyzer.com; ruf=mailto:0b49eff1c887658@for.d…",
    "spf_live": "v=spf1 include:spf.mailanyone.net include:spf.protection.outlook.com include:_spf.qualtrics.com incl…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: dk.mx1.mailanyone.net | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "codan.no",
    "grade": "D",
    "score": 45,
    "has_mx": true,
    "mx_targets": [
      "codan-no.mail.protection.outlook.com"
    ],
    "dmarc_live": null,
    "spf_live": "v=spf1 include:spf.protection.outlook.com a:spf.mas.t-systems-service.com ip4:62.154.183.80/28 ip4:8…",
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: codan-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "knif.no",
    "grade": "D",
    "score": 48,
    "has_mx": true,
    "mx_targets": [
      "knif-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; sp=none; rua=mailto:djm5ys1dmc@rua.powerdmarc.com; ruf=mailto:djm5ys1dmc@ruf.power…",
    "spf_live": "v=spf1 include:spf.protection.outlook.com include:aspnett.net include:email.mojosender.com include:_…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: knif-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "get.no",
    "grade": "D",
    "score": 48,
    "has_mx": true,
    "mx_targets": [
      "mail.cm.telia.net"
    ],
    "dmarc_live": "v=DMARC1;p=none;sp=none;fo=1;rua=mailto:cv1zdpyr@ag.dmarcian-eu.com;ruf=mailto:cv1zdpyr@fr.dmarcian-…",
    "spf_live": "v=spf1 mx ip4:84.208.20.34/32 ip4:193.208.151.32/27 ip4:80.74.207.112/28 include:spf.protection.outl…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: mail.cm.telia.net | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "altibox.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "altibox-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=reject; aspf=s; adkim=s; pct=70; rua=mailto:wlur5gvy@ag.eu.dmarcadvisor.com;",
    "spf_live": "v=spf1 ip4:62.192.28.128/26 ip4:212.203.106.0/24 ip4:195.140.184.0/22 ip4:91.192.40.0/22 ip4:79.161.…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "reject",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: altibox-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "altinn.no",
    "grade": "F",
    "score": 33,
    "has_mx": true,
    "mx_targets": [
      "altinn-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none",
    "spf_live": "v=spf1 a:ai-p-s1-ext.ai.basefarm.net ip4:195.43.63.191/32 ip4:195.43.63.192/32 ip4:51.13.102.144 inc…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: altinn-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "forsvaret.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "forsvaret-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:dmarc_agg@vali.email",
    "spf_live": "v=spf1 ip4:169.51.78.16/28 ip4:169.51.91.224/27 a include:spf.protection.outlook.com include:_spf.sn…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: forsvaret-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "nrk.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "smtp.google.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; pct=100; rua=mailto:dmarc-reports@nrk.no; ruf=mailto:dmarc-reports@nrk.no; fo=1",
    "spf_live": "v=spf1 mx a ip4:160.67.135.178 ip4:160.67.166.179 ip4:77.94.235.18 ip4:23.253.183.25 ip4:77.94.238.1…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: smtp.google.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "equinor.no",
    "grade": "F",
    "score": 0,
    "has_mx": false,
    "mx_targets": [],
    "dmarc_live": null,
    "spf_live": null,
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [
      [
        "equinor.com",
        "equinor-com.mail.protection.outlook.com"
      ]
    ],
    "verdict": "SKIP",
    "reason": "Bruker sannsynligvis alternativt domene: equinor.com (mx: equinor-com.mail.protection.outlook.com). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare."
  },
  {
    "domain": "hydro.no",
    "grade": "F",
    "score": 0,
    "has_mx": true,
    "mx_targets": [
      "smtp2.edelkey.net",
      "smtp1.edelkey.net"
    ],
    "dmarc_live": null,
    "spf_live": null,
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: smtp2.edelkey.net | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "statkraft.no",
    "grade": "F",
    "score": 33,
    "has_mx": true,
    "mx_targets": [
      "statkraft-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:wgy3ft58@ag.eu.dmarcian.com; ruf=mailto:wgy3ft58@fr.eu.dmarcian.com;",
    "spf_live": "v=spf1 mx include:_spf-a.statkraft.com include:_spf-b.statkraft.com include:_spf-c.statkraft.com inc…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: statkraft-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "yara.no",
    "grade": "F",
    "score": 0,
    "has_mx": false,
    "mx_targets": [],
    "dmarc_live": null,
    "spf_live": null,
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [
      [
        "yara.com",
        "yara-com.mail.protection.outlook.com"
      ]
    ],
    "verdict": "SKIP",
    "reason": "Bruker sannsynligvis alternativt domene: yara.com (mx: yara-com.mail.protection.outlook.com). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare."
  },
  {
    "domain": "aker-solutions.no",
    "grade": "F",
    "score": 0,
    "has_mx": false,
    "mx_targets": [],
    "dmarc_live": null,
    "spf_live": null,
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [
      [
        "solutions.com",
        "9bc5cba717f8fd66cf2192c9daad1cd2b8621ed6"
      ],
      [
        "akersolutions.com",
        "akersolutions-com.mail.protection.outlook.com"
      ]
    ],
    "verdict": "SKIP",
    "reason": "Bruker sannsynligvis alternativt domene: solutions.com (mx: 9bc5cba717f8fd66cf2192c9daad1cd2b8621ed6), akersolutions.com (mx: akersolutions-com.mail.protection.outlook.com). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare."
  },
  {
    "domain": "nyfosse.no",
    "grade": "F",
    "score": 0,
    "has_mx": false,
    "mx_targets": [],
    "dmarc_live": null,
    "spf_live": null,
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [],
    "verdict": "SKIP",
    "reason": "Ingen MX-records — domenet sender/mottar ikke e-post. F-grade er teknisk korrekt men ikke et reelt phishing-problem."
  },
  {
    "domain": "dagbladet.no",
    "grade": "D",
    "score": 38,
    "has_mx": true,
    "mx_targets": [
      "dagbladet-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:65250275ea9c3@dmarc.centerasecurity.com;",
    "spf_live": "v=spf1 include:servers.mcsv.net include:spf.protection.outlook.com include:customers.clickdimensions…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: dagbladet-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "dn.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "Dn-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:c52cb600dc9c789@rep.dmarcanalyzer.com; ruf=mailto:c52cb600dc9c789@for.d…",
    "spf_live": "v=spf1 ip4:137.221.30.0/28 ip4:137.221.26.0/28 ip4:188.95.246.87 ip4:185.175.96.15 ip4:185.47.40.123…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: Dn-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "itavisen.no",
    "grade": "D",
    "score": 48,
    "has_mx": true,
    "mx_targets": [
      "aspmx.l.google.com",
      "alt3.aspmx.l.google.com"
    ],
    "dmarc_live": "v=DMARC1; p=none;",
    "spf_live": "v=spf1 include:spf.protection.outlook.com include:_spf.google.com ~all",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: aspmx.l.google.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "digi.no",
    "grade": "F",
    "score": 33,
    "has_mx": true,
    "mx_targets": [
      "ASPMX.L.GOOGLE.COM",
      "ALT1.ASPMX.L.GOOGLE.COM"
    ],
    "dmarc_live": "v=DMARC1; p=none; pct=100; rua=mailto:re+vroa7kob7oa@dmarc.postmarkapp.com; sp=none; aspf=r;",
    "spf_live": "v=spf1 a ip4:176.58.114.74 include:_spf.tu.c.bitbit.net include:_spf.google.com include:3307297.spf0…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: ASPMX.L.GOOGLE.COM | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "tu.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "ASPMX.L.GOOGLE.COM",
      "ALT1.ASPMX.L.GOOGLE.COM"
    ],
    "dmarc_live": "v=DMARC1; p=none; pct=100; rua=mailto:re+mtez1oafpfh@dmarc.postmarkapp.com; sp=none; aspf=r;",
    "spf_live": "v=spf1 a ip4:176.58.114.74 include:_spf.tu.c.bitbit.net include:_spf.google.com include:3307297.spf0…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: ASPMX.L.GOOGLE.COM | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "faedrelandsvennen.no",
    "grade": "F",
    "score": 0,
    "has_mx": false,
    "mx_targets": [],
    "dmarc_live": null,
    "spf_live": null,
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [],
    "verdict": "SKIP",
    "reason": "Ingen MX-records — domenet sender/mottar ikke e-post. F-grade er teknisk korrekt men ikke et reelt phishing-problem."
  },
  {
    "domain": "clas-ohlson.no",
    "grade": "F",
    "score": 33,
    "has_mx": true,
    "mx_targets": [
      "mail.h-email.net"
    ],
    "dmarc_live": "v=DMARC1; p=none",
    "spf_live": "v=spf1 ip6:fd1b:212c:a5f9::/48 -all",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: mail.h-email.net | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "zalando.no",
    "grade": "D",
    "score": 51,
    "has_mx": true,
    "mx_targets": [
      "aspmx.l.google.com",
      "alt3.aspmx.l.google.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:dmarc_reports@zalando.no; ruf=mailto:dmarc_auth@zalando.no;",
    "spf_live": "v=spf1 ip4:185.85.220.205 include:_spf.google.com include:spf.protection.outlook.com ~all",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: aspmx.l.google.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "cubus.com",
    "grade": "D",
    "score": 45,
    "has_mx": true,
    "mx_targets": [
      "eu.mx1.mailanyone.net",
      "eu.mx2.mx25.net"
    ],
    "dmarc_live": "v=DMARC1; p=quarantine; rua=mailto:dmarc_agg@vali.email;",
    "spf_live": "v=spf1 include:spf.mailanyone.net include:spf.protection.outlook.com -all",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "quarantine",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: eu.mx1.mailanyone.net | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "sas.no",
    "grade": "D",
    "score": 45,
    "has_mx": true,
    "mx_targets": [
      "mx1.hc63-0.eu.iphmx.com",
      "mx2.hc63-0.eu.iphmx.com"
    ],
    "dmarc_live": "v=DMARC1; p=quarantine; rua=mailto:tcs-is-soc@sas.dk; ruf=mailto:tcs-is-soc@sas.dk; pct=100; sp=none…",
    "spf_live": "v=spf1 a include:spf.protection.outlook.com include:_spf-dc2.successfactors.com exists:%{i}.spf.hc63…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "quarantine",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: mx1.hc63-0.eu.iphmx.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "norwegian.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "norwegian-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; sp=none; fo=1; ri=86400; rua=mailto:8803750eec31473aa1000b2fd3d14a16@dmarc-reports…",
    "spf_live": "v=spf1 mx ip4:81.93.162.181 ip4:81.93.162.182 ip4:35.174.145.124 ip4:195.225.14.20 ip4:195.225.14.21…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: norwegian-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "scandichotels.no",
    "grade": "F",
    "score": 25,
    "has_mx": false,
    "mx_targets": [],
    "dmarc_live": null,
    "spf_live": "v=spf1 -all",
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [
      [
        "scandichotels.com",
        "scandichotels-com.mail.protection.outlook.com"
      ]
    ],
    "verdict": "SKIP",
    "reason": "Bruker sannsynligvis alternativt domene: scandichotels.com (mx: scandichotels-com.mail.protection.outlook.com). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare."
  },
  {
    "domain": "bring.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "pos-mailgw01.posten.no",
      "pos-mailgw02.posten.no"
    ],
    "dmarc_live": "v=DMARC1; p=none; pct=100; rua=mailto:dmarc_agg@vali.email; adkim=r; aspf=r",
    "spf_live": "v=spf1 ip4:139.118.71.0/24 ip4:139.116.71.0/25 ip4:139.117.144.107/27 ip4:85.221.23.80/29 ip4:176.12…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: pos-mailgw01.posten.no | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "schenker.no",
    "grade": "F",
    "score": 0,
    "has_mx": true,
    "mx_targets": [
      "smtp.domainnetwork.net"
    ],
    "dmarc_live": null,
    "spf_live": null,
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: smtp.domainnetwork.net | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "bilforsikring.no",
    "grade": "F",
    "score": 8,
    "has_mx": true,
    "mx_targets": [
      "ASPMX.L.GOOGLE.COM",
      "ALT1.ASPMX.L.GOOGLE.COM"
    ],
    "dmarc_live": "v=DMARC1; p=none",
    "spf_live": null,
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: ASPMX.L.GOOGLE.COM | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "visma.com",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "aspmx.l.google.com",
      "alt1.aspmx.l.google.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:re+dinga1rjzqy@dmarc.postmarkapp.com,mailto:vit-dkim@visma.com; fo=0; a…",
    "spf_live": "v=spf1 include:_spfzone.visma.com -all",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: aspmx.l.google.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "hjemla.no",
    "grade": "F",
    "score": 8,
    "has_mx": true,
    "mx_targets": [
      "hjemla-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:post@hjemla.no",
    "spf_live": null,
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: hjemla-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "funcom.com",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "mailrelay-osl.funcom.com",
      "mailrelay1-ams.funcom.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; sp=none; rua=mailto:dmarc@funcom.com; ruf=mailto:dmarc@funcom.com",
    "spf_live": "v=spf1 ip4:195.110.28.0/23 ip4:194.0.169.0/24 ip4:195.169.90.0/27 ip4:96.10.3.40/29 ip4:195.159.90.0…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: mailrelay-osl.funcom.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "uio.no",
    "grade": "F",
    "score": 33,
    "has_mx": true,
    "mx_targets": [
      "smtp.uio.no"
    ],
    "dmarc_live": "v=DMARC1; p=none;",
    "spf_live": "v=spf1 mx include:spf.uio.no include:_spf.google.com include:spf.protection.outlook.com -all",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: smtp.uio.no | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "ntnu.no",
    "grade": "F",
    "score": 18,
    "has_mx": true,
    "mx_targets": [
      "mx.ntnu.no"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:dmarc_rua@it.ntnu.no;",
    "spf_live": "v=spf1 redirect=_spf.ntnu.no",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: mx.ntnu.no | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "nmbu.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "nmbu-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; sp=none; rua=mailto:dmarc_rua@nmbu.no; ruf=mailto:dmarc_ruf@nmbu.no",
    "spf_live": "v=spf1 ip4:128.39.239.94/32 ip4:128.39.238.99/32 include:_spf.nmbu.no include:spf.uio.no include:spf…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: nmbu-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "hvl.no",
    "grade": "D",
    "score": 48,
    "has_mx": true,
    "mx_targets": [
      "hvl-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; pct=100; rua=mailto:DMARC-rua@hvl.no",
    "spf_live": "v=spf1 include:spf.protection.outlook.com ip4:167.89.59.190 ip4:158.37.32.53 include:spf.uio.no incl…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: hvl-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "khio.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "khio-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:dmarc@inbound.flowmailer.net; ruf=mailto:dmarc@inbound.flowmailer.net; …",
    "spf_live": "v=spf1 ip4:158.36.122.44 include:spf.protection.outlook.com include:spf.uio.no include:_spf.uninett.…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: khio-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "bi.no",
    "grade": "D",
    "score": 48,
    "has_mx": true,
    "mx_targets": [
      "bi-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=quarantine; sp=quarantine; pct=30; rua=mailto:30e48f5f@in.mailhardener.com; ruf=mailto:3…",
    "spf_live": "v=spf1 ip4:144.164.0.0/16 ip4:89.250.112.0 include:_spf.qualtrics.com ip4:167.89.59.190 ip4:167.89.6…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: bi-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "ks.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "ks-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:dsm1h58m@ag.dmarcian.com",
    "spf_live": "v=spf1 mx ip4:195.159.159.70 ip4:195.159.101.208 ip4:193.161.175.28 ip4:193.161.175.29 ip4:137.221.2…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: ks-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "oslo.kommune.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "oslokommune.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:nm92qxbr@ag.eu.dmarcadvisor.com;",
    "spf_live": "v=spf1 include:spf.protection.outlook.com -all",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: oslokommune.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "baerum.kommune.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "baerum-kommune-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:dmarc@baerumkommune.uriports.com; ruf=mailto:dmarc@baerumkommune.uripor…",
    "spf_live": "v=spf1 mx ip4:193.161.44.20/32 ip4:193.161.44.32/32 a:mail.baerum.kommune.no a:mail2.baerum.kommune.…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: baerum-kommune-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "tromso.kommune.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "tromso-kommune-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:lwdb7jov6p@rua.powerdmarc.com; ruf=mailto:lwdb7jov6p@ruf.powerdmarc.com…",
    "spf_live": "v=spf1 include:p24u9b3746.powerspf.com -all",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: tromso-kommune-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "sopra-steria.no",
    "grade": "F",
    "score": 25,
    "has_mx": true,
    "mx_targets": [
      "relay1.netnames.net",
      "relay2.netnames.net"
    ],
    "dmarc_live": null,
    "spf_live": "v=spf1 mx ip4:212.180.1.59/24 ip4:84.37.121.0/28 ip4:90.115.201.24/32 ip4:216.74.162.13/32 ip4:216.7…",
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: relay1.netnames.net | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "atea.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "atea.in.tmes.trendmicro.eu"
    ],
    "dmarc_live": "v=DMARC1; p=none; rua=mailto:NO.DMARC.Reports@atea.no,mailto:re+vepvuvzcil2@dmarc.postmarkapp.com;",
    "spf_live": "v=spf1 include:amazonses.com include:_spf.telecomputing.no include:_spf1.atea.no include:_spf2.atea.…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: atea.in.tmes.trendmicro.eu | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "itera.no",
    "grade": "D",
    "score": 48,
    "has_mx": true,
    "mx_targets": [
      "itera-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1; p= reject; fo=1; ri=3600; rua=mailto:DMARC-Itera@itera.no,mailto:dmarc_agg@vali.email; ruf…",
    "spf_live": "v=spf1 mx a ip4:93.190.81.166 ip4:20.107.84.202 ip4:93.190.81.183 ip6:fe80::64f2:afed:6d57:658d incl…",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": null,
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: itera-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "unicef.no",
    "grade": "D",
    "score": 53,
    "has_mx": true,
    "mx_targets": [
      "unicef-no.mail.protection.outlook.com"
    ],
    "dmarc_live": "v=DMARC1;  p=none; rua=mailto:a31abe5d89e4470ea70ccfdc8aedf5a0@dmarc-reports.cloudflare.net",
    "spf_live": "v=spf1 include:_spf.intility.com include:spf.protection.outlook.com include:_spf.salesforce.com -all",
    "snap_dmarc_present": true,
    "snap_dmarc_policy": "none",
    "alts_with_email": [],
    "verdict": "VERIFIED",
    "reason": "MX: unicef-no.mail.protection.outlook.com | Real e-post-domene + DMARC-mangel bekreftet live."
  },
  {
    "domain": "nakk.no",
    "grade": "F",
    "score": 0,
    "has_mx": false,
    "mx_targets": [],
    "dmarc_live": null,
    "spf_live": null,
    "snap_dmarc_present": false,
    "snap_dmarc_policy": null,
    "alts_with_email": [
      [
        "nakk.com",
        "localhost"
      ]
    ],
    "verdict": "SKIP",
    "reason": "Bruker sannsynligvis alternativt domene: nakk.com (mx: localhost). Sjekk det i stedet — eller bruk en formulering som ikke impliserer at de er sårbare."
  }
]
```