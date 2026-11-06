const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
function section(start, end) {
  const pos = script.indexOf(start), finish = script.indexOf(end, pos);
  assert(pos >= 0 && finish > pos);
  return script.slice(pos, finish);
}
const tick = () => new Promise(resolve => setImmediate(resolve));
async function run(oldFails, newestFails, oldFirst, failedRequest) {
  const elements = new Map(), pending = [], renders = [];
  let pages = 0;
  const context = {
    URLSearchParams, bearer: 'synthetic', taskOffset: 50, taskPageSize: 50,
    taskTotal: 101, selectedTaskIds: new Set([99]),
    $: id => {
      if (!elements.has(id)) elements.set(id, {
        value: '', textContent: '', hidden: false, attributes: {},
        setAttribute(k, v) {this.attributes[k] = v;},
        addEventListener(event, fn) {this[event] = fn;},
      });
      return elements.get(id);
    },
    taskApi: (url, method = 'GET') => {
      assert.equal(method, 'GET');
      return new Promise((resolve, reject) => pending.push({url, resolve, reject}));
    },
    renderTasks(tasks) {renders.push(tasks.map(row => row.id));},
    updateTaskPagination() {pages++;},
    withButton(button, fn) {return fn();},
  };
  vm.createContext(context);
  vm.runInContext(section('  function buildTaskUrl()', '  function renderTasks(')
    + section('  $("tasks-load-retry").addEventListener', '  // WP-155 — task date filter listeners'), context);
  context.$('task-sort').value = 'attempts';
  context.$('task-status-filter').value = 'failed';
  context.$('task-from-date').value = '2026-11-01';
  context.$('task-to-date').value = '2026-11-06';
  context.$('tasks-refresh').click();
  context.$('task-search').value = 'new & sample';
  context.$('task-search').input();
  assert.equal(context.taskOffset, 0);
  const query = new URL(pending[2].url, 'http://localhost').searchParams;
  for (const [key, value] of Object.entries({q: 'new & sample', offset: '0',
    sort: 'attempts', status: 'failed', from_date: '2026-11-01', to_date: '2026-11-06'})) {
    assert.equal(query.get(key), value);
  }
  const settle = (index, fails, id) => {
    if (fails && failedRequest === 'list') pending[index].reject(new Error('private failure'));
    else pending[index].resolve([{id}]);
    if (fails && failedRequest === 'count') pending[index + 1].reject(new Error('private failure'));
    else pending[index + 1].resolve(id);
  };
  if (oldFirst) {
    settle(0, oldFails, 99); await tick();
    assert.equal(renders.length, 0);
    assert.equal(context.taskTotal, 101);
    assert(context.selectedTaskIds.has(99));
    assert.equal(context.$('tasks-list').attributes['aria-busy'], 'true');
    assert.equal(context.$('tasks-load-status').textContent, 'Carregando tarefas...');
    assert.equal(context.$('tasks-load-retry').hidden, true);
  }
  settle(2, newestFails, 2); await tick();
  const snapshot = () => JSON.stringify({renders, pages, total: context.taskTotal,
    selection: [...context.selectedTaskIds], elements: [...elements]});
  const current = snapshot();
  if (!oldFirst) {settle(0, oldFails, 99); await tick();}
  assert.equal(snapshot(), current);
  assert.equal(context.$('tasks-list').attributes['aria-busy'], 'false');
  if (newestFails) {
    assert.equal(renders.length, 0);
    assert.equal(context.taskTotal, 101);
    assert(context.selectedTaskIds.has(99));
    assert.equal(context.$('task-bulk-bar').hidden, false);
    assert.match(context.$('tasks-load-status').textContent, /Não foi possível/);
    assert(!context.$('tasks-load-status').textContent.includes('private'));
    assert.equal(context.$('tasks-load-retry').hidden, false);
    context.$('tasks-load-retry').click();
    assert.equal(pending[4].url, pending[2].url);
    assert.equal(pending[5].url, pending[3].url);
    settle(4, false, 3); await tick();
    assert.equal(context.taskTotal, 3);
    assert.equal(context.$('tasks-load-retry').hidden, true);
  } else {
    assert.deepEqual(renders, [[2]]);
    assert.equal(pages, 1);
    assert.equal(context.taskTotal, 2);
    assert.equal(context.selectedTaskIds.size, 0);
    assert.equal(context.$('task-bulk-bar').hidden, true);
    assert.equal(context.$('tasks-load-status').textContent, '');
  }
}
(async () => {
  for (const oldFails of [false, true])
    for (const newestFails of [false, true])
      for (const oldFirst of [false, true])
        for (const failedRequest of ['list', 'count'])
          await run(oldFails, newestFails, oldFirst, failedRequest);
})().catch(error => {console.error(error); process.exitCode = 1;});
