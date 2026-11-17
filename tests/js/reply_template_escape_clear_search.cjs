const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  function normalizeReplyTemplateSearchText(');
const end = source.indexOf('\n\n  let replyTemplateSaving', start);
assert(start >= 0 && end > start);

const searchEl = {
  value: 'filtro', _focused: false, handlers: {}, hidden: false,
  addEventListener(event, callback) { this.handlers[event] = callback; },
};
function element(value = '') {
  return {
    value, textContent: '', hidden: true, disabled: false, handlers: {},
    addEventListener(event, callback) { this.handlers[event] = callback; },
    focus() { this._focused = true; },
    reset() {},
    _focused: false,
  };
}

const elements = new Map([
  ['reply-template-name', element()],
  ['reply-template-content', element()],
  ['reply-template-name-count', element()],
  ['reply-template-content-count', element()],
  ['reply-template-search', searchEl],
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
  '\nthis.applyReplyTemplateFilter = applyReplyTemplateFilter;',
  context,
);

async function run() {
  // Test 1: Escape key handler clears search when non-empty
  searchEl.value = 'filtro';
  const keydownHandler = searchEl.handlers['keydown'];
  assert.ok(keydownHandler, 'keydown handler registered on search');
  keydownHandler({key: 'Escape', currentTarget: searchEl, preventDefault() {}});
  assert.equal(searchEl.value, '', 'Search cleared by Escape');
  assert.equal(elements.get('reply-template-filter-status').textContent, 'Busca limpa.', 'Filter status announces clear');

  // Test 2: Escape does nothing when search is already empty
  searchEl.value = '';
  let prevented = false;
  keydownHandler({key: 'Escape', currentTarget: searchEl, preventDefault() { prevented = true; }});
  assert.equal(searchEl.value, '', 'Search remains empty');
  assert.equal(prevented, false, 'preventDefault not called when search empty');

  // Test 3: Other keys are not intercepted
  searchEl.value = 'filtro';
  prevented = false;
  keydownHandler({key: 'Enter', currentTarget: searchEl, preventDefault() { prevented = true; }});
  assert.equal(searchEl.value, 'filtro', 'Search unchanged for non-Escape key');
  assert.equal(prevented, false, 'preventDefault not called for non-Escape key');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
