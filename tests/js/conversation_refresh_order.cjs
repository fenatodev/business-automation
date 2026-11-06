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
  const elements = new Map(), pending = [], renders = [], notices = [];
  let pages = 0;
  const context = {
    URLSearchParams, opportunities: [{company_id: 1}],
    conversations: [{id: 99, status: 'open'}], convTotal: 41,
    selectedConvId: 99, selectedConvIds: new Set([99]),
    convFilterChannel: 'web', convFilterStatus: 'open', convFilterQuery: 'old',
    convFilterCustomerId: '', convFilterLeadId: '3', convFilterFromDate: '',
    convFilterToDate: '', convFilterSort: 'created_at', convPageSize: 20, convOffset: 20,
    $: id => {
      if (!elements.has(id)) elements.set(id, {
        value: '', textContent: '', hidden: false, attributes: {},
        setAttribute(k, v) {this.attributes[k] = v;},
        addEventListener(event, fn) {this[event] = fn;},
      });
      return elements.get(id);
    },
    conversationApi: url => new Promise((resolve, reject) => pending.push({url, resolve, reject})),
    populateCustomerFilter: async () => {}, populateLeadFilter: async () => {},
    showConversationList() {renders.push(context.conversations.map(row => row.id));},
    updateConversationPagination() {pages++;}, updateConvBulkBar() {},
    selectConversation: async () => {throw new Error('Unexpected detail read');},
    withButton(button, fn) {return fn();}, notify(message) {notices.push(message);},
  };
  vm.createContext(context);
  vm.runInContext(section('  function buildConversationUrl(', '  function showConversationList(')
    + section('  let conversationRefreshVersion = 0;', '  function updateConversationPagination()')
    + section('  $("conv-search-btn").addEventListener', '  // WP-196'), context);
  context.$('conv-refresh').click();
  context.$('conv-search-q').value = 'new & sample';
  context.$('conv-search-btn').click();
  assert.equal(context.convOffset, 0);
  const query = new URL(pending[2].url, 'http://localhost').searchParams;
  assert.equal(query.get('q'), 'new & sample');
  assert.equal(query.get('offset'), '0');
  const settle = (index, fails, id) => {
    if (fails && failedRequest === 'list') pending[index].reject(new Error('private failure'));
    else pending[index].resolve([{id, status: 'open'}]);
    if (fails && failedRequest === 'count') pending[index + 1].reject(new Error('private failure'));
    else pending[index + 1].resolve({total: id});
  };
  if (oldFirst) {
    settle(0, oldFails, 99); await tick();
    assert.equal(renders.length, 0);
    assert.equal(context.convTotal, 41);
    assert.equal(context.selectedConvId, 99);
    assert.equal(context.$('conv-list').attributes['aria-busy'], 'true');
    assert.equal(context.$('conv-load-status').textContent, 'Carregando conversas...');
    assert.equal(context.$('conv-load-retry').hidden, true);
  }
  settle(2, newestFails, 2); await tick();
  const snapshot = () => JSON.stringify({renders, pages, total: context.convTotal,
    rows: context.conversations, selection: [...context.selectedConvIds], selected: context.selectedConvId,
    elements: [...elements]});
  const current = snapshot();
  if (!oldFirst) {settle(0, oldFails, 99); await tick();}
  assert.equal(snapshot(), current);
  assert.deepEqual(notices, []);
  assert.equal(context.$('conv-list').attributes['aria-busy'], 'false');
  if (newestFails) {
    assert.equal(renders.length, 0);
    assert.equal(context.convTotal, 41);
    assert.equal(context.selectedConvId, 99);
    assert(context.selectedConvIds.has(99));
    assert.match(context.$('conv-load-status').textContent, /Não foi possível/);
    assert.equal(context.$('conv-load-retry').hidden, false);
    context.$('conv-load-retry').click();
    assert.equal(pending[4].url, pending[2].url);
    settle(4, false, 3); await tick();
    assert.equal(context.convTotal, 3);
    assert.equal(context.$('conv-load-retry').hidden, true);
  } else {
    assert(renders.every(ids => ids.length === 1 && ids[0] === 2));
    assert.equal(pages, 1);
    assert.equal(context.convTotal, 2);
    assert.equal(context.selectedConvId, null);
    assert.equal(context.selectedConvIds.size, 0);
    assert.equal(context.$('conv-open-badge').textContent, 1);
    assert.equal(context.$('conv-load-status').textContent, '');
  }
}
(async () => {
  for (const oldFails of [false, true])
    for (const newestFails of [false, true])
      for (const oldFirst of [false, true])
        for (const failedRequest of ['list', 'count'])
          await run(oldFails, newestFails, oldFirst, failedRequest);
})().catch(error => {console.error(error); process.exitCode = 1;});
