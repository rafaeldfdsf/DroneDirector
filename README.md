# DroneDirector

Aplicação local para Windows: recebe várias filmagens MP4/MOV, avalia a qualidade visual com **IA local**, combina a avaliação com estabilidade e outras métricas OpenCV, escolhe os melhores momentos e gera `final.mp4`. Interface em português de Portugal, drag and drop, progresso, player HTML5 e download. Sem contas, base de dados, música, Docker, cloud ou API de IA paga.

## Estrutura

```text
D:\Work\drone-director\
├── frontend\                  Angular standalone + TypeScript + SCSS
│   ├── src\app\pages\create-project\
│   ├── src\app\components\    video-upload, processing-progress, moment-review, video-result
│   ├── src\app\services\video.service.ts
│   ├── src\app\models\project.model.ts
│   └── tests\                 testes de browser Playwright
├── backend\                   Python + FastAPI
│   ├── .venv\
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── setup_ai.py             instalação única dos modelos locais
│   ├── ai_models\              pesos CLIP/LAION (~89 MB) + encoder de texto (~135 MB)
│   ├── api\projects.py
│   ├── models\project.py
│   ├── services\              ai_scorer, analyzer, scoring, color_enhancer, video_editor, processor
│   └── tests\
├── projects\{uuid}\
│   ├── original\
│   ├── clips\
│   ├── data\analysis.json
│   └── output\final.mp4
├── docs\                      decisões e plano
├── work\                      ficheiros sintéticos e resultados dos testes
└── README.md
```

## Requisitos

