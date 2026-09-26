<script lang="ts">
  import { onMount } from 'svelte';
  import Field from './Field.svelte';
  import TaskPanel from './TaskPanel.svelte';
  import { api, download, upload, durationEstimate, mediaLabels, speechLabels, musicLabels, type Data } from './api';
  let boot: Data | null = null;
  let params: Data = {};
  let loading = true;
  let unauthorized = false;
  let loginKey = '';
  let error = '';
  let notice = '';
  let busy = '';
  let view = 'editor';
  let stage = 'script';
  let language = 'pt';
  let theme = localStorage.getItem('mpt-theme') || 'light';
  let translations: Data = {};
  let catalog: Data | null = null;
  let catalogLoading = false;
  let voiceProvider = 'azure-tts-v1';
  let voiceMode = 'tts';
  let voiceList: string[] = [];
  let voiceFilter = '';
  let voicesLoading = false;
  let loadedVoiceProvider = '';
  let voiceError = '';
  let sampleText = '';
  let preview: Data | null = null;
  let previewInputs = '';
  let narration: Data | null = null;
  let reference: Data | null = null;
  let prompt: Data | null = null;
  let promptText = '';
  let materials: Data[] = [];
  let task: Data | null = null;
  let activeId = sessionStorage.getItem('mpt-active-task') || '';
  let taskLoading = false;
  let history: Data[] = [];
  let historySearch = '';
  let historyFilter = 'all';
  let historyLimit = 30;
  let SettingsComponent: any = null;
  let settingsCategory = 'script';
  let cache: Data | null = null;
  let cacheDays: number | undefined = undefined;
  let version: Data | null = null;
  let capabilities: Data | null = null;
  let scenePrompts = '';
  let sceneCount = 1;
  let scriptBackend = 'local';
  let modelId = '';
  let scriptCandidates: Data[] = [];
  let candidateCount = 3;
  let scriptDuration = 60;
  let scriptStyle = '';
  let quote: Data | null = null;
  let quoteKind = '';
  let quoteInputs: Data | null = null;
  let chargeConfirmed = false;
  let paidConfirmed = false;
  let paidApprovedSignature = '';
  let scriptRunId = sessionStorage.getItem('mpt-script-run') || '';
  let scriptPolling = false;
  let timer: ReturnType<typeof setInterval>;
  const voiceCache = new Map<string, string[]>();
  const pt: Data = {
    'Script AI': 'IA de roteiro', 'Video & Images': 'Vídeo e imagens', 'Narration': 'Narração',
    'Transcription & Subtitles': 'Transcrição e legendas', 'Provider Categories': 'Funções dos provedores',
    'Script Provider': 'Provedor de roteiro', 'Video Provider': 'Provedor de vídeo ou imagens',
    'Narration Provider': 'Provedor de narração', 'Music Provider': 'Fonte de música', 'Music': 'Música',
    'Configure Script AI': 'Configurar IA de roteiro', 'Configure Video AI': 'Configurar fonte de vídeo',
    'Configure Narration AI': 'Configurar IA de narração', 'Configure Music AI': 'Configurar IA de música',
    'Back to Editor': 'Voltar ao editor', 'API Address': 'Endereço da API', 'API Keys': 'Chaves de API',
    'Voice model': 'Modelo de voz', 'Voice ID': 'ID da voz', 'Voice IDs': 'IDs das vozes',
    'Video Model': 'Modelo de vídeo', 'Video Endpoint': 'Rota de geração de vídeo', 'Music Model': 'Modelo de música',
    'Service Region': 'Região do serviço', 'Resolution': 'Resolução', 'Whisper Model': 'Modelo Whisper',
    'Device': 'Dispositivo', 'Compute Type': 'Tipo de cálculo', 'Subtitle Provider': 'Modo de transcrição e legendas',
    'Configuration Section': 'Seção técnica', 'Server & Integrations': 'Servidor e integrações',
    'Advanced provider options': 'Opções avançadas deste provedor', 'Credential saved on this server.': 'Chave já salva neste servidor.',
    'Each function can use a different provider and API key. Switching categories keeps your other credentials.': 'Cada função pode usar um provedor e uma chave diferentes. Trocar de categoria mantém as demais credenciais.',
    'Writes the script and search terms. This does not choose the video, voice or music AI.': 'Escreve o roteiro e os termos de busca. Não escolhe a IA de vídeo, voz ou música.',
    'Stock services find existing footage. AI video services generate scenes; AI image services generate stills used in the video.': 'Bancos de vídeos buscam cenas prontas. IA de vídeo gera cenas novas; IA de imagens gera fotos usadas no vídeo.',
    'Local media needs no API key. Upload your images or videos in the Footage stage.': 'Arquivos locais não precisam de chave. Envie suas imagens ou vídeos na etapa Mídia.',
    'Turns your script into spoken narration. This is separate from transcription and music.': 'Transforma o roteiro em voz. É uma função diferente de transcrever áudio ou gerar música.',
    'Google voice uses your Gemini API key, also used by Gemini scripts. It does not replace your video or music keys.': 'A voz do Google usa a chave Gemini, compartilhada com roteiros Gemini. Ela não substitui as chaves de vídeo ou música.',
    'Choose a voice and listen to a sample in the Sound stage.': 'Escolha a voz e ouça uma amostra na etapa Áudio.',
    'Edge TTS needs no API key. It uses an online voice service, not a local model.': 'Edge TTS não precisa de chave. Usa um serviço de voz online, não um modelo local.',
    'MiMo voice shares the MiMo script API key. Its voice model is configured separately.': 'A voz MiMo compartilha a chave dos roteiros MiMo. O modelo de voz é configurado separadamente.',
    'MiniMax voice can use a separate key here, or reuse your MiniMax script key when empty.': 'A voz MiniMax pode usar uma chave própria aqui. Se ficar vazia, usa a chave dos roteiros MiniMax.',
    'Turns recorded speech into subtitle text. It does not generate a voice.': 'Transforma a fala de um áudio em texto para legendas. Não gera voz.',
    'Narration timing — Edge / TTS': 'Tempos da narração — Edge / TTS', 'Whisper — local audio transcription': 'Whisper — transcrição local de áudio',
    'Whisper runs locally without an API key. It is not the Google voice provider. Google voice is under Narration → Google Gemini.': 'Whisper roda localmente, sem chave de API. Não é o gerador de voz do Google. A voz do Google fica em Narração → Google Gemini.',
    'Install Whisper support with': 'Instale o suporte Whisper com',
    'The model downloads on first transcription. Restart the server after changing a model that was already loaded.': 'O modelo é baixado na primeira transcrição. Reinicie o servidor após trocar um modelo que já foi carregado.',
    'Choose local background music or an AI music service. Narration voice models do not generate background music.': 'Escolha música local ou um serviço de música por IA. Modelos de narração não geram música de fundo.',
    'ElevenLabs music shares its ElevenLabs voice API key, but uses a separate music model. Changing the music model does not change the voice model.': 'Música e voz ElevenLabs compartilham a chave, mas usam modelos diferentes. Alterar o modelo de música não altera o de voz.',
    'This music option needs no API key. Choose or upload the track in the Sound stage.': 'Esta opção não precisa de chave. Escolha ou envie a faixa na etapa Áudio.',
    'Upload-Post publishes finished videos to your configured social accounts. It is not a video-generation provider.': 'Upload-Post publica os vídeos prontos nas suas contas. Não é um gerador de vídeos.',
    'Technical settings, server access and all original configuration fields. You do not need these to configure normal providers.': 'Configuração técnica, acesso ao servidor e todos os campos originais. Não é necessário entrar aqui para cadastrar os provedores.',
    'Pexels — stock videos': 'Pexels — banco de vídeos', 'Pixabay — stock videos': 'Pixabay — banco de vídeos',
    'Coverr — stock videos': 'Coverr — banco de vídeos', 'Local files — no API': 'Arquivos locais — sem API',
    'AI images — OpenAI-compatible API': 'Imagens por IA — API compatível com OpenAI',
    'WaveSpeed — AI video': 'WaveSpeed — vídeo por IA', 'Seedance — AI video': 'Seedance — vídeo por IA',
    'OFox — AI video': 'OFox — vídeo por IA', 'Metaso / MiniMax — AI video': 'Metaso / MiniMax — vídeo por IA',
    'MuAPI — AI video': 'MuAPI — vídeo por IA', 'LoomLoom — AI video': 'LoomLoom — vídeo por IA',
    'Microsoft Edge TTS — no API key': 'Microsoft Edge TTS — sem chave', 'Microsoft Azure Speech — API key': 'Microsoft Azure Speech — com chave',
    'Google Gemini — text to speech': 'Google Gemini — gerar voz', 'No music': 'Sem música',
    'Random local music — no API': 'Música local aleatória — sem API', 'Built-in music — no API': 'Biblioteca de músicas — sem API',
    'Uploaded music — no API': 'Música enviada — sem API', 'Sonilo — AI music': 'Sonilo — música por IA', 'ElevenLabs — AI music': 'ElevenLabs — música por IA',
    'Start with an idea. Shape the story before choosing the footage.': 'Comece por uma ideia. Acerte o roteiro antes de escolher a mídia.',
    'Choose where your images come from and how they fill the screen.': 'Escolha de onde vem a mídia e como ela ocupa a tela.',
    'Listen before rendering. Keep narration, music and cloning controls together.': 'Ouça antes de renderizar. Ajuste narração, música e clonagem de voz.',
    'Make every line readable. Preview the style before rendering.': 'Deixe cada frase legível. Confira o estilo antes de renderizar.',
    'What is this video about?': 'Qual é o tema deste vídeo?',
    'Write your script, or generate a first draft from the subject.': 'Escreva o roteiro ou gere uma primeira versão a partir do tema.',
    'Script Generation Backend': 'Geração de roteiro', 'Configured LLM': 'LLM configurado',
    'Scene Count': 'Quantidade de cenas', 'Suggest Scenes': 'Sugerir cenas', 'Actual Narration': 'Narração medida',
    'video(s)': 'vídeo(s)', 'Write a script to estimate narration length.': 'Escreva um roteiro para estimar a duração.',
    'Find Voice': 'Buscar voz', 'Manual Voice ID': 'ID de voz manual',
    'Enter a MiniMax voice ID, including a private or cloned voice.': 'Informe um ID MiniMax, incluindo voz privada ou clonada.',
    'Separate terms with commas. Leave empty to generate them automatically.': 'Separe os termos por vírgulas. Deixe vazio para gerar automaticamente.',
    'This source may create paid provider requests when you generate the video.': 'Esta fonte pode fazer chamadas pagas ao gerar o vídeo.',
    'I authorize the selected provider to charge for this video generation.': 'Autorizo a cobrança deste provedor para gerar este vídeo.',
    'Inputs changed. Request a new quote before confirming.': 'Os dados mudaram. Consulte o preço novamente antes de confirmar.',
    'One scene per line. Maximum five scenes. Exact scene prompts are included in the quote.': 'Uma cena por linha, até cinco cenas. O preço consultado corresponde a estas descrições.',
    'clips needed; shorter footage repeats.': 'clipes necessários; mídia mais curta será repetida.',
    'Your story, clearly told.': 'Sua história, contada com clareza.',
    'Layout preview only; final font rendering and animation are applied by the video engine.': 'Prévia de layout. A fonte e a animação finais são aplicadas pelo renderizador.',
    'Preview requests use the selected provider. A matching full preview is reused during generation.': 'A prévia usa o provedor selecionado. A narração completa compatível será reutilizada na geração.',
    'Use Whisper subtitles for uploaded narration; the model loads only when transcription is requested.': 'Use Whisper para legendar áudio enviado. O modelo só carrega quando a transcrição é solicitada.',
    'Private reference audio expires after 30 minutes and is never stored in task history.': 'O áudio privado expira em 30 minutos e não é salvo no histórico.',
    'Uploaded narration and private reference audio must be uploaded again.': 'Envie novamente a narração e os áudios de referência privados.',
    'Settings will be saved after the active task.': 'As configurações serão salvas após a tarefa ativa.',
    'Revisit a render, download its files or use its settings as a starting point.': 'Revise um vídeo, baixe os arquivos ou restaure as configurações para começar outro.',
    'Your first video': 'Seu primeiro vídeo', 'Write a subject and generate or paste a script.': 'Escreva um tema e gere ou cole o roteiro.',
    'Configure a stock or generation provider, or upload local images and videos.': 'Configure uma fonte de mídia ou envie imagens e vídeos locais.',
    'Select a voice, upload narration or choose silent mode. Audition before rendering.': 'Escolha uma voz, envie uma narração ou selecione o modo sem voz. Ouça antes de renderizar.',
    'Set your subtitle style and generate. Progress and files stay in the output panel.': 'Ajuste as legendas e gere o vídeo. O progresso e os arquivos ficam no painel de resultado.',
    'Local deployment': 'Uso local', 'Inspect Cache': 'Consultar cache', 'files': 'arquivos', 'files removed': 'arquivos removidos',
    'Leave empty to include all cached stock-video downloads.': 'Deixe vazio para incluir todos os vídeos em cache.',
    'API Documentation': 'Documentação da API', 'Service Endpoint': 'Região do serviço', 'Configuration Sections': 'Seções de configuração',
    'Main Navigation': 'Navegação principal', 'Production Stages': 'Etapas da produção', 'Skip to content': 'Ir para o conteúdo',
    'Subtitle Provider Settings': 'Configurar provedor de legendas', 'Two-thirds down': 'A dois terços da tela',
    'Full Narration': 'Narração completa', 'Sample': 'Amostra', 'Dismiss': 'Dispensar', 'Retry': 'Tentar novamente',
    'Enter the API key configured on this server.': 'Informe a chave da API configurada neste servidor.',
    'Cannot connect to the server': 'Não foi possível conectar ao servidor', 'File is too large.': 'O arquivo é grande demais.',
    'Preset imported.': 'Preset importado.', 'Update available': 'Atualização disponível', 'You are up to date.': 'Você está na versão atual.',
    'A quote is an estimate. Actual charges can differ, including when the estimate is zero.': 'O preço é uma estimativa. A cobrança real pode ser diferente, inclusive quando a estimativa é zero.',
    'Paid script, speech, music and video services use your configured provider account. LoomLoom requires a separate quote and explicit confirmation. No provider is contacted simply by opening the editor.': 'Serviços pagos de roteiro, voz, música e vídeo usam a conta do provedor configurado. O LoomLoom exige preço consultado e confirmação explícita. Abrir o editor não faz chamadas aos provedores.',
    'Whisper and video libraries load only when their operation is requested. For uploaded narration, select Whisper in the subtitle provider settings.': 'Whisper e bibliotecas de vídeo só carregam quando necessários. Para narração enviada, selecione Whisper nas configurações do provedor de legendas.',
    'This interface is served by the same FastAPI process as the API. Node and Streamlit are not needed in production. On a headless Raspberry Pi, use the browser preview and downloads instead of opening a desktop player.': 'A interface e a API usam o mesmo processo FastAPI. Node e Streamlit não são necessários em produção. Em um Raspberry Pi sem desktop, use a prévia do navegador e os downloads.',
    'Studio': 'Estúdio', 'Editor': 'Editor', 'History': 'Histórico', 'Settings': 'Configurações', 'Help': 'Ajuda',
    'Script': 'Roteiro', 'Footage': 'Mídia', 'Sound': 'Áudio', 'Subtitles': 'Legendas', 'Output': 'Resultado',
    'Video Subject': 'Tema do vídeo', 'Video Script': 'Roteiro do vídeo', 'Generate Script': 'Gerar roteiro',
    'Generate Video': 'Gerar vídeo', 'Generating': 'Gerando', 'Failed': 'Falhou', 'Complete': 'Concluído', 'Waiting': 'Aguardando',
    'Language': 'Idioma', 'Theme': 'Tema', 'Light': 'Claro', 'Dark': 'Escuro', 'System': 'Sistema',
    'Refresh': 'Atualizar', 'Save Settings': 'Salvar configurações', 'Save Defaults': 'Salvar preferências',
    'Video Source': 'Fonte de mídia', 'Video Aspect': 'Formato do vídeo', 'Video Fit Mode': 'Enquadramento',
    'Video Clip Duration': 'Duração dos clipes (s)', 'Video Clip Speed': 'Velocidade dos clipes', 'Video Count': 'Variações',
    'Video Concat Mode': 'Ordem dos clipes', 'Video Transition Mode': 'Transição',
    'Match Materials to Script': 'Seguir a ordem do roteiro', 'Search Terms': 'Termos de busca', 'Generate Terms': 'Gerar termos',
    'Voice Mode': 'Modo de narração', 'Voice Provider': 'Provedor de voz', 'Voice': 'Voz',
    'Voice Volume': 'Volume da voz', 'Voice Rate': 'Velocidade da voz', 'Sample Text': 'Texto de teste',
    'Preview Voice': 'Ouvir amostra', 'Preview Full Narration': 'Prévia da narração completa', 'Upload Narration': 'Enviar narração',
    'Background Music': 'Música de fundo', 'Music Volume': 'Volume da música', 'Music Prompt': 'Descrição da música',
    'Upload Music': 'Enviar música', 'Enable Subtitles': 'Ativar legendas', 'Font': 'Fonte', 'Font Size': 'Tamanho da fonte',
    'Text Color': 'Cor do texto', 'Outline Color': 'Cor do contorno', 'Outline Width': 'Espessura do contorno',
    'Subtitle Position': 'Posição', 'Subtitle Display Mode': 'Exibição', 'Subtitle Animation': 'Animação',
    'Custom Position': 'Posição personalizada (%)', 'Subtitle Background': 'Fundo das legendas',
    'Background Color': 'Cor de fundo', 'Rounded Background': 'Fundo arredondado', 'Caption Preview': 'Prévia das legendas',
    'Advanced': 'Avançado', 'Script Instructions': 'Instruções do roteiro', 'System Prompt': 'Prompt de sistema',
    'Paragraphs': 'Parágrafos', 'Script Language': 'Idioma do roteiro', 'Render Threads': 'Threads de renderização',
    'Auto': 'Automático', 'None': 'Nenhum', 'Random': 'Aleatório', 'Sequential': 'Sequencial',
    'Cover': 'Preencher / cortar', 'Contain': 'Ajustar com bordas', 'TTS': 'Gerar voz', 'Upload': 'Arquivo de áudio', 'Silent': 'Sem voz',
    'Built-in': 'Biblioteca', 'Custom': 'Arquivo enviado', 'Top': 'Topo', 'Center': 'Centro', 'Bottom': 'Rodapé',
    'Sentence': 'Frase inteira', 'Word by Word': 'Palavra por palavra', 'Pop Spring': 'Entrada elástica',
    'Delete': 'Excluir', 'Remove': 'Remover', 'Restore Settings': 'Restaurar configurações', 'Open Task Folder': 'Abrir pasta',
    'Open Video': 'Abrir vídeo', 'Download Video': 'Baixar vídeo', 'All Files': 'Todos os arquivos', 'Logs': 'Logs',
    'Search History': 'Buscar no histórico', 'All': 'Todos', 'Load More': 'Carregar mais', 'No tasks found.': 'Nenhuma tarefa encontrada.',
    'Export Preset': 'Exportar preset', 'Import Preset': 'Importar preset', 'Export Credentials': 'Exportar credenciais',
    'Import Credentials': 'Importar credenciais', 'Cache': 'Cache', 'Clean Cache': 'Limpar cache', 'Age in Days': 'Idade em dias',
    'Check for Updates': 'Verificar atualizações', 'Sign In': 'Entrar', 'API Key': 'Chave da API', 'Sign Out': 'Sair',
    'Providers & Generation': 'Provedores e geração', 'Text Generation': 'Geração de texto', 'All Provider Settings': 'Configurações de todos os provedores',
    'Find Setting': 'Buscar configuração', 'Search by name': 'Buscar pelo nome', 'Discover Models': 'Buscar modelos',
    'Use This Provider': 'Usar este provedor', 'Get API Key': 'Obter chave', 'Model Documentation': 'Documentação de modelos',
    'Configured — enter only to replace': 'Configurado — preencha só para substituir', 'Clear Credential': 'Apagar credencial',
    'One value per line': 'Um valor por linha', 'Settings saved.': 'Configurações salvas.', 'Credentials imported.': 'Credenciais importadas.',
    'Your video appears here': 'Seu vídeo aparece aqui', 'From script to screen': 'Do roteiro à tela',
    'Choose your footage, voice and subtitles, then generate. You can follow progress here without leaving the editor.': 'Escolha mídia, voz e legendas e gere o vídeo. Acompanhe tudo aqui, sem sair do editor.',
    'You can keep editing while this task runs.': 'Você pode continuar editando enquanto a tarefa roda.',
    'No logs yet.': 'Ainda não há logs.', 'Social Publishing': 'Publicação nas redes', 'Material Sources': 'Fontes da mídia',
    'Providers and preferences stay on this server. Credentials are never sent to the editor.': 'Provedores e preferências ficam neste servidor. As credenciais não são enviadas ao editor.',
    'This file contains credentials. Store it privately. Continue?': 'Este arquivo contém credenciais. Guarde-o em local privado. Continuar?',
    'Delete this task and all its files? This cannot be undone.': 'Excluir esta tarefa e todos os arquivos? Não é possível desfazer.',
    'Clean these cached downloads? Task outputs and uploads are kept.': 'Limpar estes downloads em cache? Os resultados e uploads serão mantidos.',
    'Upload Local Media': 'Enviar vídeos ou imagens', 'No media uploaded.': 'Nenhuma mídia enviada.',
    'Reference Audio': 'Áudio de referência', 'Prompt Audio': 'Áudio com transcrição', 'Prompt Transcript': 'Transcrição do áudio',
    'Transcribe Audio': 'Transcrever áudio', 'Quote': 'Consultar preço', 'Run Confirmed Batch': 'Executar lote confirmado',
    'Candidates': 'Alternativas de roteiro', 'Target Duration': 'Duração desejada (s)', 'Style': 'Estilo',
    'Scene Prompts': 'Descrição de cada cena', 'Model': 'Modelo', 'Load Capabilities': 'Carregar modelos disponíveis',
    'I confirm this charge for these exact inputs.': 'Confirmo esta cobrança para os dados exibidos.',
    'Selected': 'Selecionado', 'Select Script': 'Usar roteiro', 'Project': 'Projeto', 'Progress': 'Progresso',
    'Loading…': 'Carregando…', 'Loading settings…': 'Carregando configurações…', 'Loading voices…': 'Carregando vozes…',
    'Provider Settings': 'Configurar provedores', 'Estimated Narration': 'Narração estimada', 'New Project': 'Novo projeto',
  };
  const t = (key: string) => (language === 'pt' ? pt[key] : undefined) || translations[key] || key;
  const choice = (value: any, label: string) => ({value, label: t(label)});
  async function run(name: string, action: () => Promise<void>) {
    busy = name; error = ''; notice = '';
    try { await action(); } catch (e) { error = e instanceof Error ? e.message : String(e); }
    finally { busy = ''; }
  }
  async function changeLanguage() {
    const result = await api(`/locales/${language}`); translations = result.Translation || {};
    document.documentElement.lang = language === 'pt' ? 'pt-BR' : language;
  }
  async function start() {
    loading = true; error = '';
    try {
      boot = await api('/bootstrap'); params = structuredClone(boot!.defaults);
      language = boot!.ui.language || 'pt'; voiceProvider = boot!.ui.tts_server || 'azure-tts-v1';
      voiceMode = boot!.ui.voice_mode || (params.voice_name === 'no-voice' ? 'none' : 'tts');
      candidateCount = boot!.ui.loomloom_candidate_count || 3;
      scriptDuration = boot!.ui.loomloom_script_duration_seconds || 60;
      scriptBackend = boot!.script_backend || 'local';
      await changeLanguage(); unauthorized = false;
      if (activeId) await refreshTask().catch(() => { activeId = ''; sessionStorage.removeItem('mpt-active-task'); });
    } catch (e) {
      unauthorized = [401, 403].includes((e as Data).status); error = (e as Error).message;
    } finally { loading = false; }
  }
  onMount(() => {
    void start();
    timer = setInterval(() => {
      if (document.hidden) return;
      if (activeId && (task?.state === 4 || ['pending', 'processing'].includes(task?.cross_post_state))) void refreshTask();
      if (scriptRunId) void pollScript();
    }, 1500);
    return () => clearInterval(timer);
  });
  $: document.documentElement.dataset.theme = theme;
  $: localStorage.setItem('mpt-theme', theme);
  $: narrationSignature = JSON.stringify([params.video_script, voiceProvider, params.voice_name, params.voice_rate, params.voice_volume, reference?.id, prompt?.id, promptText]);
  $: actualNarration = preview?.full && narrationSignature === previewInputs ? preview.duration : null;
  $: estimate = actualNarration ? [actualNarration,actualNarration] : durationEstimate(params.video_script || '', params.voice_rate || 1);
  $: scriptQuoteInput = { subject: params.video_subject, candidate_count: candidateCount, language: params.video_language || 'auto', duration_seconds: scriptDuration, style: scriptStyle };
  $: videoQuoteInput = {subject: params.video_subject, scene_prompts: scenePrompts.split('\n').map(v => v.trim()).filter(Boolean), model_id: modelId, aspect_ratio: params.video_aspect};
  $: quoteChanged = !!quote && JSON.stringify(quoteInputs) !== JSON.stringify(quoteKind === 'script' ? scriptQuoteInput : videoQuoteInput);
  $: if (quoteChanged) chargeConfirmed = false;
  $: paidSource = ['wavespeed','volcengine_seedance','ofox','metaso_minimax','muapi'].includes(params.video_source);
  $: paidSignature = JSON.stringify([params.video_source,params.video_subject,params.video_script,params.video_terms,params.video_count,params.video_clip_duration,params.video_aspect]);
  $: if (paidSignature !== paidApprovedSignature) paidConfirmed = false;
  $: generationBlocked = !!busy || (!params.video_subject?.trim() && !params.video_script?.trim()) || (paidSource && !paidConfirmed) || (params.video_source === 'loomloom' && (quoteKind !== 'video' || quoteChanged || !chargeConfirmed));
  $: if (boot && ['footage', 'sound', 'subtitles'].includes(stage)) void loadCatalog();
  $: if (boot && stage === 'sound' && voiceMode === 'tts') void loadVoices(voiceProvider);
  $: filteredHistory = history.filter(entry => `${entry.subject} ${entry.task_id}`.toLowerCase().includes(historySearch.toLowerCase()) && (historyFilter === 'all' || String(entry.state) === historyFilter));
  async function loadCatalog(force = false) {
    if ((catalog && !force) || catalogLoading) return;
    catalogLoading = true;
    try { catalog = await api('/catalog'); } catch (e) { error = String(e); } finally { catalogLoading = false; }
  }
  async function loadVoices(provider: string, force = false) {
    if (voicesLoading || (loadedVoiceProvider === provider && !force)) return;
    voicesLoading = true; voiceError = '';
    try {
      let entries = !force && voiceCache.has(provider) ? voiceCache.get(provider)! : (await api(`/voices?provider=${encodeURIComponent(provider)}`)).voices;
      voiceCache.set(provider, entries);
      if (voiceProvider === provider) {
        if (provider === 'minimax-tts' && params.voice_name?.startsWith('minimax:') && !entries.includes(params.voice_name)) entries = [params.voice_name,...entries];
        voiceList = entries; loadedVoiceProvider = provider;
        if (!entries.includes(params.voice_name) && entries.length) params.voice_name = entries.find((v: string) => v.startsWith('pt-BR')) || entries[0];
      }
    } catch (e) { voiceError = String(e); loadedVoiceProvider = provider; voiceList = []; }
    finally { voicesLoading = false; if (voiceProvider !== provider && stage === 'sound' && voiceMode === 'tts') void loadVoices(voiceProvider); }
  }
  async function navigate(target: string, category = 'script') {
    if (target === 'settings') settingsCategory = category;
    view = target;
    if (target === 'settings' && !SettingsComponent) SettingsComponent = (await import('./Settings.svelte')).default;
    if (target === 'history') await run('history', async () => { history = (await api(`/tasks?limit=${historyLimit}`)).tasks; });
  }
  function requestPayload(): Data {
    const value = structuredClone(params);
    value.video_terms = typeof value.video_terms === 'string' ? value.video_terms.split(',').map((s: string) => s.trim()).filter(Boolean) : value.video_terms;
    value.video_materials = value.video_source === 'local' ? materials.map(m => ({provider: 'local', url: m.id})) : null;
    value.custom_audio_file = null;
    if (voiceMode === 'none') value.voice_name = 'no-voice';
    if (voiceProvider === 'minimax-tts' && voiceMode === 'tts' && value.voice_name && !value.voice_name.startsWith('minimax:')) value.voice_name = 'minimax:' + value.voice_name.trim();
    return {params: value, narration_id: voiceMode === 'upload' ? narration?.id || '' : '', reference_id: reference?.id || '', prompt_id: prompt?.id || '', prompt_text: promptText, preview_id: preview?.id || '', quote_id: quote?.id || '', quote_inputs: quoteInputs || {}, charge_confirmed: chargeConfirmed, paid_source_confirmed: paidConfirmed && paidSignature === paidApprovedSignature};
  }
  async function generate() {
    await run('generate', async () => {
      if (voiceMode === 'upload' && !narration) throw new Error(t('Upload Narration'));
      const result = await api('/generate', requestPayload()); activeId = result.task_id;
      sessionStorage.setItem('mpt-active-task', activeId); await refreshTask();
    });
  }
  async function refreshTask() {
    if (!activeId || taskLoading) return;
    taskLoading = true;
    try { task = await api(`/tasks/${activeId}?logs=${!boot?.ui.hide_log}`); }
    catch (e) { if ((e as Data).status === 404) throw e; error = String(e); }
    finally { taskLoading = false; }
  }
  async function generateScript() {
    await run('script', async () => {
      const result = await api('/scripts', {video_subject: params.video_subject, video_language: params.video_language, paragraph_number: params.paragraph_number, video_script_prompt: params.video_script_prompt, custom_system_prompt: params.custom_system_prompt});
      params.video_script = result.data.video_script; preview = null;
    });
  }
  async function generateTerms() {
    await run('terms', async () => {
      const result = await api('/terms', {video_subject: params.video_subject, video_script: params.video_script, amount: 5, match_materials_to_script: params.match_materials_to_script});
      params.video_terms = result.data.video_terms.join(', ');
    });
  }
  async function audition(full = false) {
    await run('preview', async () => {
      const text = full ? params.video_script : sampleText || params.video_script?.slice(0, 160) || (language === 'pt' ? 'Olá! Esta é uma amostra da narração do seu vídeo.' : 'Hello! This is a sample of your video narration.');
      const signature = narrationSignature;
      preview = await api('/previews', {...requestPayload(), text, full});
      previewInputs = signature;
    });
  }
  async function uploadFiles(kind: string, event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const files = Array.from(input.files || []);
    await run('upload', async () => {
      for (const file of files) {
        const result = await upload(kind, file);
        if (kind === 'material') materials = [...materials, result];
        if (kind === 'narration') narration = result;
        if (kind === 'reference') {reference = result; preview = null;}
        if (kind === 'prompt') {prompt = result; preview = null;}
        if (kind === 'music') { params.bgm_type = 'custom'; params.bgm_file = result.id; await loadCatalog(true); }
      }
    }); input.value = '';
  }
  function restore(detail: Data) {
    params = {...structuredClone(boot!.defaults), ...detail.params};
    const hadNarration = !!params.custom_audio_file;
    params.video_terms = Array.isArray(params.video_terms) ? params.video_terms.join(', ') : params.video_terms || '';
    materials = (params.video_materials || []).map((m: Data) => ({id: m.url.split(/[\\/]/).pop(), name: m.url.split(/[\\/]/).pop()}));
    if (params.custom_audio_file) notice = t('Uploaded narration and private reference audio must be uploaded again.');
    params.custom_audio_file = null; narration = null; reference = null; prompt = null; preview = null;
    voiceMode = hadNarration ? 'upload' : params.voice_name === 'no-voice' ? 'none' : 'tts'; view = 'editor';
    const prefix = String(params.voice_name || '').split(':')[0];
    voiceProvider = ({siliconflow: 'siliconflow', gemini: 'gemini-tts', mimo: 'mimo-tts', minimax: 'minimax-tts', elevenlabs: 'elevenlabs', chatterbox: 'chatterbox', kokoro: 'kokoro', fish_audio: 'fish_audio', voxcpm: 'voxcpm'} as Data)[prefix] || (String(params.voice_name).includes('V2') ? 'azure-tts-v2' : 'azure-tts-v1');
  }
  async function selectTask(id: string) { activeId = id; sessionStorage.setItem('mpt-active-task', id); await run('task', refreshTask); view = 'editor'; }
  async function deleteTask(id: string) {
    if (!confirm(t('Delete this task and all its files? This cannot be undone.'))) return;
    await run('delete', async () => { await api(`/tasks/${id}`, undefined, 'DELETE'); history = history.filter(v => v.task_id !== id); if (activeId === id) {activeId = ''; task = null; sessionStorage.removeItem('mpt-active-task');} });
  }
  async function saveDefaults() {
    await run('settings', async () => {
      const saved = structuredClone(params); delete saved.video_materials; delete saved.custom_audio_file; delete saved.bgm_file;
      await api('/settings', {app: {script_generation_backend: scriptBackend}, ui: {...saved, language, theme, voice_mode: voiceMode, tts_server: voiceProvider, loomloom_candidate_count: candidateCount, loomloom_script_duration_seconds: scriptDuration}}, 'PATCH'); notice = t('Settings saved.');
    });
  }
  async function presetImport(event: Event) {
    const input = event.currentTarget as HTMLInputElement; const file = input.files?.[0];
    if (file) await run('preset', async () => { if (file.size > 1000000) throw new Error(t('File is too large.')); const result = await api('/presets/import', JSON.parse(await file.text())); restore({params: result.params}); notice = t('Preset imported.'); });
    input.value = '';
  }
  async function quoteBatch(kind: string) {
    await run('quote', async () => { const inputs = structuredClone(kind === 'script' ? scriptQuoteInput : videoQuoteInput); quote = await api('/loomloom/quote', {kind, inputs}); quoteInputs = inputs; quoteKind = kind; chargeConfirmed = false; });
  }
  function suggestScenes() {
    const terms = (Array.isArray(params.video_terms) ? params.video_terms : String(params.video_terms || '').split(/[,，\n]/)).map((v: string) => v.trim()).filter(Boolean);
    if (!terms.length && params.video_subject?.trim()) terms.push(params.video_subject.trim());
    if (!terms.length) return;
    const count = Math.min(5, Math.max(1, Math.round(sceneCount)));
    scenePrompts = Array.from({length:count},(_,i) => terms[i % terms.length] + (i >= terms.length ? `; alternative camera angle ${i + 1}` : '')).join('\n');
  }
  async function executeScript() {
    await run('loomloom', async () => { const result = await api('/loomloom/scripts', {kind: 'script', inputs: quoteInputs, quote_id: quote!.id, confirmed: chargeConfirmed}); scriptRunId = result.run_id; sessionStorage.setItem('mpt-script-run',scriptRunId); notice = `${t('Generating')}: ${scriptRunId}`; await pollScript(); });
  }
  async function pollScript() {
    if (!scriptRunId || scriptPolling) return;
    scriptPolling = true;
    const id = scriptRunId;
    try { const result = await api(`/loomloom/scripts/${id}`); if (result.results) { scriptCandidates = result.results.candidates; scriptRunId = ''; sessionStorage.removeItem('mpt-script-run'); notice = result.results.errors?.map((e: Data) => e.message).join('\n') || t('Complete'); } }
    catch (e) { error = String(e); if ((e as Data).status === 404) {scriptRunId = ''; sessionStorage.removeItem('mpt-script-run');} }
    finally { scriptPolling = false; }
  }
  async function settingsSaved(changes: Data = {}) {
    voiceCache.clear(); loadedVoiceProvider = ''; preview = null; quote = null; chargeConfirmed = false; paidConfirmed = false;
    if (changes.ui?.video_source !== undefined) params.video_source = changes.ui.video_source;
    if (changes.ui?.tts_server !== undefined) voiceProvider = changes.ui.tts_server;
    if (changes.ui?.bgm_type !== undefined) params.bgm_type = changes.ui.bgm_type;
    if (changes.app?.script_generation_backend !== undefined) scriptBackend = changes.app.script_generation_backend;
    try {boot = await api('/bootstrap');} catch (e) {error = String(e); unauthorized = [401,403].includes((e as Data).status);}
  }
  async function loadCapabilities() {
    await run('capabilities', async () => { capabilities = await api('/loomloom/capabilities'); modelId = capabilities!.default_model_id; if (!capabilities!.aspect_ratios.includes(params.video_aspect)) params.video_aspect = capabilities!.aspect_ratios[0]; });
  }
  async function inspectCache() { cache = await api(`/cache${cacheDays ? '?days=' + cacheDays : ''}`); }
  async function cleanCache() {
    if (!confirm(t('Clean these cached downloads? Task outputs and uploads are kept.'))) return;
    await run('cache', async () => { const result = await api(`/cache${cacheDays ? '?days=' + cacheDays : ''}`, undefined, 'DELETE'); notice = `${result.deleted_count} ${t('files removed')}`; await inspectCache(); });
  }
