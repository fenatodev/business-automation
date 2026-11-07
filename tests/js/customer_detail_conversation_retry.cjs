const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let customerConversationsVersion = 0;');
const end = source.indexOf('  // WP-110 — Edit customer', start);
assert(start >= 0 && end > start);

function element() {
  return {
    hidden: false,
    children: [],
    textContent: '',
    style: {},
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
    addEventListener(event, callback) { this[event] = callback; },
  };
}

function setup() {
  const elements = new Map();
  const requests = [];
  const context = {
    bearer: 'synthetic',
    sessionEpoch: 1,
    opportunities: [{company_id: 5}],
    currentCustomerId: null,
    customerSelectionVersion: 0,
    URLSearchParams,
    console: {error() {}},
    $: id => {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    document: {createElement: element},
    hideCustomerEditForm() {},
    conversationApi(url) {
      const params = new URL(url, 'http://localhost').searchParams;
      assert.equal(params.get('customer_id') !== null, true);
      let resolve;
      let reject;
      const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
      requests.push({customerId: params.get('customer_id'), resolve, reject, promise});
      return promise;
    },
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
  const firstLoad = context.showCustomerDetail({id: 9, name: 'Synthetic customer'});
  assert.equal(requests[0].customerId, '9');
  requests[0].reject(new Error('private backend details'));
  await firstLoad;
  assert.match(elements.get('customer-conversations-status').textContent, /Não foi possível carregar/);
  assert(!elements.get('customer-conversations-status').textContent.includes('private'));
  assert.equal(elements.get('customer-conversations-retry').hidden, false);

  elements.get('customer-conversations-retry').click();
  assert.equal(requests.length, 2);
  assert.equal(requests[1].customerId, '9');
  assert.equal(elements.get('customer-conversations-retry').hidden, true);
  await settle(requests[1], () => requests[1].resolve([
    {id: 17, channel: 'web', status: 'open'},
  ]));
  assert.equal(elements.get('customer-conversations-status').textContent, '');
  assert.equal(elements.get('customer-conversations-list').children.length, 1);
  assert.equal(elements.get('customer-conversations-list').children[0].children[0].children[0].textContent, 'web');

  const emptyLoad = context.showCustomerDetail({id: 13, name: 'Empty synthetic customer'});
  requests[2].resolve([]);
  await emptyLoad;
  assert.equal(elements.get('customer-conversations-retry').hidden, true);
  assert.equal(elements.get('customer-conversations-list').children[0].textContent, 'Nenhuma conversa encontrada.');

  const staleLoad = context.showCustomerDetail({id: 10, name: 'Another synthetic customer'});
  const currentLoad = context.showCustomerDetail({id: 11, name: 'Current synthetic customer'});
  requests[4].resolve([{id: 19, channel: 'email', status: 'closed'}]);
  await currentLoad;
  requests[3].resolve([{id: 18, channel: 'web', status: 'open'}]);
  await staleLoad;
  assert.equal(elements.get('customer-conversations-list').children[0].children[0].children[0].textContent, 'email');

  const malformedLoad = context.showCustomerDetail({id: 12, name: 'Synthetic customer'});
  requests[5].resolve(null);
  await malformedLoad;
  assert.equal(elements.get('customer-conversations-retry').hidden, false);
  assert.match(elements.get('customer-conversations-status').textContent, /Não foi possível carregar/);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
