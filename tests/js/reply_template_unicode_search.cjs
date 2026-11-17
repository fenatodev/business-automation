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
  ['reply-template-search', element('')],
  ['reply-template-search-clear', element()],
  ['reply-template-filter-status', element()],
]);
const item1 = {
  className: 'reply-template-item',
  dataset: {templateId: '1', templateName: 'Café', searchText: 'café'},
  hidden: false,
};
const item2 = {
  className: 'reply-template-item',
  dataset: {templateId: '2', templateName: 'Resumo', searchText: 'resumo'},
  hidden: false,
};
const list = {children: [item1, item2]};
const context = {
  $: id => elements.get(id) || (id === 'reply-template-list' ? list : null),
  updateReplyTemplateCharacterCount() {},
};
vm.createContext(context);
vm.runInContext(
  source.slice(start, end) +
  '\nthis.normalizeReplyTemplateSearchText = normalizeReplyTemplateSearchText; this.applyReplyTemplateFilter = applyReplyTemplateFilter;',
  context,
);

async function run() {
  // Unicode search: searching "cafe" (no accent) finds "Café"
  elements.get('reply-template-search').value = 'cafe';
  context.applyReplyTemplateFilter();
  assert.equal(item1.hidden, false, '"cafe" should find "Café"');
  assert.equal(item2.hidden, true, '"cafe" should not find "Resumo"');

  // Searching with accent also works
  elements.get('reply-template-search').value = 'café';
  context.applyReplyTemplateFilter();
  assert.equal(item1.hidden, false, '"café" should find "Café"');

  // Unicode characters in content
  const item3 = {
    className: 'reply-template-item',
    dataset: {templateId: '3', templateName: 'Emoji 🎉', searchText: 'emoji 🎉'},
    hidden: false,
  };
  list.children.push(item3);
  elements.get('reply-template-search').value = 'emoji';
  context.applyReplyTemplateFilter();
  assert.equal(item3.hidden, false, '"emoji" should find "Emoji 🎉"');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
