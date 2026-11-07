const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let replyTemplateSaving = false;');
const end = source.indexOf('\n})();', start);
assert(start >= 0 && end > start);

function element(value = '') {
  return {
    value, textContent: '', disabled: false, hidden: false, children: [],
    dataset: {}, attributes: {}, focused: false,
    addEventListener(event, callback) { if (event === 'submit') this.submit = callback; },
    setAttribute(name, value) { this.attributes[name] = value; },
    focus() { this.focused = true; },
  };
}

function setup({matchesSearch}) {
  const elements = new Map([
    ['reply-template-form', element()],
    ['reply-template-name', element('Nome atualizado')],
    ['reply-template-content', element('Conteúdo atualizado')],
    ['reply-template-save', element()],
    ['reply-template-cancel-edit', element()],
    ['reply-template-save-status', element()],
    ['reply-template-search', element('nome antigo')],
    ['reply-template-list', element()],
  ]);
  elements.get('reply-template-form').reset = () => {
    elements.get('reply-template-name').value = '';
    elements.get('reply-template-content').value = '';
  };
  const editedItem = element();
  editedItem.className = 'reply-template-item';
  editedItem.dataset.templateId = '42';
  editedItem.hidden = !matchesSearch;
  const editButton = element();
  editButton.className = 'secondary reply-template-edit';
  editedItem.children.push(editButton);
  const list = elements.get('reply-template-list');
  const requests = [];
  const context = {
    bearer: 'synthetic-token', company: 3,
    $(id) { return elements.get(id) || null; },
    updateReplyTemplateCharacterCount() {},
    templateApi(path, method, body) {
      requests.push({path, method, body});
      return Promise.resolve({id: 42, name: body.name, content: body.content});
    },
    notify() {},
    async loadReplyTemplateList() { list.children = [editedItem]; },
    loadReplyTemplates() {},
    applyReplyTemplateFilter() {
      if (elements.get('reply-template-search').value === '') editedItem.hidden = false;
    },
  };
  vm.createContext(context);
  vm.runInContext(
    'let editingReplyTemplateId = 42; function resetReplyTemplateForm() { editingReplyTemplateId = null; $("reply-template-form").reset(); }\n' +
      source.slice(start, end),
    context,
  );
  return {elements, requests, editedItem, editButton};
}

async function submit(result) {
  await result.elements.get('reply-template-form').submit({preventDefault() {}});
}

async function run() {
  const hidden = setup({matchesSearch: false});
  await submit(hidden);
  assert.equal(hidden.requests[0].method, 'PUT');
  assert.equal(hidden.requests[0].path, '/companies/3/reply-templates/42');
  assert.equal(hidden.elements.get('reply-template-search').value, '');
  assert.equal(hidden.editedItem.hidden, false);
  assert.equal(hidden.editButton.focused, true);

  const visible = setup({matchesSearch: true});
  await submit(visible);
  assert.equal(visible.elements.get('reply-template-search').value, 'nome antigo');
  assert.equal(visible.editedItem.hidden, false);
  assert.equal(visible.editButton.focused, true);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
