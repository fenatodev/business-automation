const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const section = (start, end) => script.slice(script.indexOf(start), script.indexOf(end, script.indexOf(start)));
const tick = () => new Promise(resolve => setImmediate(resolve));
async function run(oldFails, newestFails, oldFirst, failedRequest) {
  const elements = new Map(), pending = [], renders = [], notices = [];
  let pages = 0;
  const context = {
    URLSearchParams, selectedCustomerIds: new Set([99]), bearer: 'synthetic', customerOffset: 50, customerPageSize: 50,
    customerTotal: 101, customerListLength: 1,
    $: id => {
      if (!elements.has(id)) elements.set(id, {
        value: '', textContent: '', hidden: false, attributes: {},
        setAttribute(k, v) {this.attributes[k] = v;},
        addEventListener(event, fn) {this[event] = fn;},
      });
      return elements.get(id);
    },
    customerApi: (url, method) => new Promise((resolve, reject) => {
      assert.equal(method, 'GET'); pending.push({url, resolve, reject});
    }),
    renderCustomers(rows) {renders.push(rows.map(row => row.id));},
    updateCustomerPagination() {pages++;},
    withButton(button, fn) {return fn();}, notify(message) {notices.push(message);},
  };
  vm.createContext(context);
  vm.runInContext(section('  function buildCustomerUrl()', '  async function customerApi(')
    + section('  let customerRefreshVersion = 0;', '  function updateCustomerPagination()')
    + section('  $("customers-refresh").addEventListener', '  $("customer-detail-back").addEventListener'), context);
  context.$('customer-search').value = 'old';
  const old = context.$('customers-refresh').click();
  context.$('customer-search').value = 'new & sample';
  context.$('customer-search').input();
  assert.equal(context.customerOffset, 0);
  assert.equal(new URL(pending[2].url, 'http://localhost').searchParams.get('q'), 'new & sample');
  assert.equal(new URL(pending[2].url, 'http://localhost').searchParams.get('offset'), '0');
  const settle = (index, fails, id) => {
    if (fails && failedRequest === 'list') pending[index].reject(new Error('private failure'));
    else pending[index].resolve([{id}]);
    if (fails && failedRequest === 'count') pending[index + 1].reject(new Error('private failure'));
    else pending[index + 1].resolve({total: id});
  };
  if (oldFirst) {
    settle(0, oldFails, 99); await old; await tick();
    assert.equal(renders.length, 0);
    assert.equal(context.customerTotal, 101);
    assert(context.selectedCustomerIds.has(99));
    assert.equal(context.$('customers-list').attributes['aria-busy'], 'true');
    assert.equal(context.$('customers-load-status').textContent, 'Carregando clientes...');
    assert.equal(context.$('customers-load-retry').hidden, true);
  }
  settle(2, newestFails, 2); await tick();
  const snapshot = () => JSON.stringify({renders, pages, total: context.customerTotal,
    selection: [...context.selectedCustomerIds], status: context.$('customers-load-status'),
    retry: context.$('customers-load-retry'), bulk: context.$('customer-bulk-bar')});
  const current = snapshot();
  if (!oldFirst) {settle(0, oldFails, 99); await old; await tick();}
  assert.equal(snapshot(), current);
  assert.deepEqual(notices, []);
  assert.equal(context.$('customers-list').attributes['aria-busy'], 'false');
  if (newestFails) {
    assert.equal(renders.length, 0);
    assert.equal(context.customerTotal, 101);
    assert(context.selectedCustomerIds.has(99));
    assert.match(context.$('customers-load-status').textContent, /Não foi possível/);
    assert.equal(context.$('customers-load-retry').hidden, false);
    const retry = context.$('customers-load-retry').click();
    settle(4, false, 3); await retry; await tick();
    assert.equal(context.customerTotal, 3);
    assert.equal(context.$('customers-load-retry').hidden, true);
  } else {
    assert.deepEqual(renders, [[2]]);
    assert.equal(pages, 1);
    assert.equal(context.customerTotal, 2);
    assert.equal(context.selectedCustomerIds.size, 0);
    assert.equal(context.$('customers-load-status').textContent, '');
  }
}
(async () => {
  for (const oldFails of [false, true])
    for (const newestFails of [false, true])
      for (const oldFirst of [false, true])
        for (const failedRequest of ['list', 'count'])
          await run(oldFails, newestFails, oldFirst, failedRequest);
})().catch(error => {console.error(error); process.exitCode = 1;});
