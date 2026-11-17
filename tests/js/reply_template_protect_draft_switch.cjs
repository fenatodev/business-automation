const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  async function deleteReplyTemplate(');
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
]);

const editBtn1 = {className: 'secondary reply-template-edit', disabled: false, _focused: false, focus() { this._focused = true; }};
const editBtn2 = {className: 'secondary reply-template-edit', disabled: false, _focused: false, focus() { this._focused = true; }};
const item1 = {
  className: 'reply-template-item',
  dataset: {templateId: '10'},
  children: [editBtn1],
};
const item2 = {
  className: 'reply-template-item',
  dataset: {templateId: '20'},
  children: [editBtn2],
};
const list = {children: [item1, item2]};
let confirmations = 0;
const context = {
  bearer: 'synthetic-token', company: 3,
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
  '\nthis.beginReplyTemplateEdit = beginReplyTemplateEdit; this.cancelReplyTemplateEdit = cancelReplyTemplateEdit;',
  context,
);

async function run() {
  // Test 1: beginReplyTemplateEdit disables all edit buttons
  context.beginReplyTemplateEdit({id: 10, name: 'Primeiro', content: 'Conteúdo 1'}, editBtn1);
  assert.equal(editBtn1.disabled, true, 'Current edit button disabled');
  assert.equal(editBtn2.disabled, true, 'Other edit buttons disabled');

  // Test 2: Calling beginReplyTemplateEdit again is ignored (guard)
  const nameBefore = elements.get('reply-template-name').value;
  const contentBefore = elements.get('reply-template-content').value;
  context.beginReplyTemplateEdit({id: 20, name: 'Segundo', content: 'Conteúdo 2'}, editBtn2);
  assert.equal(elements.get('reply-template-name').value, nameBefore, 'Name unchanged when guard active');
  assert.equal(elements.get('reply-template-content').value, contentBefore, 'Content unchanged when guard active');
  assert.equal(elements.get('reply-template-save-status').textContent, 'Editando: Primeiro', 'Status still shows first template');

  // Test 3: Cancel re-enables edit buttons
  context.cancelReplyTemplateEdit();
  assert.equal(editBtn1.disabled, false, 'Edit buttons re-enabled after cancel');
  assert.equal(editBtn2.disabled, false, 'All edit buttons re-enabled after cancel');

  // Test 4: Save re-enables edit buttons (via replyTemplateSaving flag)
  context.beginReplyTemplateEdit({id: 10, name: 'Primeiro', content: 'Conteúdo 1'}, editBtn1);
  assert.equal(editBtn1.disabled, true);
  // Simulate save completion by calling resetReplyTemplateForm via cancel
  context.cancelReplyTemplateEdit();
  assert.equal(editBtn1.disabled, false);
  assert.equal(editBtn2.disabled, false);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
