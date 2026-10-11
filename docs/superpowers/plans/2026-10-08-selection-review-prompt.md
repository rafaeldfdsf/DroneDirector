# DroneDirector Selection, Review and Prompt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Melhorar a qualidade e os limites dos momentos, permitir revisão antes da exportação e orientar a seleção com um prompt local em português.

**Architecture:** Separar análise, sugestão e exportação. A segmentação temporal produz candidatos, CLIP/LAION calcula qualidade e um encoder multilingue produz relevância textual no mesmo espaço visual. O browser edita uma lista ordenada de IDs; o backend valida e normaliza os intervalos efetivos.

**Tech Stack:** Angular 21, FastAPI/Pydantic, OpenCV, NumPy, ONNX Runtime CPU, FFmpeg, tokenizer local e Safetensors; pytest e Playwright.

**Spec:** `D:/Work/drone-director/docs/superpowers/specs/2026-10-08-selection-review-prompt-design.md` (aprovada pelo utilizador).

## Global Constraints

- Vídeos, frames e prompts ficam no computador. Modelos podem ser descarregados explicitamente durante a instalação, nunca durante a análise.
- Prompt até 500 caracteres; pontuação base 70% estética aprendida + 30% métricas técnicas.
- Penalização por origem: dois pontos por trecho já escolhido dessa origem, limitada a seis pontos; penalização visual limitada a oito pontos; ajuste do prompt até dez pontos.
- Candidatos entre três e oito segundos, mantendo intervalos completos mais curtos para fontes pequenas; amostragem temporal aproximadamente a cada 0,5 segundos.
- Duração pedida 15/30/60 segundos; seleção curta pode ser exportada com duração explícita. Nenhum plano é acrescentado sem aparecer na revisão.
- Manter o endpoint `/process` automático compatível. Não acrescentar contas, serviços externos, base de dados, recuperação completa de projetos, uploads retomáveis ou opções de resolução/FPS.
- Trabalhar em `D:/Work/drone-director`. Não iniciar Git: este projeto não possui repositório; guardar alterações no próprio projeto e documentar verificação.

## Review Focus

1. Dois candidatos encostados da mesma origem: aceitar continuidade; rejeitar sobreposição real (tarefas 1 e 4).
2. Cena abrupta junto ao início/fim: preservar intervalos curtos válidos, sem criar duração negativa ou atravessar a fronteira (tarefa 2).
3. Prompt só com espaços ou texto longo sem espaços: vazio usa ranking base; limite de 500 caracteres e truncagem do tokenizer são explícitos (tarefa 3).
4. Nova sugestão durante edição manual: só substituir após «Aplicar prompt»; exportação duplicada é rejeitada e uma falha preserva o último vídeo (tarefas 5 e 6).
5. Codec do original não reproduzível no browser: oferecer aviso claro e pré-visualização derivada local, sem quebrar a revisão (tarefas 5 e 6).

## Ficheiros e responsabilidades

- `backend/services/scoring.py`: ranking e penalizações; `backend/services/segmentation.py`: fronteiras temporais; `backend/services/analyzer.py`: métricas e embeddings por candidato.
- `backend/services/prompt_scorer.py`: encoder multilingue offline; `backend/setup_ai.py`: instalação verificada; `backend/requirements.txt`: bibliotecas efetivamente usadas e versões verificadas.
- `backend/services/review.py`: IDs, armazenamento dos candidatos, normalização e motivos; `backend/services/processor.py`: orquestração análise/exportação e compatibilidade automática.
- `backend/models/project.py`: pedidos/estado; `backend/api/projects.py`: endpoints; `backend/services/video_editor.py`: publicação atómica do resultado e pré-visualizações compatíveis.
- `frontend/src/app/models/project.model.ts`, `services/video.service.ts`, `pages/create-project/*`: contratos, prompt, estados; novo `components/moment-review/*`: edição e pré-visualização; `components/video-result/*`: voltar à revisão.
- Novos testes `backend/tests/test_selection.py`, `test_segmentation.py`, `test_prompt.py`, `test_review.py`; atualizar `test_pipeline.py`, `test_ai.py`, `test_ai_integrity.py` e `frontend/tests/workflow.spec.ts`; novo `frontend/tests/review.spec.ts`.

