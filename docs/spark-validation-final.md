# Validação funcional final com Spark — 20/09/2026

Os **15 passos do roteiro passaram no código atual**: 44 chamadas reais a `spark/code`
e 125 verificações. A regressão real de contexto passou separadamente, com 12 chamadas
e 64 verificações. A suíte local passou novamente em 24 testes. T016 está concluído
para Spark, provedor escolhido pelo autor; o enunciado exige Gemini e essa divergência
continua explícita, sem alegação de aceite institucional.

## Evidências novas

| Execução | Resultado | Evidência |
| --- | --- | --- |
| Roteiro integral, 14:51:35–14:53:47 UTC | 15 etapas, 44 chamadas, 125 checks, todos aprovados | [JSON integral](spark-acceptance-final.json) |
| Regressão direcionada, 14:50:28–14:50:52 UTC | 12 chamadas, 64 checks, todos aprovados | [JSON direcionado](spark-context-regression-final.json) |
| Suíte offline na retomada | 24 passed, 4 avisos upstream, 2,95s | `uv run --frozen --no-editable pytest -q` |
| Clone limpo da implementação | Frozen/offline, 24 testes, restore, boot127.0.0.1:8000, dados iniciais e sessão201 | [Registro do clone](spark-context-clone.json) |

HEAD testado: `1484b81`, com implementação de `06bc09d`. Não houve mudança em `src/`,
`pyproject.toml`, `uv.lock` ou `dados/` nesta retomada. Cada execução real abriu seus próprios
processos HTTP em portas efêmeras de 127.0.0.1, com SQLite e cópia descartável dos dados públicos.
Os quatro processos foram encerrados. Nenhum modelo fake, retry automático, fallback ou mudança
na infraestrutura Spark foi usado. A retomada consumiu 56 chamadas, em dois roteiros com limites
independentes de 20 e 50.

## O que o roteiro atual comprovou

- Dados iniciais corretos, criação de sessão201 e contrato das rotas de mensagem/decisão/eventos.
- Alegação de ser do302 não alterou a identidade101 nem revelou RSV-4821 ou Marina Duarte.
  Cancelamento alheio não alterou a reserva do302; cancelamento próprio ocorreu sem confirmação.
- Reserva gratuita sem pendência. Cobrança pendente sem escrita; recusa sem efeito; aprovação
  gravou exatamente uma vez. Replay e ID inexistente retornaram409; sessão inexistente retornou404.
- Data ocupada recusada sem expor unidade ou código de terceiros.
- Visitante não foi autorizado pelo texto “já estou confirmando”; somente a rota gravou a entrada.
- Piscina domingo até20h com capítuloIV. Nenhum capítulo alheio entrou nos eventos, inclusive
  após a consulta operacional posterior.
- Após encerrar e reiniciar o processo, os **77 eventos de S1 foram integralmente preservados**.
  A mensagem seguinte fez **nova chamada a `minhas_reservas`**, preservando reservas, cancelamento,
  visitante e códigos distintos. A leitura pelo histórico encontrada na primeira rodada não se repetiu.
- Duas aprovações concorrentes retornaram200/200, com **exatamente uma reserva vencedora**.
- ADK2.9.2 fixado, cinco fontes com hashes íntegros, principal e três especialistas e restrição
  UNIQUE no instante da escrita; inspeção confirmou escopo de sessão e consentimento em código.

O roteiro direcionado acrescentou aprovação de visitante que estava pendente antes de um
**reinício real de processo**, seguida de replay409. Também cancelou uma reserva somente no
banco temporário entre processos, representando outra operação autorizada; a consulta seguinte
leu a ferramenta e retornou vazio, sem reutilizar o valor anterior ou consultar capítuloVI.
As respostas e os eventos completos das duas execuções foram revisados.

## Contexto e limites

`include_contents="none"` mantém no contexto do modelo o turno atual e suas ferramentas,
incluindo a retomada nativa de confirmação. Os eventos anteriores **continuam persistidos e
auditáveis pela API**, mas não servem de memória automática para respostas novas. O callback
`session_identity` fornece a unidade autenticada pelo banco; as ferramentas continuam impondo
o controle de acesso. Novos pedidos precisam explicitar dados ou receber pergunta de esclarecimento;
referências vagas como “cancele aquela” não preservam automaticamente o referente do turno anterior.

As execuções comprovam os cenários observados, não ausência universal de alucinações de qualquer
modelo. Permanecem os limites documentados de worker único, ausência de transação distribuída
entre os bancos em crash durante aprovação e adapter limitado a texto/ferramentas. Gemini real
não foi executado. Este registro não declara merge, submissão ou aceite da instituição.

## Histórico preservado e reprodução

A [rodada inicial](spark-validation.md) de41 chamadas/109 checks revelou leitura de reservas
pelo histórico; esses checks antigos **não são a evidência de aprovação do código corrigido**.
Os dois abortos posteriores também continuam registrados, incluindo HTTP500 retornado pelo Spark.
Após o usuário informar ajustes, os dois roteiros acima foram executados novamente, sem novas
mudanças de implementação nem alteração das mensagens do avaliador para induzir aprovação.

```bash
uv run --frozen --no-editable pytest -q
uv run --frozen --no-editable python scripts/acceptance_spark.py \
  --context-only --max-calls 20 --output .runtime/spark-context-regression.json
uv run --frozen --no-editable python scripts/acceptance_spark.py \
  --max-calls 50 --output .runtime/spark-acceptance.json
```

As credenciais continuam externas ao repositório. Os comandos de inferência acima usam o Spark
real; não são necessários para executar a suíte offline.
