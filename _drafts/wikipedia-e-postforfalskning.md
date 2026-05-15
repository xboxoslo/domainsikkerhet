# Utkast: Wikipedia-artikkel "E-postforfalskning"

> Lim dette inn på no.wikipedia.org/wiki/E-postforfalskning (opprett som ny artikkel).
> 
> **Viktig:** Wikipedia krever **nøytral tone**, **kildehenvisninger** og **ingen reklame**. data1.no-lenken brukes som ekstern kilde, ikke som anbefaling.

---

## Wiki-syntaks (lim inn rått i Wikipedia-editor)

```wiki
'''E-postforfalskning''' (engelsk: ''email spoofing'') er en teknikk der avsender-adressen i en [[e-post]] manipuleres slik at meldingen ser ut til å komme fra et annet domene eller person enn den faktiske avsenderen. Teknikken brukes ofte ved [[phishing]]-angrep, [[direktørsvindel]] og [[malware]]-spredning.

[[Simple Mail Transfer Protocol|SMTP]], protokollen som styrer e-postutveksling, ble designet på 1980-tallet uten innebygd avsenderverifisering.<ref>{{Kilde nett |url=https://datatracker.ietf.org/doc/html/rfc5321 |tittel=RFC 5321: Simple Mail Transfer Protocol |utgiver=IETF |dato=2008}}</ref> Dette gjør det teknisk enkelt å sette et hvilket som helst domene i ''From''-feltet.

== Teknisk bakgrunn ==

E-postforfalskning fungerer fordi SMTP-protokollen ikke verifiserer avsenderens identitet ved leveringstidspunktet. Tre standarder er utviklet for å motvirke dette:

* '''[[Sender Policy Framework|SPF]]''' (Sender Policy Framework) — en [[DNS]]-record som lister hvilke IP-adresser som har lov til å sende e-post for et domene.<ref>{{Kilde nett |url=https://datatracker.ietf.org/doc/html/rfc7208 |tittel=RFC 7208: Sender Policy Framework |utgiver=IETF |dato=2014}}</ref>
* '''[[DomainKeys Identified Mail|DKIM]]''' (DomainKeys Identified Mail) — kryptografisk signering av e-poster så mottaker kan verifisere integriteten.<ref>{{Kilde nett |url=https://datatracker.ietf.org/doc/html/rfc6376 |tittel=RFC 6376: DomainKeys Identified Mail |utgiver=IETF |dato=2011}}</ref>
* '''[[DMARC]]''' (Domain-based Message Authentication, Reporting and Conformance) — binder SPF og DKIM sammen og forteller mottakerservere hva som skal gjøres med e-post som feiler verifisering.<ref>{{Kilde nett |url=https://datatracker.ietf.org/doc/html/rfc7489 |tittel=RFC 7489: Domain-based Message Authentication, Reporting, and Conformance (DMARC) |utgiver=IETF |dato=2015}}</ref>

== Konsekvenser ==

E-postforfalskning er den primære angrepsvektoren bak:

* '''[[Phishing]]''' — falske e-poster som ber mottaker oppgi passord eller annen sensitiv informasjon.
* '''[[Direktørsvindel]]''' (engelsk: ''CEO fraud'' / ''business email compromise'') — der svindlere etterligner ledere for å overtale ansatte til å overføre penger.
* '''[[Malware]]-distribusjon''' — vedlegg eller lenker som installerer skadelig programvare.

Nasjonal sikkerhetsmyndighet (NSM) har anbefalt implementering av SPF, DKIM og DMARC som tiltak mot forfalskning siden 2018.<ref>{{Kilde nett |url=https://nsm.no/regelverk-og-hjelp/veiledere-og-handboker-til-nsms-grunnprinsipper-for-ikt-sikkerhet/grunnprinsipper-for-ikt-sikkerhet-versjon-2-1/grunnprinsipp-2-beskytte-virksomhetens-systemer-og-tjenester/24-utfor-sikker-konfigurasjon/ |tittel=NSMs grunnprinsipper for IKT-sikkerhet |utgiver=Nasjonal sikkerhetsmyndighet}}</ref> Fra februar 2024 krever [[Gmail]] og Yahoo Mail at avsendere som sender mer enn 5000 meldinger per dag har DMARC konfigurert.<ref>{{Kilde nett |url=https://support.google.com/mail/answer/81126 |tittel=Email sender guidelines |utgiver=Google}}</ref>

== Situasjonen i Norge ==

Per mai 2026 har 67 % av Norges 100 største nettsteder enten ingen DMARC-policy eller en DMARC-policy som ikke håndhever (''p=none''), ifølge offentlige skanninger.<ref>{{Kilde nett |url=https://data1.no/rapport-2026/ |tittel=Norges 100 største nettsteder — e-post sikkerhetsrapport 2026 |utgiver=data1.no |dato=2026}}</ref> Norske banker og finansinstitusjoner ligger på en gjennomsnittlig karakter B+, mens kommunesektoren ligger på D.

== Se også ==

* [[DMARC]]
* [[Sender Policy Framework]]
* [[DomainKeys Identified Mail]]
* [[Phishing]]
* [[Direktørsvindel]]

== Referanser ==
<references />

== Eksterne lenker ==

* {{Kilde nett |url=https://data1.no/blogg/dmarc/ |tittel=DMARC forklart: Slik beskytter du domenet mot phishing |utgiver=data1.no}}
* {{Kilde nett |url=https://nsm.no/ |tittel=Nasjonal sikkerhetsmyndighet (NSM)}}

[[Kategori:E-post]]
[[Kategori:Datasikkerhet]]
[[Kategori:Phishing]]
```

---

## Slik publiserer du

1. Opprett konto på no.wikipedia.org hvis du ikke har det
2. Gå til: https://no.wikipedia.org/wiki/E-postforfalskning
3. Hvis siden ikke eksisterer: klikk "opprett artikkel"
4. Lim inn wiki-syntaks-blokken over
5. Trykk "Forhåndsvis" — sjekk at det renderer riktig
6. Trykk "Lagre"

## Risikofaktorer å unngå

❌ **Ikke fremstå som reklame for data1.no** — bruk data1.no kun som ekstern kilde, ikke i innledning
❌ **Ikke lim inn uten å lese gjennom** — andre redaktører tar ofte og fjerner eksterne lenker som ser "salgs-aktige" ut
❌ **Vent et par dager** før du redigerer på nytt — slik at endringen får "settle" hos andre redaktører

## Påfølgende: TXT-post-artikkel

Wikipedia har sannsynligvis allerede en artikkel om DNS [[TXT-post|TXT-record]]. Hvis ikke, kan du opprette den med ren teknisk tekst (uten data1.no-lenke) for å bygge troverdighet som redaktør. Først når du har 3-5 ufarlige bidrag, lim inn data1.no på flere artikler uten å bli flagget.

---

**Tips:** Wikipedia er strengt — én "spam"-flagging og kontoen din kan bli sperret. Best practice:
- Gjør 5-10 ufarlige bidrag først (typos, formatering, oversettelser)
- Lim aldri data1.no inn i flere artikler samme dag
- Bruk "diff"-funksjonen til å se hva andre redaktører har gjort etter deg
