const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  // WP-252 — Auto-suggest reply when opening the reply form');
const end = source.indexOf('  // WP-226 — Suggest agent reply', start);
assert(start >= 0 && end > start);

function setup() {
  const elements = new Map();
  let resolveFetch;
  const context = {
    bearer: 'synthetic-token',
    $: id => {
      if (!elements.has(id)) elements.set(id, {});
      return elements.get(id);
    },
    fetch: () => new Promise(resolve => { resolveFetch = resolve; }),
  };
  const toggle = context.$('conv-reply-toggle');
  toggle.addEventListener = (event, callback) => { toggle.click = callback; };
  const form = context.$('human-reply-form');
  form.hidden = true;
  context.$('reply-conv-id').value = '12';
  context.$('reply-message').value = '';
  context.$('reply-template-insert-status').textContent = 'Template inserido.';

  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {
    context,
    finishSuggestion: () => resolveFetch({
      ok: true,
      status: 200,
      json: async () => ({suggestion: 'Resposta sugerida'}),
    }),
  };
}

async function run() {
  const typed = setup();
  const typedRequest = typed.context.$('conv-reply-toggle').click();
  typed.context.$('reply-message').value = 'Rascunho digitado durante a chamada';
  typed.finishSuggestion();
  await typedRequest;
  assert.equal(typed.context.$('reply-message').value, 'Rascunho digitado durante a chamada');
  assert.equal(typed.context.$('reply-template-insert-status').textContent, 'Template inserido.');

  const switched = setup();
  const switchedRequest = switched.context.$('conv-reply-toggle').click();
  switched.context.$('reply-conv-id').value = '13';
  switched.finishSuggestion();
  await switchedRequest;
  assert.equal(switched.context.$('reply-message').value, '');
  assert.equal(switched.context.$('reply-template-insert-status').textContent, 'Template inserido.');

  const closed = setup();
  const closedRequest = closed.context.$('conv-reply-toggle').click();
  await closed.context.$('conv-reply-toggle').click();
  closed.finishSuggestion();
  await closedRequest;
  assert.equal(closed.context.$('human-reply-form').hidden, true);
  assert.equal(closed.context.$('reply-message').value, '');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
