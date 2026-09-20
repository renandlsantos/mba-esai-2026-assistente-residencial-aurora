# Assistente Residencial Aurora

Desafio 309 do MBA em Engenharia de Software com IA. API local com Google ADK 2.9.2,
Spark local como provedor padrão e dados persistentes. A preferência do autor é executar
modelos locais por controle operacional e independência de chaves de geração na nuvem.
O consentimento e as regras de negócio continuam verificados em código. Os testes offline
usam ADK real com modelo roteirizado somente nos testes; há também smoke com Spark real.

**Decisão de implementação:** Spark substitui Gemini como padrão por solicitação do autor.
O enunciado original exige Gemini; essa é uma divergência documentada, sem alegação de
aprovação da instituição. A alternativa Gemini permanece selecionável explicitamente.
O roteiro de 15 passos foi executado com Spark; a revisão revelou leitura pelo histórico,
agora corrigida e coberta por regressão offline. A revalidação real direcionada está pendente
após HTTP 500 do backend Spark. [Resultado e limites](docs/spark-validation.md).

## Arquitetura

```mermaid
flowchart TD
    Cliente --> API[FastAPI: localhost:8000]
    API --> Runner[Runner ADK / App resumível]
    Runner --> Principal[Aurora: principal]
    Principal --> Reservas[Especialista reservas]
    Principal --> Visitantes[Especialista visitantes]
    Principal --> Regulamento[Especialista regulamento]
    Reservas --> Tools[Ferramentas com apartamento da sessão]
    Visitantes --> Tools
    Regulamento --> Capitulo[Somente capítulo solicitado]
    Tools --> SQL[(domain.sqlite3)]
    Runner --> Eventos[(adk.sqlite3: sessões e eventos)]
    API --> Decisao[Confirmação nativa + registro de decisão]
    Decisao --> Runner
```

- [`src/aurora/agents.py`](src/aurora/agents.py), `build_app`: principal e três especialistas;
  leitura/escrita exclusivamente por ferramentas. `FunctionTool` exige confirmação conforme taxa
  da área ou sempre para visitantes. `App` habilita `ResumabilityConfig`.
  O contexto do modelo inclui apenas o turno atual (`include_contents="none"`), para não reutilizar
  dados antigos. `session_identity` fornece a unidade autenticada; o controle permanece nas tools.
  Os eventos completos continuam persistidos. Novos pedidos devem explicitar seus dados;
  referências vagas a turnos anteriores podem exigir esclarecimento.
- [`src/aurora/runtime.py`](src/aurora/runtime.py), `Runtime`: `DatabaseSessionService` e `Runner`;
  namespace `app_name=aurora`, `user_id=session_id`. Recompõe pendências dos eventos persistidos,
  não de uma lista em memória. A resposta de confirmação leva o ID nativo e a invocação original.
- [`src/aurora/store.py`](src/aurora/store.py), `Store`: banco de domínio com unidades, áreas,
  reservas, visitantes, vínculo imutável da sessão, decisões e operações idempotentes.
- [`src/aurora/api.py`](src/aurora/api.py): contrato HTTP e códigos 404/409; modelos de entrada
  recusam campos extras. `confirmado` aceita somente booleano.

| Método e rota | Corpo / resultado |
| --- | --- |
| `POST /sessoes` | `{ "apartamento": "101" }` → 201 `{ "session_id": "..." }` |
| `POST /sessoes/{id}/mensagens` | `{ "texto": "Reserve a quadra para 6 de abril de 2030" }` → 200 resposta |
| `POST /sessoes/{id}/confirmacoes` | `{ "id": "...", "confirmado": true }` → 200 resposta ou 409 |
| `GET /sessoes/{id}/eventos` | Lista integral de eventos ADK em ordem |
| `GET /apartamentos/{ap}/reservas` | `[{ "codigo": "...", "area": "...", "data": "..." }]` |
| `GET /apartamentos/{ap}/visitantes` | `[{ "nome": "...", "data": "..." }]` |

Resposta de conversa/decisão: `{ "resposta": "...", "confirmacoes_pendentes":
[{ "id": "...", "acao": "reservar_area", "detalhes": { "area": "salao-de-festas",
"data": "2030-04-20", "taxa": 150.0 } }] }`.
Sessão desconhecida retorna 404 em todas as suas rotas. Apartamento desconhecido na criação:422.
Os GETs por apartamento são endpoints locais de inspeção exigidos pelo exercício;
não são ferramentas dos agentes. Autenticação está fora do escopo.

## Garantias

