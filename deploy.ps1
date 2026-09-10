# Build the deployable dist/ from the public decks, gate it, then deploy to Azure SWA.
# PowerShell equivalent of deploy.sh. Usage: .\deploy.ps1 [-BuildOnly]
param([switch]$BuildOnly)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$AppName = $env:APP_NAME ?? "hermes-at-home-walkthrough"
$Rg = $env:RG ?? "fsai-hermes-home"
$Tools = $env:DECK_TOOLS ?? ""

$py = "python"; if (-not (Get-Command $py -ErrorAction SilentlyContinue)) { $py = "py" }

if (Test-Path "$root\dist") { Remove-Item "$root\dist" -Recurse -Force }
New-Item -ItemType Directory -Path "$root\dist" | Out-Null
Copy-Item "$root\favicon.svg","$root\favicon.ico","$root\favicon.png" "$root\dist\" -ErrorAction SilentlyContinue

Copy-Item "$root\hermes-at-home-walkthrough.html"       "$root\dist\index.html"
Copy-Item "$root\your-second-brain.html"                "$root\dist\second-brain.html"
Copy-Item "$root\research-framework.html"               "$root\dist\research-framework.html"
Copy-Item "$root\speaker-notes-hermes-at-home.html"     "$root\dist\speaker-notes-hermes-at-home.html"
Copy-Item "$root\speaker-notes-research-framework.html" "$root\dist\speaker-notes-research-framework.html"

# Optional content rewrite — the scrubbers hold plaintext tokens, so they live
# outside this public repo. The stored decks are already the scrubbed copies.
if ($Tools -and (Test-Path $Tools)) {
  Write-Host "Rewriting content with local tools from: $Tools"
  if (Test-Path "$Tools\scrub_index.py") {
    & $py "$Tools\scrub_index.py" "$root\dist\index.html"
  }
  if (Test-Path "$Tools\scrub_research_framework.py") {
    & $py "$Tools\scrub_research_framework.py" "$root\dist\research-framework.html" "$root\dist\speaker-notes-research-framework.html"
  }
} else {
  Write-Host "note: DECK_TOOLS not set - skipping content rewrite (stored decks are already scrubbed)"
}

# Hard gate
& $py "$root\gate.py" "$root\dist"
if ($LASTEXITCODE -ne 0) { Write-Error "PII gate failed - nothing deployed."; exit 1 }

Write-Host "Built dist/ with index.html + second-brain.html + research-framework.html + 2 speaker-notes pages"
if ($BuildOnly) { Write-Host "Build complete (deploy skipped)."; exit 0 }

$token = az staticwebapp secrets list -n $AppName -g $Rg --query properties.apiKey -o tsv
$client = Get-ChildItem "$HOME\.swa\deploy\*\StaticSitesClient.exe" | Select-Object -First 1
if (-not $client) { Write-Host "StaticSitesClient not cached."; exit 1 }
Write-Host "Deploying to $AppName/$Rg ..."
$env:DEPLOYMENT_ACTION="upload"; $env:DEPLOYMENT_PROVIDER="SwaCli"; $env:SKIP_APP_BUILD="true"
$env:SKIP_API_BUILD="true"; $env:DEPLOYMENT_TOKEN=$token; $env:APP_LOCATION="$root\dist"; $env:VERBOSE="false"
& $client.FullName
Write-Host "Done."
