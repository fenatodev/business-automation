const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = script.indexOf('  function buildReviewUrl()');
const end = script.indexOf('  $("rq-refresh").addEventListener', start);
async function run(failedRequest, mode) {
  const elements = new Map();
  const requests = [];
  let fail = true;
  const context = {
    URLSearchParams, bearer: 'synthetic', reviewEpoch: 0, reviewOffset: 50,
    reviewPageSize: 50, reviewTotal: 101, selectedRqIds: new Set([99]),
    $: id => {
      if (!elements.has(id)) elements.set(id, {
        hidden: false, textContent: 'previous', value: '', children: ['previous'],
        attributes: {}, disabled: false,
        setAttribute(k, v) {this.attributes[k] = v;},
        replaceChildren() {this.children = [];},
        append(child) {this.children.push(child);},
        addEventListener(event, fn) {this[event] = fn;},
      });
      return elements.get(id);
    },
    document: {createElement: () => ({})},
    withButton(button, fn) {return fn();},
    async reviewApi(url, method = 'GET') {
      requests.push(url);
      assert.equal(method, 'GET');
      assert.equal(context.$('rq-list').attributes['aria-busy'], 'true');
      const kind = url.includes('/summary') ? 'summary' : url.includes('/aging') ? 'aging' : url.includes('/count') ? 'count' : 'list';
      if (fail && kind === failedRequest) {
        if (mode === 'null') return null;
        if (mode === 'invalid') return {};
        throw new Error('private details');
      }
      return {list: [], summary: {pending: 0, approve: 0, reject: 0},
        aging: {overdue_pending: 0}, count: {total: 0}}[kind];
    },
  };
  vm.createContext(context);
  vm.runInContext(script.slice(start, end), context);
  for (const [id, value] of Object.entries({'rq-status-filter': 'pending',
    'rq-search': ' synthetic & sample ', 'rq-sort': 'status',
    'rq-from-date': '2026-11-01', 'rq-to-date': '2026-11-06'})) context.$(id).value = value;
  assert.equal(await context.refreshReviewQueue(), false);
  assert.equal(context.reviewTotal, 101);
  assert(context.selectedRqIds.has(99));
  assert.equal(context.$('rq-bulk-bar').hidden, false);
  assert.deepEqual(context.$('rq-list').children, ['previous']);
  for (const id of ['rq-count', 'rq-summary', 'rq-aging', 'rq-page']) assert.equal(context.$(id).textContent, 'previous');
  assert.match(context.$('rq-load-status').textContent, /Não foi possível/);
  assert(!context.$('rq-load-status').textContent.includes('private'));
  assert.equal(context.$('rq-load-retry').hidden, false);
  assert.equal(context.$('rq-list').attributes['aria-busy'], 'false');
  fail = false;
  await context.$('rq-load-retry').click();
  assert.deepEqual(requests.slice(4), requests.slice(0, 4));
  const params = new URL(requests[4], 'http://localhost').searchParams;
  assert.equal(params.get('offset'), '50');
  assert.equal(params.get('sort'), 'status');
  assert.equal(params.get('q'), 'synthetic & sample');
  assert.equal(params.get('status'), 'pending');
  assert.equal(params.get('from_date'), '2026-11-01');
  assert.equal(params.get('to_date'), '2026-11-06');
  assert.equal(context.reviewTotal, 0);
  assert.equal(context.selectedRqIds.size, 0);
  assert.equal(context.$('rq-bulk-bar').hidden, true);
  assert.equal(context.$('rq-list').children[0].textContent, 'Nenhum item pendente.');
  assert.equal(context.$('rq-load-status').textContent, '');
  assert.equal(context.$('rq-load-retry').hidden, true);
}
(async () => {
  for (const kind of ['list', 'summary', 'aging', 'count']) {
    for (const mode of ['throw', 'null', 'invalid']) await run(kind, mode);
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
