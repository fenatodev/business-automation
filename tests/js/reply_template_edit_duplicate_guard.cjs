const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  async function duplicateReplyTemplate(');
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
const duplicateButton = {textContent: 'Duplicar', disabled: false};
const item = {
  className: 'reply-template-item',
  dataset: {templateId: '10'},
  children: [duplicateButton],
};
const list = {children: [item]};
let prompts = 0;
let requests = 0;
const context = {
  bearer: 'synthetic-token', company: 3,
  replyTemplateDuplicating: false,
  setReplyTemplateDuplicateButtonsDisabled(disabled) { duplicateButton.disabled = disabled; },
  $: id => elements.get(id) || (id === 'reply-template-list' ? list : null),
  prompt() { prompts += 1; return 'Cópia'; },
  templateApi() { requests += 1; return Promise.resolve({}); },
  updateReplyTemplateCharacterCount() {},
  notify() {},
  loadReplyTemplates() {},
  addEventListener() {},
};
vm.createContext(context);
vm.runInContext(
  'let replyTemplateSaving = false;\n' + source.slice(start, end) +
  '\nfunction suggestReplyTemplateDuplicateName(template) { return `${template.name} (cópia)`; }' +
  '\nthis.beginReplyTemplateEdit = beginReplyTemplateEdit; this.cancelReplyTemplateEdit = cancelReplyTemplateEdit; this.duplicateReplyTemplate = duplicateReplyTemplate;',
  context,
);

async function run() {
  const template = {id: 10, name: 'Saudação', content: 'Olá'};
  context.beginReplyTemplateEdit(template);
  assert.equal(duplicateButton.disabled, true);
  await context.duplicateReplyTemplate(template, duplicateButton);
  assert.equal(prompts, 0, 'queued duplicate must be ignored while editing');
  assert.equal(requests, 0);

  context.cancelReplyTemplateEdit();
  assert.equal(duplicateButton.disabled, false);
  await context.duplicateReplyTemplate(template, duplicateButton);
  assert.equal(prompts, 1);
  assert.equal(requests, 1);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