- Windows com Python 3.11+ de 64 bits, Node.js 24 e npm. Angular 21 é compatível com o Node 24 instalado: [tabela oficial](https://angular.dev/reference/versions).
- FFmpeg **e ffprobe** no PATH, com encoder `libx264`. Instalação encontrada nesta máquina: FFmpeg 8.1.2.
- Espaço livre para originais enviados, clips e resultado; o upload copia as filmagens.
- A primeira instalação das dependências precisa de Internet; o processamento é inteiramente local.
- O modelo de IA também é descarregado uma vez durante a instalação. Os pesos ficam no projeto, não numa API externa. ONNX Runtime CPU executa o modelo sem PyTorch, CUDA ou chave de API.

Versões verificadas na implementação: Python 3.11.9, Node 24.21.0, npm 11.19.0 e Angular 21. As dependências do frontend ficam registadas em `package-lock.json`.

Verificar no PowerShell:

```powershell
python --version
node --version
npm --version
ffmpeg -version
ffprobe -version
ffmpeg -hide_banner -encoders | Select-String libx264
```

### Instalar/configurar FFmpeg

Se os comandos anteriores não forem reconhecidos:

```powershell
winget install --id Gyan.FFmpeg --exact
```

Fecha e abre um novo PowerShell e confirma `ffmpeg -version` e `ffprobe -version`. Também podes extrair uma distribuição Windows indicada na [página oficial de download do FFmpeg](https://ffmpeg.org/download.html) e adicionar a pasta `bin` às variáveis de ambiente do utilizador. Para a sessão atual:

```powershell
$env:Path = 'C:\Tools\ffmpeg\bin;' + $env:Path
```

Em alternativa, define os executáveis antes de iniciares o backend:

```powershell
$env:FFMPEG_PATH = 'C:\Tools\ffmpeg\bin\ffmpeg.exe'
$env:FFPROBE_PATH = 'C:\Tools\ffmpeg\bin\ffprobe.exe'
```

Não é necessário um pacote Python chamado ffmpeg. O backend chama os executáveis diretamente, sem shell. Sem FFmpeg, a API e o frontend podem arrancar, mas o processamento apresenta uma mensagem clara e não começa.

## Instalar e iniciar

Abre **dois terminais PowerShell**, um por servidor.

### Backend

O ambiente virtual já foi criado nesta máquina. Para uma instalação nova:

```powershell
cd D:\Work\drone-director\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python setup_ai.py
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Se o PowerShell impedir a ativação, podes iniciar sem alterar a política de execução:

```powershell
cd D:\Work\drone-director\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup_ai.py
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend: <http://localhost:8000/api/health>. Swagger: <http://localhost:8000/docs>.

Estado da instalação IA: <http://localhost:8000/api/ai/status>. `ready: true` significa que os pesos estão presentes e passaram as verificações de integridade. O setup pode ser repetido: reutiliza downloads válidos e repara ficheiros ausentes/corrompidos. Sem o modelo, o endpoint de processamento responde com erro 503 em português; não recorre silenciosamente à seleção apenas heurística.

**Usa um único processo Uvicorn.** O estado é mantido em memória; múltiplos workers não partilham os projetos. O modo `--reload` é útil no desenvolvimento; alterações ao código reiniciam o servidor e perdem o estado dos projetos. Para processamentos reais, podes omitir `--reload`.

### Frontend

```powershell
cd D:\Work\drone-director\frontend
npm install
npm start
```

Ou `npx ng serve`, sem instalar Angular CLI globalmente. Abre <http://localhost:4200>.

O `VideoService` usa `http://localhost:8000/api/projects`. CORS permite explicitamente `http://localhost:4200` e `http://127.0.0.1:4200`.

No final da sessão de implementação os dois servidores foram deixados ativos em segundo plano, sem reload. Para os parar antes de voltares a usar os comandos de arranque:

```powershell
cd D:\Work\drone-director
powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop-Local.ps1
```

O script só para os processos registados em `work\servers.json` e confirma o instante de arranque para não parar um PID reutilizado. Servidores que inicias nos teus terminais param com `Ctrl+C`.

Para compilar a versão de produção:

```powershell
cd D:\Work\drone-director\frontend
npm run build
```

Saída em `frontend\dist\frontend\browser`. Os servidores de desenvolvimento não são servidores de publicação.

## Utilizar

1. Arrasta vários MP4/MOV ou carrega em **Selecionar vídeos**.
2. Confirma a lista e remove qualquer ficheiro indesejado.
3. Escolhe 15, 30 ou 60 segundos e ativa/desativa a melhoria de cor.
4. Opcionalmente, escreve uma orientação descritiva em português, como **paisagem natural, rio e vegetação** (até 500 caracteres).
5. Carrega em **Analisar momentos**. Aguarda o upload e a análise local.
6. Na revisão, pré-visualiza, remove, substitui ou ordena os momentos. A duração e os intervalos mostrados correspondem ao que será exportado. Uma seleção curta pode ser exportada com a duração indicada.
7. Para mudar a orientação, edita o prompt e carrega em **Aplicar prompt**; o texto sozinho não altera a seleção. **Restaurar seleção automática** recupera a última sugestão.
8. Carrega em **Exportar N segundos**. No resultado, reproduz/descarrega o MP4 ou usa **Voltar à revisão** para outra montagem sem nova análise.

Se a ligação falhar, a consulta é tentada novamente. Após falhas repetidas podes usar **Retomar consulta de progresso**. O processamento continua no backend enquanto o servidor estiver ativo. Mantém a página aberta; a recuperação após recarregar a página não faz parte deste MVP.

Aceita até 50 vídeos por projeto, com máximo de 20 GB por ficheiro. Valida extensões, ficheiros vazios e se o primeiro frame é legível. Se um upload múltiplo falhar, os ficheiros desse pedido são removidos; uploads anteriores válidos são preservados. Nomes repetidos recebem sufixos e nomes reservados Windows são normalizados. As filmagens originais fora da pasta do projeto não são alteradas.

## Como funciona

- Cortes variáveis (normalmente três a oito segundos), guiados por mudanças de aparência e pausas de movimento, com amostragem temporal a cada 0,5 segundos. Fontes/cenas curtas são preservadas. A análise cria miniaturas; pré-visualizações H.264 pequenas são geradas localmente a pedido.
- Seis pares de frames próximos por segmento, com resolução de análise limitada a 640 px. Não percorre todos os frames para calcular as métricas. A procura de frames em ficheiros longos/GOPs grandes ainda implica trabalho de descodificação.
- **IA estética:** três dos frames amostrados são analisados pelo CLIP ViT-B/32, seguido do preditor estético LAION V1 treinado para estimar a preferência estética por imagens. O avaliador recebe embeddings normalizados CLIP; a média dos scores dos frames define `aiScore` na escala 0–100. Não utiliza prompts manuais como substituto de um avaliador treinado.
- **Nitidez:** variância do Laplaciano, normalizada por `100 × variância / (variância + 150)`.
- **Exposição:** penaliza pixels abaixo de 16 e acima de 239, mais um pequeno desvio da luminosidade média equilibrada.
- **Estabilidade:** `goodFeaturesToTrack` + `calcOpticalFlowPyrLK`, mediana do deslocamento, mudanças entre amostras e movimento residual. Sem textura suficiente, usa 50 como estimativa conservadora. Não estabiliza as imagens.
- **Movimento:** recompensa deslocação moderada, penaliza ausência de movimento e velocidades excessivas.
- **Score técnico:** 40% estabilidade, 30% nitidez, 20% exposição e 10% movimento. O score final que determina a seleção é **70% `aiScore` + 30% `technicalScore`**. Guarda os scores e as previsões por frame em `analysis.json`, juntamente com o modelo e as revisões utilizadas.
- **Diversidade:** qualidade primeiro, com penalizações graduais por origem (até seis pontos) e semelhança visual (até oito pontos). Intervalos adjacentes são permitidos; sobreposição não é. A diversidade não tem prioridade absoluta sobre a qualidade.
- **Ordem:** agrupa pela ordem de upload, depois pelo tempo original dentro de cada vídeo. A ordem do score nunca define a montagem.
- **Cor opcional:** `eq=contrast=1.06:saturation=1.10:gamma=1.02`. Se desativada, não acrescenta o filtro `eq`.
- **Exportação:** cortes simples, sem áudio, H.264/libx264, yuv420p, 1920×1080, 30 fps, CRF 20 e preset veryfast. Mantém proporções com barras pretas, sem distorcer. FFmpeg concatena clips compatíveis; `+faststart` e respostas HTTP Range permitem reprodução e procura no browser.
- **Duração:** corta o último clip quando necessário. Se não existir material suficiente, exporta a duração disponível e mostra a duração real. Pode haver arredondamento de um frame devido aos 30 fps.

Nitidez, exposição e estabilidade são calculadas juntas por segmento para evitar três leituras completas. A IA reutiliza três desses frames, sem uma segunda leitura completa do vídeo. O modelo é carregado uma vez por processo e reutilizado. O progresso reflete análise e clips concluídos, não uma previsão exata de tempo. A melhoria de cor é aplicada durante a extração; a interface mostra estas tarefas juntas.

### Modelo e privacidade

O encoder é o [CLIP ViT-B/32 convertido para ONNX por Xenova](https://huggingface.co/Xenova/clip-vit-base-patch32), acompanhado pelo [LAION Aesthetic Predictor V1](https://github.com/LAION-AI/aesthetic-predictor). O download do encoder int8 é de cerca de 89 MB; o head estético é pequeno. As fontes, revisões e SHA-256 estão fixadas no código e são registadas em `backend\ai_models\manifest.json`.

O pré-processamento usa RGB, resize bicúbico, crop central 224×224 e normalização CLIP. O checkpoint estético é lido como dados float32 de um ZIP cujo hash foi verificado, sem executar pickle. A inferência chama apenas ONNX Runtime e NumPy; não usa Internet, telemetria de modelos ou APIs. Apenas `setup_ai.py` faz downloads dos pesos, sem receber as tuas filmagens.

Por portabilidade, a implementação atual usa CPU, mesmo em máquinas com GPU NVIDIA. Uma eventual versão GPU é uma otimização posterior. Os embeddings usados para diversidade e novos prompts ficam no ficheiro local `data/review.json`; nunca são enviados ao browser ou para fora do computador.

## Prompt e revisão local

O encoder [CLIP multilingue de Sentence Transformers](https://huggingface.co/sentence-transformers/clip-ViT-B-32-multilingual-v1) traduz texto português em embeddings compatíveis com os visuais. ONNX quantizado (~135 MB), tokenizer e projeção Safetensors são instalados pelo mesmo `setup_ai.py`, com revisão e hashes fixados. Não usa PyTorch/CUDA nem API de inferência. Executa `pip install -r requirements.txt` e `python setup_ai.py` para atualizar uma instalação anterior.

A correspondência textual contribui até dez pontos para o ranking; o score estético original fica separado. O prompt é uma preferência visual, não um modelo de linguagem: negações, narrativa e comandos de edição não têm cumprimento garantido. Descreve conteúdos desejados e confirma a montagem na revisão. Sem prompt, apenas o modelo estético é necessário. Um modelo textual ausente/corrompido gera erro explícito quando o prompt está preenchido.

A nova interface usa `/analyze` → `/review` → `/export`; `/process` continua disponível para exportação automática. `/suggest` reaplica o prompt aos embeddings já calculados; `/thumbnail/{candidate_id}` e `/preview/{candidate_id}` servem os momentos conhecidos do projeto, com preview compatível e suporte Range. Não aceitam caminhos arbitrários.

## API

| Método | Endpoint | Função |
| --- | --- | --- |
| POST | `/api/projects` | Cria projeto e devolve `projectId` |
| POST | `/api/projects/{id}/videos` | Multipart, vários campos `videos` |
| POST | `/api/projects/{id}/process` | JSON `{ "duration": 30, "enhanceColors": true }`; devolve 202 rapidamente |
| GET | `/api/projects/{id}/status` | Estado, progresso, etapa, erro, duração e momentos |
| GET | `/api/projects/{id}/result` | MP4 inline, com suporte Range |
| GET | `/api/projects/{id}/result?download=true` | Download de `final.mp4` |
| GET | `/api/ai/status` | Estado da instalação local do modelo e integridade dos ficheiros |

Estados: `created`, `uploading`, `ready`, `queued`, `processing`, `analyzing`, `review`, `exporting`, `completed`, `failed`. O executor tem um trabalhador e processa um projeto de cada vez, mantendo a API disponível. Não aceita novos uploads/processamento duplicado depois de começar. Se a análise falhar, cria um novo projeto. Uma exportação falhada volta à revisão, preservando a seleção manual e o último resultado válido.

Os erros públicos são legíveis em português. Os detalhes técnicos ficam no terminal do backend.

## Testes

Backend:

```powershell
cd D:\Work\drone-director\backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe setup_ai.py
.\.venv\Scripts\python.exe -m pytest -q --basetemp ..\work\pytest
```

Testes de browser (precisam de FFmpeg e Chromium Playwright):

```powershell
cd D:\Work\drone-director\frontend
npm install
$env:PLAYWRIGHT_BROWSERS_PATH = 'D:\Work\drone-director\work\browsers'
npx playwright install chromium
npm test
```

Playwright inicia os servidores se as portas estiverem livres e fecha os que iniciou. Se já houver servidores nas portas 4200 e 8000, usa-os. Os projetos dos testes ficam em `work\ui-projects` quando o teste inicia o backend; se usar um backend existente, ficam na pasta configurada nesse backend. Não interrompas uma montagem real para executar testes.

Os testes usam **vídeos sintéticos** gerados por FFmpeg/OpenCV: não demonstram qualidade estética em filmagens DJI reais, D-Log ou HDR. A inferência utiliza os pesos reais; um teste bloqueia chamadas de rede para verificar que a IA funciona offline. Os testes de backend verificam pré-processamento CLIP, score híbrido, diversidade visual/temporal, falta/corrupção de modelos, 15/30/60 segundos, vídeos curtos, nomes repetidos, ficheiros inválidos, ausência de FFmpeg, rollback de upload, processamento assíncrono, mistura de resolução/framerate, saída H.264 e Range. Os testes de browser exercitam seleção/remoção, drag and drop, layout móvel, recuperação de erros, upload, seleção com IA, exportação de 15 segundos, reprodução e download.

## Limitações e próximos passos

- A IA estima estética visual segundo o seu treino: não garante a tua preferência pessoal nem compreende a narrativa/ação do vídeo. São analisadas imagens amostradas, não uma sequência temporal completa. As métricas de movimento e estabilidade continuam heurísticas. Avaliar os scores em filmagens DJI reais é o próximo passo recomendado.
- A correção ligeira não converte D-Log/HDR para SDR nem aplica gestão de cor especializada. Começa por filmagens SDR comuns.
- Exportação fixa a 1080p/30 fps; não preserva 4K, áudio, metadados ou FPS original.
- Sem cancelamento, persistência do estado, limpeza automática ou recuperação de jobs após reinício. Os ficheiros permanecem em `projects`; com o backend parado, remove manualmente apenas as pastas de projetos que já não precisas.
- Filmagens extensas/4K podem demorar a analisar e recodificar; este MVP usa CPU e limita a concorrência. Cada comando FFmpeg tem timeout de uma hora.
- Se o OpenCV/FFmpeg não conseguir descodificar um codec, aparece um erro; a extensão MP4/MOV por si só não garante compatibilidade.
- O servidor destina-se ao computador local. Não o expor diretamente à Internet.

Evoluções posteriores: afinar os critérios com avaliação humana, escolher resolução de saída, acelerar com GPU e adicionar cancelamento/limpeza e recuperação de projetos. Música e contas ficam fora desta versão.
