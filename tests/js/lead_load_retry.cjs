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
    URLSearchParams, bearer: 'synthetic', leadOffset: 50, leadPageSize: 50,
    leadListLength: 7, leadTotal: 101, selectedLeadIds: new Set([99]), currentLeadId: 99,
    $: id => {
      if (!elements.has(id)) elements.set(id, {
        hidden: false, textContent: '', value: '', attributes: {},
        setAttribute(key, value) {this.attributes[key] = value;},
        addEventListener(event, callback) {this[event] = callback;},
      });
      return elements.get(id);
    },
    async leadApi(url, method) {
      requests.push(url);
      assert.equal(method, 'GET');
      assert.equal(elements.get('leads-list').attributes['aria-busy'], 'true');
      if (fail && url.includes('/count') === (failedRequest === 'count')) {
        if (failureMode === 'null') return null;
        throw new Error('private backend details');
      }
      return url.includes('/count') ? {total: 0} : [];
    },
    renderLeads(data) {renders++; assert.equal(data.length, 0);},
    updateLeadPagination() {pages++;},
    withButton(button, action) {return action();}, notify(message) {notices.push(message);},
  };
  vm.createContext(context);
  vm.runInContext(section('  async function refreshLeads()', '  function renderLeads(')
    + section('  $("leads-refresh").addEventListener', '  // WP-099 — Lead search'), context);
  for (const [id, value] of Object.entries({
    'lead-filter-status': 'new', 'lead-filter-source': 'synthetic',
    'lead-search': ' synthetic & sample ', 'lead-sort': 'name',
    'lead-from-date': '2026-11-01', 'lead-to-date': '2026-11-06',
  })) context.$(id).value = value;
  await context.refreshLeads();
  assert.equal(context.leadTotal, 101);
  assert.equal(context.currentLeadId, 99);
  assert(context.selectedLeadIds.has(99));
  assert.equal(elements.get('lead-new-badge'), undefined);
  assert.equal(context.leadListLength, 7);
  assert.equal(renders, 0);
  assert.equal(pages, 0);
  assert.match(elements.get('leads-load-status').textContent, /Não foi possível/);
  assert(!elements.get('leads-load-status').textContent.includes('private'));
  assert.equal(elements.get('leads-load-retry').hidden, false);
  assert.equal(elements.get('leads-list').attributes['aria-busy'], 'false');
  // The actual refresh button must not announce success on failure.
  await elements.get('leads-refresh').click();
  assert.deepEqual(notices, []);
  context.leadOffset = 50;
  const retryStart = requests.length;
  fail = false;
  elements.get('leads-load-retry').click();
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(requests.slice(retryStart), requests.slice(0, 2));
  const query = new URL(requests[retryStart], 'http://localhost').searchParams;
  assert.equal(query.get('offset'), '50');
  assert.equal(query.get('sort'), 'name');
  assert.equal(query.get('status'), 'new');
  assert.equal(query.get('source'), 'synthetic');
  assert.equal(query.get('q'), 'synthetic & sample');
  assert.equal(query.get('from_date'), '2026-11-01');
  assert.equal(query.get('to_date'), '2026-11-06');
  assert.equal(context.leadTotal, 0);
  assert.equal(context.leadListLength, 0);
  assert.equal(elements.get('lead-new-badge').hidden, true);
  assert.equal(renders, 1);
  assert.equal(pages, 1);
  assert.equal(elements.get('leads-load-status').textContent, '');
  assert.equal(elements.get('leads-load-retry').hidden, true);
  assert.equal(elements.get('leads-list').attributes['aria-busy'], 'false');
  await elements.get('leads-refresh').click();
  assert.deepEqual(notices, ['Leads atualizados.']);
}
(async () => {
  for (const request of ['list', 'count']) {
    for (const mode of ['throw', 'null']) await run(request, mode);
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
