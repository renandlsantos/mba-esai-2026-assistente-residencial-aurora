# Residencial Aurora Constitution

## Core Principles

### I. Autoridade fora do modelo
Apartamento deriva exclusivamente da sessão. Nenhuma ferramenta recebe apartamento do modelo.
Dados pessoais, reservas e cancelamentos devem sempre aplicar esse escopo.

### II. Confirmação nativa e vinculada
Cobranças e autorização de visitantes exigem confirmação nativa ADK. Apenas a rota de confirmação
traduz a decisão humana em FunctionResponse. IDs desconhecidos, consumidos ou de outra sessão dão 409.

### III. Persistência e concorrência verificáveis
Eventos ADK e domínio devem sobreviver ao reinício. Exclusividade de reserva ativa é restrição SQL
na gravação, inclusive após aprovações concorrentes. Códigos cancelados nunca são reutilizados.

### IV. Contexto mínimo e dados imutáveis
Regulamento retorna somente um capítulo pertinente. Os arquivos dados/ são fonte congelada.
Restore opera exclusivamente nos bancos pertencentes a esta aplicação.

### V. Evidência honesta
Testes offline usam o ADK real com modelo explicitamente injetado nos testes. Spark local é
preferido e padrão por decisão do autor; Gemini é uma alternativa explícita. O enunciado exige
Gemini: manter essa divergência visível sem alegar aprovação acadêmica. Evidência parcial Spark
não equivale aos 15 passos completos. Ausência de credenciais não produz resposta fictícia
nem troca silenciosa de provedor.

## Technical Constraints
Python >=3.12, uv.lock versionado, Google ADK série 2 com versão exata >=2.2.0.
API no localhost:8000, principal e pelo menos dois especialistas, segredos fora do Git.

## Development Workflow
Executar constitution, specify, plan, tasks, implement e converge nesta ordem.
Cada requisito crítico precisa de teste significativo. Revisar diff antes de commit e executar
testes também a partir de clone limpo. Não publicar materiais privados das aulas.

## Governance
Mudanças exigem justificativa e revisão de impacto nos critérios de aceite. Alterações incompatíveis
incrementam major; princípios adicionais, minor; esclarecimentos, patch. Revisão final verifica
cada princípio contra implementação e evidências.

**Version**: 2.0.0 | **Ratified**: 2026-09-19 | **Last Amended**: 2026-09-20

Emenda 1.1.0: opção Spark solicitada pelo usuário e autorizada pelo coordenador. Preserva todos
os critérios acadêmicos; plano e limites em specs/001-assistente-aurora/spark-experimental.md.


Emenda 2.0.0: o autor solicitou Spark como padrão, substituindo o default Gemini da emenda1.1.0.
Contrato HTTP, dados, garantias e opção Gemini são preservados. A divergência acadêmica é
explicitamente documentada; nenhum teste é marcado aprovado por essa mudança de preferência.
