param(
    [switch]$IncludeVenv
)

$ErrorActionPreference = "Stop"
trap {
    Write-Host "[FATAL] $($_.Exception.Message)"
    Write-Host "[FATAL][POSITION] $($_.InvocationInfo.PositionMessage)"
    Write-Host "[FATAL][STACK] $($_.ScriptStackTrace)"
    exit 99
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
Set-Location $projectRoot

$includeVenvFlag = $IncludeVenv.IsPresent
Write-Host "[CLEANUP] Project root: $projectRoot"
Write-Host "[CLEANUP] include_venv=$includeVenvFlag"

# 1) Repo root guard
if (-not (Test-Path (Join-Path $projectRoot "backend"))) {
    Write-Host "[CLEANUP][FAIL] backend folder not found under current directory. Run from repo root."
    exit 2
}

# 2) SSOT guard
$ssotPath = Join-Path $projectRoot "data\knowledge_v1_store"
if (-not (Test-Path $ssotPath)) {
    Write-Host "[SSOT][FAIL] missing data\knowledge_v1_store"
    exit 10
}

function Assert-NotSSOTPath {
    param(
        [string]$Path
    )
    if ($null -ne $Path -and $Path -match "[\\/]data[\\/]knowledge_v1_store[\\/]") {
        Write-Host "[SSOT][FAIL] attempted to touch SSOT path: $Path"
        exit 11
    }
}

# 3) Archive root
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$archiveRoot = Join-Path $projectRoot "_archive\cleanup_$ts"
New-Item -ItemType Directory -Force -Path $archiveRoot | Out-Null
Write-Host "[ARCHIVE_ROOT] $archiveRoot"

function Move-ToArchive {
    param(
        [System.IO.FileSystemInfo]$Item
    )
    if (-not $Item) { return }
    $full = $Item.FullName
    Assert-NotSSOTPath -Path $full
    $rel = Resolve-Path -LiteralPath $full | ForEach-Object {
        $_.Path.Substring($projectRoot.Length).TrimStart('\','/')
    }
    $dest = Join-Path $archiveRoot $rel
    $destDir = Split-Path -Parent $dest
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null

    $target = $dest
    $suffix = 1
    while (Test-Path $target) {
        $name = [System.IO.Path]::GetFileNameWithoutExtension($dest)
        $ext  = [System.IO.Path]::GetExtension($dest)
        $dir  = [System.IO.Path]::GetDirectoryName($dest)
        $target = Join-Path $dir ("{0}_{1}{2}" -f $name, $suffix, $ext)
        $suffix++
    }

    try {
        Move-Item -LiteralPath $full -Destination $target -Force
        return $true
    } catch {
        Write-Host "[CLEANUP][MOVE_FAIL] $full -> $target : $_"
        exit 20
    }
}

$archivedCount = 0
$deletedCacheDirs = 0
$deletedPyc = 0

# 4) Archive targets (dirs)
$archiveDirs = @(
    "backend\output",
    "data\runs",
    "data\_debug_sessions",
    "data\debug_evidence",
    "data\health",
    "data\ops"
)

if ($includeVenvFlag) {
    $archiveDirs = @(".venv") + $archiveDirs
}

foreach ($relDir in $archiveDirs) {
    $dirPath = Join-Path $projectRoot $relDir
    if (Test-Path $dirPath) {
        Assert-NotSSOTPath -Path $dirPath
        $item = Get-Item -LiteralPath $dirPath -ErrorAction SilentlyContinue
        if ($item) {
            if (Move-ToArchive -Item $item) {
                $archivedCount++
                Write-Host "[CLEANUP][ARCHIVED_DIR] $relDir"
            }
        }
    }
}

# 5) Archive targets (root-level files / logs)
$rootPatterns = @(
    "*_stdout.txt",
    "*_stderr.txt",
    "_debug_task_stdout.txt",
    "_debug_task_stderr.txt",
    "_replay_stdout.txt",
    "_replay_stderr.txt",
    "powershell_v7_real_*.txt",
    "v7_real_logs_*",
    "v7_real_logs_*.zip"
)

foreach ($pat in $rootPatterns) {
    $items = Get-ChildItem -LiteralPath $projectRoot -Filter $pat -ErrorAction SilentlyContinue
    foreach ($i in $items) {
        if (Move-ToArchive -Item $i) {
            $archivedCount++
            Write-Host "[CLEANUP][ARCHIVED] $($i.FullName)"
        }
    }
}

# 6) Archive *.bak files (recursive)
$bakItems = Get-ChildItem -Path $projectRoot -Recurse -File -Filter "*.bak" -ErrorAction SilentlyContinue
foreach ($i in $bakItems) {
    Assert-NotSSOTPath -Path $i.FullName
    if (Move-ToArchive -Item $i) {
        $archivedCount++
        Write-Host "[CLEANUP][ARCHIVED_BAK] $($i.FullName)"
    }
}

# 7) Delete __pycache__ dirs (recursive, but never under SSOT)
$cacheDirs = Get-ChildItem -Path $projectRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "[\\/]data[\\/]knowledge_v1_store[\\/]" }
foreach ($d in $cacheDirs) {
    Assert-NotSSOTPath -Path $d.FullName
    try {
        Remove-Item -LiteralPath $d.FullName -Recurse -Force
        $deletedCacheDirs++
        Write-Host "[CLEANUP][DELETED_CACHE_DIR] $($d.FullName)"
    } catch {
        Write-Host "[CLEANUP][DELETE_CACHE_FAIL] $($d.FullName) : $_"
        exit 21
    }
}

# 8) Delete *.pyc files (recursive, but never under SSOT)
$pycFiles = Get-ChildItem -Path $projectRoot -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "[\\/]data[\\/]knowledge_v1_store[\\/]" }
foreach ($f in $pycFiles) {
    Assert-NotSSOTPath -Path $f.FullName
    try {
        Remove-Item -LiteralPath $f.FullName -Force
        $deletedPyc++
        Write-Host "[CLEANUP][DELETED_PYC] $($f.FullName)"
    } catch {
        Write-Host "[CLEANUP][DELETE_PYC_FAIL] $($f.FullName) : $_"
        exit 21
    }
}

# Final SSOT check
$ssotExists = Test-Path $ssotPath
Write-Host "[SSOT] kept=$ssotExists"

Write-Host "[OK] archived: $archivedCount items"
Write-Host "[OK] deleted_cache_dirs: $deletedCacheDirs"
Write-Host "[OK] deleted_pyc: $deletedPyc"
Write-Host "[ARCHIVE_ROOT] $archiveRoot"

exit 0

