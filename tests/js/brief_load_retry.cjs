const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = script.indexOf('  function buildBriefUrl()');
const end = script.indexOf('  function updateBriefPagination()', start);
async function run(failedRequest, mode) {
  const elements = new Map();
  const requests = [];
  let fail = true;
  let pending;
  const context = {
    populateBriefOpportunityFilter() {},
    URLSearchParams, bearer: 'synthetic', briefEpoch: 0, briefOffset: 50,
    briefPageSize: 50, briefTotal: 101, selectedBriefIds: new Set([99]),
    $: id => {
      if (!elements.has(id)) elements.set(id, {
        hidden: false, textContent: 'previous', value: '', children: ['previous'],
        attributes: {}, disabled: false,
        get firstChild() {return this.children[0];},
        removeChild() {this.children.shift();},
        appendChild(child) {this.children.push(child);},
        setAttribute(k, v) {this.attributes[k] = v;},
        replaceChildren() {this.children = [];},
        append(child) {this.children.push(child);},
        addEventListener(event, fn) {this[event] = fn;},
      });
      return elements.get(id);
    },
    document: {createElement: () => ({setAttribute() {}})},
    withButton(button, fn) {pending = fn(); return pending;},
    async briefApi(url, method = 'GET') {
      requests.push(url);
      assert.equal(method, 'GET');
      assert.equal(context.$('briefs-list').attributes['aria-busy'], 'true');
      const kind = url.includes('/count') ? 'count' : 'list';
      if (fail && kind === failedRequest) {
        if (mode === 'null') return null;
        if (mode === 'invalid') return {};
        throw new Error('private details');
      }
      return {list: [], count: {count: 0}}[kind];
    },
  };
  vm.createContext(context);
  vm.runInContext(script.slice(start, end), context);
  vm.runInContext(script.slice(end, script.indexOf('  // WP-187 — Load and display brief detail', end)), context);
  for (const [id, value] of Object.entries({'briefs-status-filter': 'draft',
    'briefs-opportunity-filter': '7', 'briefs-search': ' synthetic & sample ', 'briefs-sort': 'status',
    'briefs-from-date': '2026-11-01', 'briefs-to-date': '2026-11-06'})) context.$(id).value = value;
  assert.equal(await context.refreshBriefs(), false);
  assert.equal(context.briefTotal, 101);
  assert(context.selectedBriefIds.has(99));
  assert.equal(context.$('briefs-bulk-bar').hidden, false);
  assert.deepEqual(context.$('briefs-list').children, ['previous']);
  for (const id of ['briefs-page-info']) assert.equal(context.$(id).textContent, 'previous');
  assert.match(context.$('briefs-load-status').textContent, /Não foi possível/);
  assert(!context.$('briefs-load-status').textContent.includes('private'));
  assert.equal(context.$('briefs-load-retry').hidden, false);
  assert.equal(context.$('briefs-list').attributes['aria-busy'], 'false');
  fail = false;
  context.$('briefs-load-retry').click();
  await pending;
  assert.deepEqual(requests.slice(2), requests.slice(0, 2));
  const params = new URL(requests[2], 'http://localhost').searchParams;
  assert.equal(params.get('offset'), '50');
  assert.equal(params.get('sort'), 'status');
  assert.equal(params.get('opportunity_id'), '7');
  assert.equal(params.get('q'), 'synthetic & sample');
  assert.equal(params.get('status'), 'draft');
  assert.equal(params.get('from_date'), '2026-11-01');
  assert.equal(params.get('to_date'), '2026-11-06');
  assert.equal(context.briefTotal, 0);
  assert.equal(context.selectedBriefIds.size, 0);
  assert.equal(context.$('briefs-bulk-bar').hidden, true);
  assert.equal(context.$('briefs-list').children[0].textContent, 'Nenhum brief encontrado.');
  assert.equal(context.$('briefs-load-status').textContent, '');
  assert.equal(context.$('briefs-load-retry').hidden, true);
  const deferred = [];
  context.briefApi = () => new Promise(resolve => deferred.push(resolve));
  const older = context.refreshBriefs();
  const newer = context.refreshBriefs();
  deferred[2]([]); deferred[3]({count: 5});
  assert.equal(await newer, true);
  deferred[0]([]); deferred[1]({count: 999});
  assert.equal(await older, false);
  assert.equal(context.briefTotal, 5);
  assert.equal(context.$('briefs-list').attributes['aria-busy'], 'false');
}
(async () => {
  for (const kind of ['list', 'count']) {
    for (const mode of ['throw', 'null', 'invalid']) await run(kind, mode);
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
