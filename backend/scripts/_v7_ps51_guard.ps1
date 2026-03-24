Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

function Set-V7SslCert {
  $env:SSL_CERT_FILE = (& python -X utf8 -c "import certifi; print(certifi.where())")
  Write-Host ("SSL_CERT_FILE=" + $env:SSL_CERT_FILE)
}

function Assert-PS51ParserSafe {
  param(
    [Parameter(Mandatory=$true)][string]$Path
  )
  if (!(Test-Path -LiteralPath $Path)) { throw ("MISSING_PS1: " + $Path) }
  $lines = Get-Content -LiteralPath $Path -Encoding UTF8
  $bad = New-Object System.Collections.Generic.List[string]

  # 위험 패턴(일반화): double-quote 내부에서 $var: (콜론) 형태는 PS5.1에서 드라이브/스코프 변수로 오해될 수 있음
  # 예: "$cycleId:" "$x:" "$env:FOO:"(의도인 env 제외) 등
  for ($i=0; $i -lt $lines.Count; $i++) {
    $ln = $lines[$i]
    if ($ln -match '^\s*#') { continue }
    # env: 는 의도적 스코프일 수 있으니 제외. 그 외 $[A-Za-z_]\w*: 는 차단
    if ($ln -match '"[^"]*(?<!\\)\$(?!env:)[A-Za-z_]\w*:' ) {
      $bad.Add(("{0}:{1} {2}" -f $Path, ($i+1), $ln.Trim()))
    }
  }
  if ($bad.Count -gt 0) {
    Write-Host "PS51_PARSER_RISK_LINES =====" -ForegroundColor Red
    $bad | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    throw "PS51_PARSER_RISK: found `$var: inside double-quotes. Use `${var}: or string concatenation or single-quotes."
  }
}

function Invoke-PythonLogged {
  param(
    [Parameter(Mandatory=$true)][string]$RepoRoot,
    [Parameter(Mandatory=$true)][string[]]$Args,
    [Parameter(Mandatory=$true)][string]$OutFile,
    [Parameter(Mandatory=$true)][string]$ErrFile,
    [Parameter(Mandatory=$true)][string]$TbFile,
    [int]$HeartbeatSec = 15,
    [int]$MaxSec = 7200,
    [string]$AssetsPath = "",
    [string]$ChunksPath = ""
  )

  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutFile) | Out-Null

  ("ARGS=" + ($Args -join " ")) | Out-File -FilePath $OutFile -Encoding utf8 -Append
  ("START_UTC=" + (Get-Date).ToUniversalTime().ToString("o")) | Out-File -FilePath $OutFile -Encoding utf8 -Append

  # TB는 stderr를 별도 tee하지 못하므로, python 실행 실패 시 caller가 try/catch로 traceback을 TbFile에 남기게 설계(PS1에서 보완)
  $p = Start-Process -FilePath "python" -ArgumentList $Args -WorkingDirectory $RepoRoot -NoNewWindow -PassThru `
        -RedirectStandardOutput $OutFile -RedirectStandardError $ErrFile

  $prevOut = (Get-Item $OutFile -ErrorAction SilentlyContinue).Length
  $prevErr = (Get-Item $ErrFile -ErrorAction SilentlyContinue).Length
  $prevA   = if ($AssetsPath -and (Test-Path -LiteralPath $AssetsPath)) { (Get-Item $AssetsPath).Length } else { -1 }
  $prevC   = if ($ChunksPath -and (Test-Path -LiteralPath $ChunksPath)) { (Get-Item $ChunksPath).Length } else { -1 }
  $elapsed = 0
  $stall   = 0

  while (-not $p.HasExited) {
    Start-Sleep -Seconds $HeartbeatSec
    $elapsed += $HeartbeatSec

    $outLen = (Get-Item $OutFile -ErrorAction SilentlyContinue).Length
    $errLen = (Get-Item $ErrFile -ErrorAction SilentlyContinue).Length
    $aLen   = if ($AssetsPath -and (Test-Path -LiteralPath $AssetsPath)) { (Get-Item $AssetsPath).Length } else { -1 }
    $cLen   = if ($ChunksPath -and (Test-Path -LiteralPath $ChunksPath)) { (Get-Item $ChunksPath).Length } else { -1 }

    $dOut = $outLen - $prevOut
    $dErr = $errLen - $prevErr
    $dA   = $aLen - $prevA
    $dC   = $cLen - $prevC

    $progress = ($dOut -ne 0) -or ($dErr -ne 0) -or ($dA -ne 0) -or ($dC -ne 0)
    if ($progress) { $stall = 0 } else { $stall += $HeartbeatSec }

    Write-Host ("[HB] elapsed=" + $elapsed + " pid=" + $p.Id +
                " outΔ=" + $dOut + " errΔ=" + $dErr +
                " assetsΔ=" + $dA + " chunksΔ=" + $dC +
                " stall_sec=" + $stall) -ForegroundColor DarkGray

    if (Test-Path -LiteralPath $TbFile) {
      $tbLen = (Get-Item $TbFile -ErrorAction SilentlyContinue).Length
      if ($tbLen -gt 0) {
        Write-Host ("[HB] TB_DETECTED len=" + $tbLen) -ForegroundColor Yellow
        Get-Content -LiteralPath $TbFile -Encoding UTF8 -Tail 30 -ErrorAction SilentlyContinue
      }
    }

    if ($stall -ge 300) {
      Write-Host "[WARN] 300s no evidence growth (still running or stuck). See OUT/ERR/TB." -ForegroundColor Yellow
    }

    if ($elapsed -ge $MaxSec) {
      Write-Host ("[FATAL] MaxSec exceeded => kill pid=" + $p.Id) -ForegroundColor Red
      try { $p.Kill() } catch {}
      break
    }

    $prevOut = $outLen; $prevErr = $errLen; $prevA = $aLen; $prevC = $cLen
  }

  return $p.ExitCode
}


