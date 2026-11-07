const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let agentConfigLoadVersion');
const end = source.indexOf('  $("agent-config-save")?.addEventListener', start);
assert(start >= 0 && end > start);

function element() {
  return {
    hidden: false,
    disabled: false,
    textContent: '',
    value: '',
    addEventListener(event, callback) {
      if (event === 'click') this.click = () => { if (!this.disabled) return callback(); };
    },
  };
}

function setup() {
  const elements = new Map();
  const requests = [];
  const context = {
    bearer: 'synthetic-token',
    company: 3,
    $: id => {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    api(path) {
      let resolve;
      let reject;
      const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
      requests.push({path, resolve, reject, promise});
      return promise;
    },
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {context, requests};
}

async function run() {
  const {context, requests} = setup();
  const retry = context.$('agent-config-load-retry');
  const status = context.$('agent-config-status');
  const prompt = context.$('agent-system-prompt');
  prompt.value = 'existing prompt';

  const failedLoad = context.loadAgentConfig();
  assert.equal(requests[0].path, '/companies/3/agent-config');
  assert.equal(status.textContent, 'Carregando configuração do agente');
  assert.equal(retry.hidden, true);
  requests[0].reject(new Error('private backend details'));
  await failedLoad;
  assert.equal(status.textContent, 'Não foi possível carregar a configuração do agente.');
  assert.equal(retry.hidden, false);
  assert.equal(retry.disabled, false);
  assert.equal(prompt.value, 'existing prompt');
  assert.equal(status.textContent.includes('private backend details'), false);

  retry.click();
  assert.equal(requests.length, 2);
  assert.equal(status.textContent, 'Carregando configuração do agente');
  requests[1].resolve({system_prompt: 'synthetic prompt', temperature: 0.5, max_tokens: 256, model: 'qwen3:8b'});
  await requests[1].promise;
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(prompt.value, 'synthetic prompt');
  assert.equal(context.$('agent-temperature').value, 0.5);
  assert.equal(context.$('agent-max-tokens').value, 256);
  assert.equal(context.$('agent-model').value, 'qwen3:8b');
  assert.equal(status.textContent, '');
  assert.equal(retry.hidden, true);

  const staleLoad = context.loadAgentConfig();
  const currentLoad = context.loadAgentConfig();
  requests[2].resolve({system_prompt: 'stale prompt'});
  await staleLoad;
  requests[3].resolve({system_prompt: 'current prompt'});
  await currentLoad;
  assert.equal(prompt.value, 'current prompt');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
