# DroneDirector — seleção, cortes, revisão e prompt local

Estado: desenho conversacional aprovado pelo utilizador em 8 de outubro de 2026; especificação escrita para revisão antes do plano de implementação.

## Objetivo e limites

Aplicar as melhorias 1, 2 e 5 da revisão da aplicação: escolher pela qualidade, encontrar cortes mais naturais e permitir rever os momentos antes da exportação. Acrescentar um prompt opcional em português que influencia realmente a seleção através de inferência local.

Manter Angular, FastAPI, OpenCV, FFmpeg e o preditor estético CLIP/LAION existente. Vídeos, frames e prompts ficam no computador. Modelos podem ser descarregados explicitamente durante a instalação, nunca durante a análise. Não acrescentar contas, serviços externos ou base de dados. Recuperação após reiniciar, uploads retomáveis e opções de resolução/FPS ficam fora desta alteração.

## Abordagem escolhida

Separar a análise da exportação no fluxo interativo. A análise produz candidatos, miniaturas e uma seleção sugerida. O utilizador confirma ou altera essa seleção antes de renderizar. Conservar um caminho de processamento automático para clientes existentes e testes de regressão.

Alternativas consideradas: editar apenas depois da exportação duplica renderizações; acrescentar um grande modelo de vídeo/linguagem muda os requisitos de hardware e não é necessário para este objetivo. Escolhe-se o aproveitamento dos embeddings CLIP existentes com um encoder de texto multilingue compatível e cortes orientados por sinais temporais medidos.

## 1. Qualidade antes da diversidade

Conservar a qualidade base: 70% estética aprendida + 30% métricas técnicas. Remover a ordenação que privilegia primeiro a contagem de trechos por ficheiro. A comparação passa a usar uma pontuação única: qualidade base, ajuste do prompt quando existir, penalização suave de semelhança visual e penalização suave de representação da mesma origem.

Penalização por origem: dois pontos por trecho já escolhido dessa origem, limitada a seis pontos. Conservar a penalização visual existente, limitada a oito pontos. Assim, diversidade não suplanta diferenças muito grandes de qualidade. Com pontuações 90 e 89 de A e 10 de B, a seleção de dois trechos deve escolher ambos de A, quando não se sobrepõem.

Rejeitar sobreposição de intervalos da mesma origem. Adjacência deixa de ser impedimento absoluto: dois planos consecutivos válidos podem ser usados, e serão unidos quando a continuidade o justificar. Todos os desempates são determinísticos. A ordem inicial mantém cronologia dentro da ordem dos ficheiros importados; na revisão, prevalece a ordem definida pelo utilizador.

Não definir um limiar estético arbitrário que torne indisponíveis vídeos válidos. Frames ilegíveis e intervalos inviáveis são excluídos. Trechos com baixa qualidade técnica são identificados por métricas e avisos na revisão, sem prometer eliminação infalível de planos maus.

## 2. Candidatos e cortes orientados pelo movimento

Acrescentar um módulo de segmentação temporal independente do ranking. Analisar imagens reduzidas aproximadamente a cada 0,5 segundos, reutilizando leituras e métricas quando possível. Medir mudança de aparência por histogramas e variação de movimento por optical flow. Mudanças abruptas são fronteiras obrigatórias de cena; mínimos locais de movimento/variação são pontos preferenciais de corte.

Criar candidatos de duração variável entre três e oito segundos, mantendo intervalos completos mais curtos para fontes pequenas. Evitar atravessar uma mudança de cena. Em tomadas longas sem um corte preferencial próximo, criar janelas limitadas no tempo para continuar a oferecer candidatos úteis. Os limites três/oito segundos são decisões iniciais verificáveis, não uma afirmação de qualidade cinematográfica universal.

Pontuar cada candidato com o pipeline estético e técnico existente, incluindo início, meio e fim. Guardar o motivo e a confiança do ponto de corte: mudança de cena, mudança/pausa de movimento ou limite temporal. A interface descreve estes sinais sem afirmar compreensão narrativa ou reconhecimento perfeito de manobras.

