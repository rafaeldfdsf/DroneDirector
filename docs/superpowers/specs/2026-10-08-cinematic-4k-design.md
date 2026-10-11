# DroneDirector — movimentos, sequência, qualidade, cor e 4K

Estado: desenho conversacional aprovado pelo utilizador; especificação escrita para revisão antes do plano de implementação.

## Resultado pretendido

Aplicar os pontos 1 a 5 da proposta: preservar movimentos completos, sugerir uma sequência com intenção, filtrar momentos fracos, reduzir repetição e tratar a cor conforme a filmagem. Acrescentar exportação 4K real a partir dos originais. Manter prompt e revisão manual, IA e ficheiros locais, sem contas, cloud, música ou aprendizagem de preferências (ponto 6 não solicitado).

O objetivo é melhorar a montagem com sinais mensuráveis e classificação visual aprendida. Não afirmar compreensão narrativa completa, reconhecimento perfeito de manobras ou garantia de qualidade estética.

## Contexto confirmado

Projeto existente: `D:/Work/drone-director`, Angular/FastAPI/OpenCV/FFmpeg e CLIP/LAION + encoder multilingue ONNX já instalados. Há análise, biblioteca de candidatos, revisão e exportação, com publicação protegida do último resultado válido.

O ficheiro DJI_20261004183832_0106_D.mp4 apresenta 3840×2160, 30000/1001 FPS, tags bt709 e encoder DJI NEO2. Isto confirma resolução/FPS, mas não demonstra inequivocamente o perfil de captura. Não assumir D-Log a partir da imagem pouco contrastada ou de metadados genéricos.

## Abordagem e componentes

Evoluir o pipeline existente, separando extração de sinais temporais, candidatos, qualidade, papéis visuais, sequenciação, cor e exportação. Reutilizar os modelos já instalados; não acrescentar um grande modelo de linguagem/vídeo nesta versão.

Acrescentar cópias de análise leves e locais, sem mudar a origem usada para exportação. Acrescentar transformação de cor explícita por fonte e parâmetros de resolução/FPS na revisão. Preservar o endpoint automático e o modo anterior por omissão para clientes antigos; o frontend novo ativa o modo cinematográfico.

## 1. Preservar movimentos completos

Extrair em cada fonte uma série temporal a cada 0,5 segundos: vetor de movimento global, velocidade, variação de direção, aceleração, movimento residual e mudança de aparência. Usar frames próximos para estimar velocidade; normalizar distâncias à resolução da análise e diferenças ao intervalo temporal.

Identificar mudanças de cena, pausas sustentadas e mudanças fortes de direção. Esses sinais definem movimentos contínuos. Aparência abrupta é uma fronteira de cena; movimento deve ter persistência em várias amostras para não fragmentar uma tomada por ruído.

Criar candidatos que acompanham o movimento, normalmente entre dois e vinte segundos, incluindo fontes completas mais curtas. Remover arranque/paragem bruscos quando há uma região estável interior. Em movimentos longos sem fronteira natural, propor uma janela com limites suaves e confiança menor, identificada como «trecho de movimento»; não apresentar um trecho arbitrário como movimento completo.

Usar embeddings de início/meio/fim e variação do enquadramento para identificar uma possível revelação; combinar com continuidade de movimento. Guardar tipo provável e confiança. Quando o sinal não é suficiente, usar «movimento contínuo» ou «tomada estática», sem inventar uma manobra.

### Duração sem cortar o último movimento

No novo modo, 15/30/60 segundos passam a ser um objetivo máximo para a sugestão. A seleção automática escolhe candidatos completos que cabem no objetivo, preferindo duração próxima apenas depois de qualidade e continuidade. Não cortar o último plano apenas para preencher os segundos.

Mostrar duração real e explicar quando a sugestão é mais curta. Um candidato mais longo do que o objetivo continua visível na biblioteca, mas só pode ser incluído após aumentar o objetivo. Permitir alterar o objetivo na revisão e recalcular a sugestão sem reenviar os vídeos.

