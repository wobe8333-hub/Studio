param(
    [string]$Root = "."
)

$ErrorActionPreference = "Stop"

function Parse-ScriptFile {
    param([string]$Path)
    $tokens = $null
    $errors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors)
    $errList = @()
    foreach ($err in $errors) {
        $msg = $err.Message
        $etype = "GenericParseError"
        if ($msg -match "Try statement is missing its Catch or Finally block") { $etype = "OrphanTry" }
        elseif ($msg -match "Unexpected token '\}'") { $etype = "BraceMismatchOrOrphanCatch" }
        elseif ($msg -match "Unexpected token 'catch'") { $etype = "OrphanCatch" }
        elseif ($msg -match "Missing closing '\}'") { $etype = "MissingClosingBrace" }
        $errList += [pscustomobject]@{ Message = $msg; Line = $err.Extent.StartLineNumber; ErrorType = $etype }
    }
    return [pscustomobject]@{ ParseOk = ($errors.Count -eq 0); ErrorCount = $errors.Count; Errors = $errList }
}

function Backup-FilePreserveTree {
    param([string]$RootPath, [string]$FullFilePath, [string]$BackupRoot)
    $rel = $FullFilePath.Substring($RootPath.Length).TrimStart('\')
    $destDir = Join-Path $BackupRoot (Split-Path $rel -Parent)
    $destFile = Join-Path $BackupRoot $rel
    if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    Copy-Item -LiteralPath $FullFilePath -Destination $destFile -Force
    return $destFile
}

function Try-FixExtraBraceBeforeCatch {
    param([string]$Path, [int]$OriginalErrorCount, [string]$RootPath, [string]$BackupPath)
    $lines = [System.Collections.ArrayList]@(Get-Content -LiteralPath $Path -Encoding UTF8 -ErrorAction Stop)
    $catchLineIndex = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if (($lines[$i].Trim() -eq "} catch {") -or ($lines[$i].Trim() -eq "} catch{")) {
            $catchLineIndex = $i
            break
        }
    }
    if ($catchLineIndex -lt 0) { return $null }
    $lookBack = [Math]::Min(15, $catchLineIndex)
    for ($j = $catchLineIndex - 1; $j -ge ($catchLineIndex - $lookBack) -and $j -ge 0; $j--) {
        if ($lines[$j].Trim() -eq "}") {
            $newLines = New-Object System.Collections.ArrayList
            for ($k = 0; $k -lt $lines.Count; $k++) {
                if ($k -ne $j) { [void]$newLines.Add($lines[$k]) }
            }
            $tempPath = [System.IO.Path]::GetTempFileName()
            $newLines -join "`r`n" | Out-File -FilePath $tempPath -Encoding utf8
            $after = Parse-ScriptFile -Path $tempPath
            Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
            if ($after.ErrorCount -lt $OriginalErrorCount -or $after.ParseOk) {
                $newLines -join "`r`n" | Set-Content -LiteralPath $Path -Encoding utf8
                return [pscustomobject]@{ Applied = $true; Action = "RemoveExtraBraceBeforeCatch"; LineRemoved = $j + 1 }
            }
        }
    }
    return $null
}

function Try-FixMissingClosingBrace {
    param([string]$Path, [int]$OriginalErrorCount)
    $content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    $newContent = $content.TrimEnd() + "`r`n}"
    $tempPath = [System.IO.Path]::GetTempFileName()
    $newContent | Out-File -FilePath $tempPath -Encoding utf8
    $after = Parse-ScriptFile -Path $tempPath
    Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
    if ($after.ErrorCount -lt $OriginalErrorCount -or $after.ParseOk) {
        $newContent | Set-Content -LiteralPath $Path -Encoding utf8
        return [pscustomobject]@{ Applied = $true; Action = "AddClosingBraceAtEOF" }
    }
    return $null
}

