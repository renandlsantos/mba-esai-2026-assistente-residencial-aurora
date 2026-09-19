# Quickstart
uv sync --frozen --no-editable
uv run --no-editable aurora restore
Configurar GOOGLE_API_KEY e GEMINI_MODEL no ambiente (ver .env.example sem valores).
uv run --no-editable aurora start
Servidor http://127.0.0.1:8000 . POST /sessoes cria sessão; mensagens operam no seu apartamento.
Apenas POST /confirmacoes aprova uma pendência. GET /eventos inspeciona o histórico.
uv run --no-editable pytest -q executa testes isolados, sem chave/modelo remoto. Ver README e docs/validacao.md.
