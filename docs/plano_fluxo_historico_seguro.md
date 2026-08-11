# Plano — Fluxo seguro de requisição histórica (confirmação + fila + link de download 48h)

Status: **proposta para aprovação** (nada implementado ainda).
Decisões já tomadas com a Angela:

- Confirmação **híbrida**: e-mail verificado **1×**, válido **30 dias**; dentro do prazo, novos pedidos não exigem novo clique.
- Entrega por **link de download** válido **48 h** (arquivo apagado automaticamente depois).
- Controle de carga por **limite de 10 requisições/dia por e-mail** (já existe). Ao atingir 10, o e-mail é bloqueado até o dia seguinte (UTC). Não haverá fila "uma por vez".

---

## 1. Objetivos

- Impedir e-mails falsos / robôs sobrecarregando o banco (confirmação antes de processar).
- Reduzir carga do servidor (limite diário por e-mail + teto global já existentes).
- Entregar resultados de forma robusta e escalável (link que expira, com limpeza automática).

---

## 2. Fluxo do usuário (passo a passo)

1. **Home**: informa os 3 modos (Histórico, Recente, Previsão).
2. **Histórico**: a tela mostra o campo de **e-mail** + **datas** + **formato** (todos visíveis).
   O usuário preenche tudo.
3. Clica em **"Confirmar"**:
   - **E-mail já verificado (≤ 30 dias)** → a requisição entra direto na fila de processamento (vai ao passo 5).
   - **E-mail não verificado** → o site mostra *"Requisição registrada, confira sua caixa de entrada"*;
     o pedido é guardado como **pendente** (Redis, TTL 30 min) e é enviado o **1º e-mail** (link de confirmação).
4. *(só na 1ª vez / após 30 dias)* Usuário clica no **link de confirmação** →
   o e-mail é marcado como verificado (30 dias) **e** o pedido pendente entra na fila.
5. **2º e-mail — "Processamento iniciado"**: avisa que entrou na fila (pode demorar conforme o tamanho).
6. **Processamento** (Celery, assíncrono).
7. **3º e-mail — "Resultados prontos"**: contém o **link de download** (válido 48 h).
8. **Após 48 h**: o arquivo é apagado automaticamente (tarefa periódica). Para obter de novo, refazer o fluxo.

> Observação de UX: isto **substitui** o fluxo atual (verificar e só então liberar datas). No novo, os
> campos aparecem juntos e o gate acontece no "Confirmar". Mais próximo da sua proposta e mais simples.

---

## 3. Regras e limites

- **10 requisições/dia por e-mail** (reset meia-noite UTC). Na 11ª: bloqueio "limite diário atingido".
- Mantém as camadas já criadas: limite por IP/visitor, **teto global diário**, **fail-closed**, **alertas de abuso**, **token interno**, bloqueio do `/internal/` no Nginx.
- **Link de download**: token aleatório longo (não sequencial), endpoint público `GET /api/v1/download/{token}`.
  Valida expiração, entrega o arquivo com headers corretos. Opcional: exigir o mesmo e-mail.
- **Armazenamento**: arquivos no volume `./data/results/` (já montado no container). Metadados
  (token → caminho, expira_em, e-mail, tamanho) em Redis (com TTL) e/ou tabela no Postgres.
- **Limpeza**: tarefa **Celery Beat** de hora em hora remove arquivos/metadados expirados.

---

## 4. Componentes a criar / alterar

### Backend
- `backend/api/security/pending_request.py` *(novo)* — guardar/consumir o pedido pendente por token (1ª vez).
- `backend/infrastructure/storage/result_files.py` *(novo)* — salvar arquivo, gerar token, TTL 48 h,
  resolver token→arquivo, apagar; função de limpeza de expirados.
- `backend/api/routes/download_routes.py` *(novo)* — `GET /download/{token}` (público, fora de `/internal/`).
- `backend/api/routes/verification_routes.py` *(alterar)* — ao confirmar o e-mail: marcar verificado **e**,
  se houver pedido pendente do token, **enfileirar** a tarefa Celery.
- `backend/api/routes/eto_routes.py` *(alterar)* — no `/calculate` do histórico:
  - verificado → enfileira direto + dispara "2º e-mail (iniciado)";
  - não verificado → salva pendente + envia "1º e-mail (confirmação)" e responde `verification_required`.
- `backend/infrastructure/celery/tasks/eto_calculation.py` *(alterar)* — ao terminar: **salvar arquivo**
  no storage, gerar token/link, enviar **3º e-mail (resultados com link)** (em vez de anexo).
- `backend/infrastructure/celery/` *(novo task + agendamento no Beat)* — `cleanup_expired_downloads`.
- `backend/core/utils/email_utils.py` / templates *(alterar)* — 3 e-mails PT/EN (confirmação, iniciado,
  resultados-com-link) com o rodapé padronizado.
- `config/settings/app_config.py` *(alterar)* — `DOWNLOAD_TTL_HOURS=48`, `RESULTS_STORAGE_DIR`,
  `DOWNLOAD_BASE_URL` (usa `PUBLIC_BASE_URL`).

