param(
    [string]$Root = ".",
    [switch]$FailOnError = $true,
    [int]$ContextRadius = 3
)

$ErrorActionPreference = "Stop"

function Write-Section($text) {
    Write-Host ""
    Write-Host ("=" * 80)
    Write-Host $text
    Write-Host ("=" * 80)
}

function Get-ContextLines {
    param(
        [string[]]$Lines,
        [int]$LineNumber,
        [int]$Radius
    )

    $start = [Math]::Max(1, $LineNumber - $Radius)
    $end   = [Math]::Min($Lines.Count, $LineNumber + $Radius)

    $out = @()
    for ($i = $start; $i -le $end; $i++) {
        $prefix = if ($i -eq $LineNumber) { ">>" } else { "  " }
        $out += ("{0} {1,4}: {2}" -f $prefix, $i, $Lines[$i - 1])
    }
    return $out
}

function Test-PowerShellScriptParse {
    param(
        [string]$Path,
        [int]$ContextRadius = 3
    )

    $tokens = $null
    $errors = $null

    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref]$tokens,
        [ref]$errors
    )

    $allLines = Get-Content -LiteralPath $Path -ErrorAction Stop
    $normalizedErrors = @()

    foreach ($err in $errors) {
        $line = $err.Extent.StartLineNumber
        $col  = $err.Extent.StartColumnNumber
        $txt  = $err.Extent.Text
        $msg  = $err.Message

        $etype = "GenericParseError"
        if ($msg -match "Try statement is missing its Catch or Finally block") {
            $etype = "OrphanTry"
        }
        elseif ($msg -match "Unexpected token '\}'") {
            $etype = "BraceMismatchOrOrphanCatch"
        }
        elseif ($msg -match "Unexpected token 'catch'") {
            $etype = "OrphanCatch"
        }
        elseif ($msg -match "Missing closing '\}'") {
            $etype = "MissingClosingBrace"
        }

        $ctx = @()
        if ($line -gt 0) {
            $ctx = Get-ContextLines -Lines $allLines -LineNumber $line -Radius $ContextRadius
        }

        $normalizedErrors += [pscustomobject]@{
            Message   = $msg
            Line      = $line
            Column    = $col
            Text      = $txt
            Context   = $ctx
            ErrorType = $etype
        }
    }

    return [pscustomobject]@{
        Path        = $Path
        ParseOk     = ($errors.Count -eq 0)
        ErrorCount  = $errors.Count
        Errors      = $normalizedErrors
    }
}

Write-Section "PowerShell Parser Audit Start"

$resolvedRoot = Resolve-Path $Root
Write-Host "[ROOT] $resolvedRoot"

$ParserAuditExcludedFiles = @(
    "smoke_runs.ps1",
    "v7_build_channels_global.ps1",
    "test_step2.ps1",
    "verify_step2.ps1",
    "rootcause_stepE.ps1",
    "run_stepF_no_documents_rootcause.ps1"
)

Write-Host "[INFO] Parser audit excluded files:"
$ParserAuditExcludedFiles | ForEach-Object {
    Write-Host ("  - {0}" -f $_)
}

$files = Get-ChildItem -Path $resolvedRoot -Recurse -File -Filter *.ps1 |
Where-Object {
    $_.FullName -notmatch '\\\.venv\\' -and
    $_.FullName -notmatch '\\node_modules\\' -and
    $_.FullName -notmatch '\\dist\\' -and
    $_.FullName -notmatch '\\build\\' -and
    $_.FullName -notmatch '\\artifacts\\' -and
    $ParserAuditExcludedFiles -notcontains $_.Name
} |
Sort-Object FullName

Write-Host "[INFO] .ps1 file count = $($files.Count)"

$results = @()
foreach ($file in $files) {
    $result = Test-PowerShellScriptParse -Path $file.FullName -ContextRadius $ContextRadius
    $results += $result

    if ($result.ParseOk) {
        Write-Host ("[OK] {0}" -f $file.FullName)
    }
    else {
        Write-Host ("[FAIL] {0} (errors={1})" -f $file.FullName, $result.ErrorCount)
    }
}

$failed = @($results | Where-Object { -not $_.ParseOk })

Write-Section "Summary"
Write-Host ("[TOTAL] {0}" -f $results.Count)
Write-Host ("[PASS]  {0}" -f (($results | Where-Object { $_.ParseOk }).Count))
Write-Host ("[FAIL]  {0}" -f $failed.Count)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = Join-Path $resolvedRoot "artifacts\ps_parser_audit"
if (!(Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

$jsonPath = Join-Path $outDir ("ps_parser_audit_{0}.json" -f $timestamp)
$txtPath  = Join-Path $outDir ("ps_parser_audit_{0}.txt" -f $timestamp)

$results | ConvertTo-Json -Depth 8 | Out-File -FilePath $jsonPath -Encoding utf8

@(
    "PowerShell Parser Audit"
    "Root: $resolvedRoot"
    "Timestamp: $timestamp"
    "Total: $($results.Count)"
    "Pass:  $(($results | Where-Object { $_.ParseOk }).Count)"
    "Fail:  $($failed.Count)"
    ""
) + (
    $failed | ForEach-Object {
        "[FILE] $($_.Path)"
        foreach ($err in $_.Errors) {
            "  [TYPE]   $($err.ErrorType)"
            "  [LINE]   $($err.Line)"
            "  [COLUMN] $($err.Column)"
            "  [TEXT]   $($err.Text)"
            "  [MSG]    $($err.Message)"
            if ($err.Context.Count -gt 0) {
                "  [CONTEXT]"
                $err.Context | ForEach-Object { "    $_" }
            }
            ""
        }
    }
) | Out-File -FilePath $txtPath -Encoding utf8

Write-Host "[INFO] JSON report saved: $jsonPath"
Write-Host "[INFO] TXT  report saved: $txtPath"

if ($FailOnError -and $failed.Count -gt 0) {
    Write-Host "[FAIL] PowerShell parser errors detected"
    exit 1
}

Write-Host "[OK] PowerShell parser audit passed"
exit 0
