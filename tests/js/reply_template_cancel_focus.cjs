const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
// Include from normalizeReplyTemplateSearchText to cover filter functions
const start = source.indexOf('  function normalizeReplyTemplateSearchText(');
const end = source.indexOf('\n\n  let replyTemplateSaving', start);
assert(start >= 0 && end > start);

function element(value = '') {
  return {
    value, textContent: '', hidden: true, disabled: false, handlers: {},
    addEventListener(event, callback) { this.handlers[event] = callback; },
    focus() { this._focused = true; },
    reset() {
      elements.get('reply-template-name').value = '';
      elements.get('reply-template-content').value = '';
    },
    _focused: false,
  };
}

const searchEl = {value: '', _focused: false, addEventListener() {}, hidden: false};
function element(value = '') {
  return {
    value, textContent: '', hidden: true, disabled: false, handlers: {},
    addEventListener(event, callback) { this.handlers[event] = callback; },
    focus() { this._focused = true; },
    reset() {
      elements.get('reply-template-name').value = '';
      elements.get('reply-template-content').value = '';
    },
    _focused: false,
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
  ['reply-template-search', searchEl],
  ['reply-template-filter-status', element()],
]);
const editButton = {className: 'secondary reply-template-edit', disabled: false, _focused: false, isConnected: true, focus() { this._focused = true; }, closest() { return item; }};
const deleteButton = {className: 'danger', disabled: false};
const duplicateButton = {textContent: 'Duplicar', disabled: false};
const item = {
  className: 'reply-template-item',
  dataset: {templateId: '10', templateName: 'Saudação', searchText: 'saudação'},
  children: [editButton, deleteButton, duplicateButton],
  hidden: false,
  closest(selector) { return this; },
};
const list = {children: [item]};
let confirmations = 0;
const document = {createElement() { return {className: '', setAttribute() {}, textContent: ''}; }};
const context = {
  bearer: 'synthetic-token', company: 3, document,
  $: id => elements.get(id) || (id === 'reply-template-list' ? list : null),
  confirm() { confirmations += 1; return true; },
  templateApi() { return Promise.resolve({}); },
  updateReplyTemplateCharacterCount() {},
  notify() {},
  loadReplyTemplates() {},
  addEventListener() {},
};
vm.createContext(context);
vm.runInContext(
  'let replyTemplateSaving = false;\n' + source.slice(start, end) +
  '\nthis.beginReplyTemplateEdit = beginReplyTemplateEdit; this.cancelReplyTemplateEdit = cancelReplyTemplateEdit; this.applyReplyTemplateFilter = applyReplyTemplateFilter;',
  context,
);

async function run() {
  // Test 1: Cancel focuses trigger button when connected
  editButton._focused = false;
  context.beginReplyTemplateEdit({id: 10, name: 'Saudação', content: 'Olá'}, editButton);
  context.cancelReplyTemplateEdit();
  assert.equal(editButton._focused, true, 'Trigger button focused after cancel');

  // Test 2: Cancel focuses name field when trigger is not connected
  editButton.isConnected = false;
  elements.get('reply-template-name')._focused = false;
  context.beginReplyTemplateEdit({id: 10, name: 'Saudação', content: 'Olá'}, editButton);
  context.cancelReplyTemplateEdit();
  assert.equal(elements.get('reply-template-name')._focused, true, 'Name field focused when trigger disconnected');

  // Test 3: Cancel with hidden item clears search and focuses trigger
  editButton.isConnected = true;
  editButton._focused = false;
  item.hidden = true;
  searchEl.value = 'filtro';
  context.beginReplyTemplateEdit({id: 10, name: 'Saudação', content: 'Olá'}, editButton);
  context.cancelReplyTemplateEdit();
  assert.equal(searchEl.value, '', 'Search cleared when item hidden');
  assert.equal(editButton._focused, true, 'Trigger focused after cancel with hidden item');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
