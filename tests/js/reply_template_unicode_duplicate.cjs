const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  function normalizeReplyTemplateSearchText(');
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
  ['reply-template-save', element()],
  ['reply-template-cancel-edit', element()],
  ['reply-template-save-status', element()],
  ['reply-template-load-status', element()],
  ['reply-template-search', element('')],
  ['reply-template-search-clear', element()],
  ['reply-template-filter-status', element()],
]);
const editButton = {className: 'secondary reply-template-edit', disabled: false};
const deleteButton = {className: 'danger', disabled: false};
const duplicateButton = {textContent: 'Duplicar', disabled: false};
const item1 = {
  className: 'reply-template-item',
  dataset: {templateId: '1', templateName: 'Café', searchText: 'café'},
  children: [editButton, deleteButton, duplicateButton],
  hidden: false,
};
const list = {children: [item1]};
let prompts = [];
let requests = 0;
const context = {
  bearer: 'synthetic-token', company: 3,
  $: id => elements.get(id) || (id === 'reply-template-list' ? list : null),
  confirm() { return true; },
  prompt(msg, defaultVal) { prompts.push({msg, defaultVal}); return defaultVal; },
  templateApi() { requests += 1; return Promise.resolve({id: 2, name: 'Café (cópia)', content: 'Conteúdo'}); },
  updateReplyTemplateCharacterCount() {},
  notify() {},
  loadReplyTemplates() {},
  addEventListener() {},
};
vm.createContext(context);
vm.runInContext(
  'let replyTemplateSaving = false;\n' + source.slice(start, end) +
  '\nthis.suggestReplyTemplateDuplicateName = suggestReplyTemplateDuplicateName; this.duplicateReplyTemplate = duplicateReplyTemplate;',
  context,
);

async function run() {
  // Test 1: suggestReplyTemplateDuplicateName uses Unicode-safe normalization
  const suggested = context.suggestReplyTemplateDuplicateName({id: 1, name: 'Café'});
  assert.ok(suggested.includes('cópia'), 'Suggested name should include "cópia"');
  assert.ok(suggested.startsWith('Café'), 'Suggested name should preserve original');

  // Test 2: Duplicate with Unicode name doesn't conflict with existing
  const item2 = {
    className: 'reply-template-item',
    dataset: {templateId: '2', templateName: 'Café (cópia)', searchText: 'café (cópia)'},
    children: [],
    hidden: false,
  };
  list.children.push(item2);
  const suggested2 = context.suggestReplyTemplateDuplicateName({id: 1, name: 'Café'});
  assert.ok(suggested2.includes('cópia 2'), 'Should skip existing "Café (cópia)" and suggest "cópia 2"');

  // Test 3: Unicode character count in duplicate name validation
  // Array.from is used for length check, so emoji count correctly
  const emojiName = '🎉'.repeat(50);
  assert.equal(Array.from(emojiName).length, 50, '50 emoji should be 50 characters');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
