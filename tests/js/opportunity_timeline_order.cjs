const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  async function loadOpportunityTimeline(');
const end = source.indexOf('  // WP-144', start);
function element() {
  return {children: [], textContent: '', hidden: false, disabled: false, attributes: {}, listeners: {},
    setAttribute(name, value) {this.attributes[name] = value;},
    addEventListener(name, handler) {this.listeners[name] = handler;},
    replaceChildren() {this.children = [];},
    append(...nodes) {this.children.push(...nodes);},
    appendChild(node) {this.children.push(node);}};
}
const event = detail => [{detail, timestamp: '2026-01-01T00:00:00Z'}];
async function run(mode, fails, oldFirst) {
  const list = element(), status = element(), retry = element(), pending = [];
  const elements = {'opp-timeline-list': list, 'opp-timeline-status': status, 'opp-timeline-retry': retry};
  const context = {sessionEpoch: 0, selectionVersion: 1, selectedId: 1,
    $: id => elements[id], document: {createElement: element},
    api: path => new Promise((resolve, reject) => pending.push({path, resolve, reject})),
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  const old = context.loadOpportunityTimeline(1, 1);
  assert.equal(pending[0].path, '/opportunities/1/timeline');
  if (mode === 'session') context.sessionEpoch++;
  else {context.selectionVersion++; context.selectedId = mode === 'close' ? null : 2;}
  if (mode === 'reopen') context.selectedId = 1;
  let current;
  if (mode !== 'close' && mode !== 'session') {
    list.children = [element()];
    current = context.loadOpportunityTimeline(context.selectedId, context.selectionVersion);
    assert.equal(list.children.length, 0, 'previous events cleared on load');
  }
  const snapshot = () => JSON.stringify(list);
  const settleOld = () => fails ? pending[0].reject(new Error('private error')) : pending[0].resolve(event('OLD'));
  if (oldFirst || !current) {
    const before = snapshot(); settleOld(); await old; assert.equal(snapshot(), before);
  }
  if (current) {
    pending[1].resolve(event('CURRENT')); await current;
    assert.equal(list.children[0].children[0].textContent, 'CURRENT');
    if (!oldFirst) {const before = snapshot(); settleOld(); await old; assert.equal(snapshot(), before);}
  }
  const count = pending.length;
  await context.loadOpportunityTimeline(999, -1);
  assert.equal(pending.length, count, 'obsolete selection must not start a request');
  context.selectedId = 3; context.selectionVersion++;
  const empty = context.loadOpportunityTimeline(3, context.selectionVersion);
  pending.at(-1).resolve([]); await empty;
  assert.equal(list.children[0].textContent, 'Nenhuma atividade registrada.');
  const failure = context.loadOpportunityTimeline(3, context.selectionVersion);
  pending.at(-1).reject(new Error('private failure')); await failure;
  assert.equal(list.children.length, 0);
  assert.equal(status.textContent, 'Falha ao carregar atividades da oportunidade.');
  assert.equal(retry.hidden, false);
  assert.equal(retry.disabled, false);
  assert.equal(list.attributes['aria-busy'], 'false');
  const callsBeforeRetry = pending.length;
  const retryRequest = retry.listeners.click();
  assert.equal(pending.length, callsBeforeRetry + 1);
  assert.equal(pending.at(-1).path, '/opportunities/3/timeline');
  assert.equal(retry.hidden, true);
  assert.equal(retry.disabled, true);
  pending.at(-1).resolve(event('RETRIED'));
  await retryRequest;
  assert.equal(list.children[0].children[0].textContent, 'RETRIED');
  assert.equal(status.textContent, '');
  assert.equal(retry.hidden, true);
  assert.equal(retry.disabled, false);
}
(async () => {
  for (const mode of ['switch', 'close', 'reopen', 'session'])
    for (const fails of [false, true])
      for (const oldFirst of [false, true]) await run(mode, fails, oldFirst);
  assert.match(source, /await loadOpportunityTimeline\(id, version\)/);
})().catch(error => {console.error(error); process.exitCode = 1;});
