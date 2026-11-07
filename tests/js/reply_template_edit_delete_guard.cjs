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
const deleteButton = {className: 'danger', disabled: false};
const item = {
  className: 'reply-template-item',
  dataset: {templateId: '10'},
  children: [deleteButton],
};
const list = {children: [item]};
let confirmations = 0;
let requests = 0;
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
  'let replyTemplateSaving = false;\n' + source.slice(start, end) + '\nthis.beginReplyTemplateEdit = beginReplyTemplateEdit; this.cancelReplyTemplateEdit = cancelReplyTemplateEdit; this.deleteReplyTemplate = deleteReplyTemplate;',
  context,
);

async function run() {
  context.beginReplyTemplateEdit({id: 10, name: 'Saudação', content: 'Olá'});
  assert.equal(deleteButton.disabled, true);
  await context.deleteReplyTemplate(10, item, deleteButton);
  assert.equal(confirmations, 0, 'queued delete must be ignored while editing');
  assert.equal(requests, 0);

  context.cancelReplyTemplateEdit();
  assert.equal(deleteButton.disabled, false);
  await context.deleteReplyTemplate(10, item, deleteButton);
  assert.equal(confirmations, 1);
  assert.equal(requests, 1);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
