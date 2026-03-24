# size_report.ps1 - Report repository size breakdown
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\size_report.ps1

$ErrorActionPreference = "Stop"

function Get-DirectorySize([string]$Path) {
    if (-not (Test-Path $Path)) {
        return 0
    }
    try {
        $size = (Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue | 
            Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
        return $size
    } catch {
        return 0
    }
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

$repoRoot = $PSScriptRoot | Split-Path -Parent
Set-Location $repoRoot

Write-Host "=========================================="
Write-Host "Repository Size Report"
Write-Host "=========================================="
Write-Host ""
Write-Host "Repository root: $repoRoot"
Write-Host ""

# Get top-level directories
$topDirs = Get-ChildItem -Path $repoRoot -Directory -ErrorAction SilentlyContinue | 
    Where-Object { $_.Name -notmatch '^\.git$' }

$dirSizes = @()
foreach ($dir in $topDirs) {
    $size = Get-DirectorySize $dir.FullName
    if ($size -gt 0) {
        $dirSizes += @{
            Name = $dir.Name
            Size = $size
            Path = $dir.FullName
        }
    }
}

# Sort by size (descending)
$dirSizes = $dirSizes | Sort-Object -Property Size -Descending

Write-Host "Top-level directories (by size):"
Write-Host "----------------------------------------"
$totalSize = 0
$topN = [Math]::Min(20, $dirSizes.Count)
for ($i = 0; $i -lt $topN; $i++) {
    $item = $dirSizes[$i]
    $totalSize += $item.Size
    Write-Host ("{0,3}. {1,-30} {2,15}" -f ($i+1), $item.Name, (Format-Size $item.Size))
}
Write-Host "----------------------------------------"
Write-Host ("{0,3}  {1,-30} {2,15}" -f "", "TOTAL (top $topN)", (Format-Size $totalSize))
Write-Host ""

# Backend subdirectories
$backendPath = Join-Path $repoRoot "backend"
if (Test-Path $backendPath) {
    Write-Host "Backend subdirectories:"
    Write-Host "----------------------------------------"
    $backendDirs = Get-ChildItem -Path $backendPath -Directory -ErrorAction SilentlyContinue
    $backendSizes = @()
    foreach ($dir in $backendDirs) {
        $size = Get-DirectorySize $dir.FullName
        if ($size -gt 0) {
            $backendSizes += @{
                Name = $dir.Name
                Size = $size
            }
        }
    }
    $backendSizes = $backendSizes | Sort-Object -Property Size -Descending
    $topBackend = [Math]::Min(10, $backendSizes.Count)
    for ($i = 0; $i -lt $topBackend; $i++) {
        $item = $backendSizes[$i]
        Write-Host ("  {0,-30} {1,15}" -f $item.Name, (Format-Size $item.Size))
    }
    Write-Host ""
}

# Frontend subdirectories
$frontendPath = Join-Path $repoRoot "frontend"
if (Test-Path $frontendPath) {
    Write-Host "Frontend subdirectories:"
    Write-Host "----------------------------------------"
    $frontendDirs = Get-ChildItem -Path $frontendPath -Directory -ErrorAction SilentlyContinue
    $frontendSizes = @()
    foreach ($dir in $frontendDirs) {
        $size = Get-DirectorySize $dir.FullName
        if ($size -gt 0) {
            $frontendSizes += @{
                Name = $dir.Name
                Size = $size
            }
        }
    }
    $frontendSizes = $frontendSizes | Sort-Object -Property Size -Descending
    $topFrontend = [Math]::Min(10, $frontendSizes.Count)
    for ($i = 0; $i -lt $topFrontend; $i++) {
        $item = $frontendSizes[$i]
        Write-Host ("  {0,-30} {1,15}" -f $item.Name, (Format-Size $item.Size))
    }
    Write-Host ""
}

# Check for large regenerable items
Write-Host "Large regenerable items (should be ignored):"
Write-Host "----------------------------------------"
$regenerableItems = @(
    @{Path="backend\.venv"; Name="Backend .venv"},
    @{Path="frontend\node_modules"; Name="Frontend node_modules"},
    @{Path="frontend\.next"; Name="Frontend .next"},
    @{Path="backend\output"; Name="Backend output"},
    @{Path="release"; Name="Release folders"}
)

foreach ($item in $regenerableItems) {
    $fullPath = Join-Path $repoRoot $item.Path
    if (Test-Path $fullPath) {
        $size = Get-DirectorySize $fullPath
        if ($size -gt 0) {
            Write-Host ("  {0,-30} {1,15} ⚠️  Should be ignored!" -f $item.Name, (Format-Size $size)) -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "=========================================="