Na edição manual, rejeitar uma adição que ultrapasse o objetivo, com mensagem que permite aumentar a duração ou escolher um plano mais curto. Não remover planos escondidos nem encurtar planos silenciosamente. O botão apresenta a duração real que será exportada. Manter a normalização anterior com corte do último intervalo apenas para clientes que não ativem o novo modo.

## 2. Sequência com intenção

Classificar candidatos por comparação CLIP com descrições fixas: plano amplo de apresentação, detalhe/ângulo próximo e plano de paisagem/revelação para fecho. Aproveitar o encoder de texto multilingue e os embeddings visuais existentes. Guardar similaridades e margem entre classes; não as apresentar como probabilidades.

No modo cinematográfico, o encoder de texto é dependência da análise, mesmo sem prompt do utilizador. A pré-verificação deve informar claramente uma instalação ausente/corrompida, sem ignorar silenciosamente a classificação. O caminho antigo sem modo cinematográfico continua a funcionar apenas com o modelo estético.

Escolher abertura que apresente o local quando existir confiança suficiente; desenvolvimento com variedade de enquadramento e movimento; fecho com plano visualmente forte. A ordem deve minimizar mudanças bruscas de direção/velocidade e repetição, sem deixar estes fatores suplantarem diferenças grandes de qualidade.

Não forçar um plano fraco para cumprir um papel. Com apenas um candidato bom, sugerir esse plano. Com papéis incertos, usar ordem coerente baseada em continuidade e qualidade, indicando a incerteza. Evitar reutilizar o mesmo instante como abertura e fecho.

Na revisão mostrar etiquetas «Abertura», «Desenvolvimento», «Fecho» e a justificação. O utilizador mantém liberdade para remover, substituir e reordenar; não recalcular automaticamente a sua ordem manual.

## 3. Filtrar os momentos fracos

Acrescentar medidas de clipping em sombras/luzes, nitidez ao longo do intervalo, movimento residual e irregularidade de direção. A escolha deve considerar a pior região sustentada, além da média: uma tomada com uma correção brusca central não fica boa só porque os extremos são estáveis.

Calibrar limiares com vídeos sintéticos e guardar os valores/limiares usados no relatório. A qualidade absoluta muito baixa deve ser sinalizada; comparação relativa entre origens ajuda a encontrar os melhores trechos, mas não pode fazer uma fonte completamente desfocada parecer boa.

Tentar recuperar uma região estável interior antes de rejeitar a tomada inteira. Excluir da sugestão candidatos claramente desfocados, com clipping severo persistente ou irregularidade forte. Se faltar material bom, sugerir uma duração inferior. Não voltar a preencher a montagem com candidatos rejeitados para atingir o objetivo.

O horizonte inclinado só é assinalado quando existem linhas/contexto suficientes. Classificar deteção insuficiente como desconhecida; nunca rodar/cortar ou excluir automaticamente um plano só por um horizonte estimado com baixa confiança.

Candidatos fracos descodificáveis continuam acessíveis na biblioteca com avisos. Permitir inclusão manual com confirmação explícita dos avisos. Ficheiros ilegíveis nunca são candidatos exportáveis.

Se todos os candidatos forem fracos, terminar em revisão com seleção sugerida vazia e mensagem útil. A API de revisão deve aceitar essa situação; exportação vazia permanece inválida. O utilizador pode incluir candidatos avisados ou importar melhores filmagens num projeto novo.

## 4. Repetição visual e de movimento

Comparar semelhança CLIP, tipo de enquadramento, direção e velocidade. Penalizar especialmente candidatos muito semelhantes e movimentos quase iguais. Conservar penalizações graduais, limitadas, para não substituir um bom plano por um claramente pior apenas por diversidade.

Separar diversidade na escolha global de continuidade entre planos adjacentes. Uma direção semelhante pode ajudar a ligação de dois enquadramentos diferentes; não a penalizar indiscriminadamente em ambos os casos. Repetição forte exige também semelhança visual/enquadramento.

