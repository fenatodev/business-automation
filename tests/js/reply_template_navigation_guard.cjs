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
]);
let beforeUnload;
const context = {
  $: id => elements.get(id) || null,
  confirm: () => true,
  addEventListener(name, callback) {
    if (name === 'beforeunload') beforeUnload = callback;
  },
  updateReplyTemplateCharacterCount() {},
};
vm.createContext(context);
vm.runInContext(
  source.slice(start, end) + '\nthis.beginReplyTemplateEdit = beginReplyTemplateEdit;',
  context,
);
assert.equal(typeof beforeUnload, 'function');

function navigateAway() {
  const event = {prevented: false, preventDefault() { this.prevented = true; }};
  beforeUnload(event);
  return event;
}

assert.equal(navigateAway().prevented, false, 'new form must not warn');
context.beginReplyTemplateEdit({id: 1, name: 'Saudação', content: 'Olá'});
assert.equal(navigateAway().prevented, false, 'unchanged edit must not warn');

elements.get('reply-template-content').value = 'Rascunho alterado';
const dirtyEvent = navigateAway();
assert.equal(dirtyEvent.prevented, true);
assert.equal(dirtyEvent.returnValue, '');

elements.get('reply-template-cancel-edit').handlers.click();
assert.equal(navigateAway().prevented, false, 'cancelled edit must not warn');
