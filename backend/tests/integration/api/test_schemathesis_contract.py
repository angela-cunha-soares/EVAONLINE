"""
API Contract Testing - Using Schemathesis

Testa todos os endpoints contra schema OpenAPI automaticamente.
"""

import pytest

# Schemathesis só funciona com servidor rodando
# Marcar como integration + requires_docker
pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_docker,
    pytest.mark.skip(reason="Requer servidor rodando - rodar manualmente"),
]


@pytest.mark.skip(reason="Exemplo - rodar quando servidor estiver up")
def test_api_schema_compliance():
    """
    Testa compliance com OpenAPI schema.

    Para rodar:
    1. Inicie o servidor: uvicorn backend.main:app --reload
    2. Rode: pytest backend/tests/integration/api/
       test_schemathesis_contract.py -v
    """
    import schemathesis

    # Carregar schema OpenAPI
    schema = schemathesis.from_uri("http://localhost:8000/openapi.json")

    @schema.parametrize()
    @schemathesis.check
    def test_endpoint(case):
        """
        Testa cada endpoint do schema.

        Schemathesis gera automaticamente:
        - Payloads válidos e inválidos
        - Headers diversos
        - Query params
        - Path params
        """
        response = case.call_and_validate()
        return response


def test_schemathesis_example_manual():
    """
    Exemplo manual de teste com schemathesis.

    Este teste mostra como usar schemathesis programaticamente.
    """
    # Este é um exemplo - descomente quando servidor estiver rodando
    pass
    # import schemathesis
    #
    # schema = schemathesis.from_dict({
    #     "openapi": "3.0.0",
    #     "info": {"title": "Test API", "version": "1.0.0"},
    #     "paths": {
    #         "/api/health": {
    #             "get": {
    #                 "responses": {
    #                     "200": {
    #                         "description": "OK",
    #                         "content": {
    #                             "application/json": {
    #                                 "schema": {
    #                                     "type": "object",
    #                                     "properties": {
    #                                         "status": {"type": "string"}
    #                                     }
    #                                 }
    #                             }
    #                         }
    #                     }
    #                 }
    #             }
    #         }
    #     }
    # })
    #
    # @schema.parametrize()
    # def test_health(case):
    #     response = case.call()
    #     case.validate_response(response)


# =============================================================================
# COMANDOS ÚTEIS DE SCHEMATHESIS
# =============================================================================
"""
# 1. Rodar via CLI (mais fácil):
schemathesis run http://localhost:8000/openapi.json

# 2. Rodar com workers paralelos:
schemathesis run http://localhost:8000/openapi.json --workers=4

# 3. Apenas endpoints específicos:
schemathesis run http://localhost:8000/openapi.json -E /api/climate/*

# 4. Com checks específicos:
schemathesis run http://localhost:8000/openapi.json \\
    --checks=all \\
    --hypothesis-max-examples=50

# 5. Salvar resultados:
schemathesis run http://localhost:8000/openapi.json \\
    --report=./reports/schemathesis_report.json

# 6. Stateful testing (testa sequências de requests):
schemathesis run http://localhost:8000/openapi.json --stateful=links

# 7. Com auth:
schemathesis run http://localhost:8000/openapi.json \\
    --header="Authorization: Bearer <token>"
"""
