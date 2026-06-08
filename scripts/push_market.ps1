# push_market.ps1
# Windows Task Scheduler triggers this every 10 min (09:00-14:10).
# Trading-hour guard is inside the script; Task Scheduler just fires it all day on weekdays.
#
# Usage (manual test):  powershell -ExecutionPolicy Bypass -File push_market.ps1 -Force

param([switch]$Force)

$RepoDir = Split-Path -Parent $PSScriptRoot
$LogDir  = Join-Path $RepoDir "logs"
$LogFile = Join-Path $LogDir  "push_market.log"

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

# ── Trading-hour guard (Mon-Fri, 08:55-14:10) ─────────────────────────────
if (!$Force) {
    $now = Get-Date
    if ($now.DayOfWeek -in @("Saturday", "Sunday")) { exit 0 }
    $m = $now.Hour * 60 + $now.Minute
    if ($m -lt 535 -or $m -gt 850) { exit 0 }
}

Set-Location $RepoDir
Log "=== push_market START ==="

# ── 1. Pull latest (picks up today's _base.json and dividend updates) ────────
$out = git pull --rebase origin main 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "git pull FAILED: $out"
    exit 1
}
Log "pull OK"

# ── 2. Run MIS fetcher → generates fresh data/market.json ───────────────────
$out = python scripts/mis_fetcher.py 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "mis_fetcher.py FAILED: $out"
    exit 1
}
Log "fetcher OK"

# ── 3. Stage; skip if nothing changed ────────────────────────────────────────
git add data/market.json
if (!(git diff --cached --name-only 2>&1)) {
    Log "No changes, skipping push."
    exit 0
}

# ── 4. Commit ─────────────────────────────────────────────────────────────────
$ts  = (Get-Date).ToString("yyyy-MM-dd HH:mm")
$msg = "chore: update market data $ts (local)"
git commit -m $msg 2>&1 | ForEach-Object { Log $_ }

# ── 5. Push with retry (-X ours: keep our fresh MIS data on rebase conflict) ─
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
