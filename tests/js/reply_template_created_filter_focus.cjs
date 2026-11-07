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
    ['reply-template-name', element('Nova resposta')],
    ['reply-template-content', element('Conteúdo sintético')],
    ['reply-template-save', element()],
    ['reply-template-cancel-edit', element()],
    ['reply-template-save-status', element()],
    ['reply-template-search', element('termo antigo')],
    ['reply-template-list', element()],
  ]);
  elements.get('reply-template-form').reset = () => {
    elements.get('reply-template-name').value = '';
    elements.get('reply-template-content').value = '';
  };
  const createdItem = element();
  createdItem.className = 'reply-template-item';
  createdItem.dataset.templateId = '42';
  createdItem.hidden = !matchesSearch;
  const editButton = element();
  editButton.className = 'secondary reply-template-edit';
  createdItem.children.push(editButton);
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
    async loadReplyTemplateList() { list.children = [createdItem]; },
    loadReplyTemplates() {},
    applyReplyTemplateFilter() {
      if (elements.get('reply-template-search').value === '') createdItem.hidden = false;
    },
  };
  vm.createContext(context);
  vm.runInContext(
    'let editingReplyTemplateId = null; let editingReplyTemplateOriginal = null;\n' +
      'function resetReplyTemplateForm() { $("reply-template-form").reset(); }\n' +
      source.slice(start, end),
    context,
  );
  return {elements, requests, createdItem, editButton};
}

async function submit(setupResult) {
  await setupResult.elements.get('reply-template-form').submit({preventDefault() {}});
}

async function run() {
  const hidden = setup({matchesSearch: false});
  await submit(hidden);
  assert.equal(hidden.requests[0].method, 'POST');
  assert.equal(hidden.requests[0].path, '/companies/3/reply-templates');
  assert.equal(hidden.elements.get('reply-template-search').value, '');
  assert.equal(hidden.createdItem.hidden, false);
  assert.equal(hidden.editButton.focused, true);

  const visible = setup({matchesSearch: true});
  await submit(visible);
  assert.equal(visible.elements.get('reply-template-search').value, 'termo antigo');
  assert.equal(visible.createdItem.hidden, false);
  assert.equal(visible.editButton.focused, true);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