Registar no relatório as contribuições de qualidade, prompt, diversidade e continuidade. Mostrar explicações curtas derivadas desses dados. Não usar texto livre inventado pelo modelo para justificar decisões.

## 5. Cor conforme a filmagem

Adicionar configuração por fonte: «Normal/SDR», «D-Log», «D-Log M». HDR/HLG identificado deve produzir aviso explícito e não receber automaticamente uma LUT de D-Log. Conversão HDR especializada não está incluída nesta versão.

Normal/SDR é a omissão; os metadados dão informação auxiliar, mas o utilizador confirma o perfil. D-Log/D-Log M exige uma LUT técnica adequada ao drone/câmara e perfil. Não aplicar uma LUT genérica de outro modelo silenciosamente. Permitir importar um ficheiro `.cube` local e atribuí-lo às fontes relevantes. A documentação indica a origem das LUTs técnicas oficiais DJI: https://www.dji.com/lut

Validar o LUT antes de aceitar: apenas tabela 3D de tamanho 2 a 65, domínio finito com mínimo inferior ao máximo, número exato de entradas, floats finitos e tamanho de upload até 20 MB. Rejeitar ficheiros malformados; tratar como dados, nunca código. Guardar com ID/nome gerado e SHA-256 no projeto; o cliente fornece ID, não um caminho de filesystem.

Com perfil Log e LUT ausente, impedir análise/exportação nesse perfil com erro legível. Não aplicar a conversão duas vezes. LUT técnica entra antes das correções de exposição/balanço e do aspeto final. A análise deve usar a representação convertida para avaliar qualidade e semelhança de forma comparável.

Ao melhorar cores, calcular ajustes conservadores de exposição e balanço de brancos por plano, com limites de intensidade. Usar estimativas robustas e confiança para não neutralizar intencionalmente pôr-do-sol, água ou vegetação. Ajustes com confiança baixa ficam neutros, com aviso; permitir desativar melhoria de cor mantendo a conversão técnica obrigatória para Log.

Mostrar pré-visualização «Original»/«Corrigido» do mesmo intervalo. Preservar a escolha manual e os originais. Reportar correções aplicadas; não prometer recuperação de detalhes já recortados nas luzes ou sombras.

## Exportação 4K e FPS

Acrescentar seletor «1080p / 4K» na criação e na revisão. O novo frontend usa 4K por omissão; clientes antigos conservam 1080p quando não fornecem a opção. 4K significa quadro 3840×2160 e 1080p significa 1920×1080, com proporção preservada e enquadramento 16:9 já existente.

Renderizar sempre a partir dos originais, nunca das cópias de análise ou previews. Se a fonte tiver resolução inferior, informar que será redimensionada e que isso não acrescenta detalhe.

FPS «Automático»: conservar taxa comum dos originais selecionados, incluindo 30000/1001 e 60000/1001. Se forem diferentes, escolher 30 e mostrar a decisão. Opções manuais 24/25/30/50/60. Conformar timestamps sem acelerar/desacelerar o movimento; não introduzir interpolação por IA.

Todos os clips da montagem têm resolução, FPS, SAR, codec e formato de pixel compatíveis antes da concatenação. Manter H.264/yuv420p, faststart e cores de saída SDR Rec.709. A escolha de encoder GPU não faz parte desta alteração. Não acrescentar áudio/música.

Guardar resolução, FPS racional, fontes/perfis/LUTs, ajustes de cor e intervalos efetivos no manifesto da exportação. Conservar a proteção do último vídeo válido e da seleção manual perante falha ou pedidos concorrentes. Resultado mostra resolução e FPS reais confirmados por ffprobe.

## Cópias de análise e recursos

Produzir proxy local até 640 px no lado maior, a dez FPS, mantendo duração e correspondência temporal com o original. Aplicar a conversão técnica do perfil antes da análise; não incorporar a melhoria estética automática que ainda está a ser estimada.

Identificar o proxy por origem, tamanho/mtime, perfil e hash da LUT para não reutilizar uma representação incompatível. As mudanças de resolução de exportação não exigem nova análise. Alterar perfil/LUT exige invalidar análise e candidatos: explicar isso antes de substituir uma seleção manual.

