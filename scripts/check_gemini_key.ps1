function Ensure-GeminiApiKey {
    $src = "session"
    $key = $env:GEMINI_API_KEY

    if ([string]::IsNullOrWhiteSpace($key)) {
        $src = "user"
        $key = [System.Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")
    }
    if ([string]::IsNullOrWhiteSpace($key)) {
        $src = "machine"
        $key = [System.Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "Machine")
    }

    if ([string]::IsNullOrWhiteSpace($key)) {
        return [pscustomobject]@{
            ok         = $false
            key_source = $null
            key_len    = 0
        }
    }

    $env:GEMINI_API_KEY = $key
    return [pscustomobject]@{
        ok         = $true
        key_source = $src
        key_len    = $key.Length
    }
}

# 직접 실행될 때만 JSON 출력 + exit
if ($MyInvocation.InvocationName -ne ".") {
    $ErrorActionPreference = "Stop"
    chcp 65001 | Out-Null
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)

    $r = Ensure-GeminiApiKey
    if (-not $r.ok) {
        Write-Host '{"ok":false,"stage":"precheck","reason":"GEMINI_API_KEY missing","exit_code":72}'
        exit 72
    }
    $r | Add-Member -NotePropertyName stage -NotePropertyValue "precheck" -Force
    $r | ConvertTo-Json -Compress | Write-Host
    exit 0
}
