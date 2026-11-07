const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  // WP-142 — Load conversations related to the selected opportunity');
const end = source.indexOf('  // WP-143 — Load activity timeline', start);
assert(start >= 0 && end > start);

function element() {
  return {
    hidden: false,
    disabled: false,
    children: [],
    attributes: {},
    textContent: '',
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
    append(...children) { this.children.push(...children); },
    setAttribute(name, value) { this.attributes[name] = value; },
    addEventListener(event, callback) {
      this[event] = callback;
      if (event === 'click') this.click = () => { if (!this.disabled) return callback(); };
    },
  };
}

function setup() {
  const elements = new Map();
  const requests = [];
  const context = {
    selectionVersion: 4,
    selectedId: 12,
    $: id => {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    document: {createElement: element},
    api(path) {
      let resolve;
      let reject;
      const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
      requests.push({path, resolve, reject, promise});
      return promise;
    },
    conversationApi: async () => ({total: 2}),
    workspaceObserver: {disconnect() {}},
    refreshConversations: async () => {},
    selectConversation: async () => {},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {context, elements, requests};
}

async function settle(request, action) {
  action();
  await request.promise.catch(() => {});
  await new Promise(resolve => setImmediate(resolve));
}

async function run() {
  const {context, elements, requests} = setup();
  const list = context.$('opp-conv-list');
  const status = context.$('opp-conv-status');
  const retry = context.$('opp-conv-retry');

  const failedLoad = context.loadOpportunityConversations(12, 4);
  assert.equal(requests[0].path, '/opportunities/12/linked-conversations');
  assert.equal(status.textContent, 'Carregando conversas…');
  assert.equal(retry.hidden, true);
  assert.equal(retry.disabled, true);
  assert.equal(list.attributes['aria-busy'], 'true');
  requests[0].reject(new Error('private backend details'));
  await failedLoad;
  assert.match(status.textContent, /Falha ao carregar/);
  assert(!status.textContent.includes('private'));
  assert.equal(retry.hidden, false);
  assert.equal(retry.disabled, false);
  assert.equal(list.attributes['aria-busy'], 'false');

  retry.click();
  retry.click();
  assert.equal(requests.length, 2);
  assert.equal(requests[1].path, '/opportunities/12/linked-conversations');
  assert.equal(retry.hidden, true);
  assert.equal(retry.disabled, true);
  await settle(requests[1], () => requests[1].resolve([
    {id: 21, channel: 'web', status: 'open'},
  ]));
  assert.equal(status.textContent, '');
  assert.equal(retry.disabled, false);
  assert.equal(list.children.length, 1);
  assert.equal(list.children[0].children[0].textContent, '#21 · web');

  const emptyLoad = context.loadOpportunityConversations(12, 4);
  requests[2].resolve([]);
  await emptyLoad;
  assert.equal(retry.hidden, true);
  assert.equal(retry.disabled, false);
  assert.equal(list.children[0].textContent, 'Nenhuma conversa registrada.');

  const staleLoad = context.loadOpportunityConversations(12, 4);
  context.selectionVersion = 5;
  context.selectedId = 13;
  requests[3].resolve([{id: 22, channel: 'email', status: 'closed'}]);
  await staleLoad;
  assert.equal(list.children[0].textContent, 'Nenhuma conversa registrada.');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