### Frontend
- `frontend/callbacks/eto_callbacks.py` / `render_conditional_form` *(alterar)* — mostrar e-mail + datas +
  formato juntos; botão **"Confirmar"**; telas de estado: *"confira seu e-mail"* (1ª vez) e
  *"sua requisição entrou na fila"* (já verificado).
- Tratar as respostas do backend: `verification_required` vs `queued`.

### Documentação
- `frontend/pages/documentation.py` + traduções — atualizar limites (10/dia por e-mail), validade de 30 dias,
  os 3 e-mails, o link de 48 h e a limpeza automática.

---

## 5. Segurança e deliverability (crítico)

- **SPF/DKIM no domínio do Resend** — se o e-mail de confirmação cair no spam, o fluxo inteiro trava.
  É pré-requisito antes de tornar o fluxo obrigatório em produção.
- Token de download **longo e aleatório** (`secrets.token_urlsafe`), nunca ID sequencial.
- Pedido pendente com **TTL curto** (30 min); token de confirmação de uso único.
- Manter fail-closed, teto global e alertas.

---

## 6. Riscos e decisões em aberto

- Reverter o "liberar campos só após verificar" para "mostrar tudo + Confirmar" — **recomendado** (alinha à sua proposta).
- Guardar metadados do download em Redis (simples, TTL nativo) **ou** Postgres (histórico/auditoria). Sugiro Redis + registro leve no Postgres.
- Testes automatizáveis: storage/token/TTL, pending request, limpeza, gates. O caminho e-mail↔Celery
  precisa de **validação em staging** (não dá para testar 100% aqui).

---

## 7. Ordem de implementação sugerida

1. Storage de resultados (salvar/gerar token/TTL) + testes unitários.
2. Endpoint de download + tarefa de limpeza (Beat).
3. Pedido pendente (1ª vez) + verificação que enfileira.
4. Alterar a task Celery: salvar arquivo, gerar link, enviar os 3 e-mails.
5. Ajustar `/calculate` (verificado→fila; não→pendente+confirmação).
6. Frontend: formulário + telas de estado.
7. Documentação.
8. Testes + validação em staging (com SPF/DKIM configurados).

---

## 9. Status da implementação (concluída) + validação em staging

Todas as 8 etapas foram implementadas e testadas em nível de lógica (unitários com
Redis/arquivos simulados) e de compilação. Resumo do que foi entregue:

- **Storage** (`backend/infrastructure/storage/result_files.py`): salvar/token/TTL/resolver/limpar.
- **Download** (`backend/api/routes/download_routes.py`): `GET /api/v1/download/{token}` (público).
- **Limpeza** (`.../celery/tasks/download_cleanup.py` + Beat a cada hora, min 15).
- **Pendente** (`backend/api/security/pending_request.py`) + `email_verification.send_verification(pending=...)`.
- **Confirmação enfileira** (`verification_routes.py`): o clique confirma o e-mail (30 dias) e enfileira o job.
- **Task** (`eto_calculation.py`): salva arquivo em memória → link de download; e-mail de resultados com botão (48h). O e-mail "processamento iniciado" continua no STEP 0.
- **/calculate** (`eto_routes.py`): verificado → enfileira; não verificado → guarda pendente + envia confirmação. Conta no limite diário mesmo pendente.
- **Frontend** (`eto_callbacks.py`): histórico mostra e-mail + datas + formato juntos; "Calcular" = "Confirmar"; resposta `verification_required` mostra "confira seu e-mail".
- **Docs** atualizadas (10/dia por e-mail, 30 dias, 3 e-mails, link 48h).

### Compartilhamento de storage (confirmado)
`api`, `api-dev`, `celery-worker*` montam `./data:/app/data` (ou `.:/app` no dev), então o
arquivo salvo pelo worker é servido pela API pelo mesmo `data/results/`. ✔

### Checklist de validação em STAGING (não dá para testar 100% aqui)
1. **SPF/DKIM no Resend** para o domínio remetente — pré-requisito; sem isso os e-mails podem cair no spam e travar o fluxo.
2. `PUBLIC_BASE_URL` correto no ambiente (produção: `https://evaonline.app.br`; dev local: `http://localhost:8050`) — usado nos links de confirmação e download.
3. Fluxo ponta a ponta: histórico → Confirmar → 1º e-mail (link) → clicar → 2º e-mail (iniciado) → 3º e-mail (link download) → baixar → após 48h, link expira e arquivo é apagado (rodar a task `storage.cleanup_expired_downloads`).
4. Conferir que o Celery Beat está ativo (serviço `celery-beat`) para a limpeza horária.
5. Recriar containers após deploy (`up -d --force-recreate`), pois o `--reload` não pega mudanças no Windows/bind mounts.

---

## 8. O que já está pronto (reaproveitado)

- Verificação de e-mail (30 dias) e endpoints `request-verification` / `verification-status`.
- Limite de 10/dia por e-mail, por IP, por visitor; teto global; fail-closed; UTC; alertas de abuso.
- Token interno Dash↔backend; bloqueio do `/internal/` no Nginx.
