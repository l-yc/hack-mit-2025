Param(
    [Parameter(Mandatory=$true)] [string]$Directory,
    [Parameter(Mandatory=$true)] [string]$MusicPath,
    [int]$MaxFiles = 20,
    [double]$TargetDurationSec = 30,
    [double]$MinDurationSec = 28,
    [double]$MaxDurationSec = 36,
    [double]$PerSegmentSec = 3.0,
    [string]$Server = 'http://localhost:6741'
)

Write-Host "Directory:" $Directory
Write-Host "MusicPath:" $MusicPath

if (-not (Test-Path $Directory)) { Write-Error "Directory not found: $Directory"; exit 1 }
$mp4Count = (Get-ChildItem $Directory -Filter *.mp4 -File | Measure-Object).Count
if ($mp4Count -lt 2) { Write-Error "Need at least 2 .mp4 files in $Directory (found $mp4Count)"; exit 1 }
if (-not (Test-Path $MusicPath)) { Write-Error "Music file not found: $MusicPath"; exit 1 }

# Build request body
$body = @{
  directory = $Directory
  mode = 'montage'
  target_duration_sec = $TargetDurationSec
  min_duration_sec = $MinDurationSec
  max_duration_sec = $MaxDurationSec
  per_segment_sec = $PerSegmentSec
  max_files = $MaxFiles
  aspect = '9:16'
  music_url = $MusicPath
  music_only = $true
  end_with_low = $true
}

$json = $body | ConvertTo-Json -Depth 6
Write-Host "Posting job to $Server ..." -ForegroundColor Cyan
Write-Host $json

try {
  $resp = Invoke-RestMethod -Uri ("{0}/api/reels/jobs" -f $Server) -Method Post -ContentType 'application/json' -Body $json
} catch {
  Write-Error "Create job failed: $($_.Exception.Message)"
  exit 1
}

if (-not $resp -or -not $resp.job_id) { Write-Error "Invalid response from server"; exit 1 }
$jobId = $resp.job_id
Write-Host "Job ID:" $jobId -ForegroundColor Green

# Poll
for ($i=0; $i -lt 600; $i++) {
  try {
    $st = Invoke-RestMethod -Uri ("{0}/api/reels/jobs/{1}" -f $Server, $jobId) -Method Get
  } catch {
    Write-Warning "Poll error: $($_.Exception.Message)"
    Start-Sleep -Seconds 1
    continue
  }

  Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $st.status)
  if ($st.status -eq 'completed' -or $st.status -eq 'failed') { break }
  Start-Sleep -Seconds 1
}

if ($st.status -eq 'completed') {
  $url = ("{0}{1}" -f $Server, $st.artifacts.best_reel_mp4)
  Write-Host "Completed: $url" -ForegroundColor Green
  try { Start-Process $url } catch { }
  exit 0
}

Write-Warning "Job ended with status: $($st.status)"
if ($st.status -eq 'failed') {
  $jobPath = Join-Path (Join-Path (Resolve-Path '.').Path 'uploads') (Join-Path 'reels' (Join-Path $jobId 'job.json'))
  if (Test-Path $jobPath) {
    Write-Host "--- uploads/reels/$jobId/job.json ---"
    Get-Content $jobPath
  }
}
exit 1


