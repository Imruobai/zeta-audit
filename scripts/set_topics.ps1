#!/usr/bin/env pwsh
# Set the repository topics and confirm the About field, via the GitHub REST API.
#
# Why a script rather than a "go click this" instruction: the topics list is one API call,
# and getting it wrong (a typo, or dropping one) is silent. This sets the whole list in one
# PUT (the API replaces, not merges) and then reads it back, so the result is verified
# rather than assumed.
#
# Requires a token with `repo` (or fine-grained: Administration -> write, or "Metadata: read
# and write"). Create one at https://github.com/settings/tokens and run:
#
#   $env:GH_TOKEN = "ghp_xxx"
#   pwsh -File scripts/set_topics.ps1

param(
    [string]$Owner = "KIDA-Nya",
    [string]$Repo  = "zeta-audit"
)

$ErrorActionPreference = "Stop"

if (-not $env:GH_TOKEN) {
    Write-Error "GH_TOKEN is not set. Create a token with repo scope, then: `$env:GH_TOKEN = 'ghp_...'"
    exit 1
}

# Chosen for how GitHub's own search actually works:
#   riemann-zeta / zeta-zeros  -> the two real browse entry points for this subject
#   number-theory / mathematics -> broad subject tags
#   verification / data-validation -> what the tool does, not what it studies
#   odlyzko / lmfdb -> the two table publishers a user is most likely to arrive from
#   mpmath -> the library the cross-check depends on
#   cli / python / scientific-computing -> language and interface
$topics = @(
    "riemann-zeta",
    "zeta-zeros",
    "number-theory",
    "mathematics",
    "verification",
    "data-validation",
    "mpmath",
    "odlyzko",
    "lmfdb",
    "scientific-computing",
    "cli",
    "python"
)

$headers = @{
    "Authorization"        = "Bearer $($env:GH_TOKEN)"
    "Accept"               = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent"           = "zeta-audit-topic-setter"
}

$body = @{ names = $topics } | ConvertTo-Json

Write-Host "Setting $($topics.Count) topics on $Owner/$Repo ..."
Invoke-RestMethod -Method Put `
    -Uri "https://api.github.com/repos/$Owner/$Repo/topics" `
    -Headers $headers -Body $body -ContentType "application/json" | Out-Null

$after = Invoke-RestMethod -Method Get `
    -Uri "https://api.github.com/repos/$Owner/$Repo/topics" `
    -Headers $headers

Write-Host ""
Write-Host "Topics now set ($($after.names.Count)):"
$after.names | ForEach-Object { Write-Host "  $_" }

$missing = $topics | Where-Object { $_ -notin $after.names }
if ($missing) {
    Write-Error "These topics did not stick: $($missing -join ', ')"
    exit 1
}

Write-Host ""
Write-Host "OK - all requested topics are live."