# Tasks: Assistente Aurora
## Phase 1: Setup
- [x] T001 Fixar dependências Python/ADK em pyproject.toml e uv.lock.
- [x] T002 Configurar ambiente e artefatos ignorados em .env.example e .gitignore.
## Phase 2: Foundation
- [x] T003 Criar banco, ownership marker e restore seguro em src/aurora/store.py e cli.py.
- [x] T004 Validar confirmação nativa do SDK e injeção exclusiva de teste em tests/fake_model.py.
## Phase 3: US1
- [x] T005 [US1] Escrever testes de contrato, isolamento e aprovação em tests/test_api.py.
- [x] T006 [US1] Implementar ferramentas com escopo da sessão em src/aurora/agents.py.
- [x] T007 [US1] Implementar Runner e seis rotas em src/aurora/runtime.py e api.py.
## Phase 4: US2
- [x] T008 [US2] Testar reinício com eventos e confirmação pendente em tests/test_api.py.
- [x] T009 [US2] Testar UNIQUE com aprovações concorrentes e códigos históricos em tests/test_api.py e test_store.py.
- [x] T010 [US2] Implementar persistência e retomada original em src/aurora/runtime.py.
## Phase 5: US3
- [x] T011 [US3] Testar capítulo isolado e horário domingo em tests/test_api.py.
- [x] T012 [US3] Implementar especialista regulamento em src/aurora/agents.py.
## Phase 6: Validation
- [x] T013 Documentar arquitetura/garantias/comandos/evidências em README.md e docs/validacao.md.
- [x] T014 Verificar hashes de dados/ e testes em clone limpo; registrar docs/clone-limpo.json.
- [x] T015 Revisar convergência e diff antes de commit/push feature.
## Dependencies & Execution Order
Setup → Foundation → US1 → US2 → US3 → Validation. Casos de testes podem ser executados
independentemente; implementação usa um único agente por restrição de coordenação.
## Implementation Strategy
Primeiro validar consentimento persistido no SDK; depois acrescentar domínio e API. Todos os
cenários críticos devem usar SQLite real. Testes de modelo falso não validam a qualidade de um modelo real.

## Phase 7: External acceptance validation

Os itens anteriores comprovam implementação e execução offline. A entrega acadêmica continua
separada da validação funcional: o provedor escolhido diverge do enunciado original.

- [x] T016 Executar os 15 passos funcionais do avaliador com Spark real, conforme preferência do autor; registrar modelo, resultados e eventos sem segredos. A divergência do requisito Gemini deve permanecer declarada.
  Nova rodada integral no código atual: 44 chamadas/125 checks aprovados; regressão real
  direcionada: 12 chamadas/64 checks aprovados. 24 testes offline passaram novamente.
  A rodada anterior de 109 checks e seu achado permanecem registrados, sem serem usados como
  prova do código corrigido. [Validação final](../../docs/spark-validation-final.md).

## Phase 8: Optional local development provider

- [x] T017 Especificar e implementar Spark experimental conforme [spark-experimental.md](spark-experimental.md), inicialmente mantendo Gemini default; decisão posterior T019 alterou o padrão. Naquela etapa T016 ainda estava aberto.
- [x] T018 Validar adapter via transporte HTTP de teste com ADK/SQLite reais e smoke Spark autorizado em bases temporárias; registrar docs/spark-smoke.json.

- [x] T019 Tornar Spark o padrão, documentar preferência/divergência e testar seleção ausente/vazia, alternativa Gemini e falta de configuração sem fallback.
