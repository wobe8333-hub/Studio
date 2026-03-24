# OAuth Client File Setup Script
# Usage: powershell -ExecutionPolicy Bypass -File .\backend\scripts\setup_oauth_client.ps1

$ErrorActionPreference = "Stop"

# 프로젝트 루트 계산
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$CredentialsDir = Join-Path $ProjectRoot "backend" "credentials"
$TargetFile = Join-Path $CredentialsDir "yt_oauth_client.json"

# credentials 디렉토리 생성
if (-not (Test-Path $CredentialsDir)) {
    New-Item -ItemType Directory -Path $CredentialsDir -Force | Out-Null
    Write-Output "Created directory: $CredentialsDir"
}

# 사용자 홈 디렉토리에서 OAuth 파일 찾기
$UserHome = $env:USERPROFILE
$SearchPatterns = @("OAuth.json", "client_secret*.json")
$FoundFiles = @()

foreach ($Pattern in $SearchPatterns) {
    $Files = Get-ChildItem -Path $UserHome -Filter $Pattern -Recurse -ErrorAction SilentlyContinue | 
        Where-Object { $_.PSIsContainer -eq $false } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 10
    
    if ($Files) {
        $FoundFiles += $Files
    }
}

# 가장 최신 파일 선택
if ($FoundFiles.Count -eq 0) {
    Write-Output "FAIL: No OAuth client file found in user home: $UserHome"
    Write-Output "Target file: $TargetFile"
    Write-Output "Test-Path result: False"
    exit 1
}

# 최신 파일 선택 (LastWriteTime 기준)
$LatestFile = $FoundFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1

# 파일 복사
try {
    Copy-Item -Path $LatestFile.FullName -Destination $TargetFile -Force
    Write-Output "Copied: $($LatestFile.FullName) -> $TargetFile"
    
    # 복사 결과 확인
    if (Test-Path $TargetFile) {
        Write-Output "Test-Path result: True"
        exit 0
    } else {
        Write-Output "FAIL: File copy failed"
        Write-Output "Test-Path result: False"
        exit 1
    }
} catch {
    Write-Output "FAIL: Error copying file: $_"
    Write-Output "Source: $($LatestFile.FullName)"
    Write-Output "Target: $TargetFile"
    Write-Output "Test-Path result: False"
    exit 1
}

