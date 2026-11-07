const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  // WP-252 — Auto-suggest reply when opening the reply form');
const end = source.indexOf('  // WP-226 — Suggest agent reply', start);
assert(start >= 0 && end > start);

const elements = new Map();
let suggestionRequests = 0;
const context = {
  bearer: 'synthetic-token',
  $: id => {
    if (!elements.has(id)) elements.set(id, {});
    return elements.get(id);
  },
  fetch: async () => {
    suggestionRequests++;
    return {
      ok: true,
      status: 200,
      json: async () => ({suggestion: 'Resposta sugerida'}),
    };
  },
};
const toggle = context.$('conv-reply-toggle');
toggle.addEventListener = (event, callback) => { toggle.click = callback; };
const form = context.$('human-reply-form');
form.hidden = true;
context.$('reply-conv-id').value = '12';
context.$('reply-message').value = 'Rascunho anterior';
const status = context.$('reply-template-insert-status');
status.textContent = 'Template "Saudação" inserido na resposta.';

vm.createContext(context);
vm.runInContext(source.slice(start, end), context);

async function run() {
  await toggle.click();
  assert.equal(form.hidden, false);
  assert.equal(context.$('reply-message').value, 'Rascunho anterior');
  assert.equal(suggestionRequests, 0);
  assert.equal(status.textContent, 'Template "Saudação" inserido na resposta.');

  context.$('reply-message').value = '';
  status.textContent = 'Template "Saudação" inserido na resposta.';
  await toggle.click();
  await toggle.click();
  assert.equal(context.$('reply-message').value, 'Resposta sugerida');
  assert.equal(suggestionRequests, 1);
  assert.equal(status.textContent, '');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
