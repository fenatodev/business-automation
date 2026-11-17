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
]);
const editButton = {className: 'secondary reply-template-edit', disabled: false};
const deleteButton = {className: 'danger', disabled: false};
const duplicateButton = {textContent: 'Duplicar', disabled: false};
const item = {
  className: 'reply-template-item',
  dataset: {templateId: '10'},
  children: [editButton, deleteButton, duplicateButton],
};
const list = {children: [item]};
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
  'let replyTemplateSaving = false;\n' + source.slice(start, end) + '\nthis.beginReplyTemplateEdit = beginReplyTemplateEdit; this.cancelReplyTemplateEdit = cancelReplyTemplateEdit;',
  context,
);

async function run() {
  // Test 1: Cancel shows "Edição cancelada." message
  context.beginReplyTemplateEdit({id: 10, name: 'Saudação', content: 'Olá'});
  assert.equal(context.$('reply-template-save-status').textContent, 'Editando: Saudação');
  context.cancelReplyTemplateEdit();
  assert.equal(context.$('reply-template-save-status').textContent, 'Edição cancelada.');

  // Test 2: Cancel resets form fields
  assert.equal(context.$('reply-template-name').value, '');
  assert.equal(context.$('reply-template-content').value, '');

  // Test 3: Cancel hides the cancel-edit button
  assert.equal(context.$('reply-template-cancel-edit').hidden, true);

  // Test 4: Cancel resets save button text
  assert.equal(context.$('reply-template-save').textContent, 'Salvar template');

  // Test 5: Re-edit and cancel with unchanged values — no confirm prompt
  confirmations = 0;
  context.beginReplyTemplateEdit({id: 10, name: 'Saudação', content: 'Olá'});
  context.cancelReplyTemplateEdit();
  assert.equal(confirmations, 0, 'No confirm when values are unchanged');
  assert.equal(context.$('reply-template-save-status').textContent, 'Edição cancelada.');

  // Test 6: Cancel with changes shows confirm, and user accepts
  confirmations = 0;
  context.beginReplyTemplateEdit({id: 10, name: 'Saudação', content: 'Olá'});
  context.$('reply-template-name').value = 'Alterado';
  context.cancelReplyTemplateEdit();
  assert.equal(confirmations, 1, 'Confirm when values changed and user accepts');
  assert.equal(context.$('reply-template-save-status').textContent, 'Edição cancelada.');

  // Test 7: Cancel with changes — user rejects, values preserved
  // Need to reset confirm before beginReplyTemplateEdit since test 6 already cancelled
  confirmations = 0;
  const origConfirm = context.confirm;
  context.confirm = () => { confirmations += 1; return false; };
  context.beginReplyTemplateEdit({id: 10, name: 'Saudação', content: 'Olá'});
  context.$('reply-template-name').value = 'Alterado';
  context.cancelReplyTemplateEdit();
  assert.equal(confirmations, 1, 'Confirm called when user rejects');
  // Values should be preserved after rejection
  assert.equal(context.$('reply-template-name').value, 'Alterado');
  // Status should still show editing state
  assert.equal(context.$('reply-template-save-status').textContent, 'Editando: Saudação');
  context.confirm = origConfirm;

  // Test 8: Edit buttons are re-enabled after cancel
  context.beginReplyTemplateEdit({id: 10, name: 'Saudação', content: 'Olá'});
  assert.equal(editButton.disabled, true);
  assert.equal(deleteButton.disabled, true);
  assert.equal(duplicateButton.disabled, true);
  context.cancelReplyTemplateEdit();
  assert.equal(editButton.disabled, false);
  assert.equal(deleteButton.disabled, false);
  assert.equal(duplicateButton.disabled, false);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
