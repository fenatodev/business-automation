const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const section = (start, end) => script.slice(script.indexOf(start), script.indexOf(end, script.indexOf(start)));
const tick = () => new Promise(resolve => setImmediate(resolve));
async function run(oldFails, newestFails, oldFirst) {
  const elements = new Map(), pending = [], renders = [], notices = [];
  let pages = 0;
  const context = {
    bearer: 'synthetic', leadOffset: 50, leadPageSize: 50,
    leadTotal: 101, leadListLength: 1,
    $: id => {
      if (!elements.has(id)) elements.set(id, {
        value: '', textContent: '', hidden: false, attributes: {},
        setAttribute(k, v) {this.attributes[k] = v;},
        addEventListener(event, fn) {this[event] = fn;},
      });
      return elements.get(id);
    },
    leadApi: (url, method) => new Promise((resolve, reject) => {
      assert.equal(method, 'GET'); pending.push({url, resolve, reject});
    }),
    renderLeads(rows) {renders.push(rows.map(row => row.id));},
    updateLeadPagination() {pages++;},
    withButton(button, fn) {return fn();}, notify(message) {notices.push(message);},
  };
  vm.createContext(context);
  vm.runInContext(section('  let leadRefreshVersion = 0;', '  function renderLeads(')
    + section('  $("leads-refresh").addEventListener', '  // WP-100 — Lead pagination'), context);
  context.$('lead-search').value = 'old';
  const old = context.$('leads-refresh').click();
  context.$('lead-search').value = 'new & sample';
  context.$('lead-search').input();
  assert.equal(context.leadOffset, 0);
  assert.equal(new URL(pending[2].url, 'http://localhost').searchParams.get('q'), 'new & sample');
  assert.equal(new URL(pending[2].url, 'http://localhost').searchParams.get('offset'), '0');
  const settle = (index, fails, id) => {
    if (fails) pending[index].reject(new Error('private failure'));
    else pending[index].resolve([{id, status: 'new'}]);
    pending[index + 1].resolve({total: id});
  };
  if (oldFirst) {
    settle(0, oldFails, 99); await old; await tick();
    assert.equal(renders.length, 0);
    assert.equal(context.leadTotal, 101);
    assert.equal(context.$('leads-list').attributes['aria-busy'], 'true');
    assert.equal(context.$('leads-load-status').textContent, 'Carregando leads...');
    assert.equal(context.$('leads-load-retry').hidden, true);
  }
  settle(2, newestFails, 2); await tick();
  const snapshot = () => JSON.stringify({renders, pages, total: context.leadTotal,
    length: context.leadListLength, status: context.$('leads-load-status'),
    retry: context.$('leads-load-retry'), badge: context.$('lead-new-badge')});
  const current = snapshot();
  if (!oldFirst) {settle(0, oldFails, 99); await old; await tick();}
  assert.equal(snapshot(), current);
  assert.deepEqual(notices, []);
  assert.equal(context.$('leads-list').attributes['aria-busy'], 'false');
  if (newestFails) {
    assert.equal(renders.length, 0);
    assert.equal(context.leadTotal, 101);
    assert.match(context.$('leads-load-status').textContent, /Não foi possível/);
    assert.equal(context.$('leads-load-retry').hidden, false);
    const retry = context.$('leads-load-retry').click();
    settle(4, false, 3); await retry; await tick();
    assert.equal(context.leadTotal, 3);
    assert.equal(context.$('leads-load-retry').hidden, true);
  } else {
    assert.deepEqual(renders, [[2]]);
    assert.equal(pages, 1);
    assert.equal(context.leadTotal, 2);
    assert.equal(context.$('lead-new-badge').textContent, 1);
    assert.equal(context.$('leads-load-status').textContent, '');
  }
}
(async () => {
  for (const oldFails of [false, true])
    for (const newestFails of [false, true])
      for (const oldFirst of [false, true]) await run(oldFails, newestFails, oldFirst);
})().catch(error => {console.error(error); process.exitCode = 1;});
