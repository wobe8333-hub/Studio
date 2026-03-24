# PowerShell UTF-8 인코딩 강제 스크립트
# 사용법: .\ps_utf8.ps1 또는 이 스크립트를 실행한 후 Python 스크립트 실행

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PowerShell UTF-8 인코딩 설정" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 코드 페이지를 UTF-8 (65001)로 변경
chcp 65001 | Out-Null

# 콘솔 출력 인코딩을 UTF-8로 설정
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

# PowerShell 인코딩 설정
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

Write-Host "✓ 코드 페이지: UTF-8 (65001)" -ForegroundColor Green
Write-Host "✓ 콘솔 출력 인코딩: UTF-8" -ForegroundColor Green
Write-Host "✓ PowerShell 인코딩: UTF-8" -ForegroundColor Green
Write-Host ""
Write-Host "이제 Python 스크립트를 실행하면 한글이 정상적으로 표시됩니다." -ForegroundColor Yellow
Write-Host ""
