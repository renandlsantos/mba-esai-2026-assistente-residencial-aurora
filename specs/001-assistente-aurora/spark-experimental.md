# Spark experimental — especificação e plano

Data: 2026-09-20. Escopo autorizado pelo usuário via coordenador; revisão do plano anterior à implementação.

## Constituição e requisito

Gemini continua padrão e obrigatório para o aceite acadêmico (T016). Spark é uma opção local
experimental para desenvolvimento. Não altera contrato HTTP, dados congelados, identidade,
confirmação nativa, persistência ou restrição UNIQUE. Nenhum resultado Spark substitui Gemini.

## Decisão de integração

ADK 2.9.2 instalado fornece BaseLlm e LiteLlm, mas LiteLLM/OpenAI não estão instalados.
A documentação oficial usa LiteLlm para OpenAI compatível. O coordenador aprovou um adapter
BaseLlm restrito a texto e tools com httpx já instalado, evitando a árvore de LiteLLM.
httpx passa a dependência explícita de runtime. Não copiar o adapter genérico do SDK.

Referências: [LiteLLM no ADK](https://adk.dev/agents/models/litellm/) e o código instalado
google/adk/models/{base_llm,llm_request,llm_response,lite_llm}.py da versão fixada.

## Plano revisado

1. Seleção explícita AURORA_MODEL_PROVIDER=spark; ausência mantém Gemini. Ler apenas
   SPARK_BASE_URL/SPARK_API_KEY de ambiente ou dotenv local explicitamente selecionado.
2. POST chat/completions não streaming: model spark/code, max_tokens 4096, timeout 300s,
   sem fallback, retry automático, redirecionamento ou proxy de ambiente.
3. Converter system/texto/function_call/function_response e JSON schema. Consumir somente
   content/tool_calls; preservar IDs e deixar ADK executar as tools. Resposta inválida falha.
4. Cobrir schemas, transferências, retorno de tool, erros, sigilo de chave, seleção de provider
   e integração real ADK/SQLite com transporte HTTP simulado, inclusive confirmação e isolamento.
5. Executar smoke opt-in real com bases temporárias, chamadas sequenciais e limite global de 15.
   Verificar reserva gratuita, paga pendente/aprovada/replay 409 e isolamento. Não gravar credenciais.
6. Atualizar documentação/evidências; rodar suite, integridade, diff e revisão antes de commit/push.

## Tarefas

- [x] S001 Implementar seleção e adapter experimental sem mudar defaults.
- [x] S002 Testar protocolo, erros e integração ADK/SQLite offline.
- [x] S003 Executar smoke real autorizado dentro do limite e registrar resultados/limitações.
- [x] S004 Documentar configuração, convergir e validar diff, suite e dados congelados.

## Resultado da revisão

23 testes offline passam; smoke real Spark passou com 11 chamadas sequenciais, sem alterar
dados originais, esquema ou contrato. A criação da pendência continuou sendo ADK nativo e
aprovação só ocorreu pela rota depois de reabrir o runtime. Gemini default preservado inclusive
com as variáveis vazias do exemplo. T016 segue pendente. Evidências em docs/spark-experimental.md
e docs/spark-smoke.json; nenhuma conclusão acadêmica foi transferida de Spark para Gemini.
