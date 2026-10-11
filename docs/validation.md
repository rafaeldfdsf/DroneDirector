# Verificação — 7 de outubro de 2026

- `npm run build`: passou, bundle inicial de 174,49 kB, sem avisos de budget.
- `python -m pytest -q --basetemp ..\work\pytest-verified`: 13 testes passaram.
- `npm test`: 5 testes Chromium passaram, incluindo reprodução real no player e download.
- `python -m pip check`: sem dependências incompatíveis.
- Exportação real FFmpeg de 15, 30 e 60 segundos com material sintético; casos de duração insuficiente e fontes com resolução/fps diferentes também passaram.
- Nenhuma filmagem DJI real foi utilizada. Qualidade estética, 4K DJI, D-Log/HDR e desempenho em projetos grandes precisam de avaliação com material real.

Avisos observados: Starlette TestClient/AnyIO mostra uma depreciação de alias; Playwright/Node avisa sobre NO_COLOR/FORCE_COLOR. Durante a troca de pedidos Range/download, Python 3.11 no Windows regista um ConnectionResetError de transporte Proactor quando o browser fecha a ligação. Os testes de reprodução e download passaram; isto não foi um erro de processamento do projeto.

Servidores locais lançados após os testes, sem reload. Logs em `work\backend.*.log` e `work\frontend.*.log`; PIDs registados em `work\servers.json`. O estado da API está em memória e perde-se quando o backend termina.
