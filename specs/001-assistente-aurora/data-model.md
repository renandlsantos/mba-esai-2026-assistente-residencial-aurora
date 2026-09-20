# Data model
- apartamentos(numero PK, nome); areas(id PK, nome, taxa).
- reservas(codigo PK nunca reutilizado, apartamento FK, area FK, data ISO, ativa boolean).
  UNIQUE(area,data) WHERE ativa=1 decide concorrência no INSERT.
- visitantes(id PK, apartamento FK, nome não vazio, data ISO, operacao UNIQUE).
- sessoes(id PK, apartamento FK imutável).
- confirmações são reconstruídas dos eventos persistidos ADK; decisões aceitas são
  registradas em ledger por ID UNIQUE, session_id, confirmado e status.
- ADK DatabaseSessionService mantém suas próprias tabelas em adk.sqlite3.
- cancelamento: ativa→inativa; aprovação: pendente→consumida; recusa: pendente→consumida sem efeito.
