# Feature Specification: Assistente Residencial Aurora

**Feature Branch**: `feature/sdd-fase-309`
**Created**: 2026-09-19
**Status**: Reviewed
**Input**: Desenvolver integralmente o desafio 309 a partir do contrato e dados públicos do starter.

## User Scenarios & Testing

### User Story 1 - Operações próprias e decisões explícitas (Priority: P1)
Morador consulta, reserva e cancela suas áreas; autoriza visitantes sem expor outra unidade.
**Why this priority**: Evita ações não autorizadas e vazamento de dados.
**Independent Test**: Criar sessão 101 e executar operações tentando alegar ser 302.
**Acceptance Scenarios**:
1. Reserva gratuita e cancelamento próprio executam sem confirmação.
2. Reserva paga ou visitante geram pendência sem gravação; recusa não grava; aprovação grava uma vez.
3. Confirmação por texto não executa pendência; ID inválido, repetido ou alheio é rejeitado.
4. Disponibilidade informa livre/ocupado sem proprietário ou código de terceiros.

### User Story 2 - Continuidade e concorrência (Priority: P1)
Morador retoma a conversa e uma confirmação depois de reiniciar o serviço.
**Why this priority**: Estado e consentimento não podem depender da memória do processo.
**Independent Test**: Reiniciar com pendência, aprovar e comparar histórico e domínio.
**Acceptance Scenarios**:
1. Histórico mantém contagem e ordem após reinício.
2. Duas aprovações simultâneas de área/data têm respostas normais e um único vencedor.
3. Códigos de reservas canceladas não reaparecem em novas reservas.

### User Story 3 - Regulamento por assunto (Priority: P2)
Morador consulta o regulamento recebendo apenas o capítulo pertinente.
**Why this priority**: Mantém resposta fundamentada e contexto limitado.
**Independent Test**: Perguntar fechamento da piscina no domingo; resposta 20h.
**Acceptance Scenarios**:
1. Histórico mostra consulta de ferramenta e nenhum capítulo não relacionado.

### Edge Cases
Sessão inexistente: 404. Confirmação não pendente: 409. Nova mensagem enquanto existe pendência
retorna a pendência sem executar outra ação. Apartamento desconhecido é rejeitado.
Falhas externas de modelo são explícitas, sem respostas simuladas.

## Requirements
### Functional Requirements
- FR-001: Criar sessão com apartamento imutável e manter consultas/cancelamentos nesse escopo.
- FR-002: Confirmar cobranças e visitantes pelo mecanismo nativo ADK e exclusivamente pela rota própria.
- FR-003: Persistir sessões, eventos, pendências, reservas e visitantes.
- FR-004: Garantir uma reserva ativa por área/data na gravação concorrente.
- FR-005: Gerar códigos únicos preservando os cancelados.
- FR-006: Consultar somente capítulo pertinente do regulamento.
- FR-007: Expor as seis rotas e formatos do enunciado, com erros 404/409 especificados.
- FR-008: Manter dados/ intacto e restauração reproduzível restrita aos bancos próprios.
- FR-009: Principal e pelo menos dois especialistas devem operar via ferramentas.
- FR-010: Documentar instalação limpa, arquitetura, garantias e limites de validação.
- FR-011 (desenvolvimento opcional): aceitar Spark local somente por seleção explícita,
  mantendo Gemini como padrão/aceite, o mesmo contrato e as mesmas garantias de domínio.
  Credenciais ficam fora de eventos/artefatos; resposta inválida não executa ferramentas.

### Key Entities
Sessão: identidade e apartamento. Confirmação: decisão pendente vinculada à sessão e chamada.
Reserva: código, apartamento, área, data e situação. Visitante: apartamento, nome e data.
Evento: histórico ordenado da interação. Capítulo: trecho isolado do regulamento.

## Success Criteria
### Measurable Outcomes
- SC-001: Nenhuma tentativa de alegar outro apartamento revela ou altera seus dados.
- SC-002: Zero gravações protegidas sem aprovação explícita; uma por aprovação válida.
- SC-003: Eventos e pendências continuam válidos após reinício.
- SC-004: Duas aprovações concorrentes resultam em exatamente uma reserva.
- SC-005: Consulta da piscina contém horário correto e zero capítulos alheios.
- SC-006: Instalação, restore e testes passam num clone limpo.

## Assumptions
Autenticação, pagamentos reais, UI, deploy e horários/capacidade de reservas estão fora de escopo.
Chave e disponibilidade Gemini pertencem ao ambiente do operador; execução real fica pendente
até credenciais autorizadas. Testes offline verificam garantias usando modelo de teste explícito.

O modo adicional FR-011 e seus testes estão em [spark-experimental.md](spark-experimental.md).
Seu smoke usa linguagem natural real, mas não conclui SC-001–SC-006 com Gemini nem T016.
