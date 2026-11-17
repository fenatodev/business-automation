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
  dataset: {templateId: '1', templateName: 'Teste', searchText: 'teste'},
  hidden: false,
};
const list = {children: [item1]};
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
  // Whitespace trimming in search
  elements.get('reply-template-search').value = '  teste  ';
  context.applyReplyTemplateFilter();
  assert.equal(item1.hidden, false, 'Whitespace-padded search should still match');

  // Multiple spaces collapsed
  elements.get('reply-template-search').value = '   teste   ';
  context.applyReplyTemplateFilter();
  assert.equal(item1.hidden, false);

  // Empty after trim
  elements.get('reply-template-search').value = '   ';
  context.applyReplyTemplateFilter();
  assert.equal(item1.hidden, false, 'Whitespace-only search shows all items');
  assert.equal(elements.get('reply-template-filter-status').textContent, '');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
