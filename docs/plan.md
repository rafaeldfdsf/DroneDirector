# Plano de implementação DroneDirector

Goal: implementar o fluxo completo solicitado em D:\Work\drone-director.
Spec: design.md e pedido anexado. Execução direta nesta sessão, autorizada pelo pedido.

- [x] Backend: testes de score, diversidade, duração curta, validação e pipeline sintética; serviços OpenCV/FFmpeg; API assíncrona e range HTTP.
- [x] Frontend: componentes upload/progresso/resultado, serviço HttpClient, polling cancelável, erros PT-PT e interface responsiva.
- [x] Verificação: pytest, build Angular, servidor real, endpoints, exportação e range. Vídeos sintéticos identificados como tal; não procurar filmagens privadas.
- [x] README: instalação PowerShell, versões, dependências, funcionamento e limitações.

Revisão independente identificou recuperação de POST perdido sem job: corrigida e teste de browser passou. Respostas de validação API foram traduzidas para português. Execução direta preservou o pedido de não pedir confirmações técnicas e de escrever somente neste projeto.

Review focus: nomes repetidos e paths; uploads durante processamento; vídeos curtos/corrompidos; clips com tamanhos/fps diferentes; perda de conexão durante polling.
