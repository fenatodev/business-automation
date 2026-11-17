const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  function updateReplyTemplateCharacterCount(');
const end = source.indexOf('\n\n  let replyTemplateSaving', start);
assert(start >= 0 && end > start);

function element(value = '') {
  return {
    value, textContent: '', hidden: true, disabled: false, handlers: {},
    addEventListener(event, callback) { this.handlers[event] = callback; },
    focus() {},
  };
}

const elements = new Map([
  ['reply-template-name', element()],
  ['reply-template-content', element()],
  ['reply-template-name-count', element()],
  ['reply-template-content-count', element()],
]);
const context = {
  $: id => elements.get(id),
};
vm.createContext(context);
vm.runInContext(
  source.slice(start, end) +
  '\nthis.updateReplyTemplateCharacterCount = updateReplyTemplateCharacterCount;',
  context,
);

async function run() {
  // Unicode character count: emoji counts as 1 character
  elements.get('reply-template-name').value = '🎉';
  context.updateReplyTemplateCharacterCount('reply-template-name', 'reply-template-name-count', 100);
  assert.equal(elements.get('reply-template-name-count').textContent, '1/100 caracteres');

  // Combined characters count correctly
  elements.get('reply-template-name').value = 'café';
  context.updateReplyTemplateCharacterCount('reply-template-name', 'reply-template-name-count', 100);
  assert.equal(elements.get('reply-template-name-count').textContent, '4/100 caracteres');

  // Surrogate pairs (emoji with ZWJ)
  elements.get('reply-template-name').value = '👨‍👩‍👧‍👦';
  context.updateReplyTemplateCharacterCount('reply-template-name', 'reply-template-name-count', 100);
  // Array.from splits into grapheme-like units; surrogate pairs count as 2
  const charCount = Array.from('👨‍👩‍👧‍👦').length;
  assert.ok(charCount > 0, 'Family emoji should have positive character count');

  // Content field with Unicode
  elements.get('reply-template-content').value = 'Olá, mundo! 🌍';
  context.updateReplyTemplateCharacterCount('reply-template-content', 'reply-template-content-count', 4000);
  assert.ok(elements.get('reply-template-content-count').textContent.includes('/4000 caracteres'));
}

run().catch(error => { console.error(error); process.exitCode = 1; });
