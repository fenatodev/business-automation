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
  let fail = true;
  let renders = 0;
  let pages = 0;
  const context = {
    URLSearchParams, bearer: 'synthetic', taskOffset: 50, taskPageSize: 50,
    taskTotal: 101, selectedTaskIds: new Set([99]),
    $: id => {
      if (!elements.has(id)) elements.set(id, {
        hidden: false, textContent: '', value: '', attributes: {},
        setAttribute(key, value) {this.attributes[key] = value;},
        addEventListener(event, callback) {this[event] = callback;},
      });
      return elements.get(id);
    },
    async taskApi(url, method = 'GET') {
      requests.push(url);
      assert.equal(method, 'GET');
      assert.equal(elements.get('tasks-list').attributes['aria-busy'], 'true');
      assert.match(elements.get('tasks-load-status').textContent, /Carregando/);
      if (fail && url.includes('/count') === (failedRequest === 'count')) {
        if (failureMode === 'null') return null;
        if (failureMode === 'invalid') return url.includes('/count') ? -1 : {};
        throw new Error('private backend details');
      }
      return url.includes('/count') ? 0 : [];
    },
    renderTasks(data) {renders++; assert.equal(data.length, 0);},
    updateTaskPagination() {pages++;},
    withButton(button, action) {return action();},
  };
  vm.createContext(context);
  vm.runInContext(section('  function buildTaskUrl()', '  function renderTasks(')
    + section('  $("tasks-load-retry").addEventListener', '  $("task-status-filter").addEventListener'), context);
  for (const [id, value] of Object.entries({
    'task-status-filter': 'failed', 'task-search': ' synthetic & sample ',
    'task-sort': 'attempts', 'task-from-date': '2026-11-01', 'task-to-date': '2026-11-06',
  })) context.$(id).value = value;
  assert.equal(await context.refreshTasks(), false);
  assert.equal(context.taskTotal, 101);
  assert(context.selectedTaskIds.has(99));
  assert.equal(context.$('task-bulk-bar').hidden, false);
  assert.equal(renders, 0);
  assert.equal(pages, 0);
  assert.match(elements.get('tasks-load-status').textContent, /Não foi possível/);
  assert(!elements.get('tasks-load-status').textContent.includes('private'));
  assert.equal(elements.get('tasks-load-retry').hidden, false);
  assert.equal(elements.get('tasks-list').attributes['aria-busy'], 'false');
  const retryStart = requests.length;
  fail = false;
  elements.get('tasks-load-retry').click();
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(requests.slice(retryStart), requests.slice(0, 2));
  const query = new URL(requests[retryStart], 'http://localhost').searchParams;
  assert.equal(query.get('offset'), '50');
  assert.equal(query.get('sort'), 'attempts');
  assert.equal(query.get('status'), 'failed');
  assert.equal(query.get('q'), 'synthetic & sample');
  assert.equal(query.get('from_date'), '2026-11-01');
  assert.equal(query.get('to_date'), '2026-11-06');
  assert.equal(context.taskTotal, 0);
  assert.equal(context.selectedTaskIds.size, 0);
  assert.equal(elements.get('task-bulk-bar').hidden, true);
  assert.equal(renders, 1);
  assert.equal(pages, 1);
  assert.equal(elements.get('tasks-load-status').textContent, '');
  assert.equal(elements.get('tasks-load-retry').hidden, true);
  assert.equal(elements.get('tasks-list').attributes['aria-busy'], 'false');
}
(async () => {
  for (const request of ['list', 'count']) {
    for (const mode of ['throw', 'null', 'invalid']) await run(request, mode);
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
