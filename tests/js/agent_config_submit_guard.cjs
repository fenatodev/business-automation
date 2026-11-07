const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let agentConfigSaving = false;');
const end = source.indexOf('\n  // Load agent config on connect', start);
assert(start >= 0 && end > start);

function element(value = '') {
  return {
    value,
    disabled: false,
    textContent: '',
    style: {},
    addEventListener(event, callback) {
      if (event === 'click') this.click = callback;
    },
  };
}

function setup() {
  const elements = new Map([
    ['agent-config-save', element()],
    ['agent-system-prompt', element('  Help customers  ')],
    ['agent-temperature', element('0.4')],
    ['agent-max-tokens', element('256')],
    ['agent-model', element('qwen3:8b')],
    ['agent-config-status', element()],
  ]);
  const requests = [];
  const context = {
    bearer: 'synthetic-token',
    company: 3,
    $: id => elements.get(id),
    api(path, method, body) {
      let resolve;
      let reject;
      const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
      requests.push({path, method, body, resolve, reject, promise});
      return promise;
    },
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {elements, requests};
}

async function run() {
  const {elements, requests} = setup();
  const button = elements.get('agent-config-save');
  const firstSave = button.click();
  const secondSave = button.click();
  assert.equal(requests.length, 1);
  assert.equal(requests[0].path, '/companies/3/agent-config');
  assert.equal(requests[0].method, 'PUT');
  assert.deepEqual(JSON.parse(JSON.stringify(requests[0].body)), {
    system_prompt: 'Help customers', temperature: 0.4, max_tokens: 256, model: 'qwen3:8b',
  });
  assert.equal(button.disabled, true);
  requests[0].resolve({});
  await Promise.all([firstSave, secondSave]);
  assert.equal(button.disabled, false);
  assert.equal(elements.get('agent-config-status').textContent, '✓ Salvo com sucesso');

  const failed = setup();
  const failedSave = failed.elements.get('agent-config-save').click();
  assert.equal(failed.elements.get('agent-config-save').disabled, true);
  failed.requests[0].reject(new Error('synthetic failure'));
  await failedSave;
  assert.equal(failed.elements.get('agent-config-save').disabled, false);
  assert.equal(failed.elements.get('agent-config-status').textContent, 'Erro ao salvar');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
