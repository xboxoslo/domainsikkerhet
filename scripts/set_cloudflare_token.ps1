# Interaktiv setter for Cloudflare-API-token i Azure Key Vault.
# Prompter for tokenet via SecureString (vises ikke i historikk eller skjerm),
# verifiserer at det er gyldig + har Zero Trust Access-scopes, og lagrer det
# i micronet-shared-kv.
#
# Kjør: pwsh -File scripts\set_cloudflare_token.ps1
# (eller fra cmd: powershell -File scripts\set_cloudflare_token.ps1)

[CmdletBinding()]
param(
    [string]$VaultName = 'micronet-shared-kv',
    [string]$SecretName = 'Cloudflare-Api-Token'
)

$ErrorActionPreference = 'Stop'

Write-Host ''
Write-Host '=== Cloudflare API-token setter ===' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Dette scriptet lagrer en ny Cloudflare API-token i Azure Key Vault.'
Write-Host ''
Write-Host 'STEG 1: Lag tokenet i Cloudflare:' -ForegroundColor Yellow
Write-Host '  https://dash.cloudflare.com/profile/api-tokens -> Create Token -> Custom token'
Write-Host ''
Write-Host '  Permissions (alle tre obligatoriske):' -ForegroundColor Yellow
Write-Host '    * Account -> Access: Apps and Policies -> Edit'
Write-Host '    * Account -> Access: Service Tokens     -> Edit'
Write-Host '    * Zone    -> Zone                       -> Read'
Write-Host ''
Write-Host '  Account Resources: Include -> Micronet-konto'
Write-Host '  Zone Resources:    Include -> data1.no'
Write-Host '  Client IP Filtering: (la stå tomt)'
Write-Host '  TTL: (la stå tomt for ingen utløp, eller sett 1 år)'
Write-Host ''
Write-Host 'STEG 2: Lim inn tokenet under (vises ikke på skjerm).' -ForegroundColor Yellow
Write-Host ''

# Prompt via SecureString — vises ikke i historikk, vises ikke på skjerm
$sec = Read-Host -AsSecureString 'Cloudflare API-token'
$tok = [System.Net.NetworkCredential]::new('', $sec).Password

if ([string]::IsNullOrWhiteSpace($tok)) {
    Write-Host '  FEIL: Tomt token. Avbryter.' -ForegroundColor Red
    exit 1
}

$tokLen = $tok.Length
$prefix = $tok.Substring(0, [Math]::Min(6, $tokLen))
Write-Host ''
Write-Host "Mottok token (lengde=$tokLen, prefix='$prefix')..."

# ===== STEG A: Verifiser at tokenet er gyldig =====
Write-Host ''
Write-Host '=== Verifiserer token mot Cloudflare API ===' -ForegroundColor Cyan

$headers = @{ 'Authorization' = "Bearer $tok"; 'Content-Type' = 'application/json' }

try {
    $verify = Invoke-RestMethod -Uri 'https://api.cloudflare.com/client/v4/user/tokens/verify' -Headers $headers -Method GET -ErrorAction Stop
} catch {
    Write-Host "  FEIL: Token-verifisering feilet med HTTP-feil:" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
    Remove-Variable tok, sec
    exit 1
}

if (-not $verify.success) {
    Write-Host '  FEIL: Tokenet er ikke gyldig.' -ForegroundColor Red
    Write-Host "  Cloudflare-svar: $($verify.errors | ConvertTo-Json -Compress)" -ForegroundColor Red
    Remove-Variable tok, sec
    exit 1
}

Write-Host "  Token aktiv (id=$($verify.result.id), status=$($verify.result.status))" -ForegroundColor Green

# ===== STEG B: Hent account-ID for å teste Access-scopes =====
Write-Host ''
Write-Host '=== Henter account-ID ===' -ForegroundColor Cyan

