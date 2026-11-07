const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  // WP-252 — Auto-suggest reply when opening the reply form');
const end = source.indexOf('  // WP-226 — Suggest agent reply', start);
assert(start >= 0 && end > start);
const inputStart = source.indexOf('  // WP-459 — Insert a template without discarding the current reply draft');
const inputEnd = source.indexOf('  if ($("reply-template-select"))', inputStart);
assert(inputStart >= 0 && inputEnd > inputStart);

function setup(fetchImpl) {
  const elements = new Map();
  const context = {
    bearer: 'synthetic-token',
    $: id => {
      if (!elements.has(id)) elements.set(id, {});
      return elements.get(id);
    },
    fetch: fetchImpl,
  };
  context.$('human-reply-form').hidden = true;
  context.$('reply-conv-id').value = '12';
  context.$('reply-message').value = '';
  context.$('reply-auto-suggestion-status').textContent = '';
  context.$('reply-template-insert-status').textContent = 'Template inserido.';
  context.$('conv-reply-toggle').addEventListener = (_event, callback) => {
    context.$('conv-reply-toggle').click = callback;
  };
  context.$('reply-message').addEventListener = (_event, callback) => {
    context.$('reply-message').input = callback;
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  vm.runInContext(source.slice(inputStart, inputEnd), context);
  return context;
}

async function run() {
  const unavailable = setup(async () => ({status: 503, ok: false}));
  await unavailable.$('conv-reply-toggle').click();
  assert.equal(unavailable.$('reply-auto-suggestion-status').textContent,
    'Agente indisponível. Você pode escrever a resposta manualmente.');

  const failed = setup(async () => { throw new Error('synthetic network failure'); });
  await failed.$('conv-reply-toggle').click();
  assert.equal(failed.$('reply-auto-suggestion-status').textContent,
    'Não foi possível gerar uma sugestão. Você pode escrever a resposta manualmente.');

  let resolveFetch;
  const pending = setup(() => new Promise(resolve => { resolveFetch = resolve; }));
  const request = pending.$('conv-reply-toggle').click();
  pending.$('reply-message').value = 'Rascunho do operador';
  resolveFetch({status: 503, ok: false});
  await request;
  assert.equal(pending.$('reply-message').value, 'Rascunho do operador');
  assert.equal(pending.$('reply-auto-suggestion-status').textContent, '');

  const edited = setup(async () => ({status: 503, ok: false}));
  await edited.$('conv-reply-toggle').click();
  edited.$('reply-message').value = 'Resposta manual';
  edited.$('reply-message').input();
  assert.equal(edited.$('reply-auto-suggestion-status').textContent, '');
  assert.equal(edited.$('reply-template-insert-status').textContent, '');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
