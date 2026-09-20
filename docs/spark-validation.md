# Roteiro funcional Spark e correção de contexto — 20/09/2026

O roteiro de 15 passos foi executado com `spark/code`, API HTTP, Google ADK 2.9.2
e SQLite reais, em cópias temporárias dos dados públicos. A rodada inicial passou
109 verificações automatizadas em 41 chamadas ao modelo, mas a revisão dos eventos
encontrou uma leitura de reservas pelo histórico. Portanto, o `passed: true` no JSON
daquela rodada descreve seus checks, **não aprovação final do requisito de leitura por tools**.

O Spark é o provedor escolhido pelo autor. O enunciado exige Gemini; essa divergência
continua declarada. Não se reivindica aceite institucional, merge ou submissão.

## Evidências e escopo

- [Rodada inicial integral](spark-acceptance-initial.json): produção em `35d434c`,
  14:11:58–14:13:16 UTC; 41 chamadas, 109 checks. Dois processos HTTP distintos,
  portas efêmeras em 127.0.0.1, ambos encerrados. Não houve substituição de respostas
  do modelo. A instrumentação apenas limita a quantidade de chamadas.
- [Primeira tentativa direcionada](spark-context-regression-attempt-1.json): uma
  chamada; o cliente não conseguiu decodificar a resposta. O diagnóstico inicial
  era insuficiente e foi corrigido no harness; não se deduz a causa desse registro.
- [Segunda tentativa direcionada](spark-context-regression-attempt-2.json): uma
  chamada; `SparkProtocolError: Spark respondeu HTTP 500.`; a API respondeu 500.
  Nenhuma tool chegou a executar. Nenhum corpo/credencial/header do provedor foi salvo.
- `tests/test_context.py`: regressão local com ADK real, banco real e modelo
  roteirizado exclusivo de teste. Demonstra que dados e capítulo de um turno anterior
  não são enviados ao modelo no turno seguinte, enquanto todos os eventos permanecem
  disponíveis pela API. Uma reserva removida entre leituras não reaparece no resultado.
- Suíte local após a correção: **24 testes passaram**, quatro avisos upstream
  (depreciação e recursos experimentais do ADK). Ruff e formatação verificados.
- [Clone limpo do commit 06bc09d](spark-context-clone.json): instalação frozen/offline,
  24 testes, restore e boot pelo CLI em 127.0.0.1:8000; dados iniciais e sessão201 corretos,
  fontes intactas, checkout limpo e processo encerrado. Nenhuma chamada ao modelo.
- [Comparação do primeiro request](spark-request-comparison.json), sem chamadas reais:
  payload capturado pelo SDK antes/depois idêntico exceto a identidade confiável acrescentada
  ao sistema. Isso descarta mudança de roles, schema ou parâmetros como causa desse 500;
  não explica o erro interno do provedor, cujo corpo não foi coletado.

As 43 chamadas desta validação se somam ao smoke histórico separado, que usou 11.
As falhas direcionadas não foram substituídas por novas execuções cegas. A validação
real da correção de contexto permanece pendente de o backend Spark voltar a responder.

## Resultado por etapa da rodada inicial

| Etapa | Resultado observado |
| --- | --- |
| 1–2 | Restore pelo CLI em cópia descartável; dados iniciais corretos e sessão 201. |
| 3–4 | Nenhuma exposição de RSV-4821/Marina Duarte; reserva do 302 preservada. O modelo chamou a unidade de 302 no texto, embora lesse somente o 101 — ver correção abaixo. |
| 5–6 | Cancelamento próprio e reserva gratuita sem confirmação. |
| 7 | Cobrança pendente com área/data/taxa; recusa não gravou reserva. |
| 8–9 | Aprovação gravou uma vez; replay e ID desconhecido 409; sessão desconhecida 404. |
| 10 | Data ocupada recusada sem código/unidade alheios na resposta. |
| 11 | Texto “já estou confirmando” não autorizou visitante; somente a rota gravou Joana Ribeiro. |
| 12 | Piscina domingo até 20h; somente capítulo IV nos eventos até essa etapa. |
| 13 | 71 eventos integralmente iguais após encerrar e reiniciar o processo; dados/códigos/visitante persistiram; nova mensagem 200. A leitura operacional usou memória e consultou capítulo VI desnecessariamente — achado confirmado. |
| 14 | Duas aprovações HTTP concorrentes retornaram 200/200; exatamente uma reserva. |
| 15 | ADK fixado, cinco hashes de dados íntegros, principal e três especialistas, índice UNIQUE. Inspeção complementar confirma apartamento oriundo da sessão e consentimento em código. |

O harness usa portas efêmeras para não interferir em outros projetos. O comando público
`aurora start` continua vinculado a 127.0.0.1:8000; o boot nessa porta e instalação em
clone limpo têm evidências próprias, separadas da conversa com o modelo.

## Achado, causa e correção

Na etapa 13, `regulamento` continuou como agente ativo do turno anterior e recebeu
todo o histórico. Consultou o capítulo VI e respondeu as reservas copiando os resultados
anteriores, sem `minhas_reservas`. Os dados coincidiam com o banco naquela ocasião,
mas poderiam estar desatualizados. A assertiva de persistência não detectava essa violação.
O harness integral agora exige `minhas_reservas` nesse turno e verifica novamente os capítulos;
não basta retornar 200 e preservar as linhas do banco.

Em `src/aurora/agents.py`, os agentes agora usam `include_contents="none"`, opção pública
do ADK que inclui o turno atual e suas tools, inclusive o par de chamada/resultado de uma
confirmação retomada, mas exclui conversas anteriores do contexto do modelo. Os eventos
continuam persistidos integralmente. O callback `session_identity` fornece a unidade
autenticada obtida do banco, tornando explícita a origem dos resultados. O controle de
acesso permanece nas ferramentas; essa informação de sistema não o substitui.

Não houve alteração de perguntas para induzir o modelo a passar. Nenhuma regra foi movida
para o prompt. Topologia, tools, decisões, schema e roteamento nativo foram preservados.
As alternativas de forçar retorno ao principal foram descartadas após regressões locais
de retomada; não estão na implementação. O teste de confirmação após reinício continuou
verde com a solução final.

Consequência deliberada: cada novo pedido deve fornecer seus dados, ou o assistente precisa
pedir esclarecimento; referências vagas a turnos anteriores não têm memória automática.
Esta correção impede reaproveitar valores antigos do contexto. Não prova que um modelo
arbitrário nunca inventará uma resposta; o rerun real exige observar uma leitura nova pela tool.

## Reprodução

Com a credencial externa Spark já configurada, sem colocá-la no repositório:

```bash
uv sync --frozen --no-editable --reinstall-package assistente-residencial-aurora
uv run --frozen --no-editable pytest -q
uv run --frozen --no-editable python scripts/acceptance_spark.py \
  --context-only --max-calls 20 --output .runtime/spark-context-regression.json
```

O modo direcionado testa a alegação de unidade alheia, consulta da piscina, visitante pendente,
reinício de processo, aprovação/replay e nova leitura operacional. Entre os processos, cancela
uma reserva exclusivamente no banco temporário, representando outra operação autorizada, para
que uma resposta baseada no histórico seja detectada. O JSON registra essa alteração de teste.

Para nova execução integral, use o mesmo script sem `--context-only`, com `--max-calls 50`.
O limite persiste entre os subprocessos; cada invocação também mantém o teto do ADK.
Não existe retry automático nem fallback. A suíte offline não faz chamadas ao Spark.
