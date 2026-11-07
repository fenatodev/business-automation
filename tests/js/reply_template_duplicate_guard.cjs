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
    focus() {},
    remove() {},
  };
}

const ids = 'reply-template-name reply-template-content reply-template-name-count reply-template-content-count reply-template-save reply-template-cancel-edit reply-template-save-status reply-template-search reply-template-search-clear reply-template-filter-status reply-template-list reply-template-load-status reply-template-load-retry';
const elements = new Map(ids.split(' ').map(id => [id, element()]));
const templates = [
  {id: 7, name: 'Saudação', content: 'Olá!'},
  {id: 8, name: 'Retorno', content: 'Obrigado!'},
];
const requests = [];
let resolvePost;
const context = {
  bearer: 'synthetic-token', company: 3,
  $: id => elements.get(id) || null,
  prompt: (_message, proposed) => proposed,
  confirm: () => true,
  notify() {},
  loadReplyTemplates() {},
  updateReplyTemplateCharacterCount() {},
  document: {createElement: () => element()},
  async templateApi(path, method, body) {
    requests.push({path, method, body});
    if (method === 'GET') return templates;
    return new Promise(resolve => { resolvePost = resolve; });
  },
};
vm.createContext(context);
vm.runInContext(
  source.slice(start, end) + '\nthis.loadReplyTemplateList = loadReplyTemplateList;',
  context,
);

async function run() {
  await context.loadReplyTemplateList();
  const items = elements.get('reply-template-list').children;
  const firstDuplicate = items[0].children.find(child => child.textContent === 'Duplicar');
  const secondDuplicate = items[1].children.find(child => child.textContent === 'Duplicar');

  const firstRequest = firstDuplicate.handlers.click();
  assert.equal(firstDuplicate.disabled, true);
  assert.equal(secondDuplicate.disabled, true);
  await secondDuplicate.handlers.click();
  assert.equal(requests.filter(request => request.method === 'POST').length, 1);

  resolvePost({id: 9});
  await firstRequest;
  assert.equal(requests.filter(request => request.method === 'POST').length, 1);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
