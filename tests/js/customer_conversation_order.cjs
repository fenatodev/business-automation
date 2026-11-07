const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = script.indexOf('  let customerConversationsVersion = 0;');
const end = script.indexOf('  // WP-110 — Edit customer', start);
function element() {
  return {hidden: false, dataset: {}, children: [], style: {}, textContent: '',
    replaceChildren() {this.children = [];},
    get firstChild() {return this.children[0];},
    appendChild(child) {this.children.push(child);},
    removeChild() {this.children.shift();},
    addEventListener(event, fn) {this[event] = fn;}};
}
async function run(mode, fails, oldFirst) {
  const elements = new Map(), pending = [];
  const context = {sessionEpoch: 0, bearer: 'synthetic', currentCustomerId: null, customerSelectionVersion: 0, opportunities: [{company_id: 1}], URLSearchParams, console: {error() {}}, hideCustomerEditForm() {},
    $: id => {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);},
    document: {createElement: element},
    conversationApi: () => new Promise((resolve, reject) => pending.push({resolve, reject})),
  };
  vm.createContext(context);
  vm.runInContext(script.slice(start, end), context);
  const old = context.showCustomerDetail({id: 1, name: 'Old'});
  let current;
  if (mode === 'switch') current = context.showCustomerDetail({id: 2, name: 'Current'});
  if (mode === 'back' || mode === 'reopen') context.hideCustomerDetail();
  if (mode === 'reopen') current = context.showCustomerDetail({id: 1, name: 'Current'});
  if (mode === 'session') context.sessionEpoch++;
  const settleOld = () => {
    if (fails) pending[0].reject(new Error('private failure'));
    else pending[0].resolve([{channel: 'OLD', status: 'open'}]);
  };
  const snapshot = () => JSON.stringify([...elements]);
  if (oldFirst || !current) {
    const before = snapshot(); settleOld(); await old;
    assert.equal(snapshot(), before);
  }
  if (current) {
    pending[1].resolve([{channel: 'CURRENT', status: 'open'}]);
    await current;
    assert.equal(context.$('customer-detail-name').textContent, 'Current');
    assert.equal(context.$('customer-conversations-list').children[0].children[0].children[0].textContent, 'CURRENT');
    if (!oldFirst) {const before = snapshot(); settleOld(); await old; assert.equal(snapshot(), before);}
  }
  const empty = context.showCustomerDetail({id: 3, name: 'Empty'});
  pending.at(-1).resolve([]); await empty;
  assert.equal(context.$('customer-conversations-list').children[0].textContent, 'Nenhuma conversa encontrada.');
}
(async () => {
  for (const mode of ['switch', 'back', 'reopen', 'session'])
    for (const fails of [false, true])
      for (const oldFirst of [false, true]) await run(mode, fails, oldFirst);
})().catch(error => {console.error(error); process.exitCode = 1;});
