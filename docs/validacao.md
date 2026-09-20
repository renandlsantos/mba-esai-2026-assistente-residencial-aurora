# Validação — 2026-09-19

## Resultado local
- Python 3.12.14; google-adk 2.9.2; FastAPI 0.141.1; dependências fixadas no uv.lock.
- `uv run --no-editable pytest -q`: **14 passed**, 4 avisos upstream (API experimental/depreciação).
- `ruff check src tests`: passou; `ruff format --check src tests`: passou.
- `uv run --no-editable aurora restore`: executado, restaurou somente runtime próprio.
- `git diff -- dados/`: vazio; hashes de cinco fontes verificados em teste.

## Cobertura dos passos de avaliação
| Passos | Testes e evidência |
| --- | --- |
| 1–2 | restore, dados iniciais e criação 201 nos testes de API/store |
| 3–4 | argumento de outra unidade ignorado e cancelamento alheio sem efeito |
| 5–6 | cancelamento próprio e reserva grátis sem pendência; novo código |
| 7–8 | recusa sem escrita, aprovação com escrita e replay409 |
| 9 | confirmação inválida409 e sessão desconhecida404 nas três rotas |
| 10 | disponibilidade e tentativa de reserva ocupada sem código/unidade alheios |
| 11 | visitante exige pendência; texto não aprova; rota aprova |
| 12 | capítulo IV e 20h; nenhum canário de capítulos não relacionados |
| 13 | reinício de processo HTTP real, eventos iguais antes/depois, aprovação pendente e continuação |
| 14 | duas aprovações via asyncio.gather retornam200; só uma reserva; teste adicional de duas threads SQLite |
| 15 | inspeção do código: consentimento nativo + ledger, apartamento por sessão, índice UNIQUE, fontes intactas |

O modelo de teste em tests/fake_model.py emite FunctionCall/transfer_to_agent roteirizados.
Não simula Runner, ferramentas, confirmação, persistência ou SQL. A injeção está apenas nos testes.
Portanto estes resultados não são resultados de interpretação de linguagem natural do Gemini.

## Diagnósticos resolvidos
- iCloud marca .pth como UF_HIDDEN; Python3.12 ignora o arquivo. Instalação não editável evita isso.
- Verificação textual ingênua de substring302 alcançava UUIDs aleatórios; teste corrigido para
  unidade isolada, conforme critério do enunciado, sem enfraquecer busca de código/nomes.
- Datas compactas aceitas por date.fromisoformat poderiam representar o mesmo dia com chave
  SQL diferente; validação exige a forma canônica YYYY-MM-DD e teste cobre a tentativa.

## Limites e pendências
- Gemini real: **não executado**, depende de chave/modelo autorizado e disponibilidade da conta.
- Endor: ferramentas dependency-reviewer/package-risk indisponíveis nesta sessão; não executado.
- App resumível/Tool Confirmation são marcados experimentais pelo SDK; versão exata e testes de
  retomada evitam declarar compatibilidade com versões diferentes.
- Não garante crash no meio de aprovação nem coordenação de múltiplos workers (ver README).
- Não houve merge em main nem submissão na plataforma; coordenador cuidará da entrega.
- Clone remoto 706dcdc: instalação frozen, restore e 14 testes passaram; checkout limpo.
  Evidência completa em [clone-limpo.json](clone-limpo.json).

## Spec Kit converge
Revisados 10 requisitos funcionais, 6 critérios mensuráveis, 8 cenários de aceite, 6 decisões
de desenho e 5 princípios da constituição. Nenhuma lacuna de código identificada.
Os 15 itens de implementação estão concluídos; a execução real do Gemini é dependência externa
explicitamente separada pela especificação. Nenhuma fase vazia foi acrescentada a tasks.md.

## Revalidação local — 2026-09-20

14 testes passaram novamente, incluindo reinício HTTP real e concorrência SQL. O comando
de restore foi executado em diretório temporário exclusivo, seguido de aurora start em
127.0.0.1:8000: dados iniciais do 101 e visitante do 302 corretos, criação de sessão HTTP 201.
Nenhuma chamada de modelo real foi feita. Arquivos dados/ idênticos ao upstream be87e1d.
A tarefa externa T016 torna explícita a pendência dos 15 passos com Gemini antes da liberação.

## Spark opcional — 2026-09-20

23 testes offline passaram após a extensão experimental (14 existentes e nove do adapter).
Smoke real autorizado com spark/code passou em 11 chamadas, bancos temporários e runtime
reinicializado antes da aprovação. Ver [registro completo](spark-experimental.md) e
[resultado estruturado](spark-smoke.json). O teste não substitui os 15 passos com Gemini.
