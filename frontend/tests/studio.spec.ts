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
    await expect(page.getByRole('link',{name:'Skip to content'})).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({path:`../.impeccable/review/${width === 1440 ? 'desktop' : 'mobile'}.png`,fullPage:true});
  });
}