function Try-FixOrphanTryExtraBrace {
    param([string]$Path, [int]$OriginalErrorCount, [object]$ParseResult)
    $errTry = $ParseResult.Errors | Where-Object { $_.ErrorType -eq "OrphanTry" } | Select-Object -First 1
    if (-not $errTry) { return $null }
    $lineNum = $errTry.Line
    $lines = Get-Content -LiteralPath $Path -Encoding UTF8
    $start = [Math]::Max(0, $lineNum - 1)
    $end = [Math]::Min($lines.Count - 1, $lineNum + 18)
    $catchIdx = -1
    for ($i = $start; $i -le $end; $i++) {
        if ($lines[$i].Trim() -match "catch\s*\{") { $catchIdx = $i; break }
    }
    if ($catchIdx -lt 0) { return $null }
    for ($j = $catchIdx - 1; $j -ge $start -and $j -ge 0; $j--) {
        if ($lines[$j].Trim() -eq "}") {
            $newLines = New-Object System.Collections.ArrayList
            for ($k = 0; $k -lt $lines.Count; $k++) {
                if ($k -ne $j) { [void]$newLines.Add($lines[$k]) }
            }
            $tempPath = [System.IO.Path]::GetTempFileName()
            $newLines -join "`r`n" | Out-File -FilePath $tempPath -Encoding utf8
            $after = Parse-ScriptFile -Path $tempPath
            Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
            if ($after.ErrorCount -lt $OriginalErrorCount -or $after.ParseOk) {
                $newLines -join "`r`n" | Set-Content -LiteralPath $Path -Encoding utf8
                return [pscustomobject]@{ Applied = $true; Action = "RemoveOrphanTryExtraBrace"; LineRemoved = $j + 1 }
            }
        }
    }
    return $null
}

function Try-FixOrphanCatch {
    param([string]$Path, [int]$OriginalErrorCount)
    $lines = Get-Content -LiteralPath $Path -Encoding UTF8
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $trimmed = $lines[$i].Trim()
        if (($trimmed -eq "catch {") -or ($trimmed -eq "} catch {")) {
            $from = [Math]::Max(0, $i - 50)
            $hasTry = $false
            for ($k = $from; $k -lt $i; $k++) {
                if ($lines[$k] -match "try\s*\{") { $hasTry = $true; break }
            }
            if (-not $hasTry) {
                $newLines = New-Object System.Collections.ArrayList
                for ($k = 0; $k -lt $lines.Count; $k++) {
                    if ($k -ne $i) { [void]$newLines.Add($lines[$k]) }
                }
                $tempPath = [System.IO.Path]::GetTempFileName()
                $newLines -join "`r`n" | Out-File -FilePath $tempPath -Encoding utf8
                $after = Parse-ScriptFile -Path $tempPath
                Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
                if ($after.ErrorCount -lt $OriginalErrorCount -or $after.ParseOk) {
                    $newLines -join "`r`n" | Set-Content -LiteralPath $Path -Encoding utf8
                    return [pscustomobject]@{ Applied = $true; Action = "RemoveOrphanCatchLine"; LineRemoved = $i + 1 }
                }
            }
        }
    }
    return $null
}

function Write-RepairReport {
    param([array]$RepairLogs, [string]$ReportDir, [string]$Timestamp)
    $jsonPath = Join-Path $ReportDir ("ps_parser_repair_{0}.json" -f $Timestamp)
    $txtPath = Join-Path $ReportDir ("ps_parser_repair_{0}.txt" -f $Timestamp)
    $RepairLogs | ConvertTo-Json -Depth 6 | Out-File -FilePath $jsonPath -Encoding utf8
    $txtLines = @("PowerShell Parser Auto Repair Report", "Timestamp: $Timestamp", "")
    foreach ($log in $RepairLogs) {
        $txtLines += "[FILE] $($log.file)"
        $txtLines += "  original_error_count: $($log.original_error_count)"
        $txtLines += "  final_error_count: $($log.final_error_count)"
        $txtLines += "  backup_path: $($log.backup_path)"
        $txtLines += "  actions_applied: $($log.actions_applied -join ', ')"
        $txtLines += "  changed_lines: $($log.changed_lines -join ', ')"
        $txtLines += ""
    }
    $txtLines | Out-File -FilePath $txtPath -Encoding utf8
    Write-Host "[INFO] Repair report: $jsonPath"
    Write-Host "[INFO] Repair report: $txtPath"
}

