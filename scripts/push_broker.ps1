# push_broker.ps1
# Windows Task Scheduler triggers this once daily at 14:30 on weekdays.
# Runs fetch_broker_signal.py (incremental, ~15 min), commits broker_signal.json.

param([switch]$Force)

$RepoDir = Split-Path -Parent $PSScriptRoot
$LogDir  = Join-Path $RepoDir "logs"
$LogFile = Join-Path $LogDir  "push_broker.log"

if (!(Test-Path $LogDir)) { New-Item -ItemType Directory $LogDir | Out-Null }

function Log($msg) {
    $ts   = (Get-Date).ToString("HH:mm:ss")
    $line = "$ts $msg"
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

# Trim log file when it exceeds ~500 KB
if ((Test-Path $LogFile) -and (Get-Item $LogFile).Length -gt 512000) {
    $lines = Get-Content $LogFile
    $lines | Select-Object -Last 2000 | Set-Content $LogFile -Encoding UTF8
}

# ── 只在平日 14:20-15:30 執行（收盤後） ──────────────────────────
if (!$Force) {
    $now = Get-Date
    if ($now.DayOfWeek -in @("Saturday", "Sunday")) { exit 0 }
    $m = $now.Hour * 60 + $now.Minute
    if ($m -lt 860 -or $m -gt 930) { exit 0 }   # 14:20-15:30
}

Set-Location $RepoDir
Log "=== push_broker START ==="

# ── 1. Pull latest ─────────────────────────────────────────────────
$out = git pull --rebase origin main 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "git pull FAILED: $out"
    exit 1
}
Log "pull OK"

# ── 2. Run broker signal fetcher ───────────────────────────────────
$out = python scripts/fetch_broker_signal.py 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "fetch_broker_signal.py FAILED: $out"
    exit 1
}
Log "fetcher OK"

# ── 3. Stage; skip if nothing changed ──────────────────────────────
git add data/broker_signal.json data/_broker_cache.json
if (!(git diff --cached --name-only 2>&1)) {
    Log "No changes, skipping push."
    exit 0
}

# ── 4. Commit ──────────────────────────────────────────────────────
$ts  = (Get-Date).ToString("yyyy-MM-dd")
$msg = "chore: update broker signal $ts"
git commit -m $msg 2>&1 | ForEach-Object { Log $_ }

# ── 5. Push with retry ─────────────────────────────────────────────
for ($i = 1; $i -le 3; $i++) {
    git pull --rebase -X ours origin main 2>&1 | ForEach-Object { Log $_ }
    git push origin main 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -eq 0) {
        Log "Push OK."
        exit 0
    }
    Log "Push failed attempt $i/3"
    if ($i -lt 3) { Start-Sleep -Seconds ($i * 5) }
}

Log "ERROR: push failed after 3 retries."
exit 1
