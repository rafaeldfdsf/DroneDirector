# Plano IA local

Spec: ai-design.md. Execução direta autorizada pelo pedido de modificar a aplicação e pela preferência explícita de IA local.

- [x] Testes e serviços: instalação verificável, inferência ONNX, score híbrido e diversidade por embeddings; testes com frames reais de vídeo sintético e rede bloqueada.
- [x] Integração: análise três frames/segmento, progresso, metadata, validação API sem fallback; manter endpoints anteriores.
- [x] Interface e entrega: copy de IA local, testes browser, build, README, reiniciar backend quando não houver jobs ativos.

Review focus: pré-processamento CLIP correto; modelos ausentes/corrompidos; inferência offline; exceções técnicas sem leakage; diversidade sem encurtar vídeo desnecessariamente.