### Task 1: Ranking pela qualidade

**Interfaces:** Conservar `select_segments(segments: list[Segment], duration: int, filenames: list[str]) -> list[Segment]`. Acrescentar `promptSimilarity`, `promptAdjustment`, `rankingScore` como metadados opcionais de `Segment`. Nunca alterar `score` base ao aplicar um novo prompt.

- [x] Escrever `test_quality_beats_source_counts`: A: [90 em 0–5, 89 em 15–20], B: [10 em 0–5], duração 10; assert os dois escolhidos pertencem a A.
- [x] Escrever `test_soft_diversity_on_close_quality`, `test_adjacent_allowed_overlap_rejected` e `test_selection_deterministic`; assert diversidade com qualidade próxima, ausência de sobreposição e resultados iguais em chamadas repetidas.
- [x] Executar `.\.venv\Scripts\python.exe -m pytest tests/test_selection.py -q` em `backend`; confirmar falha no ranking atual.
- [x] Implementar score único com as penalizações da especificação; rejeitar apenas sobreposição real. Reinicializar flags de seleção em cada chamada. Atualizar a antiga asserção que exigia distância de dez segundos entre candidatos.
- [x] Repetir os testes da tarefa e os testes de seleção em `tests/test_pipeline.py`; todos passam.

### Task 2: Segmentação temporal

**Interfaces:** Em `segmentation.py`, definir `find_candidate_windows(path: Path, on_progress: Callable[[float], None]) -> list[dict]`, com `start`, `end`, `cutReason`, `cutConfidence`. `analyze_video(path, on_progress, ai_scorer=None)` mantém assinatura e devolve `Segment` enriquecido.

- [x] Escrever `test_scene_change_never_crossed`: vídeo sintético com mudança em quatro segundos; assert nenhum candidato atravessa quatro segundos além da tolerância de amostragem de 0,5 segundos.
- [x] Escrever `test_motion_pause_changes_boundary`, `test_constant_motion_has_bounded_windows`, `test_short_edges_preserved`; assert limites válidos, duração máxima oito segundos e preservação de fonte de 2,3 segundos.
- [x] Executar `.\.venv\Scripts\python.exe -m pytest tests/test_segmentation.py -q`; confirmar falha antes de implementar.
- [x] Implementar amostragem a 0,5 segundos, detetor de mudança de histograma e pontos de pausa/variação do optical flow. Guardar thresholds como constantes com comentários sobre unidade/escala; calibrar nos vídeos sintéticos. Separar fronteiras obrigatórias de cena de cortes preferenciais. Usar janelas de três a oito segundos quando possível.
- [x] Integrar as janelas no analyzer e pontuar início/meio/fim; progresso monotónico até um. Executar testes da tarefa e regressões da análise; todos passam.

### Task 3: Encoder do prompt offline

**Interfaces:** Em `prompt_scorer.py`, `check_prompt_model_files() -> None`, `get_prompt_scorer() -> LocalPromptScorer`, `LocalPromptScorer.encode(prompt: str) -> np.ndarray` de dimensão 512 e norma um; `apply_prompt(segments: list[Segment], prompt: str) -> dict` devolve metadados de relevância e avisos.

