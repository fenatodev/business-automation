const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  // WP-265 — Reply templates management');
const end = source.indexOf('\n})();', start);
assert(start >= 0 && end > start);

function element() {
  return {
    value: '', textContent: '', hidden: false, disabled: false, children: [],
    dataset: {}, attributes: {}, handlers: {}, className: '',
    addEventListener(event, callback) { this.handlers[event] = callback; },
    setAttribute(name, value) { this.attributes[name] = value; },
    appendChild(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
    focus() { this.focused = true; },
    remove() {},
    querySelector(selector) {
      return this.children.find(child => child.className === selector.slice(1)) || null;
    },
  };
}

const ids = 'reply-template-name reply-template-content reply-template-name-count reply-template-content-count reply-template-save reply-template-cancel-edit reply-template-save-status reply-template-search reply-template-search-clear reply-template-filter-status reply-template-list reply-template-load-status reply-template-load-retry';
const elements = new Map(ids.split(' ').map(id => [id, element()]));
const templates = [
  {id: 7, name: 'Saudação', content: 'Olá!'},
  {id: 8, name: 'Retorno', content: 'Obrigado!'},
];
const context = {
  bearer: 'synthetic-token', company: 3,
  $: id => elements.get(id) || null,
  prompt: (_message, proposed) => proposed,
  confirm: () => true,
  notify() {},
  loadReplyTemplates() {},
  updateReplyTemplateCharacterCount() {},
  document: {createElement: () => element()},
  async templateApi(_path, method, body) {
    if (method === 'GET') return templates;
    templates.push({id: 9, ...body});
    return {id: 9, ...body};
  },
};
vm.createContext(context);
vm.runInContext(
  source.slice(start, end) +
  '\nthis.loadReplyTemplateList = loadReplyTemplateList; this.beginReplyTemplateEdit = beginReplyTemplateEdit; this.duplicateReplyTemplate = duplicateReplyTemplate;',
  context,
);

async function run() {
  await context.loadReplyTemplateList();
  context.beginReplyTemplateEdit(templates[0]);
  elements.get('reply-template-name').value = 'Rascunho mantido';
  const otherItem = elements.get('reply-template-list').children.find(
    item => item.dataset.templateId === '8'
  );
  const otherDuplicateButton = otherItem.children.find(
    child => child.textContent === 'Duplicar'
  );

  await context.duplicateReplyTemplate(templates[1], otherDuplicateButton);

  const editedItem = elements.get('reply-template-list').children.find(
    item => item.dataset.templateId === '7'
  );
  assert.equal(elements.get('reply-template-name').value, 'Rascunho mantido');
  assert.equal(editedItem.children.find(child => child.textContent === 'Editar').disabled, true);
  assert.equal(editedItem.children.find(child => child.textContent === 'Excluir').disabled, true);
  assert.equal(editedItem.children.find(child => child.textContent === 'Duplicar').disabled, true);

  const otherRefreshedItem = elements.get('reply-template-list').children.find(
    item => item.dataset.templateId === '8'
  );
  assert.equal(otherRefreshedItem.children.find(child => child.textContent === 'Editar').disabled, true);
  assert.equal(otherRefreshedItem.children.find(child => child.textContent === 'Excluir').disabled, false);
  assert.equal(otherRefreshedItem.children.find(child => child.textContent === 'Duplicar').disabled, false);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
