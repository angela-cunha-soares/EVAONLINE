# Auditoria de engenharia — EVAonline

Data: 10/08/2026. Escopo: testes, bugs prováveis, documentação, interface e boas
práticas. Método: análise estática (compileall, flake8), revisão de código,
consistência de i18n, execução dos testes possíveis no ambiente disponível.

> Nota de ambiente: a suíte completa exige o ambiente real (PostgreSQL, Redis,
> Python 3.12 e todas as dependências). O sandbox usa Python 3.10, então rodei
> os testes que independem disso e validei a lógica dos módulos novos com testes
> dedicados (17/17 passando).

---

## Resumo executivo

O projeto está em bom estado: **todos os 336 arquivos `.py` compilam**, **não há
nomes indefinidos nem erros de sintaxe** (flake8 F-codes limpos, exceto imports/
variáveis não usados), as **957 chaves de i18n estão 100% consistentes** entre PT
e EN, e os **segredos não estão versionados** (`.env` no `.gitignore`). Nenhum bug
crítico ativo foi encontrado. Os pontos principais são: (a) faltavam testes para os
módulos novos — **corrigido nesta auditoria**; (b) alguns trechos de **código morto**
(callbacks órfãos); (c) pequenas **inconsistências de texto/config**.

---

## O que foi corrigido nesta auditoria

- **Testes novos (17)**: criados `backend/tests/unit/infrastructure/test_result_files.py`
  e `backend/tests/unit/api/test_security_modules.py`, cobrindo storage/token/TTL/
  limpeza, proof-of-work, token interno, pedido pendente, verificação de e-mail
  (fluxo + TTL de 30 dias), monitor de abuso e teto global. **17/17 passando.**
- **Código morto que eu havia deixado**: removidos `file_path`/`temp_dir`/`Path`
  não usados em `eto_calculation.py`, `Optional` não usado em `abuse_monitor.py`.
- **Componentes órfãos do frontend**: removidos `email-verify-poll` e
  `email-verified-store` (sobraram do fluxo antigo) do `base_layout.py` e a `State`
  correspondente em `render_conditional_form`; docstring atualizada.
- **Textos "anexo" → "link de download"** (rodada anterior) em e-mails, UI e docs.

---

## Achados por prioridade

### 🔴 Crítico
Nenhum. Não há bug ativo que quebre a aplicação em produção.

### 🟠 Alto
1. **Cobertura de testes dos módulos novos era zero** (segurança + storage).
   → **Resolvido**: 17 testes adicionados. Recomendado incluir no CI.

### 🟡 Médio
1. **Callbacks órfãos / endpoint inexistente** (`frontend/callbacks/home_callbacks.py`):
   `update_api_status` e `update_services_status` referenciam componentes que não
   existem no layout (`api-status-display`, `services-status-display`,
   `interval-component`) — nunca disparam. Além disso, um deles chama
   `http://localhost:8000/api/v1/api/internal/services/status` (com `/api/`
   duplicado e rota inexistente). **Recomendação:** remover os dois callbacks
   mortos (não removi por estar fora do escopo do que já mexemos; posso remover).
2. **Inconsistência "5 dias" vs "6 dias" (Previsão)**: a UI diz ora "Previsão (5
   dias)", ora "modo Forecast (6 dias)". Tecnicamente hoje+5 = 6 dias no total,
   mas confunde. **Recomendação:** padronizar o texto (ex.: sempre "5 dias à
   frente" ou sempre "6 dias no total").
3. **Templates de ambiente incompletos**: `.env.docker` e `.env.production` não
   têm as configs de e-mail/Resend, `PUBLIC_BASE_URL`, nem as novas variáveis de
   segurança. O `.env` ativo já foi ajustado; para produção, garanta esses valores
   no `.env` do servidor (RESEND_FROM com domínio verificado, PUBLIC_BASE_URL do
   domínio real, REQUIRE_EMAIL_VERIFICATION, etc.).
4. **`CELERY_BROKER_URL` sem senha no `.env`**: mitigado no código
   (`celery_config._inject_redis_auth` injeta a senha), mas o ideal é corrigir a
   linha no `.env`/templates para clareza.

### 🟢 Baixo (limpeza / boas práticas)
1. **Imports/variáveis não usados** (flake8 F401/F841) pré-existentes:
   `websocket_service.py` (F811 `asyncio`/`AsyncResult` redefinidos),
   `results_graphs.py` (`st`), `results_statistical.py` (`dv`),
   `cache_callbacks.py` (`PreventUpdate`), `eto_callbacks.py` (`pandas`),
   `footer.py` (`texts`, dentro de `create_simple_footer`, que é legado/sem uso).
2. **Código morto**: `send_html_email_with_attachment` deixou de ser usado (a
   entrega passou a ser por link). Manter só se for virar fallback SMTP; senão
   remover. `create_simple_footer` também parece legado.
3. **`except Exception:` amplos** em alguns pontos de resiliência (clientes NWS,
   websocket, callbacks) — aceitáveis, mas idealmente logar o erro.
4. **Endpoint de download sem rate-limit próprio**: risco baixo (token aleatório
   de 32 bytes + expira em 48h), mas dá para adicionar um `limit_req` no Nginx.

---

## O que foi verificado e está OK ✅

- **Compilação**: 336 arquivos `.py` compilam; 0 erros de sintaxe.
- **Nomes/imports**: 0 `F821` (nome indefinido), 0 `E999` (sintaxe).
- **i18n**: 957 chaves em EN e PT, **0 divergências** (nenhuma chave faltando de
  um lado ou de outro).
- **Segredos**: `.env` e `.env.*` no `.gitignore`; `.env` **não** rastreado pelo git.
- **Saúde**: endpoints `/api/v1/health`, `/health/detailed` e `/ready` existem.
- **Dependências**: os módulos novos usam só stdlib + libs já presentes (redis,
  loguru, fastapi) — **nenhuma dependência nova** a instalar.
- **Segurança do fluxo histórico** (rate-limit por IP/visitor/e-mail, teto global,
  fail-closed, token interno, bloqueio do `/internal/` no Nginx, verificação de
  e-mail, PoW, alertas) — implementada e agora coberta por testes.
- **Fatos do artigo na documentação** (186.286 observações; estações BR-DWGD)
  corrigidos em rodada anterior.

---

## Não verificável neste ambiente (fazer no seu)

1. **Suíte de testes completa** (`pytest`): precisa de Postgres + Redis + todas as
   deps + Python 3.12. Rode no seu ambiente/CI:
   `pytest backend/tests -q` (com os serviços de docker-compose no ar).
2. **Renderização ao vivo da UI** e todos os callbacks Dash.
3. **Deliverability de e-mail** (reputação do domínio Resend, DMARC).

---

## Recomendações finais (curto prazo)

1. Rodar `pytest` completo no CI (incluindo os 17 testes novos) e corrigir eventuais
   testes antigos que assumam o e-mail com anexo (ex.: `test_infra_tasks_phase6`).
2. Remover os 2 callbacks órfãos de `home_callbacks.py`.
3. Padronizar o texto "5 dias vs 6 dias" da Previsão.
4. Preencher `.env.production`/`.env.docker` (e-mail, PUBLIC_BASE_URL, segurança).
5. Adicionar registro **DMARC** no DNS do `evaonline.app.br` para melhorar a entrega.
6. Limpar imports/variáveis não usados (flake8 `--select=F401,F811,F841`).
