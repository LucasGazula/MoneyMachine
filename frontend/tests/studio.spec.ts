import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';

test.beforeEach(async ({page}) => {
  await page.route('**/api/v1/studio/settings', route => {
    const request = route.request();
    if (request.method() === 'PATCH' && request.postDataJSON()?.ui?.voice_name) return route.fulfill({json:{saved:true,pending:false}});
    if (request.method() === 'GET') return route.fetch().then(async response => {
      const body = await response.json();
      body.sections.app.gemini_tts_model_name = 'gemini-2.5-flash-preview-tts';
      return route.fulfill({response, json:body});
    });
    return route.continue();
  });
  await page.route('**/api/v1/studio/bootstrap', async route => {
    const response = await route.fetch();
    const body = await response.json();
    body.ui.tts_server = 'azure-tts-v1';
    body.defaults.voice_name = 'en-AU-NatashaNeural-Female';
    await route.fulfill({response, json:body});
  });
});

test('stage navigation and editing stay local after lazy catalogs load', async ({page}) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', {name: 'Roteiro', exact: true})).toBeVisible();
  await page.getByLabel('Tema do vídeo').fill('Uma viagem pela natureza');
  await page.getByLabel('Roteiro do vídeo', {exact:true}).fill('Este é um roteiro de teste.');
  await page.getByRole('button', {name:'2 Mídia',exact:true}).click();
  await expect(page.getByLabel('Fonte de mídia')).toBeVisible();
  await page.getByRole('button', {name:'3 Áudio',exact:true}).click();
  await expect(page.getByLabel('Voz', {exact:true})).toContainText('pt-BR');
  await page.getByRole('button', {name:'4 Legendas',exact:true}).click();
  await expect(page.getByLabel('Fonte', {exact:true})).toContainText('.tt');
  const requests: string[] = [];
  page.on('request', request => {if(request.url().includes('/api/')) requests.push(request.url());});
  await page.getByRole('button', {name:'1 Roteiro',exact:true}).click();
  await page.getByLabel('Roteiro do vídeo', {exact:true}).fill('Mudança local, sem rerun do servidor.');
  for (const name of ['2 Mídia','4 Legendas','3 Áudio','1 Roteiro']) await page.getByRole('button',{name,exact:true}).click();
  await expect(page.getByLabel('Roteiro do vídeo', {exact:true})).toHaveValue('Mudança local, sem rerun do servidor.');
  expect(requests).toEqual([]);
  expect(errors).toEqual([]);
});

test('subtitle preview loads and applies the selected font immediately', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button',{name:'4 Legendas',exact:true}).click();
  const font = page.getByLabel('Fonte',{exact:true});
  const caption = page.locator('.caption-line');
  for (const name of ['Charm-Regular.ttf','BeVietnamPro-Bold.ttf']) {
    await font.selectOption(name);
    await expect.poll(() => caption.evaluate(node => getComputedStyle(node).fontFamily)).toContain(name);
    await expect.poll(() => page.evaluate(name => [...document.fonts].some(face => face.family.includes(name) && face.status === 'loaded'), name)).toBe(true);
  }
});

test('generation stays asynchronous and shows authenticated artifact links', async ({page}) => {
  await page.route('**/api/v1/studio/generate', route => route.fulfill({status:202,json:{task_id:'fake-task'}}));
  await page.route('**/api/v1/studio/tasks/fake-task?*', route => route.fulfill({json:{task_id:'fake-task',subject:'Teste',state:1,progress:100,params:{video_subject:'Teste'},video_files:[{name:'final-1.mp4',url:'/api/v1/studio/tasks/fake-task/files/final-1.mp4'}],files:[],logs:['Generation complete']}}));
  await page.goto('/');
  await page.getByLabel('Tema do vídeo').fill('Teste');
  await page.getByRole('button',{name:'Gerar vídeo',exact:true}).click();
  await expect(page.getByRole('link',{name:'Baixar vídeo'})).toHaveAttribute('href', '/api/v1/studio/tasks/fake-task/files/final-1.mp4?download=true');
  await page.getByRole('button',{name:'2 Mídia',exact:true}).click();
  await expect(page.getByRole('link',{name:'Baixar vídeo'})).toBeVisible();
});

