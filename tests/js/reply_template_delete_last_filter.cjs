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
    reset() {
      elements.get('reply-template-name').value = '';
      elements.get('reply-template-content').value = '';
    },
  };
}

const elements = new Map([
  ['reply-template-form', element()],
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
  dataset: {templateId: '10', templateName: 'Saudação', searchText: 'saudação'},
  children: [editButton, deleteButton, duplicateButton],
  hidden: false,
  remove() { const idx = list.children.indexOf(this); if (idx >= 0) list.children.splice(idx, 1); },
};
const list = {children: [item1]};
let requests = 0;
let confirmations = 0;
const context = {
  bearer: 'synthetic-token', company: 3,
  $: id => elements.get(id) || (id === 'reply-template-list' ? list : null),
  confirm() { confirmations += 1; return true; },
  templateApi() { requests += 1; return Promise.resolve({}); },
  updateReplyTemplateCharacterCount() {},
  notify() {},
  loadReplyTemplates() {},
  addEventListener() {},
};
vm.createContext(context);
vm.runInContext(
  'let replyTemplateSaving = false;\n' + source.slice(start, end) +
  '\nthis.deleteReplyTemplate = deleteReplyTemplate; this.applyReplyTemplateFilter = applyReplyTemplateFilter;',
  context,
);

async function run() {
  // Test: deleting last item with search active clears search and shows empty state
  elements.get('reply-template-search').value = 'saudação';
  context.applyReplyTemplateFilter();
  assert.equal(item1.hidden, false);

  await context.deleteReplyTemplate(10, item1, deleteButton);
  assert.equal(confirmations, 1);
  assert.equal(requests, 1);
  assert.equal(list.children.length, 0);
  // Search should be cleared when list becomes empty
  assert.equal(elements.get('reply-template-search').value, '');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
