# Implementation Plan: Assistente Aurora
**Branch**: feature/sdd-fase-309 | **Date**: 2026-09-19 | **Spec**: [spec.md](spec.md)
## Summary
FastAPI expõe o contrato; Runner ADK persiste eventos em SQLite. Principal delega a especialistas
em reservas, visitantes e regulamento. Ferramentas consultam apartamento por session_id no domínio.
Confirmação usa protocolo nativo ADK e retomada da invocação original. SQL arbitra conflitos.
## Technical Context
Python >=3.12; google-adk==2.9.2; FastAPI; SQLite; uv.lock; pytest e modelo BaseLlm de teste.
Serviço local de um processo, seis rotas, sem UI. Concorrência de sessões distintas suportada.
Sem meta arbitrária de latência: custo do modelo externo domina. Testes offline não medem Gemini.
## Constitution Check
Todos os cinco princípios passam no desenho. Nenhuma exceção. Gate final exige testes de
persistência, confirmação nativa, isolamento, UNIQUE, restore seguro e capítulos isolados.
## Project Structure
src/aurora/{config,store,agents,runtime,api,cli}.py; tests/{fake_model,test_api,test_store}.py;
docs/validacao.md; specs/001-assistente-aurora/{research,data-model,quickstart,tasks}.md.
## Complexity Tracking
Dois bancos: domínio transacional e sessões ADK. Separação evita acoplamento ao schema privado
ADK; apenas arquivos de nome fixo em diretório próprio são restaurados.

## Extensão experimental — 2026-09-20

Plano revisado antes de implementação em [spark-experimental.md](spark-experimental.md).
Adicionar models.py para seleção explícita e spark.py para BaseLlm texto/tools via httpx;
nenhuma mudança nas ferramentas de negócio ou no schema. httpx passa de dev para runtime,
sem novos pacotes no lock. Gemini continua obrigatório para T016.
