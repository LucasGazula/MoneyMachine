<script lang="ts">
  import { onMount } from 'svelte';
  import Field from './Field.svelte';
  import { api, download, type Data, type Translate } from './api';
  export let t: Translate;
  export let providers: Data[];
  export let onsaved: () => void;
  let sections: Data = {};
  let configured: Data = {};
  let original: Data = {};
  let pending: Data = {};
  let search = '';
  let selected = 'app';
  let provider = '';
  let error = '';
  let notice = '';
  let busy = true;
  let modelOptions: string[] = [];
  const secret = (key: string) => /(api_keys?|api_token|access_key|secret_key|speech_key|password)$/.test(key);
  const privateField = (section: string, key: string) => secret(key) || Object.hasOwn(configured[section] || {}, key);
  $: llmSettingKeys = new Set(providers.flatMap(p => ['api_key', 'base_url', 'model_name', ...p.extra_fields.map((f: Data) => f.config_suffix)].map(suffix => `${p.provider_id}_${suffix}`)));
  const human = (key: string) => key.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
  async function load() {
    busy = true;
    try {
      const result = await api('/settings'); sections = result.sections; configured = result.configured;
      original = structuredClone(sections); provider = sections.app.llm_provider || 'moonshot';
      for (const p of providers) {
        for (const [suffix, value] of [['api_key', ''], ['base_url', p.default_base_url], ['model_name', p.default_model]]) {
          sections.app[`${p.provider_id}_${suffix}`] ??= value;
        }
        for (const field of p.extra_fields) sections.app[`${p.provider_id}_${field.config_suffix}`] ??= field.default_value;
      }
      pending = {};
    } catch (e) { error = String(e); } finally { busy = false; }
  }
  onMount(load);
  function change(section: string, key: string, value: any) {
    pending = {...pending, [section]: {...pending[section], [key]: value}};
  }
  async function save() {
    busy = true; error = ''; notice = '';
    try {
      const changes: Data = structuredClone(pending);
      for (const [section, values] of Object.entries(sections)) {
        for (const [key, value] of Object.entries(values as Data)) {
          if (!privateField(section,key) && JSON.stringify(value) !== JSON.stringify(original[section]?.[key])) {
            (changes[section] ??= {})[key] = value;
          }
        }
      }
      const result = await api('/settings', changes, 'PATCH');
      notice = t(result.pending ? 'Settings will be saved after the active task.' : 'Settings saved.');
      await load(); onsaved();
    } catch (e) { error = String(e); } finally { busy = false; }
  }
  async function discover() {
    busy = true; error = '';
    try { await save(); modelOptions = (await api(`/models?provider=${encodeURIComponent(provider)}`)).models; }
    catch (e) { error = String(e); } finally { busy = false; }
  }
  async function backup() {
    if (!confirm(t('This file contains credentials. Store it privately. Continue?'))) return;
    try { download('moneyprinterturbo-keys.json', await api('/keys/export')); } catch (e) { error = String(e); }
  }
  async function importKeys(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0]; if (!file) return;
    try { if (file.size > 1000000) throw new Error(t('File is too large.')); await api('/keys/import', JSON.parse(await file.text())); await load(); onsaved(); notice = t('Credentials imported.'); }
    catch (e) { error = String(e); } finally { input.value = ''; }
  }
  $: spec = providers.find(p => p.provider_id === provider);
  $: shown = Object.entries(sections[selected] || {}).filter(([key]) => key.toLowerCase().includes(search.toLowerCase()) && (selected !== 'app' || !llmSettingKeys.has(key)));
</script>

