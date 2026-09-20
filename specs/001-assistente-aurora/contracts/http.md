# HTTP contract
POST /sessoes {apartamento:string} →201 {session_id:string}.
POST /sessoes/{id}/mensagens {texto:string} →200 resposta.
POST /sessoes/{id}/confirmacoes {id:string,confirmado:boolean} →200 resposta; inválido/alheio/usado409.
GET /sessoes/{id}/eventos →200 lista integral ordenada de eventos ADK.
GET /apartamentos/{ap}/reservas →200 [{codigo,area,data}].
GET /apartamentos/{ap}/visitantes →200 [{nome,data}].
Resposta: {resposta:string,confirmacoes_pendentes:[{id:string,acao:string,detalhes:object}]}.
Sessão inexistente:404 em todas as rotas de sessão. Endpoints de apartamento são inspeção local
sem autenticação, como requerido; não são ferramentas expostas ao modelo.
