const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  // WP-226 — Copy suggestion to reply form');
const end = source.indexOf('  // WP-270 — Summarize conversation', start);
assert(start >= 0 && end > start);

const elements = new Map();
const notifications = [];
const context = {
  $: id => {
    if (!elements.has(id)) elements.set(id, {});
    return elements.get(id);
  },
  notify: message => notifications.push(message),
};
const copyButton = context.$('conv-suggestion-copy');
copyButton.addEventListener = (event, callback) => { copyButton.click = callback; };
context.$('conv-suggestion-text').textContent = 'Resposta sugerida';
const reply = context.$('reply-message');
reply.value = 'Rascunho anterior';
const status = context.$('reply-template-insert-status');
status.textContent = 'Template "Saudação" inserido na resposta.';
const form = context.$('human-reply-form');
form.hidden = true;

vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
copyButton.click();

assert.equal(reply.value, 'Resposta sugerida');
assert.equal(status.textContent, '');
assert.equal(form.hidden, false);
assert.deepEqual(notifications, ['Sugestão copiada para o formulário.']);