- [x] Escrever `test_prompt_empty_uses_base_score`, `test_prompt_adjustment_bounded`, `test_missing_or_corrupt_prompt_model`, `test_prompt_lengths_and_whitespace`; assert ajuste no intervalo [-10,10], ausência de carregamento de modelo no prompt vazio e erro claro com dependência ausente.
- [x] Executar `.\.venv\Scripts\python.exe -m pytest tests/test_prompt.py -q`; confirmar falhas.
- [x] Instalar explicitamente os artefactos do modelo oficial `sentence-transformers/clip-ViT-B-32-multilingual-v1`: preferir `onnx/model.onnx` CPU, tokenizer JSON e projeção `2_Dense/model.safetensors`, aproximadamente 539 MB para o encoder. Fixar revisão obtida da API oficial e SHA-256 dos artefactos antes de declarar instalação pronta. Reutilizar ONNX Runtime; acrescentar `tokenizers` e `safetensors` se usados, com versões fixadas após instalação e `pip check`.
- [x] Implementar tokenizer local, limite de 128 tokens conforme modelo, ONNX, pooling médio com attention mask e projeção linear 768→512 segundo os configs oficiais. Inspecionar outputs reais: se o ONNX já incluir pooling/projeção, não duplicá-los. Validar dimensão/norma e não usar pickle, código remoto ou downloads no runtime.
- [x] Implementar relevância como cosine similarity. Centrar os valores dos candidatos, multiplicar diferenças por 50 e limitar a [-10,10]; informar baixa diferenciação quando amplitude das similaridades <0,02. Conservar cosine original e ajuste separado.
- [x] Executar inferência real com rede bloqueada em `test_portuguese_image_text_matching_offline`: imagens de teste locais visualmente distintas, assert correspondência correta entre descrições portuguesas e imagens, embedding finito/norma um, e ranking alterado em candidatos de qualidade próxima. Se não passar, corrigir preprocessing/pooling antes de continuar; não substituir por palavras-chave.
- [x] Repetir testes de prompt, IA estética e integridade; documentar tamanho real, hashes e dependências verificadas.

### Task 4: Modelo de revisão e normalização

**Interfaces:** Em `review.py`, `build_review(project: Project, segments: list[Segment], options: ProcessRequest) -> dict`, `load_review(project: Project) -> dict`, `normalize_selection(candidates: list[dict], selected_ids: list[str], duration: int) -> list[dict]`. DTO candidato: `id`, `filename`, `start`, `end`, `score`, métricas, `reasons`, URLs; DTO revisão: `candidates`, `suggestedIds`, `selectedIds`, `effectiveSegments`, `effectiveDuration`, opções e avisos. Arrays visuais ficam apenas no disco/backend.

- [x] Escrever `test_normalize_order_trim_and_short_duration`; assert ordem pedida, soma <= objetivo, último intervalo encurtado e seleção curta preservada.
- [x] Escrever `test_review_rejects_empty_unknown_duplicate_and_overlap`; assert ValueError para esses pedidos, aceitar intervalos adjacentes.
- [x] Executar `.\.venv\Scripts\python.exe -m pytest tests/test_review.py -q`; confirmar falhas.
- [x] Implementar IDs determinísticos por origem/intervalo, motivos derivados de métricas e miniaturas JPEG locais. Guardar JSON e embeddings NumPy sem pickle, publicar dados por substituição de ficheiro temporário. Não expor embeddings no DTO HTTP.
- [x] Executar testes da tarefa; todos passam.

### Task 5: API e exportação separadas

**Interfaces:** `analyze_project(project: Project, request: ProcessRequest) -> None`, `export_project(project: Project, selected_ids: list[str], request: ProcessRequest) -> None`, `process_project(project, request)` conserva caminho automático. Pydantic: `prompt` máximo 500, `ExportRequest` com `selectedIds`, duração/cores; `SuggestRequest` com prompt. Estados adicionais `analyzing`, `review`, `exporting`.

- [x] Escrever `test_analysis_stops_at_review_without_export`, `test_suggest_reuses_embeddings`, `test_export_order_and_validation`, `test_concurrent_export_rejected`, `test_failed_reexport_preserves_result` em `test_review.py`; assert estados, arquivos e respostas 202/409/422 esperadas.
- [x] Escrever `test_media_project_scoping_and_range` e `test_unsupported_original_preview_fallback`; assert acesso apenas a recursos do projeto e reprodução de derivado local compatível quando necessário.
- [x] Executar `.\.venv\Scripts\python.exe -m pytest tests/test_review.py -q`; confirmar falhas das novas rotas.
- [x] Acrescentar `/analyze`, `/review`, `/suggest`, `/export`, `/thumbnail/{candidate_id}` e `/preview/{candidate_id}`. Preview resolve recurso conhecido; produzir derivado curto H264 compatível quando o original não for reproduzível. Não aceitar caminhos livres. Validar modelo de texto apenas com prompt não vazio.
- [x] Separar orquestração; usar lock para transições e executor existente. Exportar para saída temporária e substituir `final.mp4` apenas após sucesso. Conservar manifesto da última exportação válida; numa falha voltar à revisão com erro e manter resultado anterior acessível. Limpar erro ao repetir operação válida.
- [x] Executar testes da tarefa e `.\.venv\Scripts\python.exe -m pytest -q`; corrigir regressões do `/process`, Range e exportação curta.

