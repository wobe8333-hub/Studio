if (-not (Test-Path "requirements.lock.txt")) { exit 90 }

if (-not (Test-Path ".\.venv")) { exit 91 }

.\.venv\Scripts\python.exe -c "import feedparser" 2>$null
if ($LASTEXITCODE -ne 0) { exit 92 }

$res = schtasks /Query /TN AIAnimationStudio_V7_Daily_10AM /V /FO LIST |
  findstr /I "Last Result"
if ($res -notmatch "0") { exit 93 }

exit 0

