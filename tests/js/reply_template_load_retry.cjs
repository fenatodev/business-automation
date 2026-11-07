const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let replyTemplateLoadVersion');
const end = source.indexOf('  async function deleteReplyTemplate', start);
assert(start >= 0 && end > start);

function element() {
  return {
    hidden: false,
    disabled: false,
    textContent: '',
    children: [],
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    addEventListener(event, callback) {
      if (event === 'click') this.click = () => { if (!this.disabled) return callback(); };
    },
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
  };
}

function setup() {
  const elements = new Map();
  const requests = [];
  const context = {
    bearer: 'synthetic-token',
    company: 3,
    $: id => {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    document: {createElement: () => element()},
    templateApi(path, method) {
      let resolve;
      let reject;
      const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
      requests.push({path, method, resolve, reject, promise});
      return promise;
    },
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {context, requests};
}

async function run() {
  const {context, requests} = setup();
  const retry = context.$('reply-template-load-retry');
  const status = context.$('reply-template-load-status');
  const list = context.$('reply-template-list');

  const failedLoad = context.loadReplyTemplateList();
  assert.equal(requests[0].path, '/companies/3/reply-templates');
  assert.equal(requests[0].method, 'GET');
  assert.equal(status.textContent, 'Carregando templates');
  assert.equal(retry.hidden, true);
  requests[0].reject(new Error('private backend details'));
  await failedLoad;
  assert.equal(status.textContent, 'Não foi possível carregar os templates.');
  assert.equal(retry.hidden, false);
  assert.equal(retry.disabled, false);
  assert.equal(status.textContent.includes('private backend details'), false);

  retry.click();
  assert.equal(requests.length, 2);
  assert.equal(status.textContent, 'Carregando templates');
  requests[1].resolve([{id: 7, name: 'Saudação', content: 'Olá'}]);
  await requests[1].promise;
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(status.textContent, '');
  assert.equal(retry.hidden, true);
  assert.equal(list.children.length, 1);
  assert.equal(list.children[0].children[0].children[0].textContent, 'Saudação');

  const staleLoad = context.loadReplyTemplateList();
  const currentLoad = context.loadReplyTemplateList();
  requests[2].resolve([{id: 8, name: 'Obsoleto', content: 'Antigo'}]);
  await staleLoad;
  requests[3].resolve([]);
  await currentLoad;
  assert.equal(list.children.length, 1);
  assert.equal(list.children[0].textContent, 'Nenhum template salvo.');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
