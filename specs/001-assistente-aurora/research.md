# Research
## ADK e confirmação
Decisão: google-adk==2.9.2 (PyPI consultado 2026-09-19), App resumível e FunctionResponse
adk_request_confirmation com ID e invocation_id originais. Validar SDK instalado e SQLite.
Razão: consentimento nativo e retomada correta no especialista, inclusive após reinício.
Alternativa rejeitada: estado apenas em memória ou booleano vindo do texto do usuário.
Fontes: https://adk.dev/tools-custom/confirmation/ e https://pypi.org/project/google-adk/ .
## Modelo
Gemini configurável via GEMINI_MODEL e GOOGLE_API_KEY. Catálogo oficial consultado:
https://ai.google.dev/gemini-api/docs/models . Sem assumir quotas/disponibilidade da conta.
Fake BaseLlm apenas nos testes; naquela pesquisa inicial a execução real estava pendente.
A decisão posterior do autor adotou Spark, com [validação funcional real concluída](../../docs/spark-validation-final.md)
e divergência do requisito Gemini documentada.
## Banco
SQLite com índice UNIQUE parcial de reserva ativa, códigos UUID e cancelamento lógico.
Alternativa rejeitada: consultar disponibilidade e inserir sem restrição de banco.
## Privacidade
Ferramentas sem argumento apartamento. Sessão aponta apartamento imutável no banco.
Regulamento particionado por cabeçalhos; ferramentas retornam só capítulo escolhido.
## Dependências
Endor indisponível no conjunto de ferramentas desta sessão; revisão automática não executada.