try {
    $accounts = Invoke-RestMethod -Uri 'https://api.cloudflare.com/client/v4/accounts' -Headers $headers -Method GET -ErrorAction Stop
} catch {
    Write-Host "  ADVARSEL: Kunne ikke hente accounts (mangler scope 'Account Settings:Read'? OK å fortsette hvis Access scopes er på plass)" -ForegroundColor Yellow
    $accounts = $null
}

$accountId = $null
if ($accounts -and $accounts.success -and $accounts.result.Count -gt 0) {
    $accountId = $accounts.result[0].id
    $accountName = $accounts.result[0].name
    Write-Host "  Account: $accountName (id=$accountId)" -ForegroundColor Green
}

# ===== STEG C: Test Zero Trust Access-scope =====
Write-Host ''
Write-Host '=== Tester Zero Trust Access-scope ===' -ForegroundColor Cyan

$accessOk = $false
if ($accountId) {
    try {
        $apps = Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/accounts/$accountId/access/apps?per_page=1" -Headers $headers -Method GET -ErrorAction Stop
        if ($apps.success) {
            $count = $apps.result_info.total_count
            Write-Host "  OK — kan lese Access apps (eksisterende: $count)" -ForegroundColor Green
            $accessOk = $true
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "  FEIL: Kan ikke lese Access-apps (HTTP $statusCode)" -ForegroundColor Red
        Write-Host "  $_" -ForegroundColor Red
    }
}

if (-not $accessOk) {
    Write-Host ''
    Write-Host '  Tokenet mangler 'Access: Apps and Policies'-scope. Gå tilbake til' -ForegroundColor Red
    Write-Host '  https://dash.cloudflare.com/profile/api-tokens og legg til scopene.' -ForegroundColor Red
    Write-Host ''
    Write-Host '  AVBRYTER — tokenet er IKKE lagret i Key Vault.' -ForegroundColor Red
    Remove-Variable tok, sec
    exit 1
}

# ===== STEG D: Lagre i Key Vault =====
Write-Host ''
Write-Host "=== Lagrer i Azure Key Vault ($VaultName / $SecretName) ===" -ForegroundColor Cyan

# Sjekk Azure CLI-pålogging
try {
    $azAccount = az account show --query name -o tsv 2>$null
    if ([string]::IsNullOrWhiteSpace($azAccount)) {
        throw "ikke pålogget"
    }
    Write-Host "  Azure-konto: $azAccount" -ForegroundColor Green
} catch {
    Write-Host "  FEIL: Ikke pålogget Azure. Kjør 'az login' først." -ForegroundColor Red
    Remove-Variable tok, sec
    exit 1
}

# Skriv til Key Vault
$result = az keyvault secret set `
    --vault-name $VaultName `
    --name $SecretName `
    --value $tok `
    --tags "set-by=set_cloudflare_token.ps1" "validated=$(Get-Date -Format 'yyyy-MM-dd')" `
    -o json 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "  FEIL: Klarte ikke skrive til Key Vault:" -ForegroundColor Red
    Write-Host "  $result" -ForegroundColor Red
    Remove-Variable tok, sec
    exit 1
}

$secret = $result | ConvertFrom-Json
Write-Host "  Lagret som $($secret.id)" -ForegroundColor Green
Write-Host "  Versjon: $($secret.attributes.version)" -ForegroundColor Green

# ===== Rydd opp =====
Remove-Variable tok, sec, headers

Write-Host ''
Write-Host '=== Ferdig ===' -ForegroundColor Green
Write-Host 'Tokenet er verifisert og lagret. Claude (eller andre scripts) kan nå hente det med:'
Write-Host '  az keyvault secret show --vault-name micronet-shared-kv --name Cloudflare-Api-Token --query value -o tsv'
Write-Host ''
Write-Host 'Account-ID for Access-API-kall:' -ForegroundColor Cyan
if ($accountId) {
    Write-Host "  $accountId"
}
Write-Host ''
