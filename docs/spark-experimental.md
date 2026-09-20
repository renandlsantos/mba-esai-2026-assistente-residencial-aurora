# Spark local — modo experimental

> Registro histórico da integração inicial. Decisão posterior do autor: Spark é agora o
> padrão. Gemini é alternativa explícita; a exigência original permanece como divergência
> declarada. T016 foi concluído posteriormente; consulte a [validação final](spark-validation-final.md).


Data: 2026-09-20. O usuário autorizou o endpoint local e a leitura de seu dotenv por meio do
coordenador. Nenhum valor de chave, URL privada ou arquivo dotenv foi copiado para os artefatos.

## Escopo e resultado

Gemini permanece padrão e exigência acadêmica; T016 segue aberto. O modo Spark selecionado
explicitamente exercitou o mesmo Runner, agentes, ferramentas, confirmação nativa e SQLite.
Não foi lançado modelo de teste em produção nem serviço de nuvem alternativo.

O [smoke real](spark-smoke.json) terminou com **11 chamadas spark/code em cerca de 31 segundos**,
16 verificações aprovadas e 29 eventos. Chamadas foram sequenciais, com teto global de 15.
HTTP da API foi exercitado em ASGI no processo; o transporte do modelo acessou o servidor Spark
real. Bancos foram criados em diretório temporário com cópia dos dados públicos e removidos ao fim.

Verificados: identidade da sessão diante da alegação de ser outra unidade; reserva gratuita sem
pendência; paga sem gravação antes de consentimento; texto de confirmação sem autoridade;
confirmação por outra sessão 409; reinicialização do runtime com eventos preservados; aprovação
pela rota com gravação única; replay 409; reserva alheia preservada e código/nome alheios ausentes
da conversa/eventos. Não foi o fluxo completo de 15 passos do avaliador; visitantes, regulamento
e disputa concorrente continuam cobertos offline, sem evidência Spark real nesta rodada.

## Adapter e evidência técnica

SDK instalado e fixado: Google ADK 2.9.2. A documentação oficial descreve
[LiteLLM](https://adk.dev/agents/models/litellm/) para modelos locais/OpenAI compatíveis.
LiteLLM não estava instalado. O coordenador aprovou BaseLlm pequeno com httpx existente,
declarado explicitamente em runtime, para evitar dependências adicionais.
Foram consultados base_llm.py, llm_request.py, llm_response.py, lite_llm.py e contents.py do SDK.

O adapter converte schemas e preserva IDs de chamadas/resultados; aceita apenas content e
tool_calls nativos. Não interpreta JSON de ferramenta em texto nem reasoning_content.
Ferramentas não declaradas, argumentos inválidos, resposta vazia/truncada e falhas HTTP levantam
erro; corpos de erro/headers não são registrados. Chave usa SecretStr e é excluída de repr/dump.
Não há fallback de provedor, retry, proxy herdado do ambiente ou redirecionamento HTTP.
Timeout 300s; max_tokens 4096; modelo spark/code; temperatura 0.

## Validação e convergência

- Suite local: 23 testes (14 existentes e nove novos), com ADK/SQL reais e transportes de teste
  nos testes offline. Schema, function_call/function_response, transferência, confirmação após
  restart, replay, identidade, seleção default e sigilo da chave foram verificados.
- Dados originais e contratos HTTP preservados; o smoke real não usou o runtime habitual.
- Falhas iniciais eram expectativas de teste: o ADK acrescenta títulos aos JSON Schemas e
  protege mensagens de outro agente convertendo a transferência para contexto textual no
  especialista. Testes passaram a verificar semântica do schema e transferência nos eventos,
  preservando checks de IDs nos resultados das ferramentas do próprio especialista.
- Ruff inicialmente detectou o import de ModelConfigurationError usado como reexport pelo
  módulo API. A API agora importa a classe diretamente de models.py. A revisão também garantiu que valores vazios do
  .env.example mantenham Gemini como padrão e não impeçam a inicialização acadêmica.
- O CLI agora carrega somente root/.env para não buscar configuração ancestral inadvertida.

Limites: adapter próprio, limitado ao caminho textual de Aurora; não é integração universal
OpenAI/LiteLLM. Streaming, multimodalidade e outros modelos não foram validados. O SDK emitirá
avisos experimentais de confirmação/resumabilidade e de ausência de métricas de tokens, pois o
adapter não publica usage_metadata. Os limites operacionais de crash entre bancos e worker
único documentados no README continuam os mesmos. Sucesso Spark não é aprovação Gemini.
