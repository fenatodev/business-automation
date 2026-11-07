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
    dataset: {}, attributes: {}, handlers: {},
    addEventListener(event, callback) { this.handlers[event] = callback; },
    setAttribute(name, value) { this.attributes[name] = value; },
    appendChild(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
    focus() { this.focused = true; },
    remove() {},
  };
}

const elements = new Map(
  'reply-template-name reply-template-content reply-template-name-count reply-template-content-count reply-template-save reply-template-cancel-edit reply-template-save-status reply-template-search reply-template-search-clear reply-template-filter-status reply-template-list reply-template-load-status reply-template-load-retry'.split(' ').map(id => [id, element()]),
);
const templates = [{id: 7, name: 'Saudação', content: 'Olá, como posso ajudar?'}];
const requests = [];
const notifications = [];
const promptAnswers = [null, '   ', 'Saudação (cópia)'];
let selectorRefreshes = 0;

const context = {
  bearer: 'synthetic-token', company: 3,
  $: id => elements.get(id) || null,
  prompt: () => promptAnswers.shift(),
  confirm: () => true,
  notify: message => notifications.push(message),
  loadReplyTemplates: () => { selectorRefreshes++; },
  updateReplyTemplateCharacterCount() {},
  document: {
    createElement() {
      const child = element();
      child.remove = function () {
        const list = elements.get('reply-template-list');
        const index = list.children.indexOf(this);
        if (index >= 0) list.children.splice(index, 1);
      };
      return child;
    },
  },
  async templateApi(path, method, body) {
    requests.push({path, method, body});
    if (method === 'GET') return templates;
    templates.push({id: 8, ...body});
    return {id: 8, ...body};
  },
};
vm.createContext(context);
vm.runInContext(source.slice(start, end) + '\nthis.loadReplyTemplateList = loadReplyTemplateList;', context);

async function run() {
  await context.loadReplyTemplateList();
  requests.length = 0;
  const item = elements.get('reply-template-list').children[0];
  const duplicateButton = item.children.find(child => child.textContent === 'Duplicar');
  assert.ok(duplicateButton);

  await duplicateButton.handlers.click();
  assert.deepEqual(requests, []);
  assert.equal(elements.get('reply-template-load-status').textContent, '');

  await duplicateButton.handlers.click();
  assert.deepEqual(requests, []);
  assert.equal(elements.get('reply-template-load-status').textContent,
    'Informe um nome de até 100 caracteres.');

  await duplicateButton.handlers.click();
  assert.deepEqual(requests.map(({path, method, body}) => ({
    path, method, body: body ? JSON.parse(JSON.stringify(body)) : null,
  })), [
    {path: '/companies/3/reply-templates', method: 'POST', body: {
      name: 'Saudação (cópia)', content: 'Olá, como posso ajudar?',
    }},
    {path: '/companies/3/reply-templates', method: 'GET', body: null},
  ]);
  assert.equal(elements.get('reply-template-list').children.length, 2);
  assert.equal(elements.get('reply-template-load-status').textContent, '');
  assert.deepEqual(notifications, ['Template duplicado.']);
  assert.equal(selectorRefreshes, 1);
  const refreshedOriginal = elements.get('reply-template-list').children.find(
    child => child.dataset.templateId === '7'
  );
  const refreshedDuplicateButton = refreshedOriginal.children.find(
    child => child.textContent === 'Duplicar'
  );
  assert.equal(refreshedDuplicateButton.focused, true);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
