param(
    [string]$RunId,
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectRoot {
    param([string]$ProjectRootInput)

    if (-not [string]::IsNullOrWhiteSpace($ProjectRootInput)) {
        return (Resolve-Path $ProjectRootInput).Path
    }

    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Get-LatestRunId {
    param([string]$RunsRoot)

    if (-not (Test-Path $RunsRoot)) {
        throw "runs root not found: $RunsRoot"
    }

    $dirs = Get-ChildItem -Path $RunsRoot -Directory | Sort-Object LastWriteTime -Descending
    if (-not $dirs -or $dirs.Count -eq 0) {
        throw "no run directories found under: $RunsRoot"
    }

    return $dirs[0].Name
}

function Assert-PathExists {
    param(
        [string]$PathToCheck,
        [string]$Label
    )

    if (-not (Test-Path $PathToCheck)) {
        Write-Host "[FAIL] $Label missing: $PathToCheck"
        exit 4
    }

    Write-Host "[OK] $Label exists: $PathToCheck"
}

function Assert-FileCountAtLeast {
    param(
        [string]$DirPath,
        [string]$Filter,
        [int]$MinCount,
        [string]$Label
    )

    if (-not (Test-Path $DirPath)) {
        Write-Host "[FAIL] $Label dir missing: $DirPath"
        exit 4
    }

    $count = (Get-ChildItem -Path $DirPath -File -Filter $Filter -ErrorAction SilentlyContinue).Count

    if ($count -lt $MinCount) {
        Write-Host "[FAIL] $Label count too small: dir=$DirPath filter=$Filter count=$count min=$MinCount"
        exit 4
    }

    Write-Host "[OK] $Label count=$count"
}

try {
    $resolvedProjectRoot = Resolve-ProjectRoot -ProjectRootInput $ProjectRoot
    Write-Host "[INFO] Project root: $resolvedProjectRoot"

    $runsRoot = Join-Path $resolvedProjectRoot "backend\output\runs"

    if ([string]::IsNullOrWhiteSpace($RunId)) {
        $RunId = Get-LatestRunId -RunsRoot $runsRoot
        Write-Host "[INFO] RunId not provided. Using latest run: $RunId"
    }
    else {
        Write-Host "[INFO] Using RunId: $RunId"
    }

    $runRoot = Join-Path $runsRoot $RunId
    $v8Root = Join-Path $runRoot "v8"
    $imagesRoot = Join-Path $v8Root "images"
    $assetsDir = Join-Path $imagesRoot "assets_ai"
    $rawDir = Join-Path $imagesRoot "response_raw"

    # 1) run root / v8 root
    Assert-PathExists -PathToCheck $runRoot -Label "run root"
    Assert-PathExists -PathToCheck $v8Root -Label "v8 root"

    # 2) 핵심 산출물 파일
    Assert-PathExists -PathToCheck (Join-Path $v8Root "script.json") -Label "script.json"
    Assert-PathExists -PathToCheck (Join-Path $v8Root "title.json") -Label "title.json"
    Assert-PathExists -PathToCheck (Join-Path $v8Root "description.txt") -Label "description.txt"
    Assert-PathExists -PathToCheck (Join-Path $v8Root "tags.json") -Label "tags.json"

    # 2b) V7.5 style_policy.json
    $stylePolicyPath = Join-Path $v8Root "style_policy.json"
    Assert-PathExists -PathToCheck $stylePolicyPath -Label "style_policy.json"
    try {
        $stylePolicy = Get-Content $stylePolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $requiredKeys = @("style_policy_version", "channel_style_id", "image_style_id", "thumbnail_style_id", "prompt_system_id", "registry_hashes", "policy_fingerprint")
        $names = @($stylePolicy.PSObject.Properties.Name)
        foreach ($k in $requiredKeys) {
            if ($names -notcontains $k) {
                Write-Host "[FAIL] style_policy.json schema invalid: missing key $k"
                exit 4
            }
        }
        if (-not $stylePolicy.registry_hashes) {
            Write-Host "[FAIL] style_policy.json schema invalid: registry_hashes empty"
            exit 4
        }
        Write-Host "[OK] style_policy schema valid"
    } catch {
        Write-Host "[FAIL] style_policy.json schema valid: $($_.Exception.Message)"
        exit 4
    }

    # 3) Gemini 이미지 검증
    Assert-PathExists -PathToCheck $assetsDir -Label "assets_ai dir"
    Assert-PathExists -PathToCheck $rawDir -Label "response_raw dir"

    Assert-FileCountAtLeast -DirPath $assetsDir -Filter "*.png" -MinCount 1 -Label "assets_ai png"
    Assert-FileCountAtLeast -DirPath $rawDir -Filter "*.json" -MinCount 1 -Label "response_raw json"

    # 4) 선택 산출물 (있으면 확인)
    $videoPath = Join-Path $v8Root "video.mp4"
    $thumbPath = Join-Path $v8Root "thumbnail.png"

    if (Test-Path $videoPath) {
        Write-Host "[OK] video.mp4 exists: $videoPath"
    }
    else {
        Write-Host "[WARN] video.mp4 missing: $videoPath"
    }

    if (Test-Path $thumbPath) {
        Write-Host "[OK] thumbnail.png exists: $thumbPath"
    }
    else {
        Write-Host "[WARN] thumbnail.png missing: $thumbPath"
    }

    # 5) V8.5 variants (title/thumbnail variants)
    $variantsDir = Join-Path $v8Root "variants"
    $titleVariantsPath = Join-Path $variantsDir "title_variants.json"
    $manifestPath = Join-Path $variantsDir "variant_manifest.json"
    $thumbV1 = Join-Path $variantsDir "thumbnail_variant_01.png"
    $thumbV2 = Join-Path $variantsDir "thumbnail_variant_02.png"
    $thumbV3 = Join-Path $variantsDir "thumbnail_variant_03.png"

    Assert-PathExists -PathToCheck $variantsDir -Label "variants dir"
    Assert-PathExists -PathToCheck $titleVariantsPath -Label "title_variants.json"
    Assert-PathExists -PathToCheck $manifestPath -Label "variant_manifest.json"
    Assert-PathExists -PathToCheck $thumbV1 -Label "thumbnail_variant_01.png"
    Assert-PathExists -PathToCheck $thumbV2 -Label "thumbnail_variant_02.png"
    Assert-PathExists -PathToCheck $thumbV3 -Label "thumbnail_variant_03.png"

    try {
        $tv = Get-Content $titleVariantsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($tv.title_variant_count -ne 3) {
            Write-Host "[FAIL] title_variants.json invalid title_variant_count=$($tv.title_variant_count) expected=3"
            exit 4
        }
        if ($tv.thumbnail_variant_count -ne 3) {
            Write-Host "[FAIL] title_variants.json invalid thumbnail_variant_count=$($tv.thumbnail_variant_count) expected=3"
            exit 4
        }
    } catch {
        Write-Host "[FAIL] title_variants.json parse error: $($_.Exception.Message)"
        exit 4
    }

    # 5b) variant_manifest.json 기본 필드 검증 (V8.5 SSOT)
    try {
        $vm = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $vmNames = @($vm.PSObject.Properties.Name)
        foreach ($k in @("title_variants_path", "thumbnail_variants", "title_variant_count", "thumbnail_variant_count")) {
            if ($vmNames -notcontains $k) {
                Write-Host "[FAIL] variant_manifest.json missing key: $k"
                exit 4
            }
        }
        if ($vm.title_variant_count -ne 3) {
            Write-Host "[FAIL] variant_manifest.json invalid title_variant_count=$($vm.title_variant_count) expected=3"
            exit 4
        }
        if ($vm.thumbnail_variant_count -ne 3) {
            Write-Host "[FAIL] variant_manifest.json invalid thumbnail_variant_count=$($vm.thumbnail_variant_count) expected=3"
            exit 4
        }
        if (-not $vm.thumbnail_variants) {
            Write-Host "[FAIL] variant_manifest.json thumbnail_variants empty"
            exit 4
        }
    } catch {
        Write-Host "[FAIL] variant_manifest.json parse error: $($_.Exception.Message)"
        exit 4
    }

    # 5c) render_report의 V8.5 필드는 optional (있으면 기록, 없어도 FAIL 아님)
    $renderReportPath = Join-Path $v8Root "render_report.json"
    if (Test-Path $renderReportPath) {
        try {
            $rr = Get-Content $renderReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $rrNames = @($rr.PSObject.Properties.Name)
            $hasV85Enabled = $rrNames -contains "v85_enabled"
            $hasTitleVariantCount = $rrNames -contains "title_variant_count"
            $hasThumbVariantCount = $rrNames -contains "thumbnail_variant_count"
            Write-Host "[INFO] render_report optional_v85_fields | v85_enabled=$hasV85Enabled | title_variant_count=$hasTitleVariantCount | thumbnail_variant_count=$hasThumbVariantCount"
        } catch {
            Write-Host "[WARN] render_report optional_v85_fields unreadable: $($_.Exception.Message)"
        }
    }

    Write-Host "[OK] V8.5 variants exist and schema valid (SSOT=variants)"

    Write-Host "[PASS] V7.5 verification passed"
    Write-Host "[PASS] V8 verification passed"
    exit 0
}
catch {
    Write-Host "[ERROR] V8 verification exception: $($_.Exception.Message)"
    exit 99
}

