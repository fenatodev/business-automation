const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
function section(start, end) {
  const pos = script.indexOf(start);
  assert(pos >= 0);
  const finish = script.indexOf(end, pos);
  assert(finish > pos);
  return script.slice(pos, finish);
}
async function run(failedRequest) {
  const elements = new Map();
  const requests = [];
  const notices = [];
  let fail = true;
  let renders = 0;
  let pages = 0;
  const previous = [{id: 99, status: 'open'}];
  const context = {
    URLSearchParams,
    $: id => {
      if (!elements.has(id)) elements.set(id, {
        hidden: true, textContent: '', attributes: {},
        setAttribute(key, value) {this.attributes[key] = value;},
        addEventListener(event, callback) {this[event] = callback;},
      });
      return elements.get(id);
    },
    opportunities: [{company_id: 1}], conversations: previous, convTotal: 41,
    convFilterChannel: 'web', convFilterStatus: 'open', convFilterQuery: 'synthetic & sample',
    convFilterCustomerId: '', convFilterLeadId: '3', convFilterFromDate: '2026-11-01',
    convFilterToDate: '2026-11-06', convFilterSort: 'created_at', convPageSize: 20,
    convOffset: 20, selectedConvId: 99,
    async conversationApi(url) {
      requests.push(url);
      assert.equal(elements.get('conv-list').attributes['aria-busy'], 'true');
      if (fail && url.includes('/count') === (failedRequest === 'count')) {
        throw new Error('private backend details');
      }
      return url.includes('/count') ? {total: 0} : [];
    },
    populateCustomerFilter: async () => {}, populateLeadFilter: async () => {},
    showConversationList() {renders++;}, updateConversationPagination() {pages++;},
    selectedConvIds: new Set([99]), updateConvBulkBar() {},
    withButton(button, action) {return action();}, notify(message) {notices.push(message);},
  };
  vm.createContext(context);
  vm.runInContext(section('  function buildConversationUrl(', '  function showConversationList(')
    + section('  let conversationRefreshVersion = 0;', '  function updateConversationPagination()')
    + section('  $("conv-refresh").addEventListener', '  // WP-196'), context);
  elements.get('conv-refresh').click();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(context.conversations, previous);
  assert.equal(context.convTotal, 41);
  assert.equal(context.selectedConvId, 99);
  assert.equal(renders, 0);
  assert.equal(pages, 0);
  assert.deepEqual(notices, []);
  assert.match(elements.get('conv-load-status').textContent, /Não foi possível/);
  assert(!elements.get('conv-load-status').textContent.includes('private'));
  assert.equal(elements.get('conv-load-retry').hidden, false);
  assert.equal(elements.get('conv-list').attributes['aria-busy'], 'false');
  fail = false;
  elements.get('conv-load-retry').click();
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(requests.slice(2), requests.slice(0, 2));
  const query = new URL(requests[2], 'http://localhost').searchParams;
  assert.equal(query.get('offset'), '20');
  assert.equal(query.get('lead_id'), '3');
  assert.equal(query.get('q'), 'synthetic & sample');
  assert.equal(query.get('from_date'), '2026-11-01');
  assert.equal(query.get('to_date'), '2026-11-06');
  assert.equal(context.conversations.length, 0);
  assert.equal(context.convTotal, 0);
  assert.equal(context.selectedConvId, null);
  assert.equal(elements.get('conv-detail').hidden, true);
  assert.equal(elements.get('conv-load-status').textContent, '');
  assert.equal(elements.get('conv-load-retry').hidden, true);
  assert.equal(elements.get('conv-list').attributes['aria-busy'], 'false');
  assert(renders > 0);
  assert.equal(pages, 1);
  elements.get('conv-refresh').click();
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(notices, ['Conversas atualizadas.']);
}
(async () => {
  await run('list');
  await run('count');
})().catch(error => {console.error(error); process.exitCode = 1;});