Validar duração/alinhamento do proxy; conservar metadados originais para renderização e limites dos intervalos. Limitar concorrência conforme executor existente e manter progresso/erros em português. Não apagar originais, montagens anteriores ou outros projetos.

## Contratos e interface

Acrescentar às opções `cinematic`, `resolution`, `fps` e configurações de cor por fonte. `cinematic=false`, `resolution=1080p` e FPS 30 conservam o caminho antigo dos clientes; o frontend fornece explicitamente cinematic/4K/auto.

Acrescentar metadados de fonte/candidato: resolução/FPS/perfil, movimento/direção, confiança, papel visual, avisos de qualidade e ajustes de cor. Expor apenas o necessário para revisão; embeddings e séries brutas permanecem no backend/disco local.

Estender `/suggest` para objetivo de duração e modo, sem reextração de frames quando só muda prompt/duração. Estender `/export` para resolução/FPS e confirmação dos IDs de candidatos fracos incluídos manualmente. Validar IDs, estados e combinações de opções no backend.

Adicionar upload/consulta de LUT por projeto, restritos a IDs conhecidos. Mudança de perfil/LUT usa nova análise com confirmação para descartar a revisão atual; não faz isso ao alterar resolução/FPS.

A revisão mostra motivos, avisos, papéis e duração real; permite alterar objetivo, resolução/FPS e pré-visualizar cor. Exportação é sempre uma ação explícita. Preservar acesso por teclado e layout mobile; erros não fazem perder a seleção nem criam trabalho duplicado.

## Verificação e aceitação

1. Movimento sintético com arranque, trecho suave e paragem: candidato recupera a região útil; pausa/direção persistente altera limites; ruído isolado não fragmenta. Revelação sintética tem rótulo/confiança coerentes ou desconhecido quando insuficiente.
2. Duração natural: sugestão usa planos completos dentro do objetivo; não corta o último para preencher. Fonte curta e candidato longo têm UI/erros claros; modo antigo conserva as regressões de duração exata.
3. Sequência: plano amplo bom abre quando disponível, planos de desenvolvimento variam, fecho forte; ausência de um papel não força candidato fraco. Ordem manual é preservada.
4. Qualidade: blur/clipping/correção brusca sustentados recebem avisos/exclusão automática; todos fracos produzem revisão vazia; override exige confirmação; horizonte incerto não é tratado como facto.
5. Diversidade: pares visualmente iguais com movimento igual recebem maior penalização; direções semelhantes com enquadramentos distintos podem manter continuidade; qualidade muito superior continua a prevalecer.
6. Cor: LUT identidade e transformação conhecida, ficheiro inválido/tamanho excessivo/domínio incorreto, perfil Log sem LUT, fonte SDR sem LUT, conversão única, ajuste conservador e caso de baixa confiança. Comparação visual do mesmo trecho e consistência análise/exportação.
7. Exportação real 3840×2160 H.264, FPS racional confirmado, preservação de duração, fontes mistas e entrada menor com aviso. Teste consegue demonstrar que renderiza do original e não do proxy. Falha de render/publicação conserva resultado anterior.
8. Browser: configuração, prompt, revisão vazia/avisos/override, sequência/ordem manual, cor, objetivo variável e 4K; mobile/teclado; regressões de recuperação de erros, reprodução e download.
9. Avaliação nos quatro DJI disponíveis, com originais/resultado anterior preservados. Comparar candidatos e sequência antes/depois e registar tempo real. A preferência estética final exige avaliação humana, não apenas uma pontuação maior.

## Auto-revisão

Cobertura dos cinco pontos e 4K confirmada; arquitetura reaproveita o fluxo existente e modelos locais. Conflito entre duração exata e movimento completo resolvido com objetivo máximo no novo modo e compatibilidade no modo antigo. Perfil de cor não é inferido de forma conclusiva; LUT local explícita e validação antes do uso. Nenhum código de produto alterado nesta etapa. Projeto sem Git: guardar o documento sem inicializar repositório.
