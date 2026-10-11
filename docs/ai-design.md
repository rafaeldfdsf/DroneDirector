# IA local — revisão do MVP

Pedido: substituir a escolha exclusivamente heurística por IA, mantendo frames e vídeos no computador. A escolha local foi confirmada pelo utilizador.

CLIP ViT-B/32 em ONNX quantizado (Xenova/OpenAI) produz embeddings visuais de três frames por segmento. O preditor estético LAION V1, treinado sobre embeddings CLIP, dá uma pontuação estética por frame. O score do segmento é a média dessas previsões (escala 0–100). Score final: 70% IA estética e 30% score técnico anterior. Mantêm-se estabilidade, exposição, nitidez, diversidade temporal, ordem cronológica e exportação.

As semelhanças entre embeddings servem como penalização suave de repetição visual durante a seleção, sem impedir alcançar a duração disponível. A IA não é um modelo de linguagem nem um modelo de ação/temporal: estima estética visual a partir de imagens; estabilidade e movimento continuam medidos por optical flow.

ONNX Runtime CPU evita instalar PyTorch/CUDA e permite funcionar em Windows sem GPU específica. Downloads de cerca de 89 MB apenas na instalação, com revisões e SHA-256 fixados. O runtime não faz pedidos de rede nem downloads automáticos. Sem o modelo, o processamento falha com mensagem em português, nunca volta silenciosamente à escolha sem IA.

Pré-processamento igual ao CLIP: RGB, resize bicúbico com lado menor 224, crop central 224, médias/desvios CLIP e embeddings normalizados. O checkpoint estético possui dois storages float32 conhecidos: são lidos como dados de ZIP verificado por hash, sem executar pickle ou código remoto.

analysis.json guarda nome do modelo, scores por frame e por segmento, score técnico e final. Embeddings são usados apenas em memória para não inflacionar o JSON. O frontend informa IA local, apresenta a etapa de IA e mostra que o resultado foi selecionado com IA. Endpoint de estado do modelo permite verificar a instalação.

Verificação: regressões de score e diversidade visual; falta/corrupção de modelo; inferência real local com rede bloqueada; pipeline completa e browser; builds. Filmagens sintéticas não provam qualidade estética em filmagens DJI reais.
