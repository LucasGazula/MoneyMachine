<script lang="ts">
  import { onMount } from 'svelte';
  import Field from './Field.svelte';
  import { api, download, mediaLabels, speechLabels, musicLabels, geminiTtsModels, type Data, type Translate } from './api';
  export let t: Translate;
  export let providers: Data[];
  export let sources: string[];
  export let speechProviders: Data;
  export let initialCategory = 'script';
  export let videoSource: string | undefined = undefined;
  export let speechSource: string | undefined = undefined;
  export let musicSource: string | undefined = undefined;
  export let onsaved: (changes: Data) => void;
  export let onclose: () => void;
  let category = initialCategory;
  let sections: Data = {};
  let configured: Data = {};
  let original: Data = {};
  let pending: Data = {};
  let initialized = false;
  let search = '';
  let technicalSection = 'app';
  let provider = '';
  let videoProvider = '';
  let speechProvider = '';
  let musicProvider = '';
  let error = '';
  let notice = '';
  let busy = true;
  let modelOptions: string[] = [];
  const categories = [
    ['script', 'Script AI'], ['video', 'Video & Images'], ['speech', 'Narration'],
    ['transcription', 'Transcription & Subtitles'], ['music', 'Music'],
    ['publishing', 'Social Publishing'], ['advanced', 'Advanced'],
  ];
  const speechSections: Record<string,string> = {'azure-tts-v2':'azure','minimax-tts':'minimax_tts'};
  const secret = (key: string) => /(api_keys?|api_token|access_key|secret_key|speech_key|password)$/.test(key);
  const privateField = (section: string, key: string) => secret(key) || Object.hasOwn(configured[section] || {}, key);
  const human = (key: string) => key.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
  const fieldLabels: Record<string,string> = {
    api_key: 'API Key', api_keys: 'API Keys', api_token: 'API Key', base_url: 'API Address',
    model: 'Model', model_name: 'Model', model_id: 'Model', text_to_video_model: 'Video Model',
    video_endpoint: 'Video Endpoint', voice_id: 'Voice ID', voices: 'Voice IDs',
    speech_key: 'API Key', speech_region: 'Service Region', model_size: 'Whisper Model',
    device: 'Device', compute_type: 'Compute Type', resolution: 'Resolution',
    music_base_url: 'API Address', music_model_id: 'Music Model', tts_model_name: 'Voice model',
  };
  function fieldLabel(key: string, prefix = '') {
    const suffix = prefix && key.startsWith(prefix) ? key.slice(prefix.length) : key;
    return t(fieldLabels[suffix] || human(suffix));
  }
  const keys = (section: string, prefix = '') => Object.keys(sections[section] || {}).filter(key => key.startsWith(prefix));
  const basic = (key: string) => /(^|_)(api_keys?|api_token|base_url|model|model_name|model_id|text_to_video_model|video_endpoint|voice_id|voices|speech_key|speech_region|resolution)$/.test(key);
  async function load() {
    busy = true;
    try {
      const result = await api('/settings'); sections = result.sections; configured = result.configured;
      original = structuredClone(sections);
      for (const p of providers) {
        for (const suffix of ['api_key', 'base_url', 'model_name', ...p.extra_fields.map((f: Data) => f.config_suffix)]) sections.app[`${p.provider_id}_${suffix}`] ??= '';
      }
      if (!initialized) {
        provider = sections.app.llm_provider || 'moonshot';
        videoProvider = videoSource ?? sections.ui.video_source ?? sections.app.video_source ?? 'pexels';
        speechProvider = speechSource ?? sections.ui.tts_server ?? 'azure-tts-v1';
        musicProvider = musicSource ?? sections.ui.bgm_type ?? '';
        initialized = true;
      }
      pending = {};
    } catch (e) { error = String(e); } finally { busy = false; }
  }
  onMount(load);
  function change(section: string, key: string, value: any) {
    pending = {...pending, [section]: {...pending[section], [key]: value}};
  }
  async function save(): Promise<boolean> {
    busy = true; error = ''; notice = '';
    try {
      const changes: Data = structuredClone(pending);
      for (const [section, values] of Object.entries(sections)) {
        for (const [key, value] of Object.entries(values as Data)) {
          if (!privateField(section,key) && JSON.stringify(value) !== JSON.stringify(original[section]?.[key])) (changes[section] ??= {})[key] = value;
        }
      }
      const result = await api('/settings', changes, 'PATCH');
      notice = t(result.pending ? 'Settings will be saved after the active task.' : 'Settings saved.');
      await load(); onsaved(changes); return true;
    } catch (e) { error = String(e); return false; } finally { busy = false; }
  }
  async function discover() {
    const selectedProvider = provider;
    if (!await save()) return;
    busy = true; error = '';
    try { const result = await api(`/models?provider=${encodeURIComponent(selectedProvider)}`); if (provider === selectedProvider) modelOptions = result.models; }
    catch (e) { error = String(e); } finally { busy = false; }
  }
  async function backup() {
    if (!confirm(t('This file contains credentials. Store it privately. Continue?'))) return;
    try { download('moneymachine-keys.json', await api('/keys/export')); } catch (e) { error = String(e); }
  }
  async function importKeys(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0]; if (!file) return;
    try { if (file.size > 1000000) throw new Error(t('File is too large.')); await api('/keys/import', JSON.parse(await file.text())); await load(); onsaved({}); notice = t('Credentials imported.'); }
    catch (e) { error = String(e); } finally { input.value = ''; }
  }
  $: spec = providers.find(p => p.provider_id === provider);
  $: speechSection = speechSections[speechProvider] || speechProvider;
  $: groups = category === 'video' && videoProvider !== 'local' ? [{section:'app', prefix:videoProvider + '_', fields:keys('app',videoProvider + '_')}]
    : category === 'speech' ? speechProvider === 'azure-tts-v1' ? []
      : speechProvider === 'gemini-tts' ? [{section:'app',prefix:'gemini_',fields:['gemini_api_key']}]
      : speechProvider === 'mimo-tts' ? [{section:'app',prefix:'mimo_',fields:['mimo_api_key','mimo_base_url',...keys('app','mimo_tts_')]}]
      : [{section:speechSection, prefix:'', fields:keys(speechSection).filter(key => !key.startsWith('music_'))}]
    : category === 'music' && musicProvider === 'sonilo' ? [{section:'app',prefix:'sonilo_',fields:keys('app','sonilo_')}]
    : category === 'music' && musicProvider === 'elevenlabs' ? [{section:'elevenlabs',prefix:'',fields:['api_key',...keys('elevenlabs','music_')]}]
    : category === 'music' && musicProvider === 'lyria' ? [{section:'app',prefix:'gemini_',fields:['gemini_api_key']}]
    : category === 'transcription' && sections.app?.subtitle_provider === 'gemini' ? [{section:'app',prefix:'gemini_',fields:['gemini_api_key']}]
    : category === 'publishing' ? [{section:'app',prefix:'upload_post_',fields:keys('app','upload_post_')}]
    : category === 'script' && sections.app?.script_generation_backend === 'loomloom' ? [{section:'app',prefix:'loomloom_',fields:keys('app','loomloom_')}]
    : [];
  $: technicalKeys = Object.keys(sections[technicalSection] || {}).filter(key => key.toLowerCase().includes(search.toLowerCase()));
