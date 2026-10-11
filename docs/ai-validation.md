# Verificação da IA local — 7 de outubro de 2026

- Instalação real dos pesos: CLIP ViT-B/32 ONNX int8 (~89 MB) e head LAION V1; ambos verificados por SHA-256 fixado.
- Backend: 21 testes passaram, incluindo inferência real sem acesso à rede, pré-processamento RGB/CLIP, métricas aprendidas, score com peso maioritário da IA, diversidade visual, ausência/corrupção de modelos e regressões da pipeline/exportação.
- Browser: cinco testes passaram, incluindo confirmação de `selectionMethod=local-ai` e modelo LAION no resultado, reprodução e download.
- Frontend: `npm run build` passou sem erros ou avisos de budget, bundle inicial ~175 kB.
- `pip check`: sem dependências incompatíveis.
- O modelo usa CPU e ONNX Runtime com telemetria desativada. A inferência não usa APIs externas; downloads são exclusivos do script de instalação.

Os vídeos utilizados são sintéticos. Estes testes verificam funcionamento e uso real da IA, não demonstram preferência estética em filmagens DJI reais. A IA avalia frames, não compreende a narrativa/ação de uma sequência inteira. O crop central segue o pré-processamento do CLIP.

Persiste o aviso de depreciação de alias AnyIO/Starlette no TestClient. O browser pode provocar ConnectionResetError de transporte Python/Windows ao fechar pedidos Range; a exportação e o download passaram.
