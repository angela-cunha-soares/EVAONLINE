# =====================================================
# EVAonline - Infrastructure Integration Test
# Version: 1.0.0
# Usage: powershell -ExecutionPolicy Bypass -File scripts/test_infrastructure.ps1
# =====================================================

param(
    [string]$BaseUrl = "http://localhost",
    [string]$GrafanaPassword = "admin"
)

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host " EVAonline Infrastructure Test Suite" -ForegroundColor Cyan
Write-Host "=========================================`n" -ForegroundColor Cyan

$passed = 0
$failed = 0
$warnings = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedCode
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -Method GET -UseBasicParsing -TimeoutSec 15 -MaximumRedirection 5 -ErrorAction Stop
        $code = $response.StatusCode
    }
    catch {
        if ($_.Exception.Response) {
            $code = [int]$_.Exception.Response.StatusCode
        }
        else {
            $code = 0
        }
    }

    if ($code -eq $ExpectedCode) {
        Write-Host "  [PASS] $Name -> HTTP $code" -ForegroundColor Green
        $script:passed++
    }
    else {
        Write-Host "  [FAIL] $Name -> HTTP $code (expected $ExpectedCode)" -ForegroundColor Red
        $script:failed++
    }
}

function Test-PortBlocked {
    param(
        [string]$Name,
        [int]$Port
    )

    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $asyncResult = $tcp.BeginConnect("localhost", $Port, $null, $null)
        $waited = $asyncResult.AsyncWaitHandle.WaitOne(2000, $false)
        if ($waited -and $tcp.Connected) {
            Write-Host "  [WARN] $Name ($Port) -> ACCESSIBLE (should be internal only)" -ForegroundColor Red
            $script:failed++
        }
        else {
            Write-Host "  [PASS] $Name ($Port) -> Blocked" -ForegroundColor Green
            $script:passed++
        }
        $tcp.Close()
    }
    catch {
        Write-Host "  [PASS] $Name ($Port) -> Blocked" -ForegroundColor Green
        $script:passed++
    }
}

# ===========================================================
# 1. Container Status
# ===========================================================
Write-Host "[1/8] Container Status:" -ForegroundColor Yellow
docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>$null
Write-Host ""

# ===========================================================
# 2. Frontend & Dash Pages
# ===========================================================
Write-Host "[2/8] Frontend Pages:" -ForegroundColor Yellow
Test-Endpoint "Dashboard Home (/)" "$BaseUrl/" 200
Test-Endpoint "Documentation" "$BaseUrl/documentation" 200
Test-Endpoint "Architecture" "$BaseUrl/architecture" 200
Test-Endpoint "About" "$BaseUrl/about" 200

# ===========================================================
# 3. API Endpoints
# ===========================================================
Write-Host "`n[3/8] API Endpoints:" -ForegroundColor Yellow
Test-Endpoint "Health" "$BaseUrl/api/v1/health" 200
Test-Endpoint "Health Detailed" "$BaseUrl/api/v1/health/detailed" 200
Test-Endpoint "Ready" "$BaseUrl/api/v1/ready" 200
Test-Endpoint "Swagger Docs" "$BaseUrl/api/v1/docs" 200
Test-Endpoint "OpenAPI Schema" "$BaseUrl/api/v1/openapi.json" 200

# ===========================================================
# 4. Security - Blocked Endpoints
# ===========================================================
Write-Host "`n[4/8] Security - Blocked Endpoints:" -ForegroundColor Yellow
Test-Endpoint "/metrics BLOCKED" "$BaseUrl/metrics" 404

# ===========================================================
# 5. Monitoring Tools (via Nginx sub-paths)
# ===========================================================
Write-Host "`n[5/8] Monitoring Tools:" -ForegroundColor Yellow
Test-Endpoint "Grafana Login" "$BaseUrl/grafana/login" 200
Test-Endpoint "Grafana API Health" "$BaseUrl/grafana/api/health" 200
Test-Endpoint "Flower (needs auth)" "$BaseUrl/flower/" 401

