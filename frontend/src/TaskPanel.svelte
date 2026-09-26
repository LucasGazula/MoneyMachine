<script lang="ts">
  import { api, type Data, type Translate } from './api';
  export let task: Data | null = null;
  export let t: Translate;
  export let refresh: () => Promise<void>;
  export let restore: (task: Data) => void;
  let error = '';
  let busy = false;
  async function open(file?: string) {
    busy = true; error = '';
    try { const result = await api(`/tasks/${task!.task_id}/open`, {file}); if (!result.opened) error = result.path; }
    catch (e) { error = String(e); } finally { busy = false; }
  }
  $: active = task?.state === 4 || ['pending', 'processing'].includes(task?.cross_post_state);
</script>

<aside class="monitor" aria-label={t('Output')}>
  <div class="section-heading"><h2>{t('Output')}</h2>{#if task}<button class="quiet" on:click={refresh}>{t('Refresh')}</button>{/if}</div>
  {#if task}
    <div class="task-heading"><strong>{task.subject || task.task_id}</strong><span class="status" class:failed={task.state === -1}>{task.state === 4 ? t('Generating') : task.state === -1 ? t('Failed') : task.video_files?.length ? t('Complete') : t('Waiting')}</span></div>
    {#if task.state === 4}<progress value={task.progress || 0} max="100" aria-label={t('Progress')}></progress><p class="muted">{task.progress || 0}% · {t('You can keep editing while this task runs.')}</p>{/if}
    {#if task.error}<p class="notice error" role="alert">{task.failed_stage}: {task.error}</p>{/if}
    {#if task.warnings}<div class="notice">{JSON.stringify(task.warnings)}</div>{/if}
    {#each task.video_files || [] as file}
      <figure><video controls playsinline preload="metadata" src={file.url}><track kind="captions"></video><figcaption>{file.name}</figcaption></figure>
      <div class="actions"><a class="button" href="{file.url}?download=true">{t('Download Video')}</a><button disabled={busy} on:click={() => open(file.name)}>{t('Open Video')}</button></div>
    {/each}
    {#if task.material_sources?.length}<details><summary>{t('Material Sources')}</summary>{#each task.material_sources as source}<p>{source.provider || source.source} · {source.author || source.creator || ''} {#if source.page_url}<a href={source.page_url} target="_blank" rel="noreferrer">{t('Source')}</a>{/if}</p>{/each}</details>{/if}
    {#if task.cross_post_state}<details open><summary>{t('Social Publishing')}: {task.cross_post_state}</summary><pre>{JSON.stringify(task.cross_post_results || task.cross_post_error || {}, null, 2)}</pre></details>{/if}
    <div class="actions"><button on:click={() => restore(task)}>{t('Restore Settings')}</button><button disabled={busy} on:click={() => open()}>{t('Open Task Folder')}</button></div>
    {#if error}<p class="notice" role="status">{error}</p>{/if}
    {#if task.files?.length}<details><summary>{t('All Files')}</summary><ul class="file-list">{#each task.files as file}<li><a href="{file.url}?download=true">{file.name}</a><small>{Math.round(file.size / 1024)} KB</small></li>{/each}</ul></details>{/if}
    <details open={active}><summary>{t('Logs')}</summary><pre class="logs" aria-label={t('Logs')}>{task.logs?.join('\n') || t('No logs yet.')}</pre></details>
  {:else}
    <div class="empty-monitor"><div class="preview-frame"><span>{t('Your video appears here')}</span></div><h3>{t('From script to screen')}</h3><p>{t('Choose your footage, voice and subtitles, then generate. You can follow progress here without leaving the editor.')}</p></div>
  {/if}
</aside>
