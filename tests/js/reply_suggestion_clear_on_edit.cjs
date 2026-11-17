const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
// Find the WP-459 section that clears suggestion status on input
const startIdx = source.indexOf('// WP-459 — Insert a template without discarding');
const endIdx = source.indexOf('\n\n  if ($("reply-template-select")', startIdx);
assert(startIdx >= 0 && endIdx > startIdx);

function element(opts = {}) {
  return {
    value: opts.value || '',
    textContent: opts.textContent || '',
    hidden: false,
    disabled: false,
    handlers: {},
    addEventListener(event, callback) { this.handlers[event] = callback; },
    focus() {},
  };
}

const elements = new Map([
  ['reply-message', element({value: ''})],
  ['reply-template-insert-status', element({textContent: 'Template "Saudação" inserido na resposta.'})],
  ['reply-auto-suggestion-status', element({textContent: 'Gerando sugestão...'})],
]);
const context = {
  $: id => elements.get(id),
};
vm.createContext(context);
vm.runInContext(
  source.slice(startIdx, endIdx),
  context,
);

async function run() {
  // WP-509: Editing reply message clears suggestion feedback
  const replyMessage = elements.get('reply-message');
  const insertStatus = elements.get('reply-template-insert-status');
  const suggestionStatus = elements.get('reply-auto-suggestion-status');

  // Before editing, statuses have values
  assert.equal(insertStatus.textContent, 'Template "Saudação" inserido na resposta.');
  assert.equal(suggestionStatus.textContent, 'Gerando sugestão...');

  // Simulate input event on reply-message
  replyMessage.value = 'Texto editado pelo usuário';
  const inputHandler = replyMessage.handlers['input'];
  assert.ok(inputHandler, 'reply-message should have input handler');
  inputHandler.call(replyMessage, {});

  // After editing, both statuses should be cleared
  assert.equal(insertStatus.textContent, '', 'Insert status should be cleared on edit');
  assert.equal(suggestionStatus.textContent, '', 'Suggestion status should be cleared on edit');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