</script>

<svelte:head><title>MoneyPrinterTurbo — {t(view === 'editor' ? 'Studio' : view === 'history' ? 'History' : view === 'settings' ? 'Settings' : 'Help')}</title></svelte:head>

<a class="skip-link" href="#main">{t('Skip to content')}</a>
<header class="app-bar">
  <a href="/" class="brand" on:click|preventDefault={() => navigate('editor')}><svg aria-hidden="true" width="27" height="27" viewBox="0 0 28 28" fill="none"><path d="M4 6h20v16H4zM10 6v16M18 6v16" stroke="currentColor" stroke-width="1.5"/><path d="m12 10 5 4-5 4z" fill="currentColor"/></svg><span>MoneyPrinterTurbo<small>{t('Studio')}</small></span></a>
  {#if boot}<nav class="app-nav" aria-label={t('Main Navigation')}>{#each ['editor', 'history', 'settings', 'help'] as target}<button class:current={view === target} aria-current={view === target ? 'page' : undefined} on:click={() => navigate(target)}>{t(target[0].toUpperCase() + target.slice(1))}</button>{/each}</nav>{/if}
  <div class="preferences"><label><span class="sr-only">{t('Language')}</span><select aria-label={t('Language')} bind:value={language} on:change={() => run('language', changeLanguage)}>{#each boot?.locales || ['pt', 'en'] as lang}<option value={lang}>{lang.toUpperCase()}</option>{/each}</select></label><label><span class="sr-only">{t('Theme')}</span><select aria-label={t('Theme')} bind:value={theme}><option value="light">{t('Light')}</option><option value="dark">{t('Dark')}</option><option value="system">{t('System')}</option></select></label></div>
</header>

<main id="main">
  {#if loading}<div class="startup" role="status"><h1>{t('Studio')}</h1><p>{t('Loading…')}</p></div>
  {:else if unauthorized}
    <form class="login" on:submit|preventDefault={() => run('login', async () => { await api('/session', {key: loginKey}); loginKey = ''; await start(); })}><h1>{t('Sign In')}</h1><p>{t('Enter the API key configured on this server.')}</p><Field label={t('API Key')} bind:value={loginKey} type="password"/>{#if error}<p role="alert" class="notice error">{error}</p>{/if}<button class="primary" disabled={!!busy}>{t('Sign In')}</button></form>
  {:else if !boot}<div class="startup"><h1>{t('Cannot connect to the server')}</h1><p class="notice error" role="alert">{error}</p><button on:click={start}>{t('Retry')}</button></div>
  {:else}
    {#if error}<div class="global-notice notice error" role="alert">{error}<button class="quiet" on:click={() => error = ''}>{t('Dismiss')}</button></div>{/if}
    {#if notice}<div class="global-notice notice" role="status">{notice}<button class="quiet" on:click={() => notice = ''}>{t('Dismiss')}</button></div>{/if}
    {#if view === 'editor'}
      <div class="editor-layout">
        <nav class="stage-rail" aria-label={t('Production Stages')}>
          {#each [['script', 'Script'], ['footage', 'Footage'], ['sound', 'Sound'], ['subtitles', 'Subtitles']] as [key, label], index}
            <button class:current={stage === key} aria-current={stage === key ? 'step' : undefined} on:click={() => stage = key}><span class="stage-number">{index + 1}</span>{t(label)}</button>
          {/each}
          <div class="rail-tools"><button class="quiet" on:click={() => run('preset', async () => download('moneyprinterturbo-preset.json', await api('/presets/export', params)))}>{t('Export Preset')}</button><label class="button quiet">{t('Import Preset')}<input class="file-picker" type="file" accept=".json,application/json" on:change={presetImport}></label><button class="quiet" on:click={saveDefaults} disabled={!!busy}>{t('Save Defaults')}</button><button class="quiet" on:click={() => { params = structuredClone(boot!.defaults); materials = []; preview = null; narration = null; reference = null; prompt = null; scenePrompts = ''; quote = null; chargeConfirmed = false; }} >{t('New Project')}</button></div>
        </nav>
        <section class="editor" aria-labelledby="stage-title">
          <div class="workspace-heading"><div><h1 id="stage-title">{t(stage === 'script' ? 'Script' : stage === 'footage' ? 'Footage' : stage === 'sound' ? 'Sound' : 'Subtitles')}</h1><p>{t(stage === 'script' ? 'Start with an idea. Shape the story before choosing the footage.' : stage === 'footage' ? 'Choose where your images come from and how they fill the screen.' : stage === 'sound' ? 'Listen before rendering. Keep narration, music and cloning controls together.' : 'Make every line readable. Preview the style before rendering.')}</p></div></div>
          {#if stage === 'script'}
            <Field label={t('Video Subject')} bind:value={params.video_subject} placeholder={t('What is this video about?')}/>
            <div class="script-editor"><Field label={t('Video Script')} bind:value={params.video_script} type="textarea" placeholder={t('Write your script, or generate a first draft from the subject.')}/></div>
            <Field label={t('Script Generation Backend')} bind:value={scriptBackend} choices={[choice('local','Configured LLM'),choice('loomloom','LoomLoom')]}/>
            <div class="actions">{#if scriptBackend !== 'loomloom'}<button disabled={!!busy || !params.video_subject?.trim()} on:click={generateScript}>{busy === 'script' ? t('Generating') : t('Generate Script')}</button>{/if}<button class="quiet" on:click={() => navigate('settings','script')}>{t('Configure Script AI')} · {boot.llm_provider}</button></div>
            <div class="form-grid"><Field label={t('Script Language')} bind:value={params.video_language} placeholder={t('Auto')}/><Field label={t('Paragraphs')} bind:value={params.paragraph_number} type="number" min={1} max={10} step={1}/></div>
            <details><summary>{t('Script Instructions')}</summary><Field label={t('Script Instructions')} bind:value={params.video_script_prompt} type="textarea"/><Field label={t('System Prompt')} bind:value={params.custom_system_prompt} type="textarea"/></details>
            {#if scriptBackend === 'loomloom'}
              <h2>LoomLoom</h2><div class="form-grid"><Field label={t('Candidates')} bind:value={candidateCount} type="number" min={1} max={10} step={1}/><Field label={t('Target Duration')} bind:value={scriptDuration} type="number" min={1} step={1}/></div><Field label={t('Style')} bind:value={scriptStyle}/><button disabled={!!busy} on:click={() => quoteBatch('script')}>{t('Quote')}</button>
            {/if}
            {#each scriptCandidates as candidate}<article class="candidate"><h3>{t('Script')} {candidate.row_index + 1}</h3><p>{candidate.script}</p><button on:click={() => {params.video_script = candidate.script; params.video_terms = candidate.video_terms.join(', ');}}>{t('Select Script')}</button></article>{/each}
          {:else if stage === 'footage'}
            <Field label={t('Video Source')} bind:value={params.video_source} choices={boot.sources.map((value: string) => ({value,label:t(mediaLabels[value] || value)}))}/>
            <button class="quiet" on:click={() => navigate('settings','video')}>{t('Configure Video AI')}</button>
            {#if params.video_source === 'local'}
              <label class="upload-zone">{t('Upload Local Media')}<input type="file" accept="video/*,image/*" multiple disabled={!!busy} on:change={e => uploadFiles('material', e)}></label>
              <ul class="file-list">{#each materials as material}<li><span>{material.name}</span><button class="quiet" on:click={() => materials = materials.filter(v => v.id !== material.id)}>{t('Remove')}</button></li>{/each}</ul>{#if !materials.length}<p class="muted">{t('No media uploaded.')}</p>{/if}
            {:else if params.video_source === 'loomloom'}
              <button disabled={!!busy} on:click={loadCapabilities}>{t('Load Capabilities')}</button>
              {#if capabilities}<Field label={t('Model')} bind:value={modelId} choices={capabilities.models.map((m: Data) => ({value:m.model_id, label:m.display_name}))}/>{/if}
              <Field label={t('Scene Prompts')} bind:value={scenePrompts} type="textarea" help={t('One scene per line. Maximum five scenes. Exact scene prompts are included in the quote.')}/>
              <div class="form-grid"><Field label={t('Scene Count')} bind:value={sceneCount} type="number" min={1} max={5} step={1}/><button disabled={!!busy || !params.video_subject?.trim()} on:click={suggestScenes}>{t('Suggest Scenes')}</button></div>
              {#if estimate}<p class="notice">{t(actualNarration ? 'Actual Narration' : 'Estimated Narration')}: {estimate[0]}–{estimate[1]} s · {Math.ceil(estimate[0] / params.video_clip_duration)}–{Math.ceil(estimate[1] / params.video_clip_duration)} {t('clips needed; shorter footage repeats.')} <button class="quiet" on:click={() => {sceneCount = Math.min(5, Math.max(1, Math.ceil(estimate![1] / params.video_clip_duration))); suggestScenes();}}>{t('Suggest Scenes')} ({Math.min(5, Math.max(1, Math.ceil(estimate[1] / params.video_clip_duration)))})</button></p>{/if}
              <button disabled={!!busy || !modelId || !scenePrompts.trim()} on:click={() => quoteBatch('video')}>{t('Quote')}</button>
            {:else}
              <Field label={t('Search Terms')} bind:value={params.video_terms} help={t('Separate terms with commas. Leave empty to generate them automatically.')}/><div class="actions"><button disabled={!!busy || !params.video_script} on:click={generateTerms}>{t('Generate Terms')}</button></div>
              {#if !['pexels', 'pixabay', 'coverr'].includes(params.video_source)}<p class="notice">{t('This source may create paid provider requests when you generate the video.')}</p>{/if}
              {#if paidSource}<label class="field check"><input type="checkbox" checked={paidConfirmed && paidSignature === paidApprovedSignature} on:change={e => {paidApprovedSignature = paidSignature; paidConfirmed = (e.currentTarget as HTMLInputElement).checked;}}>{t('I authorize the selected provider to charge for this video generation.')}</label>{/if}
            {/if}
            <div class="form-grid"><Field label={t('Video Aspect')} bind:value={params.video_aspect} choices={params.video_source === 'loomloom' && capabilities ? capabilities.aspect_ratios : ['9:16', '16:9', '1:1']}/><Field label={t('Video Fit Mode')} bind:value={params.video_fit_mode} choices={[choice('cover', 'Cover'), choice('contain', 'Contain')]}/><Field label={t('Video Clip Duration')} bind:value={params.video_clip_duration} type="number" min={1} max={600} step={1}/><Field label={t('Video Clip Speed')} bind:value={params.video_clip_speed} type="number" min={.5} max={2} step={.1}/><Field label={t('Video Count')} bind:value={params.video_count} type="number" min={1} max={100} step={1}/><Field label={t('Video Concat Mode')} bind:value={params.video_concat_mode} choices={[choice('random','Random'),choice('sequential','Sequential')]}/></div>
            <Field label={t('Video Transition Mode')} bind:value={params.video_transition_mode} choices={[choice(null,'None'), ...['Shuffle','FadeIn','FadeOut','SlideIn','SlideOut','ZoomIn','ZoomOut']]}/><Field label={t('Match Materials to Script')} bind:value={params.match_materials_to_script} type="checkbox"/>
            <details><summary>{t('Advanced')}</summary><Field label={t('Render Threads')} bind:value={params.n_threads} type="number" min={1} max={64} step={1}/></details>
          {:else if stage === 'sound'}
            <h2>{t('Voice')}</h2><Field label={t('Voice Mode')} bind:value={voiceMode} choices={[choice('tts', 'TTS'),choice('upload','Upload'),choice('none','Silent')]}/>
            {#if voiceMode === 'tts'}
              <Field label={t('Voice Provider')} bind:value={voiceProvider} choices={Object.entries(boot.tts_providers).map(([value,label]) => ({value,label:t(speechLabels[value] || String(label))}))}/>
              {#if voicesLoading}<p role="status">{t('Loading voices…')}</p>{/if}{#if voiceError}<p class="notice error" role="alert">{voiceError}</p>{/if}
              <Field label={t('Find Voice')} bind:value={voiceFilter}/>
              <Field label={t('Voice')} bind:value={params.voice_name} choices={voiceList.filter(v => v.toLowerCase().includes(voiceFilter.toLowerCase()))}/>
              {#if voiceProvider === 'minimax-tts'}<label class="field">{t('Manual Voice ID')}<input type="text" value={params.voice_name?.replace(/^minimax:/,'') || ''} on:input={e => {params.voice_name = 'minimax:' + (e.currentTarget as HTMLInputElement).value.trim();}}><small>{t('Enter a MiniMax voice ID, including a private or cloned voice.')}</small></label>{/if}
              <div class="actions"><button class="quiet" disabled={voicesLoading} on:click={() => loadVoices(voiceProvider,true)}>{t('Refresh')}</button><button class="quiet" on:click={() => navigate('settings','speech')}>{t('Configure Narration AI')}</button></div>
              {#if voiceProvider === 'voxcpm'}
                <label class="upload-zone">{t('Reference Audio')}<input type="file" accept="audio/*" disabled={!!busy} on:change={e => uploadFiles('reference',e)}></label>{#if reference}<p>{reference.name}<button class="quiet" on:click={() => {reference = null; preview = null;}}>{t('Remove')}</button></p>{/if}
                <label class="upload-zone">{t('Prompt Audio')}<input type="file" accept="audio/*" disabled={!!busy} on:change={e => uploadFiles('prompt',e)}></label>{#if prompt}<p>{prompt.name}<button class="quiet" on:click={() => {prompt = null; promptText = ''; preview = null;}}>{t('Remove')}</button></p><button disabled={!!busy} on:click={() => run('transcribe', async () => {promptText = (await api('/transcription', {id: prompt!.id})).text;})}>{t('Transcribe Audio')}</button>{/if}
                <Field label={t('Prompt Transcript')} bind:value={promptText} type="textarea" help={t('Private reference audio expires after 30 minutes and is never stored in task history.')}/>
              {/if}
              <Field label={t('Sample Text')} bind:value={sampleText} type="textarea"/>
              <div class="actions"><button disabled={!!busy || !params.voice_name} on:click={() => audition()}>{t('Preview Voice')}</button><button disabled={!!busy || !params.video_script} on:click={() => audition(true)}>{t('Preview Full Narration')}</button></div>
              <small>{t('Preview requests use the selected provider. A matching full preview is reused during generation.')}</small>
              {#if preview}<audio class="audio-player" controls src={preview.url} preload="metadata"></audio><p class="muted">{preview.duration.toFixed(1)} s · {t(preview.full ? 'Full Narration' : 'Sample')}</p>{/if}
            {:else if voiceMode === 'upload'}
              <label class="upload-zone">{t('Upload Narration')}<input type="file" accept="audio/*" disabled={!!busy} on:change={e => uploadFiles('narration',e)}></label>{#if narration}<p>{narration.name}</p><audio controls src={narration.url} preload="metadata"></audio>{/if}<p class="muted">{t('Use Whisper subtitles for uploaded narration; the model loads only when transcription is requested.')}</p>
            {/if}
            <div class="form-grid"><Field label={t('Voice Volume')} bind:value={params.voice_volume} type="number" min={0} max={10} step={.1}/><Field label={t('Voice Rate')} bind:value={params.voice_rate} type="number" min={.25} max={4} step={.05}/></div>
            <h2>{t('Background Music')}</h2><Field label={t('Background Music')} bind:value={params.bgm_type} choices={Object.entries(musicLabels).map(([value,label]) => ({value,label:t(label)}))}/>
            {#if params.bgm_type === 'preset' || params.bgm_type === 'custom'}
              <Field label={t('Background Music')} bind:value={params.bgm_file} choices={params.bgm_type === 'preset' ? catalog?.builtin_music || [] : catalog?.music?.map((m: Data) => ({value:m.id,label:m.name})) || []}/>{#if params.bgm_file}<audio class="audio-player" controls src="/api/v1/studio/music/{encodeURIComponent(params.bgm_file.split(/[\\/]/).pop())}" preload="none"></audio>{/if}
            {/if}
            {#if params.bgm_type === 'custom'}<label class="upload-zone">{t('Upload Music')}<input type="file" accept="audio/*" disabled={!!busy} on:change={e => uploadFiles('music',e)}></label>{/if}
            {#if ['sonilo','elevenlabs'].includes(params.bgm_type)}<Field label={t('Music Prompt')} bind:value={params.video_music_prompt} type="textarea"/><button class="quiet" on:click={() => navigate('settings','music')}>{t('Configure Music AI')}</button>{/if}
            <Field label={t('Music Volume')} bind:value={params.bgm_volume} type="number" min={0} max={10} step={.05}/>
          {:else}
            <Field label={t('Enable Subtitles')} bind:value={params.subtitle_enabled} type="checkbox"/>
            <div class="caption-preview" style:aspect-ratio={params.video_aspect?.replace(':',' / ')} aria-label={t('Caption Preview')}>
              <span class="canvas-label">{t('Caption Preview')}</span>
              {#if params.subtitle_enabled}<span class="caption-line" style:top={params.subtitle_position === 'top' ? '12%' : params.subtitle_position === 'center' ? '50%' : params.subtitle_position === 'custom' ? params.custom_position + '%' : params.subtitle_position === 'two_thirds_bottom' ? '66%' : '83%'} style:color={params.text_fore_color} style:font-size={Math.max(12,params.font_size/3) + 'px'} style:background={params.text_background_color || 'transparent'} style:border-radius={params.rounded_subtitle_background ? '6px' : '0'} style:-webkit-text-stroke={params.stroke_width / 3 + 'px ' + params.stroke_color}>{params.video_script?.split(/[.!?\n]/)[0]?.slice(0,80) || t('Your story, clearly told.')}</span>{/if}
            </div>
            <small>{t('Layout preview only; final font rendering and animation are applied by the video engine.')}</small>
            <div class="form-grid"><Field label={t('Font')} bind:value={params.font_name} choices={catalog?.fonts || []}/><Field label={t('Font Size')} bind:value={params.font_size} type="number" min={1} max={500} step={1}/><Field label={t('Text Color')} bind:value={params.text_fore_color} type="color"/><Field label={t('Outline Color')} bind:value={params.stroke_color} type="color"/><Field label={t('Outline Width')} bind:value={params.stroke_width} type="number" min={0} max={50} step={.1}/><Field label={t('Subtitle Position')} bind:value={params.subtitle_position} choices={[choice('top','Top'),choice('center','Center'),choice('bottom','Bottom'),choice('two_thirds_bottom','Two-thirds down'),choice('custom','Custom')]}/></div>
            {#if params.subtitle_position === 'custom'}<Field label={t('Custom Position')} bind:value={params.custom_position} type="number" min={0} max={100} step={1}/>{/if}
            <Field label={t('Subtitle Display Mode')} bind:value={params.subtitle_display_mode} choices={[choice('sentence','Sentence'),choice('word_by_word','Word by Word')]}/><Field label={t('Subtitle Animation')} bind:value={params.subtitle_animation} choices={[choice('none','None'),choice('pop_spring','Pop Spring')]}/>
            <label class="field check"><input type="checkbox" checked={!!params.text_background_color} on:change={e => params.text_background_color = (e.currentTarget as HTMLInputElement).checked ? '#000000' : false}>{t('Subtitle Background')}</label>{#if params.text_background_color}<Field label={t('Background Color')} bind:value={params.text_background_color} type="color"/><Field label={t('Rounded Background')} bind:value={params.rounded_subtitle_background} type="checkbox"/>{/if}
            <button class="quiet" on:click={() => navigate('settings','transcription')}>{t('Subtitle Provider Settings')}</button>
          {/if}
          {#if quote && ((quoteKind === 'script' && stage === 'script') || (quoteKind === 'video' && stage === 'footage'))}<section class="quote-panel" aria-label={t('Quote')}><h2>{t('Quote')}</h2><p>{quote.estimated_buyer_payable_amount} {quote.currency} · {quote.task_count} {t('tasks')}</p><p class="muted">{t('A quote is an estimate. Actual charges can differ, including when the estimate is zero.')}</p><small>{t('Listing version')}: {quote.listing_version_id}</small>{#if quoteChanged}<p class="notice error">{t('Inputs changed. Request a new quote before confirming.')}</p>{:else}<Field label={t('I confirm this charge for these exact inputs.')} bind:value={chargeConfirmed} type="checkbox"/>{#if quoteKind === 'script'}<button class="primary" disabled={!!busy || !chargeConfirmed || !!scriptRunId} on:click={executeScript}>{t('Run Confirmed Batch')}</button>{/if}{/if}</section>{/if}
          <footer class="generation-bar"><div><strong>{params.video_aspect} · {params.video_count} {t('video(s)')}</strong><small>{estimate ? `${t('Estimated Narration')}: ${estimate[0]}–${estimate[1]} s` : t('Write a script to estimate narration length.')}</small></div><button class="primary" disabled={generationBlocked} on:click={generate}>{busy === 'generate' ? t('Generating') : t('Generate Video')}</button></footer>
        </section>
        <TaskPanel {task} {t} refresh={refreshTask} {restore}/>
      </div>
    {:else if view === 'settings'}
      {#if SettingsComponent}<svelte:component this={SettingsComponent} {t} providers={boot.llm_providers} sources={boot.sources} speechProviders={boot.tts_providers} initialCategory={settingsCategory} videoSource={params.video_source} speechSource={voiceProvider} musicSource={params.bgm_type} onsaved={settingsSaved} onclose={() => navigate('editor')}/>{:else}<p role="status">{t('Loading settings…')}</p>{/if}
    {:else if view === 'history'}
      <section class="history-workspace"><div class="workspace-heading"><div><h1>{t('History')}</h1><p>{t('Revisit a render, download its files or use its settings as a starting point.')}</p></div><button disabled={!!busy} on:click={() => navigate('history')}>{t('Refresh')}</button></div><div class="form-grid"><Field label={t('Search History')} bind:value={historySearch}/><Field label={t('Status')} bind:value={historyFilter} choices={[choice('all','All'),choice('4','Generating'),choice('1','Complete'),choice('-1','Failed')]}/></div>
      {#if !filteredHistory.length}<p class="empty-state">{busy === 'history' ? t('Loading…') : t('No tasks found.')}</p>{/if}
      <ul class="history-list">{#each filteredHistory as entry}<li><button class="history-entry" on:click={() => selectTask(entry.task_id)}><strong>{entry.subject}</strong><small>{entry.task_id}</small></button><span class="status" class:failed={entry.state === -1}>{t(entry.state === 4 ? 'Generating' : entry.state === -1 ? 'Failed' : entry.video_files?.length ? 'Complete' : 'Waiting')}</span><small>{entry.mtime ? new Date(entry.mtime * 1000).toLocaleDateString(language) : ''}</small><button class="quiet danger" disabled={!!busy || entry.state === 4 || ['pending','processing'].includes(entry.cross_post_state)} on:click={() => deleteTask(entry.task_id)}>{t('Delete')}</button></li>{/each}</ul>
      {#if history.length >= historyLimit && historyLimit < 1000}<button on:click={() => {historyLimit = Math.min(1000,historyLimit + 30); void navigate('history');}}>{t('Load More')}</button>{/if}</section>
    {:else}
      <section class="help-workspace"><div class="workspace-heading"><div><h1>{t('Help')}</h1><p>MoneyPrinterTurbo {boot.version}</p></div><button disabled={!!busy} on:click={() => run('version',async () => {version = await api('/version');})}>{t('Check for Updates')}</button></div>{#if version}<p class="notice">{version.update ? `${t('Update available')}: ${version.update}` : t('You are up to date.')}</p>{/if}
      <h2>{t('Your first video')}</h2><ol class="help-steps"><li>{t('Write a subject and generate or paste a script.')}</li><li>{t('Configure a stock or generation provider, or upload local images and videos.')}</li><li>{t('Select a voice, upload narration or choose silent mode. Audition before rendering.')}</li><li>{t('Set your subtitle style and generate. Progress and files stay in the output panel.')}</li></ol>
      <p>{t('Paid script, speech, music and video services use your configured provider account. LoomLoom requires a separate quote and explicit confirmation. No provider is contacted simply by opening the editor.')}</p>
      <p>{t('Whisper and video libraries load only when their operation is requested. For uploaded narration, select Whisper in the subtitle provider settings.')}</p><div class="actions"><button on:click={() => navigate('settings')}>{t('Provider Settings')}</button><a href="/docs" target="_blank" rel="noreferrer">{t('API Documentation')}</a><a href="https://github.com/LucasGazula/MoneyPrinterTurbo" target="_blank" rel="noreferrer">GitHub</a></div>
      <h2>{t('Cache')}</h2><Field label={t('Age in Days')} bind:value={cacheDays} type="number" min={1} step={1} help={t('Leave empty to include all cached stock-video downloads.')}/><div class="actions"><button disabled={!!busy} on:click={() => run('cache', inspectCache)}>{t('Inspect Cache')}</button><button disabled={!!busy || !cache} on:click={cleanCache}>{t('Clean Cache')}</button></div>{#if cache}<p>{cache.file_count} {t('files')} · {(cache.total_size / 1024 / 1024).toFixed(1)} MB</p>{/if}
      <h2>{t('Local deployment')}</h2><p>{t('This interface is served by the same FastAPI process as the API. Node and Streamlit are not needed in production. On a headless Raspberry Pi, use the browser preview and downloads instead of opening a desktop player.')}</p><button on:click={() => run('logout',async () => {await api('/session',undefined,'DELETE'); unauthorized = true;})}>{t('Sign Out')}</button>
      </section>
    {/if}
  {/if}
</main>
