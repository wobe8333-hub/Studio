# v7 Run Now - Execute v7-run once (minimal wrapper)

$ErrorActionPreference = "Continue"
$OutputEncoding = [System.Text.Encoding]::UTF8

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
Set-Location $projectRoot

# Load facts
$factsCli = Get-Content -Path "$scriptDir\_facts_cli.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$categories = $factsCli.default_categories -join ","

# Execute v7-run
$command = "cd `"$projectRoot`" ; python -m backend.cli.run knowledge v7-run --categories $categories --mode run --max-keywords-per-category 10 --approve-fallback"

Write-Host "Executing: $command"
Invoke-Expression $command

exit $LASTEXITCODE

