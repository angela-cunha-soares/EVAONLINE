<#
.SYNOPSIS
    Generates per-module coverage reports for the EVAonline test suite.
.DESCRIPTION
    Runs pytest with coverage for each test module individually and generates
    an HTML index page aggregating all coverage reports.
.NOTES
    Usage: .\scripts\generate_coverage_reports.ps1
#>

$ErrorActionPreference = "Continue"

Write-Host "[INFO] Generating per-module coverage reports..." -ForegroundColor Cyan
Write-Host ""

# Create base directory
$coverageDir = "htmlcov"
if (-not (Test-Path $coverageDir)) {
    New-Item -ItemType Directory -Path $coverageDir | Out-Null
}

# Array of modules to test
$modules = @(
    # ============ UNIT TESTS ============
    @{
        Name = "Unit: API Layer"
        TestPath = "backend/tests/unit/api/"
        SourcePath = "backend.api"
        OutputDir = "htmlcov/unit/api"
        Color = "Green"
    },
    @{
        Name = "Unit: Application Layer"
        TestPath = "backend/tests/unit/application/"
        SourcePath = "backend.application"
        OutputDir = "htmlcov/unit/application"
        Color = "DarkCyan"
    },
    @{
        Name = "Unit: Core Layer"
        TestPath = "backend/tests/unit/core/"
        SourcePath = "backend.core"
        OutputDir = "htmlcov/unit/core"
        Color = "Blue"
    },
    @{
        Name = "Unit: Database Layer"
        TestPath = "backend/tests/unit/database/"
        SourcePath = "backend.database"
        OutputDir = "htmlcov/unit/database"
        Color = "Magenta"
    },
    @{
        Name = "Unit: Domain Layer"
        TestPath = "backend/tests/unit/domain/"
        SourcePath = "backend.domain"
        OutputDir = "htmlcov/unit/domain"
        Color = "Cyan"
    },
    @{
        Name = "Unit: Infrastructure Layer"
        TestPath = "backend/tests/unit/infrastructure/"
        SourcePath = "backend.infrastructure"
        OutputDir = "htmlcov/unit/infrastructure"
        Color = "Yellow"
    },
    @{
        Name = "Unit: Fixtures"
        TestPath = "backend/tests/unit/fixtures/"
        SourcePath = "backend.tests.fixtures"
        OutputDir = "htmlcov/unit/fixtures"
        Color = "Gray"
    },
    
    # ============ INTEGRATION TESTS ============
    @{
        Name = "Integration: API"
        TestPath = "backend/tests/integration/api/"
        SourcePath = "backend.api"
        OutputDir = "htmlcov/integration/api"
        Color = "Green"
    },
    @{
        Name = "Integration: Celery"
        TestPath = "backend/tests/integration/celery/"
        SourcePath = "backend.infrastructure.celery"
        OutputDir = "htmlcov/integration/celery"
        Color = "DarkYellow"
    },
    @{
        Name = "Integration: Database"
        TestPath = "backend/tests/integration/database/"
        SourcePath = "backend.database"
        OutputDir = "htmlcov/integration/database"
        Color = "Magenta"
    },
    @{
        Name = "Integration: Infrastructure"
        TestPath = "backend/tests/integration/infrastructure/"
        SourcePath = "backend.infrastructure"
        OutputDir = "htmlcov/integration/infrastructure"
        Color = "Yellow"
    },
    @{
        Name = "Integration: Redis"
        TestPath = "backend/tests/integration/redis/"
        SourcePath = "backend.infrastructure.redis"
        OutputDir = "htmlcov/integration/redis"
        Color = "Red"
    },
    @{
        Name = "Integration: WebSockets"
        TestPath = "backend/tests/integration/websockets/"
        SourcePath = "backend.api.websockets"
        OutputDir = "htmlcov/integration/websockets"
        Color = "DarkGreen"
    },
    
    # ============ E2E TESTS ============
    @{
        Name = "E2E: API"
        TestPath = "backend/tests/e2e/api/"
        SourcePath = "backend.api"
        OutputDir = "htmlcov/e2e/api"
        Color = "DarkGreen"
    },
    @{
        Name = "E2E: Celery"
        TestPath = "backend/tests/e2e/celery/"
        SourcePath = "backend.infrastructure.celery"
        OutputDir = "htmlcov/e2e/celery"
        Color = "DarkYellow"
    },
    @{
        Name = "E2E: Dash"
        TestPath = "backend/tests/e2e/dash/"
        SourcePath = "frontend"
        OutputDir = "htmlcov/e2e/dash"
        Color = "DarkBlue"
    },
    @{
        Name = "E2E: Scenarios"
        TestPath = "backend/tests/e2e/test_*.py"
        SourcePath = "backend"
        OutputDir = "htmlcov/e2e/scenarios"
        Color = "DarkMagenta"
    },
    
    # ============ PERFORMANCE TESTS ============
    @{
        Name = "Performance: All"
        TestPath = "backend/tests/performance/"
        SourcePath = "backend"
        OutputDir = "htmlcov/performance"
        Color = "DarkYellow"
    },
    
    # ============ SECURITY TESTS ============
    @{
        Name = "Security: All"
        TestPath = "backend/tests/security/"
        SourcePath = "backend"
        OutputDir = "htmlcov/security"
        Color = "Red"
    },
    
    # ============ HELPERS & FIXTURES ============
    @{
        Name = "Test Fixtures"
        TestPath = "backend/tests/fixtures/"
        SourcePath = "backend.tests.fixtures"
        OutputDir = "htmlcov/test_infrastructure/fixtures"
        Color = "Gray"
    },
    @{
        Name = "Test Helpers"
        TestPath = "backend/tests/helpers/"
        SourcePath = "backend.tests.helpers"
        OutputDir = "htmlcov/test_infrastructure/helpers"
        Color = "DarkGray"
    },
    
    # ============ CONSOLIDATED REPORTS ============
    @{
        Name = "[UNIT] ALL UNIT TESTS"
        TestPath = "backend/tests/unit/"
        SourcePath = "backend"
        OutputDir = "htmlcov/consolidated/unit"
        Color = "Blue"
    },
    @{
        Name = "[INTEGRATION] ALL INTEGRATION TESTS"
        TestPath = "backend/tests/integration/"
        SourcePath = "backend"
        OutputDir = "htmlcov/consolidated/integration"
        Color = "Green"
    },
    @{
        Name = "[E2E] ALL E2E TESTS"
        TestPath = "backend/tests/e2e/"
        SourcePath = "backend"
        OutputDir = "htmlcov/consolidated/e2e"
        Color = "DarkMagenta"
    },
    @{
        Name = "[COMPLETE] ALL TESTS"
        TestPath = "backend/tests/"
        SourcePath = "backend"
        OutputDir = "htmlcov/consolidated/all"
        Color = "White"
    }
)