test('preview loads the finished video after an earlier incomplete response', async ({page}) => {
  const video = execFileSync('ffmpeg', ['-v','error','-f','lavfi','-i','color=green:s=64x64:r=10','-t','1','-c:v','libx264','-pix_fmt','yuv420p','-movflags','frag_keyframe+empty_moov','-f','mp4','pipe:1']);
  let finished = false;
  await page.route('**/api/v1/studio/generate', route => route.fulfill({status:202,json:{task_id:'preview-task'}}));
  await page.route('**/api/v1/studio/tasks/preview-task?*', route => route.fulfill({json:{task_id:'preview-task',subject:'Teste',state:finished ? 1 : 4,progress:finished ? 100 : 90,params:{},video_files:[{name:'final-1.mp4',url:'/api/v1/studio/tasks/preview-task/files/final-1.mp4',size:finished ? video.length : 14}],files:[]}}));
  await page.route('**/api/v1/studio/tasks/preview-task/files/final-1.mp4*', route => route.fulfill({contentType:'video/mp4',body:finished ? video : Buffer.from('partial-render')}));
  await page.goto('/');
  await page.getByLabel('Tema do vídeo').fill('Teste');
  await page.getByRole('button',{name:'Gerar vídeo',exact:true}).click();
  const player = page.locator('.monitor video');
  await expect.poll(() => player.evaluate(node => (node as HTMLVideoElement).error !== null)).toBe(true);
  finished = true;
  await page.getByRole('button',{name:'Atualizar',exact:true}).click();
  await expect.poll(() => player.evaluate(node => (node as HTMLVideoElement).readyState)).toBeGreaterThanOrEqual(2);
  expect(await player.evaluate(node => (node as HTMLVideoElement).duration)).toBeGreaterThan(0);
});

for (const width of [1440, 390]) {
  test(`stopping generation confirms before cancelling at ${width}px`, async ({page}) => {
    await page.setViewportSize({width, height:1000});
    let cancelRequests = 0;
    let cancelled = false;
    await page.route('**/api/v1/studio/generate', route => route.fulfill({status:202,json:{task_id:'cancel-task'}}));
    await page.route('**/api/v1/studio/tasks/cancel-task?*', route => route.fulfill({json:{task_id:'cancel-task',subject:'Teste',state:cancelled ? -2 : 4,progress:50,params:{},video_files:[],files:[]}}));
    await page.route('**/api/v1/studio/tasks/cancel-task/cancel', route => {
      cancelRequests++; cancelled = true;
      return route.fulfill({json:{task_id:'cancel-task',subject:'Teste',state:4,cancel_requested:true,progress:50,params:{},video_files:[],files:[]}});
    });
    await page.goto('/');
    await page.getByLabel('Tema do vídeo').fill('Teste');
    await page.getByRole('button',{name:'Gerar vídeo',exact:true}).click();
    const stop = page.getByRole('button',{name:'Parar geração',exact:true});
    await expect(stop).toBeVisible();
    page.once('dialog', async dialog => {
      expect(dialog.message()).toContain('Tem certeza');
      await dialog.dismiss();
    });
    await stop.click();
    expect(cancelRequests).toBe(0);
    await expect(stop).toBeEnabled();
    page.once('dialog', dialog => dialog.accept());
    await stop.click();
    await expect(page.getByRole('button',{name:'Cancelando…',exact:true})).toBeDisabled();
    await expect(page.getByText('Geração cancelada. Os arquivos concluídos foram mantidos.',{exact:true})).toBeVisible();
    expect(cancelRequests).toBe(1);
    await expect(stop).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}

test('settings do not autosave edits or return configured credentials', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button',{name:'Configurações',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Configurações',exact:true})).toBeVisible();
  const saves: any[] = [];
  await page.route('**/api/v1/studio/settings', async route => {
    if(route.request().method() === 'PATCH') { saves.push(route.request().postDataJSON()); await route.fulfill({json:{saved:true,pending:false}}); }
    else await route.continue();
  });
  await page.getByLabel('Provedor de roteiro', {exact:true}).selectOption('openai');
  await page.getByLabel('OpenAI: Chave da API', {exact:true}).fill('test-key-not-real');
  expect(saves).toEqual([]);
  await page.getByRole('button',{name:'Salvar configurações'}).click();
  await expect.poll(() => saves.length).toBe(1);
  expect(saves[0].app.openai_api_key).toBe('test-key-not-real');
  expect(saves[0].app.llm_provider).toBe('openai');
});