</script>

{#snippet fields(section: string, fieldKeys: string[], prefix: string = '')}
  <div class="form-grid">
    {#each fieldKeys.filter(key => Object.hasOwn(sections[section] || {},key)) as key}
      {@const value = sections[section][key]}
      <div role="group" on:input={() => { if (privateField(section,key)) change(section, key, sections[section][key]); }}>
        {#if Array.isArray(value)}
          <label class="field">{fieldLabel(key,prefix)}<textarea rows="3" placeholder={configured[section]?.[key] ? t('Configured — enter only to replace') : t('One value per line')} value={(value as string[]).join('\n')} on:input={e => {sections[section][key] = (e.currentTarget as HTMLTextAreaElement).value.split('\n').map(v => v.trim()).filter(Boolean); if (privateField(section,key)) change(section,key,sections[section][key]);}}></textarea></label>
        {:else}
          <Field label={fieldLabel(key,prefix)} bind:value={sections[section][key]} type={privateField(section,key) ? 'password' : typeof value === 'boolean' ? 'checkbox' : typeof value === 'number' ? 'number' : 'text'} placeholder={configured[section]?.[key] ? t('Configured — enter only to replace') : ''}/>
        {/if}
        {#if privateField(section,key) && configured[section]?.[key]}<small class="credential-status">{t('Credential saved on this server.')}</small><button class="quiet" on:click={() => {const empty = Array.isArray(value) ? [] : ''; sections[section][key] = empty; change(section,key,empty);}}>{t('Clear Credential')}</button>{/if}
      </div>
    {/each}
  </div>
{/snippet}

<section class="settings-workspace">
  <div class="workspace-heading"><div><h1>{t('Settings')}</h1><p>{t('Each function can use a different provider and API key. Switching categories keeps your other credentials.')}</p></div><div class="actions"><button class="quiet" on:click={onclose}>{t('Back to Editor')}</button><button class="primary" disabled={busy} on:click={save}>{t('Save Settings')}</button></div></div>
  {#if error}<p class="notice error" role="alert">{error}</p>{/if}
  {#if notice}<p class="notice" role="status">{notice}</p>{/if}
  {#if busy && !Object.keys(sections).length}<p role="status">{t('Loading settings…')}</p>{/if}
  {#if sections.app}
    <div class="settings-layout">
      <nav aria-label={t('Provider Categories')}>
        {#each categories as [id,label]}<button class:current={category === id} aria-current={category === id ? 'page' : undefined} on:click={() => category = id}>{t(label)}</button>{/each}
        <hr><button disabled={busy} on:click={backup}>{t('Export Credentials')}</button>
        <label class="button">{t('Import Credentials')}<input class="file-picker" type="file" accept="application/json,.json" on:change={importKeys}></label>
      </nav>
      <div class="settings-fields">
        <h2>{t(categories.find(([id]) => id === category)?.[1] || 'Settings')}</h2>
        {#if category === 'script'}
          <p class="muted">{t('Writes the script and search terms. This does not choose the video, voice or music AI.')}</p>
          <Field label={t('Script Generation Backend')} bind:value={sections.app.script_generation_backend} choices={[{value:'local',label:t('Configured LLM')},{value:'loomloom',label:'LoomLoom'}]}/>
          {#if sections.app.script_generation_backend !== 'loomloom'}
            <div role="group" on:change={() => {sections.app.llm_provider = provider; change('app','llm_provider',provider); modelOptions = [];}}><Field label={t('Script Provider')} bind:value={provider} choices={providers.map(p => ({value:p.provider_id,label:p.provider_id === 'gemini' ? 'Google Gemini' : p.default_label}))}/></div>
            <div class="actions">{#if spec?.api_key_url}<a href={spec.api_key_url} target="_blank" rel="noreferrer">{t('Get API Key')}</a>{/if}{#if spec?.model_docs_url}<a href={spec.model_docs_url} target="_blank" rel="noreferrer">{t('Model Documentation')}</a>{/if}</div>
            {#if spec?.service_endpoints?.length}<label class="field">{t('Service Region')}<select on:change={e => sections.app[`${provider}_base_url`] = (e.currentTarget as HTMLSelectElement).value}><option value="">{t('Custom')}</option>{#each spec.service_endpoints as endpoint}<option value={endpoint.base_url}>{endpoint.default_label}</option>{/each}</select></label>{/if}
            {#each ['api_key','base_url','model_name',...(spec?.extra_fields || []).map((f: Data) => f.config_suffix)] as suffix}
              {@const key = `${provider}_${suffix}`}
              {@const isSecret = privateField('app',key) || spec?.extra_fields?.some((f: Data) => f.config_suffix === suffix && f.secret)}
              {#if !((suffix === 'api_key' && spec?.show_api_key === false) || (suffix === 'base_url' && spec?.show_base_url === false))}
                <div role="group" on:input={() => {if(isSecret) change('app',key,sections.app[key]);}}><Field label={`${spec?.default_label}: ${fieldLabel(suffix)}`} bind:value={sections.app[key]} type={isSecret ? 'password' : 'text'} placeholder={configured.app?.[key] ? t('Configured — enter only to replace') : suffix === 'model_name' ? spec?.default_model || '' : suffix === 'base_url' ? spec?.default_base_url || '' : ''}/></div>
                {#if isSecret && configured.app?.[key]}<small class="credential-status">{t('Credential saved on this server.')}</small><button class="quiet" on:click={() => {sections.app[key] = ''; change('app',key,'');}}>{t('Clear Credential')}</button>{/if}
              {/if}
            {/each}
            <button disabled={busy} on:click={discover}>{t('Discover Models')}</button>
            {#if modelOptions.length}<div class="model-list" aria-label={t('Available Models')}>{#each modelOptions as name}<button class="quiet" on:click={() => sections.app[`${provider}_model_name`] = name}>{name}</button>{/each}</div>{/if}
          {/if}
        {:else if category === 'video'}
          <p class="muted">{t('Stock services find existing footage. AI video services generate scenes; AI image services generate stills used in the video.')}</p>
          <div role="group" on:change={() => {sections.ui.video_source = videoProvider; change('ui','video_source',videoProvider);}}><Field label={t('Video Provider')} bind:value={videoProvider} choices={sources.map(value => ({value,label:t(mediaLabels[value] || value)}))}/></div>
          {#if videoProvider === 'local'}<p>{t('Local media needs no API key. Upload your images or videos in the Footage stage.')}</p>{/if}
        {:else if category === 'speech'}
          <p class="muted">{t('Turns your script into spoken narration. This is separate from transcription and music.')}</p>
          <div role="group" on:change={() => {sections.ui.tts_server = speechProvider; change('ui','tts_server',speechProvider);}}><Field label={t('Narration Provider')} bind:value={speechProvider} choices={Object.entries(speechProviders).map(([value,label]) => ({value,label:t(speechLabels[value] || String(label))}))}/></div>
          {#if speechProvider === 'gemini-tts'}
            <p class="notice">{t('Google voice shares your Gemini API key with scripts, transcription and Lyria music.')} {t('Choose a voice and listen to a sample in the Sound stage.')}</p>
            <Field label={t('Gemini TTS Model')} bind:value={sections.app.gemini_tts_model_name} choices={geminiTtsModels}/>
            <p class="muted">{t('Gemini 3.8 models can browse the extended Google voice library. Save the model, then choose a voice in Sound.')}</p>
          {:else if speechProvider === 'azure-tts-v1'}<p>{t('Edge TTS needs no API key. It uses an online voice service, not a local model.')}</p>
          {:else if speechProvider === 'mimo-tts'}<p>{t('MiMo voice shares the MiMo script API key. Its voice model is configured separately.')}</p>
          {:else if speechProvider === 'minimax-tts'}<p>{t('MiniMax voice can use a separate key here, or reuse your MiniMax script key when empty.')}</p>{/if}
        {:else if category === 'transcription'}
          <p class="muted">{t('Turns recorded speech into subtitle text. It does not generate a voice.')}</p>
          <Field label={t('Subtitle Provider')} bind:value={sections.app.subtitle_provider} choices={[{value:'edge',label:t('Narration timing — Edge / TTS')},{value:'whisper',label:t('Whisper — local audio transcription')},{value:'gemini',label:t('Gemini 3.5 Transcribe — online')},{value:'',label:t('None')}]}/>
          {#if sections.app.subtitle_provider === 'gemini'}<p class="notice">{t('Gemini transcription uses your Google API key and uploads narration audio for online transcription. The same key can be used for Google voice and Lyria music.')}</p>
          {:else}<p class="notice">{t('Whisper runs locally without an API key. It is not the Google voice provider. Google voice is under Narration → Google Gemini.')}</p>{/if}
          {#if sections.app.subtitle_provider === 'whisper'}
            <Field label={t('Whisper Model')} bind:value={sections.whisper.model_size} choices={Array.from(new Set(['tiny','base','small','medium','large-v2','large-v3','large-v3-turbo',sections.whisper.model_size]))}/>
            {@render fields('whisper',keys('whisper').filter(key => key !== 'model_size'))}
            <p class="muted">{t('Install Whisper support with')} <code>uv sync --extra whisper</code>. {t('The model downloads on first transcription. Restart the server after changing a model that was already loaded.')}</p>
          {/if}
        {:else if category === 'music'}
          <p class="muted">{t('Choose local background music or an AI music service. Narration voice models do not generate background music.')}</p>
          <div role="group" on:change={() => {sections.ui.bgm_type = musicProvider; change('ui','bgm_type',musicProvider);}}><Field label={t('Music Provider')} bind:value={musicProvider} choices={Object.entries(musicLabels).map(([value,label]) => ({value,label:t(label)}))}/></div>
          {#if musicProvider === 'elevenlabs'}<p class="notice">{t('ElevenLabs music shares its ElevenLabs voice API key, but uses a separate music model. Changing the music model does not change the voice model.')}</p>
          {:else if musicProvider === 'lyria'}<p class="notice">{t('Lyria 3.5 shares your Gemini API key with Google scripts and narration. It generates music from a text prompt; when the music prompt is empty, the video subject is used.')} <a href="https://ai.google.dev/gemini-api/docs/music-generation" target="_blank" rel="noreferrer">{t('Model Documentation')}</a></p>
          {:else if !['sonilo','elevenlabs'].includes(musicProvider)}<p>{t('This music option needs no API key. Choose or upload the track in the Sound stage.')}</p>{/if}
        {:else if category === 'publishing'}
          <p class="muted">{t('Upload-Post publishes finished videos to your configured social accounts. It is not a video-generation provider.')}</p>
        {:else}
          <p class="muted">{t('Technical settings, server access and all original configuration fields. You do not need these to configure normal providers.')}</p>
          <Field label={t('Configuration Section')} bind:value={technicalSection} choices={Object.keys(sections).map(value => ({value,label:value === 'app' ? t('Server & Integrations') : human(value)}))}/>
          <Field label={t('Find Setting')} bind:value={search} placeholder={t('Search by name')}/>
          {@render fields(technicalSection,technicalKeys)}
        {/if}
        {#each groups as group}
          {@render fields(group.section, category === 'publishing' ? group.fields : group.fields.filter(basic),group.prefix)}
          {#if category !== 'publishing' && group.fields.some(key => !basic(key))}<details><summary>{t('Advanced provider options')}</summary>{@render fields(group.section,group.fields.filter(key => !basic(key)),group.prefix)}</details>{/if}
        {/each}
      </div>
    </div>
  {/if}
</section>
