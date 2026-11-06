const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = script.indexOf('  let currentLeadId = null;');
const end = script.indexOf('  $("lead-detail-back")', start);
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
  const context = {sessionEpoch: 0, bearer: 'synthetic', leadTotal: 0, leadPageSize: 20, leadStatusLabels: {}, opportunities: [], URLSearchParams, console: {error() {}},
    $: id => {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);},
    document: {createElement: element},
    conversationApi: path => {assert.match(path, /^\/companies\/1\/conversations\?lead_id=\d+&limit=50$/); return new Promise((resolve, reject) => pending.push({resolve, reject}));},
  };
  vm.createContext(context);
  vm.runInContext(script.slice(start, end), context);
  const old = context.showLeadDetail({id: 1, company_id: 1, name: 'Old'});
  let current;
  if (mode === 'switch') current = context.showLeadDetail({id: 2, company_id: 1, name: 'Current'});
  if (mode === 'back' || mode === 'reopen') context.hideLeadDetail();
  if (mode === 'reopen') current = context.showLeadDetail({id: 1, company_id: 1, name: 'Current'});
  if (mode === 'session') context.sessionEpoch++;
  const settleOld = () => {
    if (fails) pending[0].reject(new Error('private failure'));
    else pending[0].resolve([{id: 10, lead_id: 1, channel: 'OLD', status: 'open'}]);
  };
  const snapshot = () => JSON.stringify([...elements]);
  if (oldFirst || !current) {
    const before = snapshot(); settleOld(); await old;
    assert.equal(snapshot(), before);
  }
  if (current) {
    pending[1].resolve([{id: 20, lead_id: mode === 'reopen' ? 1 : 2, channel: 'CURRENT', status: 'open'}]);
    await current;
    assert.equal(context.$('lead-detail-name').textContent, 'Current');
    assert.equal(context.$('lead-conversations-list').children[0].textContent, '#20 · CURRENT · open');
    if (!oldFirst) {const before = snapshot(); settleOld(); await old; assert.equal(snapshot(), before);}
  }
  const empty = context.showLeadDetail({id: 3, company_id: 1, name: 'Empty'});
  pending.at(-1).resolve([]); await empty;
  assert.equal(context.$('lead-conversations-list').children[0].textContent, 'Nenhuma conversa associada.');
}
(async () => {
  for (const mode of ['switch', 'back', 'reopen', 'session'])
    for (const fails of [false, true])
      for (const oldFirst of [false, true]) await run(mode, fails, oldFirst);
})().catch(error => {console.error(error); process.exitCode = 1;});