try {
    $resolvedRoot = (Resolve-Path $Root).Path
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupRoot = Join-Path $resolvedRoot "artifacts\ps_parser_backup\$timestamp"
    $reportDir = Join-Path $resolvedRoot "artifacts\ps_parser_repair"
    if (!(Test-Path $reportDir)) { New-Item -ItemType Directory -Path $reportDir -Force | Out-Null }

    $files = Get-ChildItem -Path $resolvedRoot -Recurse -File -Filter *.ps1 |
        Where-Object {
            $_.FullName -notmatch '\\\.venv\\' -and
            $_.FullName -notmatch '\\node_modules\\' -and
            $_.FullName -notmatch '\\dist\\' -and
            $_.FullName -notmatch '\\build\\' -and
            $_.FullName -notmatch '\\artifacts\\'
        } |
        Sort-Object FullName

    $repairLogs = @()
    $anyFixed = $false

    foreach ($file in $files) {
        $path = $file.FullName
        $parseResult = Parse-ScriptFile -Path $path
        if ($parseResult.ParseOk) { continue }

        $origCount = $parseResult.ErrorCount
        $backupPath = Backup-FilePreserveTree -RootPath $resolvedRoot -FullFilePath $path -BackupRoot $backupRoot
        $actions = @()
        $changedLines = @()
        $currentPath = $path
        $currentCount = $origCount

        $fix = Try-FixExtraBraceBeforeCatch -Path $currentPath -OriginalErrorCount $currentCount -RootPath $resolvedRoot -BackupPath $backupPath
        if ($fix) {
            $actions += $fix.Action
            if ($fix.LineRemoved) { $changedLines += $fix.LineRemoved }
            $parseResult = Parse-ScriptFile -Path $currentPath
            $currentCount = $parseResult.ErrorCount
            $anyFixed = $true
            $repairLogs += [pscustomobject]@{ file = $path; original_error_count = $origCount; final_error_count = $currentCount; actions_applied = $actions; changed_lines = $changedLines; backup_path = $backupPath }
            Write-Host "[FIX] $path (errors $origCount -> $currentCount)"
            continue
        }
        Copy-Item -LiteralPath $backupPath -Destination $currentPath -Force

        $parseResult = Parse-ScriptFile -Path $currentPath
        $currentCount = $parseResult.ErrorCount
        $fix = Try-FixOrphanTryExtraBrace -Path $currentPath -OriginalErrorCount $currentCount -ParseResult $parseResult
        if ($fix) {
            $actions += $fix.Action
            if ($fix.LineRemoved) { $changedLines += $fix.LineRemoved }
            $parseResult = Parse-ScriptFile -Path $currentPath
            $currentCount = $parseResult.ErrorCount
            $anyFixed = $true
            $repairLogs += [pscustomobject]@{ file = $path; original_error_count = $origCount; final_error_count = $currentCount; actions_applied = $actions; changed_lines = $changedLines; backup_path = $backupPath }
            Write-Host "[FIX] $path (errors $origCount -> $currentCount)"
            continue
        }
        Copy-Item -LiteralPath $backupPath -Destination $currentPath -Force

        $parseResult = Parse-ScriptFile -Path $currentPath
        $currentCount = $parseResult.ErrorCount
        $fix = Try-FixMissingClosingBrace -Path $currentPath -OriginalErrorCount $currentCount
        if ($fix) {
            $actions += $fix.Action
            $anyFixed = $true
            $parseResult = Parse-ScriptFile -Path $currentPath
            $currentCount = $parseResult.ErrorCount
            $repairLogs += [pscustomobject]@{ file = $path; original_error_count = $origCount; final_error_count = $currentCount; actions_applied = $actions; changed_lines = @(); backup_path = $backupPath }
            Write-Host "[FIX] $path (errors $origCount -> $currentCount)"
            continue
        }
        Copy-Item -LiteralPath $backupPath -Destination $currentPath -Force

        $parseResult = Parse-ScriptFile -Path $currentPath
        $currentCount = $parseResult.ErrorCount
        $fix = Try-FixOrphanCatch -Path $currentPath -OriginalErrorCount $currentCount
        if ($fix) {
            $actions += $fix.Action
            if ($fix.LineRemoved) { $changedLines += $fix.LineRemoved }
            $anyFixed = $true
            $parseResult = Parse-ScriptFile -Path $currentPath
            $currentCount = $parseResult.ErrorCount
            $repairLogs += [pscustomobject]@{ file = $path; original_error_count = $origCount; final_error_count = $currentCount; actions_applied = $actions; changed_lines = $changedLines; backup_path = $backupPath }
            Write-Host "[FIX] $path (errors $origCount -> $currentCount)"
        }
        else {
            $repairLogs += [pscustomobject]@{ file = $path; original_error_count = $origCount; final_error_count = $origCount; actions_applied = @(); changed_lines = @(); backup_path = $backupPath }
        }
    }

    if ($repairLogs.Count -gt 0) {
        Write-RepairReport -RepairLogs $repairLogs -ReportDir $reportDir -Timestamp $timestamp
    }

    Write-Host "[OK] Auto repair completed (any fixed: $anyFixed)"
    exit 0
}
catch {
    Write-Host "[ERROR] Auto repair failed: $_"
    exit 2
}
