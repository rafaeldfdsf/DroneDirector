# DroneDirector Cinematic and 4K Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preservar movimentos, sugerir uma sequência coerente, filtrar planos fracos, reduzir repetição, corrigir cor por fonte e exportar 4K a partir dos originais.

**Architecture:** Evoluir a análise/revisão/exportação já existentes. Extrair sinais temporais de proxies tecnicamente convertidos, calcular qualidade e papéis visuais com os modelos locais, sugerir planos completos e sequência; a revisão continua a controlar a escolha final. A exportação usa os originais e parâmetros de cor/resolução/FPS confirmados.

**Tech Stack:** Angular 21, FastAPI/Pydantic, OpenCV/NumPy, CLIP/LAION e encoder multilingue ONNX já instalados, FFmpeg/ffprobe, pytest/Playwright. Sem novos modelos ou serviços de inferência.

**Spec:** `D:/Work/drone-director/docs/superpowers/specs/2026-10-08-cinematic-4k-design.md`, aprovada pelo utilizador.

## Global Constraints

- Trabalho em `D:/Work/drone-director`; projeto sem Git, não inicializar repositório. Preservar originais, resultados anteriores e outros projetos.
- Manter tudo local; sem contas, cloud, música ou aprendizagem de preferências.
- Série temporal a cada 0,5 segundos; candidatos normalmente entre dois e vinte segundos, preservando fontes completas mais curtas.
- Novo modo: objetivo máximo 15/30/60, planos completos sem encurtamento silencioso; modo antigo conserva duração exata e corte do último intervalo.
- Frontend novo: cinematográfico ativo, 4K e FPS automático. Clientes sem opções: `cinematic=false`, `resolution=1080p`, FPS 30.
- 4K: 3840×2160; 1080p: 1920×1080; H.264/yuv420p, 16:9, faststart, SDR Rec.709; sem interpolação por IA ou encoder GPU.
- LUT local `.cube`: tabela 3D de tamanho 2 a 65, domínio finito com mínimo inferior ao máximo, entradas exatas e finitas, até 20 MB; perfil Log exige LUT explícita apropriada.
- Proxy até 640 px no lado maior, dez FPS, alinhado ao original; alteração de perfil/LUT invalida análise, alteração de resolução/FPS não.
- Prompt até 500 caracteres e avaliação estética atual mantidos. O novo modo exige modelo textual para papéis visuais mesmo com prompt vazio; nenhum fallback silencioso.

## Review Focus

1. Todos os candidatos fracos ou maiores que o objetivo: revisão vazia recuperável, nunca exportação automática de material rejeitado (tarefas 3/5/8).
2. Fontes com taxas fracionárias diferentes: resolução/FPS comuns, duração correta e decisão explícita de 30 FPS automático (tarefas 1/7).
3. LUT válido com negativos/valores acima de um, ou nomes Windows com espaços/apóstrofos: tratar como dados e evitar injeção no filtro FFmpeg (tarefas 1/6/7).
4. Reanálise após mudança de perfil: IDs/previews antigos não podem identificar outros candidatos; preservar último vídeo e exigir confirmação para descartar seleção (tarefas 6/8).
5. Céu/água/cena sem textura e pôr-do-sol: confiança baixa não prova desfoque, inclinação ou erro de cor; não excluir nem neutralizar automaticamente (tarefas 2/3/6).

## Mapa de ficheiros

- Novos serviços `backend/services/source_media.py` (metadados, proxy e LUT), `motion_analysis.py` (sinais/limites), `quality.py` (avisos e exclusão), `sequencing.py` (papéis/diversidade/ordem).
- Evoluir `analyzer.py`, `segmentation.py`, `ai_scorer.py`, `scoring.py`, `review.py`, `processor.py`, `color_enhancer.py`, `video_editor.py` sem concentrar toda a lógica num ficheiro.
- Evoluir `backend/models/project.py`, `api/projects.py`; LUTs e proxies guardados no projeto, não no diretório global de modelos.
- Frontend: modelos/serviço HTTP, `create-project/*`, `moment-review/*`, `video-result/*`; novo `source-settings/*` para perfis/LUT por ficheiro e opções comuns de exportação.
- Novos testes `test_source_media.py`, `test_motion_quality.py`, `test_sequencing.py`, `test_color_4k.py`; ampliar regressões existentes. Novo browser `frontend/tests/cinematic.spec.ts`.

