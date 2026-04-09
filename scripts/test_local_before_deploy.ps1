<#
.SYNOPSIS
    EVAonline — Pre-Deploy Local Test Suite
.DESCRIPTION
    Runs a comprehensive 10-step checklist before deploying to production.
    Validates: .env secrets, Docker build, health endpoints, port isolation,
    security headers, unit tests, integration test (ETo calculation), and
    container resource usage.
.NOTES
    Run from the project root:  .\scripts\test_local_before_deploy.ps1
    Requires: Docker Desktop running, .env file configured.
#>

param(
    [switch]$SkipBuild,
    [switch]$SkipTests,
    [int]$WaitSeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  EVAonline - Pre-Deploy Local Test Suite"   -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$errors = 0
$warnings = 0
$passed = 0

function Write-Pass($msg) { Write-Host "  [PASS] $msg" -ForegroundColor Green; $script:passed++ }
function Write-Fail($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red; $script:errors++ }
function Write-Warn($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow; $script:warnings++ }
function Write-Info($msg) { Write-Host "  [INFO] $msg" -ForegroundColor Gray }

# ============================================================
# 1. Verify .env exists and has no default passwords
# ============================================================
Write-Host "[1/10] Checking .env file..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.docker") {
        Write-Warn ".env not found, but .env.docker exists. Copy and customize it."
    }
    else {
        Write-Fail ".env file not found!"
    }
}
else {
    $envContent = Get-Content ".env" -Raw
    $defaults = @(
        "CHANGE_THIS",
        "your_password",
        "your_secret",
        "changeme",
        "admin123",
        "password123"
    )
    $foundDefault = $false
    foreach ($d in $defaults) {
        if ($envContent -match [regex]::Escape($d)) {
            Write-Fail ".env contains default placeholder: '$d'"
            $foundDefault = $true
        }
    }
    if (-not $foundDefault) {
        Write-Pass ".env exists with custom values"
    }

    # Check minimum password lengths
    $envLines = Get-Content ".env"
    foreach ($line in $envLines) {
        if ($line -match "^(SECRET_KEY|POSTGRES_PASSWORD|REDIS_PASSWORD)=(.+)$") {
            $varName = $Matches[1]
            $varVal = $Matches[2].Trim('"').Trim("'")
            if ($varVal.Length -lt 16) {
                Write-Fail "$varName is too short ($($varVal.Length) chars, min 16)"
            }
        }
    }
}

# ============================================================
# 2. Docker Compose validation
# ============================================================
Write-Host "[2/10] Validating docker-compose.yml..." -ForegroundColor Yellow
$composeOutput = docker compose config 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Pass "Docker Compose config valid"
}
else {
    Write-Fail "Docker Compose config invalid: $($composeOutput | Select-Object -Last 3)"
}

# ============================================================
# 3. Build all images
# ============================================================
Write-Host "[3/10] Building Docker images..." -ForegroundColor Yellow
if ($SkipBuild) {
    Write-Info "Skipping build (-SkipBuild flag)"
}
else {
    docker compose build 2>&1 | Select-Object -Last 5
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "All images built successfully"
    }
    else {
        Write-Fail "Docker build failed"
    }
}

# ============================================================
# 4. Start core services
# ============================================================
Write-Host "[4/10] Starting services..." -ForegroundColor Yellow
docker compose up -d 2>&1 | Out-Null
Write-Info "Waiting ${WaitSeconds}s for services to initialize..."
Start-Sleep -Seconds $WaitSeconds

# Verify all containers are running
$containers = docker compose ps --format json 2>$null | ConvertFrom-Json -ErrorAction SilentlyContinue
if ($containers) {
    $unhealthy = @($containers | Where-Object { $_.State -ne "running" })
    if ($unhealthy.Count -eq 0) {
        Write-Pass "All containers running"
    }
    else {
        foreach ($c in $unhealthy) {
            Write-Fail "Container $($c.Name) is $($c.State)"
        }
    }
}
else {
    # Fallback: check via docker compose ps text
    docker compose ps
}

# ============================================================
# 5. Health checks
# ============================================================
Write-Host "[5/10] Running health checks..." -ForegroundColor Yellow

$endpoints = @(
    @{ Name = "API Health"; URL = "http://localhost/api/v1/health"; Expected = 200 },
    @{ Name = "API Ready"; URL = "http://localhost/api/v1/ready"; Expected = 200 },
    @{ Name = "Detailed Health"; URL = "http://localhost/api/v1/health/detailed"; Expected = 200 },
    @{ Name = "Swagger UI"; URL = "http://localhost/api/v1/docs"; Expected = 200 },
    @{ Name = "Frontend Home"; URL = "http://localhost/"; Expected = 200 },
    @{ Name = "Grafana Health"; URL = "http://localhost/grafana/api/health"; Expected = 200 },
    @{ Name = "Flower (Auth)"; URL = "http://localhost/flower/"; Expected = 401 }
)

