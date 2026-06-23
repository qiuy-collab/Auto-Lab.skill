# auto-lab environment check
#Requires -Version 5.1

param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$GeneratePy = Join-Path $Root "scripts\generate_images.py"
$BrowserCapturePy = Join-Path $Root "scripts\capture_frontend_screenshots.py"
$DiagramAssetsPy = Join-Path $Root "scripts\generate_diagram_assets.py"
$VideoProcessPy = Join-Path $Root "scripts\video_process.py"
$BlankTemplatePy = Join-Path $Root "scripts\prepare_blank_template.py"
$ImageConcurrencyPy = Join-Path $Root "scripts\test_image_concurrency.py"
$SubmissionPackagePy = Join-Path $Root "scripts\package_submission.py"
$EnvFile = Join-Path $Root ".env"
$EnvExample = Join-Path $Root ".env.example"
$MiniMaxSkill = Join-Path $Root "vendor\minimax-docx\SKILL.md"
$LocalFfmpeg = Join-Path $env:USERPROFILE "Tools\ffmpeg\bin\ffmpeg.exe"
$LocalFfprobe = Join-Path $env:USERPROFILE "Tools\ffmpeg\bin\ffprobe.exe"
$VendorFfmpeg = Join-Path $Root "vendor\ffmpeg\bin\ffmpeg.exe"
$VendorFfprobe = Join-Path $Root "vendor\ffmpeg\bin\ffprobe.exe"
$BrowserCandidates = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

$script:Status = "READY"
$script:Warnings = 0

function Ok($msg)   { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "[WARN]  $msg" -ForegroundColor Yellow; $script:Warnings++ }
function Fail($msg) { Write-Host "[FAIL]  $msg" -ForegroundColor Red; $script:Status = "NOT READY" }

function Read-EnvKeys([string]$Path) {
    $map = @{}
    if (-not (Test-Path $Path)) { return $map }
    foreach ($line in Get-Content $Path -Encoding UTF8) {
        $trim = $line.Trim()
        if (-not $trim -or $trim.StartsWith("#")) { continue }
        $delimiter = if ($trim.Contains("=")) { "=" } elseif ($trim.Contains(":")) { ":" } else { $null }
        if (-not $delimiter) { continue }
        $parts = $trim.Split($delimiter, 2)
        if ($parts.Count -eq 2) { $map[$parts[0].Trim()] = $parts[1].Trim() }
    }
    return $map
}

Write-Host "=== auto-lab Environment Check ==="
Write-Host "Root: $Root"
Write-Host ""

if (Get-Command python -ErrorAction SilentlyContinue) {
    Ok "python $(& python --version 2>&1)"
} else {
    Fail "python not found"
}

if (Get-Command dotnet -ErrorAction SilentlyContinue) {
    Ok "dotnet $(& dotnet --version 2>&1)"
} else {
    Fail "dotnet not found"
}

if (Test-Path $GeneratePy) { Ok "scripts\generate_images.py found" } else { Fail "scripts\generate_images.py missing" }
if (Test-Path $BrowserCapturePy) { Ok "scripts\capture_frontend_screenshots.py found" } else { Fail "scripts\capture_frontend_screenshots.py missing" }
if (Test-Path $DiagramAssetsPy) { Ok "scripts\generate_diagram_assets.py found" } else { Fail "scripts\generate_diagram_assets.py missing" }
if (Test-Path $VideoProcessPy) { Ok "scripts\video_process.py found" } else { Fail "scripts\video_process.py missing" }
if (Test-Path $BlankTemplatePy) { Ok "scripts\prepare_blank_template.py found" } else { Fail "scripts\prepare_blank_template.py missing" }
if (Test-Path $ImageConcurrencyPy) { Ok "scripts\test_image_concurrency.py found" } else { Fail "scripts\test_image_concurrency.py missing" }
if (Test-Path $SubmissionPackagePy) { Ok "scripts\package_submission.py found" } else { Fail "scripts\package_submission.py missing" }
if (Test-Path $MiniMaxSkill) { Ok "minimax-docx skill found" } else { Fail "minimax-docx skill missing" }

