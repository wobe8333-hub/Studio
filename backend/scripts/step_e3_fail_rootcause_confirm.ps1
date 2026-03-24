# ==========================================================
# STEP E3 FAIL ROOTCAUSE CONFIRM (PS 5.1 COMPLETE)
# - Confirms why avg_chunks_per_asset < 3.0 with evidence.
# ==========================================================
$ErrorActionPreference="Stop"
$repo=(Get-Location).Path
Write-Host ("REPO=" + $repo) -ForegroundColor Cyan

# 0) cycle id (prefer last_v7_stats.txt → fallback last_cycle_id.txt)
$statsFile = Join-Path $repo "data\knowledge_v1_store\reports\last_v7_stats.txt"
$cid = $null
if(Test-Path $statsFile){
  $m = Select-String -Path $statsFile -Pattern '^Cycle ID\s+(.+)$' -ErrorAction SilentlyContinue
  if($m){ $cid = $m.Matches[0].Groups[1].Value.Trim() }
}
if(-not $cid){
  $cidFile = Join-Path $repo "data\knowledge_v1_store\keyword_discovery\snapshots\last_cycle_id.txt"
  if(Test-Path $cidFile){ $cid=(Get-Content $cidFile -Raw -Encoding UTF8).Trim() }
}
Write-Host ("CYCLE_ID=" + $cid) -ForegroundColor Cyan

# 1) paths
$assets = Join-Path $repo "data\knowledge_v1_store\discovery\raw\assets.jsonl"
$chunks = Join-Path $repo "data\knowledge_v1_store\discovery\derived\chunks.jsonl"
if(!(Test-Path $assets)){ throw "MISSING: $assets" }
if(!(Test-Path $chunks)){ throw "MISSING: $chunks" }
Write-Host ("ASSETS=" + $assets) -ForegroundColor Cyan
Write-Host ("CHUNKS=" + $chunks) -ForegroundColor Cyan

# 2) line counts (ground truth)
Write-Host "`n[1] LINE COUNTS (ground truth)" -ForegroundColor Yellow
$assetsCount = (Get-Content $assets -Encoding UTF8 | Measure-Object -Line).Lines
$chunksCount = (Get-Content $chunks -Encoding UTF8 | Measure-Object -Line).Lines
$avg = [math]::Round(($chunksCount / [double]$assetsCount), 4)
Write-Host ("assets_lines=" + $assetsCount)
Write-Host ("chunks_lines=" + $chunksCount)
Write-Host ("avg_chunks_per_asset=" + $avg)

# 3) parse & distribution on sample(200 assets) without loading full files into memory-heavy structures
Write-Host "`n[2] SAMPLE DISTRIBUTION (200 assets)" -ForegroundColor Yellow
$sampleN = 200
$assetIds = @()
Get-Content $assets -Encoding UTF8 -TotalCount $sampleN | ForEach-Object {
  try { $o = $_ | ConvertFrom-Json } catch { return }
  if($o.asset_id){ $assetIds += [string]$o.asset_id }
}
$assetSet = New-Object 'System.Collections.Generic.HashSet[string]'
$assetIds | ForEach-Object { [void]$assetSet.Add($_) }

# count chunks per sampled asset_id
$counts = @{}
Get-Content $chunks -Encoding UTF8 | ForEach-Object {
  try { $c = $_ | ConvertFrom-Json } catch { return }
  $aid = [string]$c.asset_id
  if($assetSet.Contains($aid)){
    if(-not $counts.ContainsKey($aid)){ $counts[$aid]=0 }
    $counts[$aid] += 1
  }
}

# summarize
$vals = $counts.Values
if($vals.Count -eq 0){
  Write-Host "NO_CHUNKS_MATCHED_SAMPLE_ASSETS (asset_id join mismatch suspected)" -ForegroundColor Red
} else {
  $valsSorted = $vals | Sort-Object
  $min = $valsSorted[0]
  $max = $valsSorted[$valsSorted.Count-1]
  $mean = [math]::Round(($vals | Measure-Object -Average).Average, 4)
  $p50 = $valsSorted[[int]($valsSorted.Count*0.50)]
  $p10 = $valsSorted[[int]($valsSorted.Count*0.10)]
  $p90 = $valsSorted[[int]($valsSorted.Count*0.90)]
  Write-Host ("sample_assets_with_chunks=" + $vals.Count)
  Write-Host ("chunks_per_asset: min=" + $min + " p10=" + $p10 + " p50=" + $p50 + " p90=" + $p90 + " max=" + $max + " mean=" + $mean)

  # show worst 10 (lowest chunks)
  Write-Host "`nLowest 10 assets by chunk count:" -ForegroundColor DarkYellow
  $counts.GetEnumerator() | Sort-Object Value,Name | Select-Object -First 10 | ForEach-Object { "asset_id=" + $_.Key + " chunks=" + $_.Value }
}

# 4) field sparsity hints (first 300 chunks): which fields are empty → chunking filter/threshold suspects
Write-Host "`n[3] CHUNK FIELD SPARSITY (first 300 chunks)" -ForegroundColor Yellow
$N=300
$empty_text=0; $empty_title=0; $empty_source=0; $missing_asset_id=0
Get-Content $chunks -Encoding UTF8 -TotalCount $N | ForEach-Object {
  try { $c = $_ | ConvertFrom-Json } catch { return }
  if(-not $c.asset_id){ $missing_asset_id += 1 }
  if(-not $c.text -or ([string]$c.text).Trim().Length -eq 0){ $empty_text += 1 }
  if(-not $c.title -or ([string]$c.title).Trim().Length -eq 0){ $empty_title += 1 }
  if(-not $c.source -or ([string]$c.source).Trim().Length -eq 0){ $empty_source += 1 }
}
"missing_asset_id=$missing_asset_id / $N"
"empty_text=$empty_text / $N"
"empty_title=$empty_title / $N"
"empty_source=$empty_source / $N"

Write-Host "`nDONE" -ForegroundColor Green
# ==========================================================