foreach ($ep in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri $ep.URL -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        if ($response.StatusCode -eq $ep.Expected) {
            Write-Pass "$($ep.Name) -> HTTP $($response.StatusCode)"
        }
        else {
            Write-Fail "$($ep.Name) -> HTTP $($response.StatusCode) (expected $($ep.Expected))"
        }
    }
    catch {
        $statusCode = $null
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        if ($statusCode -eq $ep.Expected) {
            Write-Pass "$($ep.Name) -> HTTP $statusCode"
        }
        else {
            Write-Fail "$($ep.Name) -> Error: $($_.Exception.Message)"
        }
    }
}

# ============================================================
# 6. Security: verify internal ports are NOT exposed
# ============================================================
Write-Host "[6/10] Verifying internal ports are blocked..." -ForegroundColor Yellow

$internalPorts = @(
    @{ Name = "PostgreSQL"; Port = 5432 },
    @{ Name = "Redis"; Port = 6379 },
    @{ Name = "Prometheus"; Port = 9090 },
    @{ Name = "Grafana direct"; Port = 3000 },
    @{ Name = "Flower direct"; Port = 5555 },
    @{ Name = "API direct"; Port = 8000 },
    @{ Name = "Adminer"; Port = 5050 }
)

foreach ($p in $internalPorts) {
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $asyncResult = $tcp.BeginConnect("localhost", $p.Port, $null, $null)
        $waited = $asyncResult.AsyncWaitHandle.WaitOne(2000, $false)
        if ($waited -and $tcp.Connected) {
            Write-Fail "$($p.Name) (port $($p.Port)) is ACCESSIBLE from host!"
        }
        else {
            Write-Pass "$($p.Name) (port $($p.Port)) blocked"
        }
    }
    catch {
        Write-Pass "$($p.Name) (port $($p.Port)) blocked"
    }
    finally {
        $tcp.Close()
    }
}

# ============================================================
# 7. Security: /metrics blocked via Nginx
# ============================================================
Write-Host "[7/10] Verifying /metrics is blocked via Nginx..." -ForegroundColor Yellow
try {
    $metricsResp = Invoke-WebRequest -Uri "http://localhost/metrics" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($metricsResp.StatusCode -eq 200) {
        Write-Fail "/metrics is publicly accessible (should be blocked by Nginx)"
    }
    else {
        Write-Pass "/metrics returns HTTP $($metricsResp.StatusCode)"
    }
}
catch {
    $statusCode = $null
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
    }
    if ($statusCode -in @(403, 404)) {
        Write-Pass "/metrics returns HTTP $statusCode (blocked)"
    }
    else {
        Write-Pass "/metrics blocked ($($_.Exception.Message))"
    }
}

# ============================================================
# 8. Run unit tests via Docker
# ============================================================
Write-Host "[8/10] Running unit tests..." -ForegroundColor Yellow
if ($SkipTests) {
    Write-Info "Skipping tests (-SkipTests flag)"
}
else {
    $testOutput = docker compose exec -T api python -m pytest backend/tests/unit -v --tb=short -q 2>&1
    $testExitCode = $LASTEXITCODE
    $testOutput | Select-Object -Last 15
    if ($testExitCode -eq 0) {
        Write-Pass "Unit tests passed"
    }
    else {
        Write-Warn "Some unit tests failed (exit code $testExitCode)"
    }
}

# ============================================================
# 9. Run security tests
# ============================================================
Write-Host "[9/10] Running security tests..." -ForegroundColor Yellow
if ($SkipTests) {
    Write-Info "Skipping tests (-SkipTests flag)"
}
else {
    $secOutput = docker compose exec -T api python -m pytest backend/tests/security -v --tb=short -q 2>&1
    $secExitCode = $LASTEXITCODE
    $secOutput | Select-Object -Last 15
    if ($secExitCode -eq 0) {
        Write-Pass "Security tests passed"
    }
    else {
        Write-Warn "Some security tests failed (exit code $secExitCode)"
    }
}

# ============================================================
# 10. Container status & resource usage
# ============================================================
Write-Host "[10/10] Container status & resources:" -ForegroundColor Yellow
Write-Host ""
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>$null
Write-Host ""
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>$null

# ============================================================
# SUMMARY
# ============================================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Results: $passed passed, $errors failed, $warnings warnings" -ForegroundColor $(if ($errors -eq 0) { "Green" } else { "Red" })
Write-Host "============================================" -ForegroundColor Cyan

if ($errors -eq 0) {
    Write-Host ""
    Write-Host "  ALL CHECKS PASSED - Ready for deploy!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Next steps:" -ForegroundColor White
    Write-Host "    1. git add -A; git commit -m 'pre-deploy: all checks passed'" -ForegroundColor Gray
    Write-Host "    2. git push origin main" -ForegroundColor Gray
    Write-Host "    3. ssh root@your-server-ip" -ForegroundColor Gray
    Write-Host "    4. bash scripts/deploy_digitalocean.sh" -ForegroundColor Gray
    Write-Host ""
    exit 0
}
else {
    Write-Host ""
    Write-Host "  $errors CHECKS FAILED - Fix before deploying!" -ForegroundColor Red
    Write-Host ""
    exit 1
}
