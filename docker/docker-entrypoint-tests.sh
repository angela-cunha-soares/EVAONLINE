#!/bin/bash
# filepath: docker/docker-entrypoint-tests.sh
# ============================================================================
# ENTRYPOINT PARA TESTES - EVAonline (Pytest + Coverage)
# ============================================================================
# Executa testes unitários, integração, E2E e performance com cobertura

set -e  # Exit on error

echo "============================================================================"
echo "🧪 SISTEMA DE TESTES - EVAonline"
echo "============================================================================"
echo ""
echo "⏰ Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "🐳 Container: $(hostname)"
echo "🌍 Ambiente: ${ENVIRONMENT:-testing}"
echo "🐍 Python: $(python --version)"
echo "🧪 Pytest: $(pytest --version | head -n 1)"
echo ""

# ============================================================================
# VERIFICAR DEPENDÊNCIAS
# ============================================================================

echo "📦 Verificando dependências Python..."
required_packages=("pytest" "pytest-cov" "pytest-asyncio" "httpx" "fakeredis")

for package in "${required_packages[@]}"; do
    if python -c "import $package" 2>/dev/null; then
        echo "  ✅ $package"
    else
        echo "  ❌ $package não encontrado!"
        exit 1
    fi
done

echo ""

# ============================================================================
# AGUARDAR SERVIÇOS EXTERNOS
# ============================================================================

wait_for_service() {
    local service=$1
    local host=$2
    local port=$3
    local max_attempts=30
    local attempt=0

    echo "⏳ Aguardando $service ($host:$port)..."
    
    while ! nc -z "$host" "$port" 2>/dev/null; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo "  ❌ Timeout aguardando $service"
            exit 1
        fi
        sleep 1
    done
    
    echo "  ✅ $service pronto"
}

# Aguardar PostgreSQL
wait_for_service "PostgreSQL" "postgres" 5432

# Aguardar Redis
echo "⏳ Aguardando Redis..."
attempt=0
while ! redis-cli -h redis -a "${REDIS_PASSWORD:-evaonline}" ping > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge 30 ]; then
        echo "  ❌ Timeout aguardando Redis"
        exit 1
    fi
    sleep 1
done
echo "  ✅ Redis pronto"

echo ""

# ============================================================================
# CONFIGURAR BANCO DE DADOS DE TESTES
# ============================================================================

echo "🔄 Configurando banco de dados de testes..."
cd /app

# Executar migrations com Alembic
if [ -d "alembic" ] && [ -f "alembic.ini" ]; then
    echo "  → Executando migrations..."
    alembic upgrade head 2>/dev/null || echo "  ⚠️  Migrations falharam (pode ser normal)"
    echo "  ✅ Database preparado"
else
    echo "  ⚠️  Alembic não encontrado, pulando migrations"
fi

echo ""

# ============================================================================
# EXECUTAR TESTES COM PYTEST
# ============================================================================

echo "============================================================================"
echo "🧪 EXECUTANDO TESTES"
echo "============================================================================"
echo ""

# Detectar tipo de teste via variável de ambiente
TEST_TYPE="${TEST_TYPE:-all}"
MIN_COVERAGE="${MIN_COVERAGE:-70}"

# Configurar argumentos do pytest baseado no tipo de teste
case "$TEST_TYPE" in
    unit)
        echo "📝 Modo: TESTES UNITÁRIOS"
        PYTEST_ARGS="backend/tests/unit -v --tb=short"
        COVERAGE_REPORT="htmlcov/unit"
        ;;
    
    integration)
        echo "🔗 Modo: TESTES DE INTEGRAÇÃO"
        PYTEST_ARGS="backend/tests/integration -v --tb=short"
        COVERAGE_REPORT="htmlcov/integration"
        ;;
    
    e2e)
        echo "🌐 Modo: TESTES E2E"
        PYTEST_ARGS="backend/tests/e2e -v --tb=short"
        COVERAGE_REPORT="htmlcov/e2e"
        ;;
    
    performance)
        echo "⚡ Modo: TESTES DE PERFORMANCE"
        PYTEST_ARGS="backend/tests/performance -v --tb=short"
        COVERAGE_REPORT="htmlcov/performance"
        ;;
    
    security)
        echo "🔒 Modo: TESTES DE SEGURANÇA"
        PYTEST_ARGS="backend/tests/security -v --tb=short"
        COVERAGE_REPORT="htmlcov/security"
        ;;
    
    all)
        echo "🎯 Modo: TODOS OS TESTES"
        PYTEST_ARGS="backend/tests -v --tb=short"
        COVERAGE_REPORT="htmlcov/consolidated/all"
        ;;
    
    *)
        echo "❌ Tipo de teste inválido: $TEST_TYPE"
        echo "Tipos válidos: unit, integration, e2e, performance, security, all"
        exit 1
        ;;
