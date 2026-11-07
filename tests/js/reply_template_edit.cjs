const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let editingReplyTemplateId = null;');
const end = source.indexOf('\n})();', start);
assert(start >= 0 && end > start);

function element(value = '') {
  return {
    value,
    textContent: '',
    hidden: true,
    disabled: false,
    attributes: {},
    handlers: {},
    addEventListener(event, callback) { this.handlers[event] = callback; },
    setAttribute(name, value) { this.attributes[name] = value; },
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
const requests = [];
const refreshed = [];
const context = {
  bearer: 'synthetic-token', company: 3,
  $: id => elements.get(id) || null,
  updateReplyTemplateCharacterCount(inputId, countId, maxLength) {
    elements.get(countId).textContent = `${elements.get(inputId).value.length}/${maxLength} caracteres`;
  },
  templateApi(path, method, body) {
    return new Promise(resolve => requests.push({path, method, body, resolve}));
  },
  notify: message => refreshed.push(message),
  loadReplyTemplateList: async () => { refreshed.push('list'); },
  loadReplyTemplates: () => { refreshed.push('selector'); },
};
vm.createContext(context);
vm.runInContext(source.slice(start, end) + '\nthis.beginReplyTemplateEdit = beginReplyTemplateEdit;', context);

async function run() {
  context.beginReplyTemplateEdit({id: 12, name: 'Saudação', content: 'Olá'});
  assert.equal(elements.get('reply-template-name').value, 'Saudação');
  assert.equal(elements.get('reply-template-content').value, 'Olá');
  assert.equal(elements.get('reply-template-save').textContent, 'Salvar alterações');
  assert.equal(elements.get('reply-template-cancel-edit').hidden, false);

  const submit = elements.get('reply-template-form').handlers.submit;
  const saved = submit({preventDefault() {}});
  assert.equal(requests[0].path, '/companies/3/reply-templates/12');
  assert.equal(requests[0].method, 'PUT');
  assert.deepEqual(JSON.parse(JSON.stringify(requests[0].body)), {name: 'Saudação', content: 'Olá'});
  requests[0].resolve({id: 12});
  await saved;
  assert.equal(elements.get('reply-template-save-status').textContent, 'Template atualizado.');
  assert.equal(elements.get('reply-template-save').textContent, 'Salvar template');
  assert.equal(elements.get('reply-template-cancel-edit').hidden, true);
  assert.deepEqual(refreshed, ['Template atualizado.', 'list', 'selector']);

  context.beginReplyTemplateEdit({id: 13, name: 'Rascunho', content: 'Texto'});
  elements.get('reply-template-cancel-edit').handlers.click();
  assert.equal(elements.get('reply-template-name').value, '');
  assert.equal(elements.get('reply-template-cancel-edit').hidden, true);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
