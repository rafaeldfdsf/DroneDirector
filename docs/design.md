# DroneDirector — MVP local

Nota: este documento descreve a versão inicial sem IA. A versão atual foi revista a pedido do utilizador e usa IA local; ver `ai-design.md` e README.

O pedido anexado é a especificação funcional. Angular 21 standalone comunica por HttpClient com FastAPI local. O estado fica em memória, protegido por lock; um executor com um trabalhador limita processamento concorrente. Uploads são gravados em blocos e validados antes de serem aceites.

OpenCV amostra seis pares próximos por segmento de cinco segundos, com resolução de análise até 640 px. Nitidez usa Laplaciano, exposição usa pixels extremos, estabilidade usa fluxo ótico e variações do movimento global, movimento favorece deslocações suaves. A seleção tenta distribuir os clips pelos ficheiros e excluir vizinhos; relaxa a restrição apenas quando necessário. A montagem agrupa pela ordem de upload e cronologia dentro de cada vídeo.

FFmpeg extrai e normaliza todos os clips para 1920×1080, 30 fps, H.264/yuv420p sem áudio, preservando proporções com barras pretas. Aplica eq opcional e concatena com faststart. A duração é limitada ao material disponível, sem repetição. Progresso representa trabalho concluído; as métricas são analisadas juntas por eficiência.

Erros públicos são em português; detalhes ficam no logger. Não há persistência de estado após reinício, autenticação, IA ou cloud. Os ficheiros permanecem até limpeza manual com o backend parado.