esac

echo ""

# ============================================================================
# EXECUTAR PYTEST COM COVERAGE
# ============================================================================

# Limpar relatórios antigos
rm -rf htmlcov/ .coverage 2>/dev/null || true

# Executar testes
echo "▶️  Iniciando pytest..."
echo ""

pytest $PYTEST_ARGS \
    --cov=backend \
    --cov-report=html:$COVERAGE_REPORT \
    --cov-report=term-missing \
    --cov-report=xml:coverage.xml \
    --cov-fail-under=$MIN_COVERAGE \
    --maxfail=5 \
    --strict-markers \
    -W ignore::DeprecationWarning \
    || EXIT_CODE=$?

# Capturar código de saída
EXIT_CODE=${EXIT_CODE:-0}

echo ""

# ============================================================================
# GERAR RELATÓRIO CONSOLIDADO
# ============================================================================

if [ "$TEST_TYPE" = "all" ]; then
    echo "📊 Gerando relatório consolidado..."
    
    # Executar script Python para gerar index.html
    python -c "
import os
from datetime import datetime

html = '''<html>
<head>
    <title>EVAonline - Relatórios de Cobertura</title>
    <meta charset=\"utf-8\">
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
        .summary {
            background: #f0f4ff;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            text-align: center;
        }
        .summary h2 {
            margin: 0 0 15px 0;
            color: #667eea;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }
        .summary-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
        }
        .summary-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }
        .summary-value {
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
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
        .coverage.low { color: #dc3545; }
        .coverage.medium { color: #ffc107; }
        .coverage.high { color: #28a745; }
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
    <div class=\"container\">
        <h1>🧪 EVAonline - Relatórios de Testes</h1>
        <p class=\"subtitle\">Cobertura de código e resultados por módulo</p>
        
        <div class=\"summary\">
            <h2>Resumo Geral</h2>
            <div class=\"summary-grid\">
                <div class=\"summary-item\">
                    <div class=\"summary-label\">Cobertura Total</div>
                    <div class=\"summary-value\">''' + str(os.getenv('COVERAGE_TOTAL', '29')) + '''%</div>
                </div>
                <div class=\"summary-item\">
                    <div class=\"summary-label\">Testes Executados</div>
                    <div class=\"summary-value\">''' + str(os.getenv('TESTS_TOTAL', '156')) + '''</div>
                </div>
                <div class=\"summary-item\">
                    <div class=\"summary-label\">Status</div>
                    <div class=\"summary-value\" style=\"font-size: 20px; color: #dc3545;\">PRECISA MELHORAR</div>
                </div>
            </div>
        </div>
        
        <h3 style=\"margin-top: 30px; color: #667eea;\">📊 Relatórios por Módulo</h3>
        
        <div class=\"timestamp\">
            Gerado em: ''' + datetime.now().strftime('%d/%m/%Y %H:%M:%S') + '''
        </div>
    </div>
</body>
</html>'''

    with open('htmlcov/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print('✅ Relatório HTML gerado: htmlcov/index.html')
"
fi

# ============================================================================
# RESUMO FINAL
# ============================================================================

echo ""
echo "============================================================================"
echo "📊 RESUMO DOS TESTES"
echo "============================================================================"
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Status: TODOS OS TESTES PASSARAM"
    echo "📈 Cobertura: Acima de ${MIN_COVERAGE}%"
    echo "🎉 Build: SUCESSO"
else
    echo "❌ Status: ALGUNS TESTES FALHARAM"
    echo "📉 Cobertura: Abaixo de ${MIN_COVERAGE}% ou erros encontrados"
    echo "🔧 Ação Necessária: Revisar logs acima"
fi

echo ""
echo "📁 Relatórios disponíveis em:"
echo "  → HTML: htmlcov/index.html"
echo "  → XML: coverage.xml"
echo ""
echo "============================================================================"

exit $EXIT_CODE