<section class="settings-workspace">
  <div class="workspace-heading"><div><h1>{t('Settings')}</h1><p>{t('Providers and preferences stay on this server. Credentials are never sent to the editor.')}</p></div><button class="primary" disabled={busy} on:click={save}>{t('Save Settings')}</button></div>
  {#if error}<p class="notice error" role="alert">{error}</p>{/if}
  {#if notice}<p class="notice" role="status">{notice}</p>{/if}
  {#if busy && !Object.keys(sections).length}<p role="status">{t('Loading settings…')}</p>{/if}
  {#if sections.app}
    <div class="settings-layout">
      <nav aria-label={t('Configuration Sections')}>
        {#each Object.keys(sections) as name}<button class:current={selected === name} on:click={() => { selected = name; search = ''; }}>{name === 'app' ? t('Providers & Generation') : human(name)}</button>{/each}
        <button disabled={busy} on:click={backup}>{t('Export Credentials')}</button>
        <label class="button">{t('Import Credentials')}<input class="file-picker" type="file" accept="application/json,.json" on:change={importKeys}></label>
      </nav>
      <div class="settings-fields">
        {#if selected === 'app'}
          <h2>{t('Text Generation')}</h2>
          <Field label={t('LLM Provider')} bind:value={provider} choices={providers.map(p => ({value: p.provider_id, label: p.default_label}))} />
          <div class="actions"><button on:click={() => { sections.app.llm_provider = provider; change('app', 'llm_provider', provider); }}>{t('Use This Provider')}</button>{#if spec?.api_key_url}<a href={spec.api_key_url} target="_blank" rel="noreferrer">{t('Get API Key')}</a>{/if}{#if spec?.model_docs_url}<a href={spec.model_docs_url} target="_blank" rel="noreferrer">{t('Model Documentation')}</a>{/if}</div>
          {#if spec?.service_endpoints?.length}
            <label class="field">{t('Service Endpoint')}<select on:change={(e) => { sections.app[`${provider}_base_url`] = (e.currentTarget as HTMLSelectElement).value; }}><option value="">{t('Custom')}</option>{#each spec.service_endpoints as endpoint}<option value={endpoint.base_url}>{endpoint.default_label}</option>{/each}</select></label>
          {/if}
          {#each ['api_key', 'base_url', 'model_name', ...(spec?.extra_fields || []).map((f: Data) => f.config_suffix)] as suffix}
            {@const key = `${provider}_${suffix}`}
            {@const isSecret = privateField('app',key) || spec?.extra_fields?.some((f: Data) => f.config_suffix === suffix && f.secret)}
            {#if !((suffix === 'api_key' && spec?.show_api_key === false) || (suffix === 'base_url' && spec?.show_base_url === false))}
              <div on:input={() => { if (isSecret) change('app', key, sections.app[key]); }} role="group">
                <Field label={`${spec?.default_label}: ${human(suffix)}`} bind:value={sections.app[key]} type={isSecret ? 'password' : 'text'} placeholder={configured.app?.[key] ? t('Configured — enter only to replace') : ''}/>
              </div>
              {#if isSecret && configured.app?.[key]}<button class="quiet" on:click={() => { sections.app[key] = ''; change('app', key, ''); }}>{t('Clear Credential')}</button>{/if}
            {/if}
          {/each}
          <button disabled={busy} on:click={discover}>{t('Discover Models')}</button>
          {#if modelOptions.length}<div class="model-list" aria-label={t('Available Models')}>{#each modelOptions as name}<button class="quiet" on:click={() => sections.app[`${provider}_model_name`] = name}>{name}</button>{/each}</div>{/if}
          <hr><h2>{t('All Provider Settings')}</h2>
        {:else}<h2>{human(selected)}</h2>{/if}
        <Field label={t('Find Setting')} bind:value={search} placeholder={t('Search by name')}/>
        <div class="form-grid">
          {#each shown as [key, value]}
            <div role="group" on:input={() => { if (privateField(selected,key)) change(selected, key, sections[selected][key]); }}>
              {#if Array.isArray(value)}
                <label class="field">{human(key)}<textarea rows="3" placeholder={configured[selected]?.[key] ? t('Configured — enter only to replace') : t('One value per line')} value={(value as string[]).join('\n')} on:input={(e) => { sections[selected][key] = (e.currentTarget as HTMLTextAreaElement).value.split('\n').map(v => v.trim()).filter(Boolean); if (privateField(selected,key)) change(selected, key, sections[selected][key]); }}></textarea></label>
              {:else}
                <Field label={human(key)} bind:value={sections[selected][key]} type={privateField(selected,key) ? 'password' : typeof value === 'boolean' ? 'checkbox' : typeof value === 'number' ? 'number' : 'text'} placeholder={configured[selected]?.[key] ? t('Configured — enter only to replace') : ''}/>
              {/if}
              {#if privateField(selected,key) && configured[selected]?.[key]}<button class="quiet" on:click={() => { const empty = Array.isArray(value) ? [] : ''; sections[selected][key] = empty; change(selected, key, empty); }}>{t('Clear Credential')}</button>{/if}
            </div>
          {/each}
        </div>
      </div>
    </div>
  {/if}
</section>
