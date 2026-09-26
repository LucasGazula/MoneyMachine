<script lang="ts">
  export let label: string;
  export let value: any;
  export let choices: (string | {value: any; label: string})[] | undefined = undefined;
  export let type = 'text';
  export let help = '';
  export let min: number | undefined = undefined;
  export let max: number | undefined = undefined;
  export let step: number | string = 'any';
  export let placeholder = '';
  export let disabled = false;
  const id = `field-${Math.random().toString(36).slice(2)}`;
</script>

<div class:check={type === 'checkbox'} class="field">
  {#if type === 'checkbox'}
    <input {id} type="checkbox" bind:checked={value} {disabled} aria-describedby={help ? `${id}-help` : undefined}>
    <label for={id}>{label}</label>
  {:else}
    <label for={id}>{label}</label>
    {#if choices}
      <select {id} bind:value {disabled} aria-describedby={help ? `${id}-help` : undefined}>
        {#each choices as choice}
          <option value={typeof choice === 'string' ? choice : choice.value}>{typeof choice === 'string' ? choice : choice.label}</option>
        {/each}
      </select>
    {:else if type === 'textarea'}
      <textarea {id} bind:value rows="5" {placeholder} {disabled} aria-describedby={help ? `${id}-help` : undefined}></textarea>
    {:else if type === 'number'}
      <input {id} type="number" bind:value {min} {max} {step} {placeholder} {disabled} aria-describedby={help ? `${id}-help` : undefined}>
    {:else if type === 'color'}
      <div class="color-input"><input {id} type="color" bind:value {disabled}><output for={id}>{value}</output></div>
    {:else if type === 'password'}
      <input {id} type="password" bind:value {placeholder} {disabled} autocomplete="new-password" aria-describedby={help ? `${id}-help` : undefined}>
    {:else}
      <input {id} type="text" bind:value {placeholder} {disabled} aria-describedby={help ? `${id}-help` : undefined}>
    {/if}
  {/if}
  {#if help}<small id="{id}-help">{help}</small>{/if}
</div>
