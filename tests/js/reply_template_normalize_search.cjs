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
  dataset: {templateId: '1', templateName: 'Saudação', searchText: 'saudação'},
  hidden: false,
};
const item2 = {
  className: 'reply-template-item',
  dataset: {templateId: '2', templateName: 'Adeus', searchText: 'adeus'},
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
  // Test 1: normalizeReplyTemplateSearchText strips accents
  assert.equal(context.normalizeReplyTemplateSearchText('Saudação'), 'saudacao');
  assert.equal(context.normalizeReplyTemplateSearchText('CAFÉ'), 'cafe');
  assert.equal(context.normalizeReplyTemplateSearchText('naïve'), 'naive');

  // Test 2: normalize is case-insensitive
  assert.equal(context.normalizeReplyTemplateSearchText('Saudação'), context.normalizeReplyTemplateSearchText('SAUDAÇÃO'));

  // Test 3: normalize collapses whitespace
  assert.equal(context.normalizeReplyTemplateSearchText('  hello   world  '), 'hello world');

  // Test 4: Search with accents finds accented items
  elements.get('reply-template-search').value = 'saudacao';
  context.applyReplyTemplateFilter();
  assert.equal(item1.hidden, false, 'Searching "saudacao" should find "Saudação"');
  assert.equal(item2.hidden, true, 'Searching "saudacao" should not find "Adeus"');

  // Test 5: Search without accents finds accented items
  elements.get('reply-template-search').value = 'saudacao';
  context.applyReplyTemplateFilter();
  assert.equal(item1.hidden, false);

  // Test 6: Filter status shows correct count
  elements.get('reply-template-search').value = 'saudacao';
  context.applyReplyTemplateFilter();
  assert.equal(elements.get('reply-template-filter-status').textContent, '1 template corresponde à busca.');

  // Test 7: Empty search shows all items
  elements.get('reply-template-search').value = '';
  context.applyReplyTemplateFilter();
  assert.equal(item1.hidden, false);
  assert.equal(item2.hidden, false);
  assert.equal(elements.get('reply-template-filter-status').textContent, '');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
