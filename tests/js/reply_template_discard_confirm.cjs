const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let editingReplyTemplateId = null;');
const end = source.indexOf('\n})();', start);
assert(start >= 0 && end > start);

function element(value = '') {
  return {
    value, textContent: '', hidden: true, handlers: {},
    addEventListener(event, callback) { this.handlers[event] = callback; },
    focus() { this.focused = true; },
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
]);
const confirmations = [];
const context = {
  $: id => elements.get(id) || null,
  confirm: message => confirmations.shift(),
  updateReplyTemplateCharacterCount() {},
};
vm.createContext(context);
vm.runInContext(source.slice(start, end) + '\nthis.beginReplyTemplateEdit = beginReplyTemplateEdit;', context);

const trigger = element();
trigger.isConnected = true;
context.beginReplyTemplateEdit({id: 1, name: 'Saudação', content: 'Olá'}, trigger);
elements.get('reply-template-cancel-edit').handlers.click();
assert.equal(confirmations.length, 0);
assert.equal(elements.get('reply-template-cancel-edit').hidden, true);
assert.equal(elements.get('reply-template-save-status').textContent, 'Edição cancelada.');

context.beginReplyTemplateEdit({id: 2, name: 'Retorno', content: 'Obrigado'}, trigger);
trigger.focused = false;
elements.get('reply-template-content').value = 'Rascunho alterado';
confirmations.push(false);
elements.get('reply-template-cancel-edit').handlers.click();
assert.equal(elements.get('reply-template-content').value, 'Rascunho alterado');
assert.equal(elements.get('reply-template-cancel-edit').hidden, false);
assert.equal(trigger.focused, false);

let prevented = false;
confirmations.push(false);
elements.get('reply-template-content').handlers.keydown({
  key: 'Escape', preventDefault() { prevented = true; },
});
assert.equal(prevented, true);
assert.equal(elements.get('reply-template-content').value, 'Rascunho alterado');

confirmations.push(true);
elements.get('reply-template-content').handlers.keydown({
  key: 'Escape', preventDefault() {},
});
assert.equal(elements.get('reply-template-name').value, '');
assert.equal(elements.get('reply-template-content').value, '');
assert.equal(elements.get('reply-template-cancel-edit').hidden, true);
assert.equal(trigger.focused, true);
assert.equal(elements.get('reply-template-save-status').textContent, 'Edição cancelada.');