$results = @()

foreach ($module in $modules) {
    Write-Host "[TEST] $($module.Name)" -ForegroundColor $module.Color
    Write-Host "   Testes: $($module.TestPath)" -ForegroundColor Gray
    Write-Host "   Fonte: $($module.SourcePath)" -ForegroundColor Gray
    
    # Executar pytest com coverage
    $output = pytest $module.TestPath.Split() `
        --cov=$($module.SourcePath) `
        --cov-report=html:$($module.OutputDir) `
        --cov-report=term-missing `
        --cov-report=json:$($module.OutputDir)/coverage.json `
        -v `
        --tb=short `
        2>&1
    
    # Extrair estatsticas
    $coverageLine = $output | Select-String -Pattern "TOTAL.*\d+%"
    
    if ($coverageLine) {
        $percentage = $coverageLine -replace '.*?(\d+)%.*', '$1'
        $status = if ($LASTEXITCODE -eq 0) { "PASSED" } else { "FAILED" }
        
        Write-Host "   Cobertura: $percentage%" -ForegroundColor $module.Color
        Write-Host "   Status: $status" -ForegroundColor $(if ($LASTEXITCODE -eq 0) { "Green" } else { "Red" })
        
        $results += @{
            Module = $module.Name
            Coverage = "$percentage%"
            Status = $status
            ReportPath = $module.OutputDir
        }
    } else {
        Write-Host "   [WARNING] No foi possvel extrair cobertura" -ForegroundColor Yellow
        $results += @{
            Module = $module.Name
            Coverage = "N/A"
            Status = "ERROR"
            ReportPath = $module.OutputDir
        }
    }
    
    Write-Host ""
}

# Resumo final
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "RESUMO DE COBERTURA POR MDULO" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

foreach ($result in $results) {
    $color = if ($result.Status -like "*PASSED*") { "Green" } 
             elseif ($result.Status -like "*FAILED*") { "Red" }
             else { "Yellow" }
    
    Write-Host "  $($result.Module.PadRight(25))" -NoNewline -ForegroundColor White
    Write-Host " $($result.Coverage.PadRight(10))" -NoNewline -ForegroundColor $color
    Write-Host " $($result.Status)" -ForegroundColor $color
    Write-Host "    PATH: $($result.ReportPath)/index.html" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "[SUCCESS] Relatrios gerados! Abra os arquivos index.html em cada pasta." -ForegroundColor Green
Write-Host ""

# Gerar ndice HTML com links para todos os relatrios
$indexHtml = @"
<!DOCTYPE html>
<html>
<head>
    <title>EVAonline - Relatrios de Cobertura</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            border-radius: 10px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 40px;
        }
        .module {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
            transition: all 0.3s;
        }
        .module:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateX(5px);
        }
        .module-name {
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        .module-stats {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .coverage {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        .status {
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }
        .status.passed {
            background: #d4edda;
            color: #155724;
        }
        .status.failed {
            background: #f8d7da;
            color: #721c24;
        }
        .link {
            display: inline-block;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s;
        }
        .link:hover {
            background: #764ba2;
        }
        .timestamp {
            text-align: center;
            color: #999;
            margin-top: 40px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>EVonline - Relatrios de Cobertura de Testes</h1>
        <p class="subtitle">Cobertura de cdigo por mdulo</p>
"@

foreach ($result in $results) {
    $statusClass = if ($result.Status -like "*PASSED*") { "passed" } else { "failed" }
    $indexHtml += @"
        <div class="module">
            <div class="module-name">$($result.Module)</div>
            <div class="module-stats">
                <span class="coverage">$($result.Coverage)</span>
                <span class="status $statusClass">$($result.Status)</span>
            </div>
            <a href="$($result.ReportPath)/index.html" class="link" target="_blank">Ver Relatrio Detalhado</a>
        </div>
"@
}

$indexHtml += @"
        <div class="timestamp">
            Gerado em: $(Get-Date -Format "dd/MM/yyyy HH:mm:ss")
        </div>
    </div>
</body>
</html>
"@

$indexHtml | Out-File -FilePath "htmlcov/index.html" -Encoding UTF8

Write-Host "[SUCCESS] ndice principal criado: htmlcov/index.html" -ForegroundColor Green
Write-Host "Abra este arquivo no navegador para ver todos os relatrios!" -ForegroundColor Yellow