test('last selected voice and provider are saved automatically and restored on reload', async ({page}) => {
  let saved: any = null;
  await page.route('**/api/v1/studio/bootstrap', async route => {
    const response = await route.fetch();
    const body = await response.json();
    body.ui.tts_server = saved?.tts_server || 'azure-tts-v1';
    body.defaults.voice_name = saved?.voice_name || 'en-AU-NatashaNeural-Female';
    body.ui.voice_mode = 'tts';
    body.ui.gemini_voice_locale = saved?.gemini_voice_locale;
    await route.fulfill({response,json:body});
  });
  await page.route('**/api/v1/studio/voices?provider=gemini-tts*', route => route.fulfill({json:{voices:['gemini:voice-one','gemini:voice-two'],model:'gemini-2.5-flash-preview-tts'}}));
  await page.route('**/api/v1/studio/settings', route => {
    saved = route.request().postDataJSON().ui;
    return route.fulfill({json:{saved:true,pending:false}});
  });
  await page.goto('/');
  await page.getByRole('button',{name:'3 Áudio',exact:true}).click();
  await page.getByLabel('Provedor de voz').selectOption('gemini-tts');
  await page.getByLabel('Voz',{exact:true}).selectOption('gemini:voice-two');
  await expect.poll(() => saved?.voice_name).toBe('gemini:voice-two');
  expect(saved.tts_server).toBe('gemini-tts');
  expect(saved.gemini_voice_locale).toBe('pt-BR');
  await page.evaluate(() => localStorage.removeItem('mpt-gemini-voice-locale'));
  await page.reload();
  await page.getByRole('button',{name:'3 Áudio',exact:true}).click();
  await expect(page.getByLabel('Provedor de voz')).toHaveValue('gemini-tts');
  await expect(page.getByLabel('Voz',{exact:true})).toHaveValue('gemini:voice-two');
});

for (const width of [1440,390]) {
  test(`editor fits ${width}px and keyboard navigation works`, async ({page}) => {
    await page.setViewportSize({width,height:1000});
    await page.goto('/');
    await expect(page.getByRole('heading',{name:'Roteiro',exact:true})).toBeVisible();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('link',{name:'Ir para o conteúdo'})).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    if (process.env.MPT_CAPTURE) {await page.getByRole('heading',{name:'Roteiro',exact:true}).click(); await page.screenshot({path:`../.impeccable/review/${width === 1440 ? 'desktop' : 'mobile'}.png`,fullPage:true});}
  });
}

test('paid sources require a fresh confirmation when generation inputs change', async ({page}) => {
  await page.goto('/');
  await page.getByLabel('Tema do vídeo').fill('Teste');
  await page.getByRole('button',{name:'2 Mídia',exact:true}).click();
  await page.getByLabel('Fonte de mídia').selectOption('wavespeed');
  const generate = page.getByRole('button',{name:'Gerar vídeo',exact:true});
  await expect(generate).toBeDisabled();
  const confirmation = page.getByRole('checkbox',{name:'Autorizo a cobrança deste provedor para gerar este vídeo.'});
  await confirmation.check();
  await expect(generate).toBeEnabled();
  await page.getByLabel('Variações',{exact:true}).fill('2');
  await expect(confirmation).not.toBeChecked();
  await expect(generate).toBeDisabled();
});