# ===========================================================
# 6. Internal Ports (should NOT be accessible externally)
# ===========================================================
Write-Host "`n[6/8] Internal Ports (should be blocked):" -ForegroundColor Yellow
Test-PortBlocked "Prometheus" 9090
Test-PortBlocked "Grafana direct" 3000
Test-PortBlocked "Flower direct" 5555
Test-PortBlocked "API direct" 8000
Test-PortBlocked "PostgreSQL" 5432
Test-PortBlocked "Redis" 6379

# ===========================================================
# 7. Prometheus Targets (via Docker exec)
# ===========================================================
Write-Host "`n[7/8] Prometheus Targets:" -ForegroundColor Yellow
try {
    $raw = docker exec evaonline-prometheus wget -qO- "http://localhost:9090/api/v1/targets" 2>$null
    if ($raw) {
        $targets = $raw | ConvertFrom-Json
        foreach ($t in $targets.data.activeTargets) {
            $h = $t.health
            $j = $t.labels.job
            if ($h -eq "up") {
                Write-Host "  [PASS] Target '$j' -> $h" -ForegroundColor Green
                $script:passed++
            }
            else {
                Write-Host "  [FAIL] Target '$j' -> $h ($($t.lastError))" -ForegroundColor Red
                $script:failed++
            }
        }
    }
    else {
        Write-Host "  [WARN] Could not reach Prometheus" -ForegroundColor Yellow
        $script:warnings++
    }
}
catch {
    Write-Host "  [WARN] Could not query Prometheus: $($_.Exception.Message)" -ForegroundColor Yellow
    $script:warnings++
}

# ===========================================================
# 8. Grafana Datasource
# ===========================================================
Write-Host "`n[8/8] Grafana Datasource:" -ForegroundColor Yellow
try {
    $auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:$GrafanaPassword"))
    $dsRaw = docker exec evaonline-grafana wget -qO- --header="Authorization: Basic $auth" "http://localhost:3000/grafana/api/datasources" 2>$null
    if ($dsRaw) {
        $ds = $dsRaw | ConvertFrom-Json
        if ($ds.Count -gt 0) {
            foreach ($d in $ds) {
                Write-Host "  [PASS] Datasource: $($d.name) (type: $($d.type))" -ForegroundColor Green
                $script:passed++
            }
        }
        else {
            Write-Host "  [WARN] No datasources configured" -ForegroundColor Yellow
            $script:warnings++
        }
    }
    else {
        Write-Host "  [WARN] Could not reach Grafana API" -ForegroundColor Yellow
        $script:warnings++
    }
}
catch {
    Write-Host "  [WARN] Could not query Grafana: $($_.Exception.Message)" -ForegroundColor Yellow
    $script:warnings++
}

# ===========================================================
# Summary
# ===========================================================
Write-Host "`n=========================================" -ForegroundColor Cyan
$totalColor = if ($failed -eq 0) { "Green" } else { "Red" }
Write-Host " RESULTS: $passed passed, $failed failed, $warnings warnings" -ForegroundColor $totalColor
Write-Host "=========================================`n" -ForegroundColor Cyan

if ($failed -gt 0) {
    Write-Host "Debug commands:" -ForegroundColor Yellow
    Write-Host "  docker compose logs nginx --tail=30" -ForegroundColor Gray
    Write-Host "  docker compose logs api --tail=30" -ForegroundColor Gray
    Write-Host "  docker compose logs prometheus --tail=20" -ForegroundColor Gray
    Write-Host "  docker compose logs grafana --tail=20" -ForegroundColor Gray
    Write-Host "  docker compose logs flower --tail=20" -ForegroundColor Gray
    Write-Host "  docker compose logs celery-worker --tail=20" -ForegroundColor Gray
    exit 1
}
else {
    Write-Host "All infrastructure tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Open in browser:" -ForegroundColor Cyan
    Write-Host "  Dashboard:  $BaseUrl" -ForegroundColor White
    Write-Host "  API Docs:   $BaseUrl/api/v1/docs" -ForegroundColor White
    Write-Host "  Grafana:    $BaseUrl/grafana/" -ForegroundColor White
    Write-Host "  Flower:     $BaseUrl/flower/" -ForegroundColor White
    exit 0
}