### Task 1: Contratos, metadados e LUTs locais

**Interfaces:** `SourceColor(BaseModel)` com `profile: Literal['sdr','dlog','dlogm']` e `lutId: str | None`; ProcessRequest ganha `cinematic: bool=False`, `resolution: Literal['1080p','2160p']='1080p'`, `fps: Literal['auto','24','25','30','50','60']='30'`, `sourceProfiles: dict[str,SourceColor]` e `replaceReview: bool=False`. ExportRequest ganha `acknowledgedWeakIds: list[str]=[]`. SuggestRequest ganha duração/modo opcionais. Configurações de fonte usam nomes normalizados devolvidos pelo upload, nunca caminhos livres.

Em `source_media.py`: `probe_source(path: Path) -> dict` devolve dimensão, duração, FPS racional e tags de cor; `validate_cube(content: bytes) -> dict`; `store_lut(project: Project, content: bytes) -> dict` devolve ID/hash/tamanho; `resolve_source_color(project, filename, profiles) -> dict` valida a pertença e LUT. Endpoints POST/GET `/{id}/luts`, GET `/{id}/sources`.

- [ ] Escrever testes: `test_fractional_source_metadata` assert FPS `30000/1001`; `test_cube_identity_and_bounds` aceita tabela 2 e floats finitos negativos/maiores que um; `test_invalid_cube_rejected` rejeita tamanho 1/66, contagem errada, domínio invertido, NaN/Inf e >20 MB; `test_lut_project_scoping` rejeita ID externo; `test_old_options_defaults` fixa compatibilidade.
- [ ] Executar `.\.venv\Scripts\python.exe -m pytest tests/test_source_media.py -q` no backend; confirmar falha por interfaces ausentes.
- [ ] Implementar probe via lista de argumentos ffprobe, validação streaming/limite de LUT e armazenamento canónico com ID gerado/hash. Não usar shell, pickle ou nome fornecido pelo utilizador como caminho. Guardar manifestos de fontes/LUT no projeto e validar Log sem LUT antes da análise.
- [ ] Repetir testes e validação API existente; todos passam.

### Task 2: Proxy e movimentos contínuos

**Interfaces:** `prepare_proxy(project: Project, filename: str, color: dict) -> Path` em source_media; `sample_motion(path: Path, duration: float, on_progress) -> list[dict]` e `movement_windows(samples: list[dict], duration: float) -> list[dict]` em motion_analysis. Amostra contém `time`, `vector`, `speed`, `residual`, `appearanceChange`, `confidence`; janela contém limites/tipo/confiança. Analyzer acrescenta parâmetros opcionais `cinematic=False`, `source_filename=None`, mantendo as três entradas existentes compatíveis.

- [ ] Escrever `test_proxy_duration_and_profile_cache` assert lado maior <=640, dez FPS, duração/alinhamento com erro <=0,1 s, cache distinto com perfil/hash distinto; `test_export_resolution_does_not_invalidate_proxy` assert mesma identidade para 1080p/4K.
- [ ] Escrever `test_smooth_motion_preserved`, `test_isolated_motion_noise_not_boundary`, `test_sustained_pause_or_reversal_is_boundary`, `test_short_or_static_source_valid`; assert limite natural além de oito segundos, persistência >=três amostras, intervalos válidos e confiança conservadora sem textura.
- [ ] Executar testes novos; confirmar falha antes de implementar.
- [ ] Implementar proxy FFmpeg sequencial a dez FPS, incluindo LUT técnica mas sem ajuste estético, com publicação temporária e verificação da duração. Séries normalizadas por largura/tempo; agregar pausas/alterações por três amostras. Mudança forte de aparência permanece fronteira. Dar prioridade a pausas/inícios/fins; trecho >20 s usa limite suave de baixa confiança.
- [ ] Analyzer usa proxy apenas no novo modo, conserva filename/tempos originais, mede métricas/embeddings ao longo do candidato. Guardar embeddings por frame necessários para possível revelação em dados privados; não os enviar no DTO público. Assegurar progresso monotónico.
- [ ] Executar `test_motion_quality.py` e regressões de segmentation/analyzer; todos passam.