| Garantia | Implementação | Evidência offline |
| --- | --- | --- |
| Consentimento só pela rota | `Runtime.confirm` confere pendência da sessão, registra decisão UNIQUE e envia `FunctionResponse(adk_request_confirmation)`; `permitted` exige confirmação nativa **e** decisão com sessão/chamada/argumentos iguais | `test_native_confirmation_restart_isolation`, `test_approved_flag_without_route_decision_cannot_write` |
| Isolamento de unidade | `apartment` consulta `Store.apartment(context.session.id)`; nenhuma ferramenta recebe apartamento como parâmetro; consultas/cancelamento filtram a unidade | `test_full_domain_journey_and_chapter`, `test_occupied_area_never_exposes_owner` |
| Persistência | Sessões/eventos no ADK SQLite, domínio no SQLite separado; pendências derivam do histórico | `test_actual_process_restart_with_pending_visitor`: encerra processo próprio, abre outro, compara eventos e aprova no especialista correto |
| Contexto do regulamento | `consultar_regulamento` escolhe um cabeçalho a partir do tópico; retorna apenas aquele capítulo; texto integral nunca entra nas instruções | Pergunta da piscina retorna capítulo IV / domingo até 20h; canários de capítulos alheios ausentes dos eventos |
| Exclusividade | Índice `UNIQUE(area,data) WHERE ativa=1` no INSERT; conflito é resultado normal `indisponivel` | Duas aprovações HTTP simultâneas: 200/200, um vencedor; também duas threads disputando SQLite |

Reservas gratuitas e cancelamentos próprios não exigem aprovação. Reservas pagas e visitantes
aguardam a decisão; texto “confirmo” não é resposta de sistema. Enquanto houver pendência, nova
mensagem apenas devolve essa pendência. IDs desconhecidos, alheios ou já respondidos retornam 409.
Códigos usam UUID; cancelamento é lógico, preservando o código histórico. Operações já aplicadas
são idempotentes por sessão/chamada. Disponibilidade nunca retorna unidade ou código de terceiros.

Limites operacionais: executar um processo/worker, como no comando abaixo. Os locks por sessão
são locais, enquanto a exclusividade das reservas reside no banco. Não há transação distribuída
entre os dois bancos nem garantia de conclusão após crash no meio de uma aprovação. A decisão
é consumida antes de retomar o Runner: se houver falha nesse intervalo, inspecione eventos e dados;
não reenvie a mesma confirmação esperando nova execução. Falhas de modelo propagam erro, nunca
sucesso fictício. A falta de configuração retorna 503 antes de consumir uma decisão.

As fontes públicas `dados/` estão intactas; [hashes](docs/upstream-integrity.json) são testados.
[`docs/validacao.md`](docs/validacao.md) detalha a cobertura e as pendências externas.
O SDD está em [`specs/001-assistente-aurora/`](specs/001-assistente-aurora/), governado pela
[constituição](.specify/memory/constitution.md). Spec Kit oficial 1.0.8.

