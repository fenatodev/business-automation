const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = script.indexOf('  // WP-187 — Load and display brief detail');
const end = script.indexOf('  // WP-184 — Bulk status handlers', start);
function element() {
  return {hidden: true, dataset: {}, children: [], style: {}, textContent: '',
    get firstChild() {return this.children[0];},
    appendChild(child) {this.children.push(child);},
    removeChild() {this.children.shift();},
    addEventListener(event, fn) {this[event] = fn;}};
}
async function run(mode, fails, oldFirst) {
  const elements = new Map(), pending = [];
  const context = {sessionEpoch: 0, bearer: 'synthetic', briefStatusLabels: {},
    $: id => {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);},
    document: {createElement: element},
    briefApi: () => new Promise((resolve, reject) => pending.push({resolve, reject})),
  };
  vm.createContext(context);
  vm.runInContext(script.slice(start, end), context);
  const old = context.selectBrief(1, 'Old');
  let current;
  if (mode === 'switch') current = context.selectBrief(2, 'Current');
  if (mode === 'toggle') await context.selectBrief(1, 'Old');
  if (mode === 'back' || mode === 'reopen') context.$('brief-detail-back').click();
  if (mode === 'reopen') current = context.selectBrief(1, 'Current');
  if (mode === 'session') context.sessionEpoch++;
  const settleOld = () => {
    if (fails) pending[0].reject(new Error('private failure'));
    else pending[0].resolve({offer_reference: 'OLD'});
    pending[1].resolve([{channel: 'old-channel', status: 'open'}]);
  };
  const snapshot = () => JSON.stringify([...elements]);
  if (oldFirst || !current) {
    const before = snapshot(); settleOld(); await old;
    assert.equal(snapshot(), before);
  }
  if (current) {
    pending[2].resolve({offer_reference: 'CURRENT'}); pending[3].resolve([]);
    await current;
    assert.equal(context.$('brief-detail-title').textContent, 'Brief: Current');
    assert.equal(context.$('brief-detail-content').children[0].children[1].textContent, 'CURRENT');
    if (!oldFirst) {const before = snapshot(); settleOld(); await old; assert.equal(snapshot(), before);}
  }
  // A current error remains visible, and reopening allows recovery.
  const retry = context.selectBrief(3, 'Retry');
  pending.at(-2).reject(new Error('private failure')); pending.at(-1).resolve([]);
  await retry;
  assert.equal(context.$('brief-detail-content').textContent, 'Falha ao carregar brief.');
}
(async () => {
  for (const mode of ['switch', 'toggle', 'back', 'reopen', 'session'])
    for (const fails of [false, true])
      for (const oldFirst of [false, true]) await run(mode, fails, oldFirst);
})().catch(error => {console.error(error); process.exitCode = 1;});