test('provider settings are separated by their video and narration function', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button',{name:'Configurações',exact:true}).click();
  await page.getByRole('button',{name:'Vídeo e imagens',exact:true}).click();
  await page.getByLabel('Provedor de vídeo ou imagens').selectOption('openai_image');
  await expect(page.getByLabel('Chaves de API',{exact:true})).toBeVisible();
  await page.getByLabel('Provedor de vídeo ou imagens').selectOption('volcengine_seedance');
  await expect(page.getByLabel('Chave da API',{exact:true})).toBeVisible();
  await expect(page.getByLabel('Modelo',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Narração',exact:true}).click();
  await page.getByLabel('Provedor de narração').selectOption('mimo-tts');
  await expect(page.getByLabel('Modelo de voz',{exact:true})).toBeVisible();
});

test('restoring uploaded narration never silently switches to paid TTS', async ({page}) => {
  await page.route('**/api/v1/studio/tasks?*', route => route.fulfill({json:{tasks:[{task_id:'upload-task',subject:'Old upload',state:1,video_files:[]}]}}));
  await page.route('**/api/v1/studio/tasks/upload-task?*', route => route.fulfill({json:{task_id:'upload-task',subject:'Old upload',state:1,params:{video_subject:'Old upload',video_script:'Actual historical script',custom_audio_file:'/private/audio.mp3'},video_files:[],files:[]}}));
  await page.goto('/');
  await page.getByRole('button',{name:'Histórico',exact:true}).click();
  await page.getByRole('button',{name:/Old upload/}).click();
  await page.getByRole('button',{name:'Restaurar configurações',exact:true}).click();
  await expect(page.getByLabel('Roteiro do vídeo',{exact:true})).toHaveValue('Actual historical script');
  await page.getByRole('button',{name:'3 Áudio',exact:true}).click();
  await expect(page.getByLabel('Modo de narração')).toHaveValue('upload');
  await page.getByRole('button',{name:'Gerar vídeo',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Enviar narração');
});

test('LoomLoom scene coverage uses matching full narration and invalidates changed inputs', async ({page}) => {
  await page.route('**/api/v1/studio/previews',route=>route.fulfill({json:{id:'mock-preview',url:'/missing-audio',full:true,duration:21}}));
  await page.goto('/');
  await page.getByLabel('Tema do vídeo').fill('Natureza');
  await page.getByLabel('Roteiro do vídeo',{exact:true}).fill('Uma floresta e um rio.');
  await page.getByRole('button',{name:'3 Áudio',exact:true}).click();
  await expect(page.getByLabel('Voz',{exact:true})).toContainText('pt-BR');
  await page.getByRole('button',{name:'Prévia da narração completa',exact:true}).click();
  await page.getByRole('button',{name:'2 Mídia',exact:true}).click();
  await page.getByLabel('Fonte de mídia').selectOption('loomloom');
  await expect(page.getByText('Narração medida: 21–21 s',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'Sugerir cenas (5)',exact:true}).click();
  expect((await page.getByLabel('Descrição de cada cena').inputValue()).split('\n')).toHaveLength(5);
  await page.getByRole('button',{name:'1 Roteiro',exact:true}).click();
  await page.getByLabel('Roteiro do vídeo',{exact:true}).fill('Outro roteiro.');
  await page.getByRole('button',{name:'2 Mídia',exact:true}).click();
  await expect(page.getByText('Narração medida: 21–21 s',{exact:false})).not.toBeVisible();
});

test('MiniMax private voice survives catalog refresh and saved defaults', async ({page}) => {
  await page.route('**/api/v1/studio/voices?provider=minimax-tts',route=>route.fulfill({json:{voices:['minimax:default']}}));
  await page.goto('/');
  await page.getByRole('button',{name:'3 Áudio',exact:true}).click();
  await expect(page.getByLabel('Voz',{exact:true})).toContainText('pt-BR');
  await page.getByLabel('Provedor de voz').selectOption('minimax-tts');
  await expect(page.getByLabel('Voz',{exact:true})).toHaveValue('minimax:default');
  await page.getByLabel('ID de voz manual').fill('private-clone');
  await page.getByRole('button',{name:'Atualizar',exact:true}).click();
  await expect(page.getByLabel('ID de voz manual')).toHaveValue('private-clone');
  await expect(page.getByLabel('Voz',{exact:true})).toHaveValue('minimax:private-clone');
  let saved: any;
  await page.route('**/api/v1/studio/settings',route=>{saved=route.request().postDataJSON();return route.fulfill({json:{saved:true}});});
  await page.getByRole('button',{name:'Salvar preferências',exact:true}).click();
  await expect.poll(()=>saved?.ui.voice_name).toBe('minimax:private-clone');
  await page.route('**/api/v1/studio/bootstrap',async route=>{const response=await route.fetch();const boot=await response.json();boot.defaults.voice_name=saved.ui.voice_name;boot.ui.tts_server='minimax-tts';await route.fulfill({json:boot});});
  await page.reload();
  await page.getByRole('button',{name:'3 Áudio',exact:true}).click();
  await expect(page.getByLabel('Voz',{exact:true})).toHaveValue('minimax:private-clone');
});

test('importing a rotated server API key returns to login instead of trapping the editor', async ({page}) => {
  let rotated = false;
  await page.route('**/api/v1/studio/bootstrap', route => rotated ? route.fulfill({status:401,json:{detail:'Invalid API key'}}) : route.continue());
  await page.route('**/api/v1/studio/settings', route => rotated ? route.fulfill({status:401,json:{detail:'Invalid API key'}}) : route.continue());
  await page.route('**/api/v1/studio/keys/import',route=>{rotated=true;return route.fulfill({json:{saved:true}});});
  await page.goto('/');
  await page.getByRole('button',{name:'Configurações',exact:true}).click();
  await expect(page.getByLabel('Provedor de roteiro',{exact:true})).toBeVisible();
  await page.getByLabel('Importar credenciais',{exact:true}).setInputFiles({name:'keys.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({schema:'moneyprinterturbo.key-backup',version:1,keys:{app:{api_key:'rotated'}}}))});
  await expect(page.getByRole('heading',{name:'Entrar',exact:true})).toBeVisible();
});

test('Google narration and AI music keys save independently without overwriting other providers', async ({page}) => {
  const saves: any[] = [];
  await page.route('**/api/v1/studio/settings',route => {
    if(route.request().method() === 'PATCH') {saves.push(route.request().postDataJSON());return route.fulfill({json:{saved:true,pending:false}});}
    return route.continue();
  });
  await page.goto('/');
  await page.getByRole('button',{name:'3 Áudio',exact:true}).click();
  await page.getByLabel('Provedor de voz').selectOption('gemini-tts');
  await page.getByRole('button',{name:'Configurar IA de narração',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Narração',exact:true})).toBeVisible();
  await expect(page.getByLabel('Provedor de narração')).toHaveValue('gemini-tts');
  await page.getByLabel('Chave da API',{exact:true}).fill('google-test-key');
  await page.getByRole('button',{name:'Música',exact:true}).click();
  await page.getByLabel('Fonte de música').selectOption('sonilo');
  await page.getByLabel('Chave da API',{exact:true}).fill('music-test-key');
  await page.getByRole('button',{name:'Vídeo e imagens',exact:true}).click();
  await page.getByLabel('Provedor de vídeo ou imagens').selectOption('ofox');
  await page.getByLabel('Chave da API',{exact:true}).fill('video-test-key');
  expect(saves).toEqual([]);
  await page.getByRole('button',{name:'Salvar configurações',exact:true}).click();
  await expect.poll(()=>saves.length).toBe(1);
  expect(saves[0].app.gemini_api_key).toBe('google-test-key');
  expect(saves[0].app.sonilo_api_key).toBe('music-test-key');
  expect(saves[0].app.ofox_api_key).toBe('video-test-key');
  expect(saves[0].app.openai_api_key).toBeUndefined();
  expect(saves[0].app.pexels_api_keys).toBeUndefined();
  expect(saves[0].ui.video_source).toBe('ofox');
  expect(saves[0].ui.bgm_type).toBe('sonilo');
  await page.getByRole('button',{name:'Voltar ao editor',exact:true}).click();
  await expect(page.getByLabel('Provedor de voz')).toHaveValue('gemini-tts');
  await expect(page.getByRole('combobox',{name:'Música de fundo',exact:true})).toHaveValue('sonilo');
  await page.getByRole('button',{name:'2 Mídia',exact:true}).click();
  await expect(page.getByLabel('Fonte de mídia')).toHaveValue('ofox');
});

test('Google voice and local Whisper transcription are clearly distinct', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button',{name:'4 Legendas',exact:true}).click();
  await page.getByRole('button',{name:'Configurar provedor de legendas',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Transcrição e legendas',exact:true})).toBeVisible();
  await page.getByLabel('Modo de transcrição e legendas').selectOption('whisper');
  await expect(page.getByLabel('Modelo Whisper')).toBeVisible();
  await expect(page.getByLabel('Chave da API',{exact:true})).toHaveCount(0);
  await page.getByLabel('Modo de transcrição e legendas').selectOption('gemini');
  await expect(page.getByLabel('Chave da API',{exact:true})).toBeVisible();
  await expect(page.getByLabel('Modo de transcrição e legendas')).toHaveValue('gemini');
  await page.getByRole('button',{name:'Narração',exact:true}).click();
  await page.getByLabel('Provedor de narração').selectOption('gemini-tts');
  await expect(page.getByLabel('Chave da API',{exact:true})).toBeVisible();
  await expect(page.getByLabel('Modelo de voz Gemini')).toHaveValue('gemini-2.5-flash-preview-tts');
  await page.getByLabel('Modelo de voz Gemini').selectOption('gemini-3.8-flash-tts');
  await expect(page.getByLabel('Modelo de voz Gemini')).toHaveValue('gemini-3.8-flash-tts');
  await expect(page.getByLabel('Modelo Whisper')).toHaveCount(0);
  await page.getByRole('button',{name:'Música',exact:true}).click();
  await page.getByLabel('Fonte de música').selectOption('elevenlabs');
  await expect(page.getByLabel('Modelo de música')).toBeVisible();
  await expect(page.getByLabel('Modelo',{exact:true})).toHaveCount(0);
});

test('Gemini voice locale shows only matching voices', async ({page}) => {
  await page.route('**/api/v1/studio/voices?*', route => {
    const url = new URL(route.request().url());
    if (url.searchParams.get('provider') !== 'gemini-tts') return route.continue();
    const locale = url.searchParams.get('language_code');
    const voices = locale === 'en-US'
      ? ['gemini:en-us-advisor-1 | Advisor (en-US)']
      : ['gemini:pt-br-advisor-1 | Conselheira (pt-BR)', 'gemini:pt-br-narrator-1 | Narrador (pt-BR)'];
    return route.fulfill({json:{model:'gemini-3.8-flash-tts',locales:['en-US','pt-BR'],voices,voice_details:Object.fromEntries(voices.map(value => [value, {
      display_name: value.includes('narrator') ? 'Narrador' : value.includes('en-us') ? 'Advisor' : 'Conselheira',
      gender: value.includes('narrator') ? 'male' : 'female', context: value.includes('narrator') ? 'Content & Media' : 'Wellness & Culture',
      description: value.includes('narrator') ? 'Voz firme' : 'Voz acolhedora',
    }]))}});
  });
  await page.goto('/');
  await page.getByRole('button',{name:'3 Áudio',exact:true}).click();
  await page.getByLabel('Provedor de voz').selectOption('gemini-tts');
  await expect(page.getByLabel('Idioma e região da voz')).toHaveValue('pt-BR');
  await expect(page.getByLabel('Voz',{exact:true})).toContainText('Conselheira (pt-BR) · Feminina');
  await page.getByLabel('Gênero da voz').selectOption('female');
  await expect(page.getByLabel('Voz',{exact:true}).locator('option')).toHaveCount(1);
  await page.getByLabel('Categoria da voz').selectOption('Wellness & Culture');
  await expect(page.getByLabel('Voz',{exact:true})).toHaveValue('gemini:pt-br-advisor-1 | Conselheira (pt-BR)');
  await page.getByLabel('Gênero da voz').selectOption('male');
  await expect(page.getByText('Nenhuma voz corresponde a esses filtros.')).toBeVisible();
  await page.getByLabel('Categoria da voz').selectOption('');
  await expect(page.getByLabel('Voz',{exact:true})).toHaveValue('gemini:pt-br-narrator-1 | Narrador (pt-BR)');
  await page.getByLabel('Idioma e região da voz').selectOption('en-US');
  await expect(page.getByLabel('Gênero da voz')).toHaveValue('');
  await expect(page.getByLabel('Voz',{exact:true})).toContainText('Advisor (en-US) · Feminina');
  await expect(page.getByLabel('Voz',{exact:true})).not.toContainText('Conselheira');
});

test('Gemini model can be changed from the Sound stage', async ({page}) => {
  let model = 'gemini-3.8-flash-tts';
  await page.route('**/api/v1/studio/voices?*', route => {
    if (new URL(route.request().url()).searchParams.get('provider') !== 'gemini-tts') return route.continue();
    return route.fulfill({json:{model,locales:model.startsWith('gemini-3.8-') ? ['pt-BR'] : [],
      voices:model.startsWith('gemini-3.8-') ? ['gemini:pt-br-advisor-1 | Advisor (pt-BR)'] : ['gemini:Kore-Firm'],
      voice_details:{}}});
  });
  await page.route('**/api/v1/studio/settings', route => {
    if (route.request().method() !== 'PATCH') return route.continue();
    model = route.request().postDataJSON().app.gemini_tts_model_name;
    return route.fulfill({json:{saved:true,pending:false}});
  });
  await page.goto('/');
  await page.getByRole('button',{name:'3 Áudio',exact:true}).click();
  await page.getByLabel('Provedor de voz').selectOption('gemini-tts');
  await expect(page.getByLabel('Modelo de voz Gemini')).toHaveValue('gemini-3.8-flash-tts');
  await page.getByLabel('Modelo de voz Gemini').selectOption('gemini-2.5-flash-preview-tts');
  await expect(page.getByLabel('Modelo de voz Gemini')).toHaveValue('gemini-2.5-flash-preview-tts');
  await expect(page.getByLabel('Idioma e região da voz')).toHaveCount(0);
  await expect(page.getByLabel('Voz',{exact:true})).toHaveValue('gemini:Kore-Firm');
});

test('Google Lyria music uses the Gemini key and exposes a music prompt', async ({page}) => {
  const saves: any[] = [];
  await page.route('**/api/v1/studio/settings', route => route.request().method() === 'PATCH'
    ? (saves.push(route.request().postDataJSON()), route.fulfill({json:{saved:true,pending:false}}))
    : route.continue());
  await page.goto('/');
  await page.getByRole('button',{name:'Configurações',exact:true}).click();
  await page.getByRole('button',{name:'Música',exact:true}).click();
  await page.getByLabel('Fonte de música').selectOption('lyria');
  await expect(page.getByText('Lyria 3.5 compartilha a chave Gemini')).toBeVisible();
  await page.getByLabel('Chave da API',{exact:true}).fill('lyria-test-key');
  await page.getByRole('button',{name:'Salvar configurações',exact:true}).click();
  expect(saves.at(-1).app.gemini_api_key).toBe('lyria-test-key');
  expect(saves.at(-1).ui.bgm_type).toBe('lyria');
  await page.getByRole('button',{name:'Voltar ao editor',exact:true}).click();
  await page.getByRole('button',{name:'3 Áudio',exact:true}).click();
  await expect(page.getByRole('combobox',{name:'Música de fundo',exact:true})).toHaveValue('lyria');
  await expect(page.getByLabel('Descrição da música',{exact:true})).toBeVisible();
});

test('changing narration provider cannot generate with the previous provider voice', async ({page}) => {
  let voiceName = '';
  await page.route('**/api/v1/studio/settings', route => route.request().method() === 'PATCH'
    ? route.fulfill({json:{saved:true,pending:false}}) : route.continue());
  await page.route('**/api/v1/studio/generate', route => {
    voiceName = route.request().postDataJSON().params.voice_name;
    return route.fulfill({status:202,json:{task_id:'fake-task'}});
  });
  await page.route('**/api/v1/studio/tasks/fake-task?*', route => route.fulfill({json:{task_id:'fake-task',subject:'Teste',state:4,progress:100,params:{video_subject:'Teste'},video_files:[],files:[],logs:[]}}));
  await page.goto('/');
  await page.getByRole('button',{name:'Configurações',exact:true}).click();
  await page.getByRole('button',{name:'Narração',exact:true}).click();
  await page.getByLabel('Provedor de narração').selectOption('gemini-tts');
  await page.getByRole('button',{name:'Salvar configurações',exact:true}).click();
  await page.getByRole('button',{name:'Voltar ao editor',exact:true}).click();
  await page.getByLabel('Tema do vídeo').fill('Teste');
  const generate = page.getByRole('button',{name:'Gerar vídeo',exact:true});
  await expect(generate).toBeDisabled();
  await page.getByRole('button',{name:'3 Áudio',exact:true}).click();
  await expect(page.getByLabel('Voz',{exact:true})).toHaveValue(/^gemini:/);
  await generate.click();
  await expect.poll(() => voiceName).toMatch(/^gemini:/);
});

for (const width of [1440,390]) {
  test(`provider categories fit ${width}px and retain technical settings`, async ({page}) => {
    await page.setViewportSize({width,height:1000});
    await page.goto('/');
    await page.getByRole('button',{name:'Configurações',exact:true}).click();
    await expect(page.getByLabel('Provedor de roteiro',{exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Avançado',exact:true}).click();
    await expect(page.getByLabel('Llm Provider',{exact:true})).toBeVisible();
    await page.getByLabel('Seção técnica').selectOption('whisper');
    await expect(page.getByLabel('Modelo Whisper',{exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Narração',exact:true}).click();
    await page.getByLabel('Provedor de narração').selectOption('gemini-tts');
    await expect(page.getByLabel('Chave da API',{exact:true})).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    if (process.env.MPT_CAPTURE) await page.screenshot({path:`../.impeccable/review/settings-${width}.png`,fullPage:true});
  });
}
