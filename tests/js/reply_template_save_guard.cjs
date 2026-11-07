const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let editingReplyTemplateId = null;');
const end = source.indexOf('\n})();', start);
assert(start >= 0 && end > start);

function setup() {
  const elements = new Map();
  function element(value = '') {
    return {
      value, textContent: '', hidden: true, disabled: false, attributes: {},
      handlers: {}, focused: false,
      addEventListener(event, callback) { this.handlers[event] = callback; },
      setAttribute(name, value) { this.attributes[name] = value; },
      focus() { this.focused = true; },
      reset() {
        elements.get('reply-template-name').value = '';
        elements.get('reply-template-content').value = '';
      },
    };
  }
  for (const id of [
    'reply-template-form', 'reply-template-name', 'reply-template-content',
    'reply-template-name-count', 'reply-template-content-count',
    'reply-template-save', 'reply-template-cancel-edit',
    'reply-template-save-status',
  ]) elements.set(id, element());

  let rejectRequest;
  const context = {
    bearer: 'synthetic-token', company: 3,
    $: id => elements.get(id) || null,
    updateReplyTemplateCharacterCount() {},
    templateApi() {
      return new Promise((resolve, reject) => {
        rejectRequest = reject;
      });
    },
    notify() {},
    loadReplyTemplateList: async () => {},
    loadReplyTemplates() {},
  };
  vm.createContext(context);
  vm.runInContext(
    source.slice(start, end) + '\nthis.beginReplyTemplateEdit = beginReplyTemplateEdit;',
    context,
  );
  return {context, elements, rejectRequest: () => rejectRequest(new Error('synthetic failure'))};
}

async function run() {
  const {context, elements, rejectRequest} = setup();
  context.beginReplyTemplateEdit({id: 12, name: 'Saudação', content: 'Olá'});
  elements.get('reply-template-name').value = 'Rascunho atualizado';
  const submit = elements.get('reply-template-form').handlers.submit({preventDefault() {}});

  const cancelButton = elements.get('reply-template-cancel-edit');
  assert.equal(cancelButton.disabled, true);
  let prevented = false;
  elements.get('reply-template-name').handlers.keydown({
    key: 'Escape', preventDefault() { prevented = true; },
  });
  assert.equal(prevented, false);
  cancelButton.handlers.click();
  assert.equal(elements.get('reply-template-name').value, 'Rascunho atualizado');
  assert.equal(cancelButton.hidden, false);

  rejectRequest();
  await submit;
  assert.equal(cancelButton.disabled, false);
  assert.equal(elements.get('reply-template-name').value, 'Rascunho atualizado');

  cancelButton.handlers.click();
  assert.equal(elements.get('reply-template-name').value, '');
  assert.equal(cancelButton.hidden, true);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
