const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
function section(start, end) {
  const pos = script.indexOf(start);
  const finish = script.indexOf(end, pos);
  assert(pos >= 0 && finish > pos);
  return script.slice(pos, finish);
}
async function run(failedRequest, failureMode) {
  const elements = new Map();
  const requests = [];
  const notices = [];
  let fail = true;
  let renders = 0;
  let pages = 0;
  const context = {
    URLSearchParams, bearer: 'synthetic', customerOffset: 50, customerPageSize: 50,
    customerTotal: 101, selectedCustomerIds: new Set([99]), currentCustomerId: 99,
    $: id => {
      if (!elements.has(id)) elements.set(id, {
        hidden: false, textContent: '', value: '', attributes: {},
        setAttribute(key, value) {this.attributes[key] = value;},
        addEventListener(event, callback) {this[event] = callback;},
      });
      return elements.get(id);
    },
    async customerApi(url, method) {
      requests.push(url);
      assert.equal(method, 'GET');
      assert.equal(elements.get('customers-list').attributes['aria-busy'], 'true');
      if (fail && url.includes('/count') === (failedRequest === 'count')) {
        if (failureMode === 'null') return null;
        throw new Error('private backend details');
      }
      return url.includes('/count') ? {total: 0} : [];
    },
    renderCustomers(data) {renders++; assert.equal(data.length, 0);},
    updateCustomerPagination() {pages++;},
    withButton(button, action) {return action();}, notify(message) {notices.push(message);},
  };
  vm.createContext(context);
  vm.runInContext(section('  function buildCustomerUrl()', '  async function customerApi(')
    + section('  let customerRefreshVersion = 0;', '  function updateCustomerPagination()')
    + section('  $("customers-refresh").addEventListener', '  // WP-104 — Customer search'), context);
  for (const [id, value] of Object.entries({
    'customer-search': ' synthetic & sample ', 'customer-sort': 'name',
    'customer-from-date': '2026-11-01', 'customer-to-date': '2026-11-06',
  })) context.$(id).value = value;
  await context.refreshCustomers();
  assert.equal(context.customerTotal, 101);
  assert.equal(context.currentCustomerId, 99);
  assert(context.selectedCustomerIds.has(99));
  assert.equal(elements.get('customer-bulk-bar'), undefined);
  assert.equal(renders, 0);
  assert.equal(pages, 0);
  assert.match(elements.get('customers-load-status').textContent, /Não foi possível/);
  assert(!elements.get('customers-load-status').textContent.includes('private'));
  assert.equal(elements.get('customers-load-retry').hidden, false);
  assert.equal(elements.get('customers-list').attributes['aria-busy'], 'false');
  // The actual refresh button must not announce success on failure.
  await elements.get('customers-refresh').click();
  assert.deepEqual(notices, []);
  context.customerOffset = 50;
  const retryStart = requests.length;
  fail = false;
  elements.get('customers-load-retry').click();
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(requests.slice(retryStart), requests.slice(0, 2));
  const query = new URL(requests[retryStart], 'http://localhost').searchParams;
  assert.equal(query.get('offset'), '50');
  assert.equal(query.get('sort'), 'name');
  assert.equal(query.get('q'), 'synthetic & sample');
  assert.equal(query.get('from_date'), '2026-11-01');
  assert.equal(query.get('to_date'), '2026-11-06');
  assert.equal(context.customerTotal, 0);
  assert.equal(context.selectedCustomerIds.size, 0);
  assert.equal(elements.get('customer-bulk-bar').hidden, true);
  assert.equal(renders, 1);
  assert.equal(pages, 1);
  assert.equal(elements.get('customers-load-status').textContent, '');
  assert.equal(elements.get('customers-load-retry').hidden, true);
  assert.equal(elements.get('customers-list').attributes['aria-busy'], 'false');
  await elements.get('customers-refresh').click();
  assert.deepEqual(notices, ['Customers atualizados.']);
}
(async () => {
  for (const request of ['list', 'count']) {
    for (const mode of ['throw', 'null']) await run(request, mode);
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