A seleção procura cobrir a duração pedida sem repetição dos mesmos instantes. O último trecho pode ser encurtado para cumprir 15/30/60 segundos. Mostrar exatamente o intervalo que será exportado. Se os originais somados forem mais curtos, usar a duração disponível e informar o utilizador. A soma dos intervalos mostrados deve coincidir com a duração prevista; diferenças de exportação ficam limitadas à tolerância dos frames.

## 3. Prompt opcional com efeito real

Adicionar um campo «Orientação extra para a IA», até 500 caracteres, com exemplo descritivo em português. Sem prompt, o comportamento usa estética, qualidade técnica e diversidade. O texto não é executado como instrução de sistema, código ou comando FFmpeg.

Usar o encoder `sentence-transformers/clip-ViT-B-32-multilingual-v1`, cuja documentação inclui português e compatibilidade com o espaço visual CLIP ViT-B/32. Converter texto em embedding normalizado de 512 dimensões e comparar com os embeddings dos candidatos. A compatibilidade com o encoder visual quantizado instalado precisa de teste real; não declarar funcionamento apenas pela compatibilidade teórica.

Fonte primária: https://huggingface.co/sentence-transformers/clip-ViT-B-32-multilingual-v1

O encoder funciona com ficheiros locais e carregamento offline, sem código remoto. A instalação fixa a revisão do modelo e hashes dos artefactos, incluindo tokenizer, pooling e projeção. O plano escolhe a implementação e versões após inspecionar os artefactos disponíveis; o contrato exige o mesmo pipeline e embeddings válidos, independentemente do runtime utilizado.

Converter a relevância semântica numa preferência limitada, até dez pontos de ajuste, para não suplantar uma grande diferença de qualidade. Guardar similaridade original e contribuição separadas, sem apresentar similaridade como probabilidade ou garantia de cumprir o prompt. Informar quando os candidatos têm pouca diferenciação semântica e o efeito do prompt é reduzido.

O prompt favorece conteúdos descritos visualmente. Não prometer execução precisa de negações, sequências narrativas ou comandos de edição através de um encoder de similaridade. Corrigir o exemplo anterior: em vez de «evita edifícios», preferir «paisagem natural, rio e vegetação». Exibir ajuda: «Descreve o que queres destacar. O prompt orienta a seleção; revê os momentos antes de exportar.» Preferências de movimento continuam apoiadas nas métricas temporais, sem fingir que uma imagem demonstra movimento suave.

Alterar o prompt na revisão reaplica o ranking aos embeddings já analisados, sem reenviar os vídeos ou repetir a extração de frames. Uma nova sugestão substitui a seleção manual apenas depois de o utilizador carregar em «Aplicar prompt». Preservar os candidatos e permitir regressar à seleção automática.

Se o modelo de texto estiver ausente ou corrompido e houver prompt, devolver erro explícito antes de iniciar a análise. O funcionamento sem prompt continua disponível com o modelo estético atual. Nunca ignorar silenciosamente um prompt preenchido.

## 4. Revisão dos momentos

Novo ecrã entre processamento e resultado, com duas áreas: seleção atual na ordem de montagem e biblioteca dos candidatos disponíveis. Cada cartão apresenta miniatura, nome do original, intervalo, duração e motivos baseados nos scores calculados, por exemplo «boa nitidez», «movimento estável» e «correspondência com o prompt». Estas explicações são derivadas das métricas, não texto inventado por um modelo.

Permitir pré-visualizar o trecho, remover, acrescentar uma alternativa, substituir e mover para cima/baixo. Os botões de ordenação funcionam com teclado e em mobile; drag and drop não é necessário para esta primeira versão. Pré-visualização dos originais locais deve respeitar os limites do trecho e permitir pedidos Range. Não expor caminhos livres no endpoint.

Mostrar duração total e objetivo. Após cada edição, normalizar a lista de intervalos efetivos: rejeitar duplicados/sobreposição, encurtar o último trecho quando excede o objetivo e mostrar um aviso quando falta duração. Não acrescentar planos escondidos. Permitir exportar uma seleção mais curta com confirmação explícita através de «Exportar N segundos» e mostrar por que difere do objetivo. Uma seleção vazia não pode ser exportada.

