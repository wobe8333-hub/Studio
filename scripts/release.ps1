param(
  [Parameter(Mandatory=$true)]
  [string]$Version
)

$ErrorActionPreference = "Stop"

function UtcStamp() { (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss") + "Z" }
function Load-Json([string]$Path) { Get-Content -Raw -Encoding UTF8 $Path | ConvertFrom-Json }
function ToRel([string]$Full, [string]$Root) { $Full.Substring($Root.Length).TrimStart("\","/").Replace("\","/") }

# Hard block roots (must never appear in release)
$HARD_BLOCK_PREFIXES = @(
  "backend/.venv",
  "frontend/node_modules",
  "backend/output/runs",
  "backend/output/cache"
)

function IsHardBlocked([string]$rel) {
  foreach($p in $HARD_BLOCK_PREFIXES) {
    if ($rel -eq $p) { return $true }
    if ($rel.StartsWith($p + "/")) { return $true }
  }
  return $false
}

function GlobToRegex([string]$glob) {
  $g = $glob.Replace("\","/")
  $e = [Regex]::Escape($g)
  $e = $e.Replace("\*\*", "<<<TWOSTAR>>>")
  $e = $e.Replace("\*", "[^/]*")
  $e = $e.Replace("<<<TWOSTAR>>>", ".*")
  return "^" + $e + "$"
}

function IsExcludedByGlobs([string]$rel, [object[]]$exclude_globs) {
  foreach($g in $exclude_globs) {
    $rx = GlobToRegex([string]$g)
    if ($rel -match $rx) { return $true }
  }
  return $false
}

function ShouldSkip([string]$rel, [object[]]$exclude_globs) {
  if ([string]::IsNullOrWhiteSpace($rel)) { return $true }
  if (IsHardBlocked $rel) { return $true }
  if (IsExcludedByGlobs $rel $exclude_globs) { return $true }
  return $false
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$manifestPath = Join-Path $repoRoot "backend\configs\release_manifest.json"
if (!(Test-Path $manifestPath)) { throw "Missing manifest: $manifestPath" }
$manifest = Load-Json $manifestPath

$stamp = UtcStamp
$releaseRoot = Join-Path $repoRoot ("release\" + $Version + "\" + $stamp)
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null

function CopyFilteredPath([string]$srcPath) {
  $srcItem = Get-Item -LiteralPath $srcPath -Force
  if (-not $srcItem.PSIsContainer) {
    $rel = ToRel $srcItem.FullName $repoRoot
    if (ShouldSkip $rel $manifest.exclude_globs) { return }
    $dst = Join-Path $releaseRoot $rel
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
    Copy-Item -LiteralPath $srcItem.FullName -Destination $dst -Force
    return
  }

  # enumerate children; never create excluded dirs
  $items = Get-ChildItem -LiteralPath $srcItem.FullName -Recurse -Force
  foreach($it in $items) {
    $rel = ToRel $it.FullName $repoRoot
    if (ShouldSkip $rel $manifest.exclude_globs) { continue }

    $dst = Join-Path $releaseRoot $rel
    if ($it.PSIsContainer) {
      New-Item -ItemType Directory -Force -Path $dst | Out-Null
    } else {
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
      Copy-Item -LiteralPath $it.FullName -Destination $dst -Force
    }
  }
}

foreach($p in $manifest.include_paths) {
  $src = Join-Path $repoRoot $p
  if (!(Test-Path $src)) { throw "Missing include path: $p" }
  CopyFilteredPath $src
}

if ($manifest.PSObject.Properties.Name -contains "include_if_exists") {
  foreach($p in $manifest.include_if_exists) {
    $src = Join-Path $repoRoot $p
    if (Test-Path $src) { CopyFilteredPath $src }
  }
}

& python -m backend.scripts.build_info --out (Join-Path $releaseRoot "build_info.json") --version $Version
"Version: $Version`nBuilt: $stamp" | Set-Content (Join-Path $releaseRoot "RELEASE_NOTES.txt") -Encoding UTF8

Write-Output $releaseRoot