Conceitos consultados no acervo local, sem publicar transcrições:
[Aprovando Execução de Tools](https://plataforma.fullcycle.com.br/courses/a091b0fe-a5c6-4287-a3d3-1ec61defcfd3/413/224/290/conteudos?capitulo=290&conteudo=18102),
[Idempotência](https://plataforma.fullcycle.com.br/courses/a091b0fe-a5c6-4287-a3d3-1ec61defcfd3/413/224/290/conteudos?capitulo=290&conteudo=18561),
[Limitação do Workflow com Tool Confirmation](https://plataforma.fullcycle.com.br/courses/a091b0fe-a5c6-4287-a3d3-1ec61defcfd3/413/224/290/conteudos?capitulo=290&conteudo=18578),
[Persistência da sessão no banco de dados](https://plataforma.fullcycle.com.br/courses/a091b0fe-a5c6-4287-a3d3-1ec61defcfd3/413/224/290/conteudos?capitulo=290&conteudo=18485).
A limitação descrita na aula foi tratada com teste na versão fixada, não presumida como resolvida.

## Como rodar

Requisitos: Python 3.12 ou 3.13 e [uv](https://docs.astral.sh/uv/). Na raiz do clone:

```bash
uv sync --frozen --no-editable
uv run --no-editable aurora restore
cp .env.example .env
# O Spark lê a credencial externa; ajuste SPARK_ENV_FILE se necessário.
uv run --no-editable aurora start
```

O `--no-editable` também evita que o iCloud marque o `.pth` editável como oculto, o que faz
Python 3.12 ignorar o caminho do pacote. Após mudar código local, use
`uv sync --frozen --no-editable --reinstall-package assistente-residencial-aurora`.

`.env.example` contém apenas configuração não secreta e campos vazios de credenciais.
A chave permanece no arquivo externo; `.env` é ignorado pelo Git. O padrão usa `spark/code`
com timeout de 300 segundos e 4096 tokens. Ausência de configuração gera erro explícito,
sem resposta fictícia nem fallback para nuvem.

Para selecionar Gemini opcionalmente, configure `AURORA_MODEL_PROVIDER=gemini`,
`GOOGLE_API_KEY` e `GEMINI_MODEL` no ambiente local. Essa alternativa foi preservada,
mas não é o caminho preferido nem foi avaliada com modelo real nesta entrega.

O servidor escuta exclusivamente `http://127.0.0.1:8000`; contrato interativo em `/docs`.
Exemplo de criação:

```bash
curl -s http://127.0.0.1:8000/sessoes -H 'Content-Type: application/json' \
  -d '{"apartamento":"101"}'
# Use o session_id retornado nas rotas de mensagens e confirmações.
```

**Restore:** pare o servidor antes. `aurora restore` recarrega os JSONs originais e remove também
sessões/eventos/decisões. Opera somente nos nomes fixos `domain.sqlite3` e `adk.sqlite3` e seus
journals dentro de `.runtime/aurora/`, após verificar o marcador `OWNER`. Recusa diretório não vazio
sem marcador e links simbólicos. Não recebe caminho de banco externo e não remove outros arquivos.

Testes, sem chave e sem rede de modelo:

```bash
uv run --no-editable pytest -q
```

Os testes de HTTP abrem apenas processos próprios em portas efêmeras e os encerram ao terminar.
As chamadas do modelo de teste são roteirizadas: comprovam código/ADK/SQL, não interpretação de
linguagem natural. A rodada inicial Spark teve 41 chamadas e 109 checks positivos, mas revelou
uma leitura de reservas pelo histórico. A correção passou em 24 testes; sua revalidação real
está pendente por HTTP 500 do Spark. [Evidências](docs/spark-validation.md).
A diferença em relação ao provedor exigido no enunciado permanece declarada. Referências técnicas:
[confirmação nativa ADK](https://adk.dev/tools-custom/confirmation/),
[Google ADK no PyPI](https://pypi.org/project/google-adk/2.9.2/).

### Modelos locais preferidos: Spark

O padrão é Spark quando `AURORA_MODEL_PROVIDER` está ausente, vazio ou definido como `spark`.
Com ambiente e dados inicializados, execute:

```bash
uv run --no-editable aurora start
```

Somente nesse modo, `SPARK_BASE_URL` e `SPARK_API_KEY` são lidos do ambiente ou de
`~/.config/spark/spark-api.env`. `SPARK_ENV_FILE` permite selecionar outro dotenv local;
valores do ambiente têm prioridade. O arquivo deve apontar para a base OpenAI compatível
do servidor autorizado, normalmente terminando em `/v1`. Não copie sua chave para o repositório.
O CLI lê apenas o `.env` da raiz atual, sem procurar arquivos ancestrais.

[`src/aurora/models.py`](src/aurora/models.py) seleciona o provedor e
[`src/aurora/spark.py`](src/aurora/spark.py) implementa um adapter `BaseLlm` limitado a texto
e chamadas nativas de ferramentas. Usa `spark/code`, `max_tokens=4096`, timeout de 300 segundos,
sem streaming, retry automático, fallback para nuvem ou leitura de raciocínio interno.
IDs e resultados de tools passam pelo ADK; confirmação e regras continuam nas mesmas camadas.
O adapter usa `httpx`, dependência já presente e agora declarada em runtime. Não adiciona LiteLLM.

Smoke real opt-in, com cópia temporária dos dados públicos e no máximo 15 chamadas sequenciais:

```bash
AURORA_MODEL_PROVIDER=spark uv run --no-editable python scripts/smoke_spark.py \
  --output .runtime/spark-smoke.json
```

Em 20/09/2026, o smoke passou com **11 chamadas reais**, reserva gratuita, cobrança pendente,
aprovação após reinicializar o runtime, replay 409 e isolamento. [Evidência](docs/spark-smoke.json)
e [limites do experimento](docs/spark-experimental.md). A validação posterior está em
[spark-validation.md](docs/spark-validation.md); T016 permanece aberto para a correção ainda sem rerun real concluído.