### Task 6: Prompt e revisão na interface

**Interfaces:** Definir `MomentCandidate`, `EffectiveSegment`, `ReviewData`, `ExportOptions` no modelo TypeScript, espelhando task 4. VideoService: `analyze(id, options)`, `getReview(id)`, `suggest(id, prompt)`, `export(id, options)`. Componente `MomentReviewComponent` recebe `ReviewData`; emite seleção ordenada, pedido de sugestão e pedido de exportação. Frontend recalcula intervalos com a mesma normalização do backend e reconcilia resposta do servidor.

- [x] Escrever testes Playwright `prompt_and_review_before_export`, `replace_remove_reorder_and_duration`, `prompt_requires_explicit_apply`, `review_keyboard_mobile`, `preview_failure_is_actionable`; assert controlos, ordem, duração, ausência de exportação antecipada e preservação da seleção durante edição do prompt.
- [x] Executar `npm test -- tests/review.spec.ts`; confirmar falha antes do ecrã existir.
- [x] Adicionar textarea com maxlength 500 e ajuda exata da especificação; botão inicial «Analisar momentos». Integrar novos estados no polling e carregar revisão quando estado `review`.
- [x] Implementar cartões de selecionados e biblioteca, miniaturas, preview limitado ao intervalo, motivos, botões remover/substituir/adicionar/subir/descer, duração explícita e aviso de seleção curta. Não depender de drag and drop. Desativar ações enquanto analisa/sugere/exporta.
- [x] Implementar «Aplicar prompt» e «Restaurar seleção automática»; editar o texto não muda seleção manual. Exportar lista ordenada de IDs e mostrar «Exportar N segundos»; lista vazia impede submissão. Resultado oferece «Voltar à revisão».
- [x] Executar `npm test -- tests/review.spec.ts` e `npm run build`; todos passam. Atualizar testes de workflow para o passo de revisão, preservando regressões de falhas de ligação e uploads.

### Task 7: Verificação integrada e entrega

**Interfaces:** Todos os contratos anteriores; não acrescentar funcionalidades fora da especificação.

- [x] Executar backend `.\.venv\Scripts\python.exe -m pytest -q` e `.\.venv\Scripts\python.exe -m pip check`; confirmar zero falhas/conflitos.
- [x] Executar frontend `npm test` e `npm run build`; confirmar revisão mobile/teclado, inferência local, resultado reproduzível e download.
- [x] Comparar os candidatos dos quatro originais DJI já disponíveis num projeto de verificação separado, preservando a montagem existente. Registar tempo de análise, intervalos propostos e limites observados; não declarar preferência estética sem avaliação humana.
- [x] Atualizar `README.md` com instalação do modelo textual, exemplo de prompt descritivo, limites e fluxo; guardar resultados reais em `docs/selection-review-prompt-validation.md`.
- [x] Rever alterações contra os critérios de aceitação, incluindo modelos ausentes, prompt vazio, lista vazia, duração curta e exportação repetida. Corrigir defeitos antes de apresentar conclusão.
- [x] Se for preciso reiniciar serviços para validar, usar o script local existente e processos ocultos; verificar health/AI status e atualizar `work/servers.json` com PIDs e horas reais. Não reiniciar sem necessidade.

## Auto-revisão do plano

Cobertura: ranking (1), cortes (2), prompt/instalação (3), edição/intervalos (4), estados/API/exportação (5), interface (6), regressões/documentação (7). Nomes e DTOs são consistentes entre backend e frontend. As cinco condições de Review Focus têm testes atribuídos. Não inclui contas, APIs de IA remotas ou recuperação de projetos fora do âmbito. Nenhum código de produto foi alterado durante o planeamento.

## Execução proposta

Recomenda-se execução nativa nesta conversa: os contratos são dependentes e é útil validar o modelo real antes de integrar o resto. O utilizador ainda deve rever o plano e escolher o método; não iniciar implementação apenas porque o documento foi escrito.