### Task 3: Qualidade sustentada e avisos

**Interfaces:** `assess_quality(samples: list[dict], horizon: dict | None=None) -> dict` em quality devolve `qualityWarnings`, `autoEligible`, `qualityConfidence`, `weakReasonCodes`. `recover_stable_windows(samples, windows) -> list[dict]` devolve candidatos interiores utilizáveis.

- [ ] Escrever `test_sustained_blur_clipping_or_jerk_rejected` assert inelegibilidade após pelo menos três amostras consecutivas; `test_isolated_bad_sample_is_warning_only`; `test_stable_middle_recovered`; `test_textureless_or_unknown_horizon_not_rejected`; `test_all_weak_candidates_stay_in_library`.
- [ ] Executar testes novos; confirmar falhas.
- [ ] Implementar limiares iniciais explícitos: clipping severo quando >35% dos pixels estão perto de extremos e persistente; nitidez normalizada <20 com confiança/textura suficiente; irregularidade global com aceleração/residual altos calibrada ao proxy. Guardar limiares no relatório e validar contra blur/clipping/jerk sintéticos antes de aplicar exclusão. Se calibração contradizer estes valores, registar decisão fundamentada no ledger e ajustar.
- [ ] Estimar horizonte com linhas longas/contexto e confiança; inclinação >5° é aviso apenas com confiança >=0,8, nunca uma rotação automática. Sem contexto, horizonte desconhecido. Aplicar recuperação de região estável antes de excluir candidatos.
- [ ] Executar testes e verificar que cenas escuras/claras intencionais e sem textura não são excluídas por mera média luminosa.

### Task 4: Papéis visuais, diversidade e sequência

**Interfaces:** `classify_visual_roles(segments: list[dict]) -> None`, `motion_repetition_penalty(candidate: dict, chosen: list[dict]) -> float`, `sequence_segments(selected: list[dict]) -> list[dict]` em sequencing. Segment ganha `visualRole`, `roleConfidence`, `motionType`, `direction`, `speed`, `sequenceRole`, `sequenceReasons`; `select_cinematic_segments(segments,duration,filenames) -> list[dict]` em scoring.

- [ ] Escrever `test_opening_development_closing`, `test_missing_role_does_not_force_weak_candidate`, `test_visual_and_motion_duplicates_penalized`, `test_shared_direction_can_support_different_views`, `test_quality_still_dominates_diversity`. Usar candidatos explícitos com embeddings/métricas conhecidos e assert ordem, elegibilidade e penalização limitada.
- [ ] Executar testes novos; confirmar falhas.
- [ ] Implementar classificação com descrições fixas de plano amplo/detalhe/paisagem e o encoder local existente, margem inicial de 0,025 para rótulo confiável. Guardar similarities/margens, não probabilidades. Possível revelação combina mudança de enquadramento com movimento suave; sinais insuficientes mantêm tipo desconhecido.
- [ ] Escolha só entre autoEligible e candidatos completos que cabem no objetivo. Manter base estética/técnica e ajuste do prompt existentes. Penalização conjunta adicional de repetição limitada a seis pontos; continuidade entre vizinhos limitada a três pontos, para não inverter diferenças grandes de qualidade.
- [ ] Ordenar abertura ampla boa, desenvolvimento diverso e fecho forte quando existirem; fallback determinístico por continuidade/qualidade sem forçar papéis. Não repetir IDs/instantes, não sobrescrever ordem manual.
- [ ] Executar testes novos e inferência real dos papéis com rede bloqueada: scores finitos, dimensões corretas e rótulo desconhecido permitido; não fingir precisão sem validação visual.

### Task 5: Revisão natural, vazia e objetivo variável

**Interfaces:** `normalize_selection(..., cinematic: bool=False, acknowledged_weak_ids: list[str] | None=None) -> list[dict]` mantém assinatura anterior compatível. No modo cinematográfico devolve planos completos ou erro para excesso de duração/avisos sem confirmação. DTO revisão passa a incluir fontes/opções/modo e candidatos avisados; public_review aceita seleção vazia.

