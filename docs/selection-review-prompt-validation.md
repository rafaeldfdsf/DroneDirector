# Verificação — seleção, cortes, revisão e prompt (8 outubro 2026)

- 41 testes backend passaram; 10 testes browser passaram; dois testes browser foram repetidos para capturar e inspecionar a revisão desktop/mobile.
- Build Angular de produção: ~200,42 kB iniciais, sem erros; pip check sem conflitos.
- CLIP/LAION estético mantido; encoder multilingue ONNX quint8 AVX2 (~135 MB), tokenizer e projeção Safetensors instalados, com revisão 58edf8cada9e398793dca955574a48cbb7f18be2 e SHA-256 fixados.
- Inferência real sem rede: descrições portuguesas de imagens vermelhas/azuis correspondem aos embeddings visuais corretos; dimensão 512 e norma um verificadas.
- Seleção de qualidade, diversidade gradual, ausência de sobreposição, cortes por cena/pausa, fontes curtas e exportações 15/30/60 verificadas.
- Análise termina em revisão; prompt reaplica ranking sem reanálise; preview H.264/Range, edição, ordenação, substituição, duração curta, exportação, reprodução e download verificados.
- Revisão independente e regressões: nenhum momento escondido ao reordenar; falha de GET /review tem botão de nova tentativa; falha de exportação preserva edição e resultado anterior; falha ao preparar metadados preserva vídeo anterior.
- Filmagens DJI reais: quatro vídeos, 17 candidatos, sete momentos efetivos, 30 segundos; prompt «Paisagem natural, rio e vegetação», sem aviso de baixa diferenciação. Análise levou 227 segundos nesta máquina, com outros testes a correr. Relatório detalhado local: work/real-review-validation.json. Originais e montagem anterior preservados.

Limites: preferência visual textual não é cumprimento garantido de negações/narrativa; cortes usam sinais medidos, sem compreensão completa de ação; avaliação estética humana ainda necessária. Saída continua 1080p/30, sem recuperação após reiniciar. Aviso AnyIO/Starlette e reset de transporte Windows ao abortar Range permanecem; não impediram os testes de reprodução/download.