Guardar no estado de revisão a seleção sugerida e a seleção manual em separado. Durante exportação, desativar alterações. Após concluir, permitir voltar à revisão e exportar outra montagem a partir da mesma análise. Exportar para um ficheiro temporário e publicar o resultado apenas quando a renderização terminar com sucesso, preservando o último resultado válido se uma nova renderização falhar.

## Contratos e estado

Acrescentar `analyzing`, `review`, `exporting` ao estado, mantendo os estados existentes para compatibilidade. Frontend mantém polling apenas durante trabalho ativo e muda para revisão quando a análise termina.

- `POST /{id}/analyze`: duração, cores e prompt opcional; valida dependências, coloca a análise na fila e devolve 202.
- `GET /{id}/review`: candidatos com IDs estáveis, metadados, URLs de miniaturas/pré-visualização, seleção sugerida e intervalos efetivos. Embeddings não são enviados ao browser.
- `POST /{id}/suggest`: reaplica prompt/ranking aos candidatos locais; devolve nova sugestão sem renderizar.
- `POST /{id}/export`: recebe IDs na ordem desejada e opções de duração/cores; valida contra candidatos do projeto e normaliza intervalos antes de colocar exportação na fila.
- Endpoints de miniatura e original aceitam apenas IDs que pertençam ao projeto; nenhum caminho fornecido pelo cliente é aberto diretamente.
- `POST /{id}/process` mantém o fluxo automático análise + seleção + exportação para compatibilidade. O frontend passa a usar o fluxo de revisão.

Guardar análise, parâmetros, motivos de corte e seleções em JSON no diretório do projeto. Embeddings podem ser guardados como arrays locais para permitir novas sugestões sem nova análise. Isto não acrescenta recuperação completa do registo dos projetos após reiniciar o backend, que permanece fora do âmbito.

Bloquear submissões concorrentes da mesma análise/exportação com 409. Um pedido repetido ou uma ligação interrompida não deve iniciar duas renderizações enquanto o estado indicar trabalho ativo. Não permitir exportação durante análise, seleção inexistente, IDs de outros projetos, intervalos sobrepostos ou parâmetros inválidos.

## Componentes abrangidos

Backend: modelos de pedido/estado, scoring, segmentação temporal, encoder de prompts, orquestração separada de análise/exportação, API de revisão e instalação dos modelos. Frontend: modelos e serviço HTTP, formulário de prompt, ecrã/componente de revisão, polling e regresso do resultado à revisão. Manter responsabilidades separadas, sem concentrar todos os novos controlos no componente de criação.

## Verificação e critérios de aceitação

1. Teste regressivo demonstra que qualidade 89 não é preterida por qualidade 10 só para representar outra origem; testar diversidade suave entre qualidades próximas e ausência de sobreposição.
2. Vídeos sintéticos com mudança abrupta e movimento/paragem produzem limites variáveis, intervalos válidos e não atravessam uma fronteira de cena. Testar fonte curta, movimento contínuo e duração exata.
3. Inferência real do prompt com rede bloqueada: descrições portuguesas correspondem melhor a imagens distintas do que descrições incompatíveis. Testar saída normalizada, prompt vazio, limite de texto, dependência ausente/corrompida e mudança de ranking por relevância.
4. API: análise termina em revisão sem vídeo final; alterações usam candidatos do projeto; ordem pedida é exportada; rejeição de IDs inválidos, duplicados, sobreposição, lista vazia e trabalho concorrente; nova exportação preserva o último resultado numa falha.
5. Browser: escrever prompt, analisar, pré-visualizar, substituir, remover, reordenar, ver duração e exportar; teclado e largura mobile; erro do modelo de texto é compreensível; processamento sem prompt continua funcional.
6. Regressões do caminho automático, build Angular e reprodução/download do vídeo exportado. Comparação dos novos momentos nos quatro vídeos DJI disponíveis pode complementar os testes, mas não substitui avaliação humana da qualidade estética.

## Revisão da especificação

Verificado: âmbito limitado aos pedidos aprovados; IA local preservada; efeito do prompt distinto de compreensão narrativa; limites e falhas explícitos; fluxo/API e testes alinhados. Não há dependência de serviços externos nem promessas de qualidade ainda não medidas. O projeto não possui repositório Git; guardar a especificação sem iniciar um repositório ou criar um commit.
