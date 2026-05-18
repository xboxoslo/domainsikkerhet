# Wikipedia-API-oppsett

Setter opp bot-passord for `Terje_Otterlei` på `no.wikipedia.org` og lagrer i Azure Key Vault, slik at `scripts/wiki_edit.py` kan lese/skrive artikler.

## 1. Generer bot-passord på Wikipedia

1. Logg inn på <https://no.wikipedia.org> som `Terje_Otterlei`.
2. Gå til <https://no.wikipedia.org/wiki/Spesial:Botpassord>.
3. Fyll inn `Bot name`: f.eks. `data1`.
4. Velg minimum disse rettighetene (Grants):
   - **Basic rights** (alltid med)
   - **Edit existing pages**
   - **Create, edit, and move pages**
5. (Valgfritt for ekstra sikkerhet) Lås til IP-range.
6. Klikk **Opprett**. Du får et **brukernavn** på formen `Terje_Otterlei@data1` og et **passord** — passordet vises **kun én gang**, kopier det med en gang.

## 2. Lagre i Azure Key Vault

```powershell
# Brukernavn (formen "Terje_Otterlei@data1")
az keyvault secret set --vault-name micronet-data1-kv --name Wikipedia-Bot-Username --value "Terje_Otterlei@data1"

# Passord
az keyvault secret set --vault-name micronet-data1-kv --name Wikipedia-Bot-Password --value "DET-LANGE-PASSORDET-FRA-WIKIPEDIA"
```

`scripts/wiki_edit.py` plukker disse opp automatisk via samme mønster som resten av prosjektet (`AZURE_SECRETS`-mappingen).

## 3. Verifiser

```powershell
python scripts\wiki_edit.py whoami
```

Forventet utdata:

```
Innlogget som: Terje Otterlei
Grupper:       *, user, autoconfirmed, ...
ID:            <tall>
```

## 4. Bruk

```powershell
# Les en artikkel
python scripts\wiki_edit.py read "Terje Otterlei"

# Se historikk
python scripts\wiki_edit.py history "Terje Otterlei" --limit 5

# Legg til kilder nederst (dry-run først — INGEN endring publiseres uten --yes)
python scripts\wiki_edit.py append "Terje Otterlei" --text "`n== Referanser ==`n{{Reflist}}" --summary "Legger til referanser"

# Når dry-run ser OK ut, kjør på nytt med --yes
python scripts\wiki_edit.py append "Terje Otterlei" --text "`n== Referanser ==`n{{Reflist}}" --summary "Legger til referanser" --yes

# Erstatt en seksjon (seksjonsnummer fra read-output)
python scripts\wiki_edit.py replace-section "Tittel" --section 2 --text "ny tekst med <ref>kilde</ref>" --yes
```

## Viktig — policy

- **Ingen bot-flag**: vi har ikke søkt om bot-status, så masseredigeringer (mange artikler raskt) er ikke tillatt. Lavfrekvent, manuelt initiert er greit.
- **Edit summary** får automatisk `(via wiki_edit.py)` for sporbarhet.
- **Selvbiografier**: Hvis en artikkel handler om deg selv, vær ekstra forsiktig — se [WP:SELVBIO](https://no.wikipedia.org/wiki/Wikipedia:Selvbiografi). Bare objektive, kildebelagte tilføyelser.
- **Alltid kilder**: hver påstand som ikke er åpenbar bør ha `<ref>...</ref>` med en autoritativ kilde.