- [ ] Escrever `test_complete_intervals_not_trimmed`, `test_over_goal_requires_change`, `test_empty_suggestion_review_valid_export_invalid`, `test_weak_override_requires_acknowledgement`, `test_duration_resuggest_reuses_analysis` e `test_legacy_trim_still_supported`.
- [ ] Executar testes novos; confirmar falhas.
- [ ] Implementar normalização por modo; biblioteca conserva candidatos fracos/longos, sugestão exclui-os quando necessário. GET de revisão vazia devolve zero segundos e aviso. Confirmar cada ID fraco incluído; IDs fora do projeto/duplicados/sobrepostos continuam inválidos.
- [ ] Integrar /suggest com duração/mode opcionais; mudar objetivo reaplica ranking/ordem aos dados locais. Só aplicar nova sugestão após ação explícita. Não deixar normalização legada esconder/truncar planos no modo novo.
- [ ] Executar testes novos, test_review e regressões de recuperação/concorrrência/exportação.

### Task 6: Cor por plano, previews e reanálise

**Interfaces:** Em color_enhancer: `estimate_color_adjustment(frames: list[np.ndarray]) -> dict`, `build_color_filters(source_color: dict, adjustment: dict, enabled: bool) -> list[str]`. LUT técnica sempre precede ajustes; melhoria desativada não remove conversão Log. `run_ffmpeg(arguments, cwd: Path | None=None)` acrescenta cwd sem quebrar chamadas existentes.

- [ ] Escrever `test_identity_lut_and_known_conversion`, `test_log_requires_lut_and_not_double_applied`, `test_neutral_color_adjustment_bounded`, `test_sunset_or_no_neutral_pixels_not_neutralized`, `test_sdr_no_lut`, `test_preview_original_and_corrected_same_interval`.
- [ ] Executar testes novos; confirmar falhas.
- [ ] Implementar exposição conservadora limitada a ±0,35 EV e ganhos de canais entre 0,9 e 1,1. Estimar WB apenas com pixels de baixa cromaticidade representativos em >=1% da amostra; confiança insuficiente mantém ganhos um. Não fixar média cinzenta universal para cenas intencionais.
- [ ] Construir filtros com LUT de ID validado em nome gerado relativo a cwd controlado, evitando caminhos Windows livres. Cache de preview inclui revisão/hash/opções de cor; variantes `original`/`corrected` usam o mesmo intervalo. HDR/HLG produz aviso e bloqueia conversão Log automática.
- [ ] Integrar reanálise confirmada em /analyze: requer `replaceReview=true` e estado review/completed; nova geração de candidatos tem prefixo de revisão novo. Não reutilizar IDs/previews antigos para outros instantes; último vídeo publicado mantém-se disponível perante falha de nova análise. Mudança de perfil/LUT requer reanálise; resolução/FPS não.
- [ ] Executar testes de cor, LUT, caminhos com espaços/apóstrofos e invalidação de cache.

### Task 7: Renderização 4K/FPS e manifesto

**Interfaces:** `resolve_export_settings(source_info: list[dict], selected: list[dict], resolution: str, fps: str) -> dict`; extract_clip acrescenta parâmetros opcionais de exportação/cor com defaults anteriores. Snapshot/manifesto incluem resolução/FPS efetivos e ajustes por plano.

- [ ] Escrever `test_4k_actual_dimensions_and_fractional_fps`, `test_mixed_fps_auto_uses_30`, `test_manual_fps_duration_preserved`, `test_smaller_sources_warn_upscale`, `test_render_uses_original_not_proxy`, `test_failed_4k_preserves_prior_result`.
- [ ] Executar testes novos; confirmar falhas.
- [ ] Implementar quadro 3840×2160/1920×1080, rational FPS comum ou 30 para fontes mistas; opções manuais conforme contratos. Conformar FPS sem alterar timestamps/velocidade. Renderizar originais com LUT técnica + ajustes por plano; todos os clips têm parâmetros de concatenação idênticos.
- [ ] Preparar manifesto temporário com fontes, intervalos efetivos, resolução/FPS racional e LUTs/ajustes. Verificar saída real com ffprobe antes de publicar, preservar tratamento atual de rollback/backup/seleção manual.
- [ ] Executar testes reais FFmpeg, incluindo padrão de detalhe em fonte 4K que se perderia no proxy; assert resolução/FPS e detalhe/uso do original, não apenas argumentos mockados. Executar regressões 15/30/60 no caminho antigo.

