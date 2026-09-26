import { test, expect } from '@playwright/test';

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

test('settings do not autosave edits or return configured credentials', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button',{name:'Configurações',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Configurações',exact:true})).toBeVisible();
  const saves: any[] = [];
  await page.route('**/api/v1/studio/settings', async route => {
    if(route.request().method() === 'PATCH') { saves.push(route.request().postDataJSON()); await route.fulfill({json:{saved:true,pending:false}}); }
    else await route.continue();
  });
  await page.getByLabel('Provedor LLM', {exact:true}).selectOption('openai');
  await page.getByLabel('OpenAI: Api Key', {exact:true}).fill('test-key-not-real');
  expect(saves).toEqual([]);
  await page.getByRole('button',{name:'Usar este provedor'}).click();
  await page.getByRole('button',{name:'Salvar configurações'}).click();
  await expect.poll(() => saves.length).toBe(1);
  expect(saves[0].app.openai_api_key).toBe('test-key-not-real');
  expect(saves[0].app.llm_provider).toBe('openai');
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

test('non-LLM provider fields remain visible in settings', async ({page}) => {
  await page.goto('/');
  await page.getByRole('button',{name:'Configurações',exact:true}).click();
  await expect(page.getByLabel('Openai Image Api Keys',{exact:true})).toBeVisible();
  await expect(page.getByLabel('Volcengine Seedance Api Key',{exact:true})).toBeVisible();
  await expect(page.getByLabel('Mimo Tts Model Name',{exact:true})).toBeVisible();
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
  await expect(page.getByLabel('Provedor LLM',{exact:true})).toBeVisible();
  await page.getByLabel('Importar credenciais',{exact:true}).setInputFiles({name:'keys.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({schema:'moneyprinterturbo.key-backup',version:1,keys:{app:{api_key:'rotated'}}}))});
  await expect(page.getByRole('heading',{name:'Entrar',exact:true})).toBeVisible();
});
