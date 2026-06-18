<script>
  import { getInputContext } from '@evidence-dev/sdk/utils/svelte';

  export let name;
  export let title = 'Job Title';
  export let placeholder = 'Type a title and press Enter';
  export let defaultValue = [];

  const inputs = getInputContext();
  const delimiter = '|||';

  let entry = '';
  let values = Array.isArray(defaultValue)
    ? defaultValue.filter(Boolean)
    : String(defaultValue ?? '')
        .split(delimiter)
        .map((value) => value.trim())
        .filter(Boolean);

  const escapeSqlString = (value) => String(value).replaceAll("'", "''");

  const updateInputStore = () => {
    const joinedValues = values.join(delimiter);
    const escapedValues = escapeSqlString(joinedValues);

    $inputs[name] = {
      label: values.length ? values.join(', ') : 'All Values',
      value: joinedValues,
      sql: `'${escapedValues}'`,
      rawValues: values.map((value) => ({ value, label: value })),
      toString() {
        return escapedValues;
      }
    };
  };

  $: if (name) {
    values;
    updateInputStore();
  }

  const addValue = () => {
    const nextValue = entry.trim();
    if (!nextValue) return;

    if (!values.some((value) => value.toLowerCase() === nextValue.toLowerCase())) {
      values = [...values, nextValue];
    }
    entry = '';
  };

  const removeValue = (index) => {
    values = values.filter((_, valueIndex) => valueIndex !== index);
  };

  const handleKeydown = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      addValue();
    }

    if (event.key === 'Backspace' && !entry && values.length) {
      values = values.slice(0, -1);
    }
  };
</script>

<div class="job-title-token-input">
  <span class="filter-title">{title}</span>
  <div class="token-box">
    {#each values as value, index}
      <button class="token" type="button" on:click={() => removeValue(index)} title="Remove {value}">
        <span>{value}</span>
        <span class="token-x">×</span>
      </button>
    {/each}
    <input bind:value={entry} {placeholder} on:keydown={handleKeydown} on:blur={addValue} />
  </div>
</div>

<style>
  .job-title-token-input {
    width: 100%;
    min-width: 0;
    margin: 0 0 1rem 0;
  }

  .filter-title {
    display: block;
    margin-bottom: 0.125rem;
    color: #263238;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .token-box {
    min-height: 2rem;
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.25rem;
    padding: 0.2rem 0.35rem;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 0.375rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
  }

  .token {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    max-width: 100%;
    padding: 0.1rem 0.35rem;
    border: 0;
    border-radius: 0.25rem;
    background: #2563eb;
    color: #ffffff;
    font-size: 0.75rem;
    line-height: 1.15rem;
    cursor: pointer;
  }

  .token span:first-child {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .token-x {
    font-weight: 700;
  }

  input {
    min-width: 9rem;
    flex: 1;
    border: 0;
    outline: none;
    background: transparent;
    color: #263238;
    font-size: 0.75rem;
    line-height: 1.5rem;
  }

  input::placeholder {
    color: #64748b;
  }
</style>