if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        & python -W ignore -c "import requests, docx; from PIL import Image; print('ok')" *> $null
        if ($LASTEXITCODE -eq 0) { Ok "python modules available: requests, python-docx, pillow" } else { Fail "python module check failed" }
    } catch {
        Fail "python module check failed"
    }

    try {
        & python -W ignore -c "from playwright.sync_api import sync_playwright; print('ok')" *> $null
        if ($LASTEXITCODE -eq 0) { Ok "python browser screenshot module available: playwright" } else { Warn "python playwright unavailable; browser screenshot route may not work" }
    } catch {
        Warn "python playwright unavailable; browser screenshot route may not work"
    }

    try {
        & python -W ignore -c "import av; print('ok')" *> $null
        if ($LASTEXITCODE -eq 0) { Ok "video analyzer available: PyAV" } else { Warn "PyAV unavailable; video analysis will fall back to OpenCV/ffprobe" }
    } catch {
        Warn "PyAV unavailable; video analysis will fall back to OpenCV/ffprobe"
    }

    try {
        & python -W ignore -c "import cv2, numpy; print('ok')" *> $null
        if ($LASTEXITCODE -eq 0) { Ok "video fallback available: opencv-python + numpy" } else { Warn "opencv-python/numpy unavailable; video recording fallback may not work" }
    } catch {
        Warn "opencv-python/numpy unavailable; video recording fallback may not work"
    }

    try {
        & python -W ignore -c "import mss; print('ok')" *> $null
        if ($LASTEXITCODE -eq 0) { Ok "screen recording capture available: mss" } else { Warn "mss unavailable; use OBS/ffmpeg fallback for screen recording" }
    } catch {
        Warn "mss unavailable; use OBS/ffmpeg fallback for screen recording"
    }
}

if (Test-Path $LocalFfmpeg) {
    Ok "local ffmpeg available: $LocalFfmpeg"
} elseif (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Ok "local ffmpeg available: $((Get-Command ffmpeg).Source)"
} elseif (Test-Path $VendorFfmpeg) {
    Ok "vendor ffmpeg available: $VendorFfmpeg"
} else {
    Warn "ffmpeg not found locally or in vendor; video fallback unavailable"
}

if (Test-Path $LocalFfprobe) {
    Ok "local ffprobe available: $LocalFfprobe"
} elseif (Get-Command ffprobe -ErrorAction SilentlyContinue) {
    Ok "local ffprobe available: $((Get-Command ffprobe).Source)"
} elseif (Test-Path $VendorFfprobe) {
    Ok "vendor ffprobe available: $VendorFfprobe"
} else {
    Warn "ffprobe not found locally or in vendor; metadata fallback unavailable"
}

$BrowserFound = $false
foreach ($candidate in $BrowserCandidates) {
    if (Test-Path $candidate) {
        Ok "browser executable found: $candidate"
        $BrowserFound = $true
        break
    }
}
if (-not $BrowserFound) {
    Warn "no local Chrome/Edge executable found; browser screenshot route may not work"
}

$envKeys = Read-EnvKeys $EnvFile
if (Test-Path $EnvFile) {
    if ($envKeys.ContainsKey("BASEURL") -and $envKeys.ContainsKey("APIKEY")) {
        Ok ".env contains BASEURL and APIKEY for ai_simulated route"
    } else {
        Warn ".env exists but BASEURL/APIKEY are incomplete; ai_simulated route may not work"
    }
} else {
    Warn ".env missing; diagram_assets and browser_capture can still run, but ai_simulated needs real values"
    if (Test-Path $EnvExample) { Warn "copy .env.example to .env and fill real values before using ai_simulated" }
}

foreach ($scriptName in @("init_run.py", "run_workflow.py", "capture_frontend_screenshots.py", "generate_diagram_assets.py", "video_process.py", "prepare_blank_template.py", "test_image_concurrency.py", "package_submission.py")) {
    try {
        & python (Join-Path $PSScriptRoot $scriptName) --help *> $null
        if ($LASTEXITCODE -eq 0) { Ok "$scriptName executable" } else { Fail "$scriptName help command failed" }
    } catch {
        Fail "$scriptName not executable"
    }
}

Write-Host ""
if ($script:Status -eq "READY") {
    if ($script:Warnings -gt 0) {
        Write-Host "Status: READY (with $script:Warnings warning(s))" -ForegroundColor Yellow
    } else {
        Write-Host "Status: READY" -ForegroundColor Green
    }
} else {
    Write-Host "Status: NOT READY" -ForegroundColor Red
    exit 1
}