### Task 8: Controlos e revisão no frontend

**Interfaces:** Modelos TypeScript espelham Process/Export/SuggestRequest e DTOs. SourceSettingsComponent recebe fontes/opções/LUTs e emite alterações; VideoService ganha sources, uploadLut, reanalyze e variantes de preview. MomentReview mantém ordem/IDs manuais; export emite confirmações de candidatos fracos.

- [ ] Escrever `cinematic.spec.ts`: `cinematic_default_4k_auto_fps`, `complete_movements_and_goal_change`, `empty_suggestion_manual_weak_ack`, `color_profile_requires_lut`, `same_clip_original_corrected_preview`, `color_reanalysis_confirmation_preserves_result`, `4k_export_and_manual_order`, `mobile_keyboard_settings`. Assert rótulos/durações/contratos e erros recuperáveis.
- [ ] Executar `npm test -- tests/cinematic.spec.ts`; confirmar falhas dos novos controlos.
- [ ] Criar configuração SDR/D-Log/D-Log M por fonte, importação de LUT, resolução/FPS e objetivo. Mapear perfis às fontes normalizadas após upload. Mostrar metadados como ajuda, sem afirmar deteção conclusiva do perfil. Mostrar aviso para upscale/HDR e Log sem LUT.
- [ ] Revisão mostra papéis/avisos/duração real, permite objetivo/resolução/FPS, inclusão explícita de planos fracos, preview original/corrigido e confirmação de reanálise antes de substituir seleção. No modo novo, não remover/truncar IDs ao ultrapassar duração: recusar adição ou pedir aumento do objetivo. Mudança de ordem não chama sequenciador.
- [ ] Resultado mostra resolução/FPS reais; criar/analisar/exportar e erros preservam projeto/seleção. Manter acessibilidade teclado/mobile. Atualizar testes antigos do frontend para novo modo e escolher 1080p nos testes que não verificam 4K, evitando custo excessivo sem cobertura adicional.
- [ ] Executar testes novos e build; todos passam.

### Task 9: Verificação integrada e entrega

- [ ] Executar backend `.\.venv\Scripts\python.exe -m pytest -q` e `.\.venv\Scripts\python.exe -m pip check`; zero falhas/conflitos.
- [ ] Executar frontend `npm test` e `npm run build`; confirmar playback/download e opções/estados novos.
- [ ] Usar cópias/hardlinks locais isolados dos quatro DJI já disponíveis; medir análise por proxy, limites, elegibilidade, papéis e duração/ordem sugeridas. Criar uma exportação 4K real separada e verificar ffprobe. Preservar montagem/originais existentes e não afirmar superioridade estética sem avaliação humana.
- [ ] Capturar/inspecionar revisão desktop/mobile com novos controlos e comparação de cor. Atualizar README, guardar evidência em `docs/cinematic-4k-validation.md` e ledger próprio deste plano.
- [ ] Fazer revisão independente do conjunto, conforme executing-plans; defeitos importantes recebem regressão observada a falhar, uma passagem de correção e suite verde. Não adicionar funcionalidades fora dos cinco pontos/4K.
- [ ] Se necessário, atualizar servidores locais sem interromper jobs reais, usar identidades PID/StartTime e processos ocultos; verificar health, frontend HTTP e modelos, guardar identidade atual em work/servers.json.

## Auto-revisão do plano

Cobertura: modelos/LUT (1), movimento/proxy (2), qualidade (3), sequência/diversidade (4), duração/revisão (5), cor/cache (6), 4K/FPS (7), interface (8), verificação/entrega (9). Contratos com defaults antigos e novo modo explícito evitam mudar clientes legados. Review Focus tem testes atribuídos. Metadados/embeddings/séries locais permanecem privados. Sem placeholders ou dependências externas novas; limiares indicados exigem calibração documentada, não garantia de qualidade.

## Execução

Método preservado: nativo nesta conversa, escolhido anteriormente pelo utilizador. Após revisão/aprovação deste plano, usar executing-plans e o ledger `docs/cinematic-4k-progress.md`; não implementar antes dessa revisão.
