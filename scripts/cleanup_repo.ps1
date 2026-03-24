# cleanup_repo.ps1 - Remove regenerable files/folders from repository
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\cleanup_repo.ps1

$ErrorActionPreference = "Stop"

function Get-Size([string]$Path) {
    if (Test-Path $Path) {
        $item = Get-Item $Path -ErrorAction SilentlyContinue
        if ($item) {
            if ($item.PSIsContainer) {
                $size = (Get-ChildItem -Path $Path -Recurse -ErrorAction SilentlyContinue | 
                    Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
            } else {
                $size = $item.Length
            }
            return $size
        }
    }
    return 0
}

function Format-Size([long]$Bytes) {
    if ($Bytes -ge 1GB) {
        return "{0:N2} GB" -f ($Bytes / 1GB)
    } elseif ($Bytes -ge 1MB) {
        return "{0:N2} MB" -f ($Bytes / 1MB)
    } elseif ($Bytes -ge 1KB) {
        return "{0:N2} KB" -f ($Bytes / 1KB)
    } else {
        return "$Bytes B"
    }
}

Write-Host "=========================================="
Write-Host "Repository Cleanup Script"
Write-Host "=========================================="
Write-Host ""

$repoRoot = $PSScriptRoot | Split-Path -Parent
Set-Location $repoRoot

Write-Host "Repository root: $repoRoot"
Write-Host ""

# Calculate size before cleanup
Write-Host "Calculating size before cleanup..."
$totalBefore = 0
$itemsToRemove = @(
    @{Path="backend\.venv"; Name="Backend virtualenv"},
    @{Path="frontend\node_modules"; Name="Frontend node_modules"},
    @{Path="frontend\.next"; Name="Frontend build artifacts"},
    @{Path="backend\output"; Name="Backend output"},
    @{Path="release"; Name="Release folders"},
    @{Path="releases"; Name="Releases folders"}
)

$sizesBefore = @{}
foreach ($item in $itemsToRemove) {
    $fullPath = Join-Path $repoRoot $item.Path
    $size = Get-Size $fullPath
    if ($size -gt 0) {
        $sizesBefore[$item.Path] = $size
        $totalBefore += $size
        Write-Host "  {0}: {1}" -f $item.Name, (Format-Size $size)
    }
}

# Find all __pycache__ and *.pyc
Write-Host ""
Write-Host "Scanning for Python cache files..."
$pycacheDirs = Get-ChildItem -Path $repoRoot -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue
$pycFiles = Get-ChildItem -Path $repoRoot -File -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue

$pycacheSize = 0
foreach ($dir in $pycacheDirs) {
    $size = Get-Size $dir.FullName
    $pycacheSize += $size
}
foreach ($file in $pycFiles) {
    $pycacheSize += $file.Length
}

if ($pycacheSize -gt 0) {
    Write-Host "  Python cache files: {0}" -f (Format-Size $pycacheSize)
    $totalBefore += $pycacheSize
}

Write-Host ""
Write-Host "Total size to remove: {0}" -f (Format-Size $totalBefore)
Write-Host ""

# Confirm
$confirm = Read-Host "Do you want to proceed with cleanup? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Cleanup cancelled."
    exit 0
}

Write-Host ""
Write-Host "Starting cleanup..."
Write-Host ""

# Remove items
foreach ($item in $itemsToRemove) {
    $fullPath = Join-Path $repoRoot $item.Path
    if (Test-Path $fullPath) {
        Write-Host "Removing: {0}" -f $item.Name
        try {
            Remove-Item -Path $fullPath -Recurse -Force -ErrorAction Stop
            Write-Host "  ✓ Removed" -ForegroundColor Green
        } catch {
            Write-Host "  ✗ Failed: {0}" -f $_.Exception.Message -ForegroundColor Red
        }
    }
}

# Remove __pycache__ directories
if ($pycacheDirs) {
    Write-Host "Removing __pycache__ directories..."
    foreach ($dir in $pycacheDirs) {
        try {
            Remove-Item -Path $dir.FullName -Recurse -Force -ErrorAction Stop
        } catch {
            # Ignore errors for individual cache dirs
        }
    }
    Write-Host "  ✓ Removed {0} __pycache__ directories" -f $pycacheDirs.Count -ForegroundColor Green
}

# Remove *.pyc files
if ($pycFiles) {
    Write-Host "Removing *.pyc files..."
    foreach ($file in $pycFiles) {
        try {
            Remove-Item -Path $file.FullName -Force -ErrorAction Stop
        } catch {
            # Ignore errors for individual pyc files
        }
    }
    Write-Host "  ✓ Removed {0} *.pyc files" -f $pycFiles.Count -ForegroundColor Green
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Cleanup completed!"
Write-Host "=========================================="
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Run: python -m backend.scripts.import_sanity"
Write-Host "  2. Run: python -m backend.scripts.verify_runs"
Write-Host "  3. Run: .\scripts\size_report.ps1 (to verify size reduction)"
Write-Host ""

