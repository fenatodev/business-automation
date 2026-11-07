const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let currentLeadId = null;');
const end = source.indexOf('  $("lead-detail-back")', start);
assert(start >= 0 && end > start);

function element() {
  return {hidden: false, children: [], textContent: '', replaceChildren() {this.children = [];},
    appendChild(child) {this.children.push(child);}, addEventListener(event, fn) {this[event] = fn;}};
}

async function run() {
  const elements = new Map(), pending = [];
  const context = {sessionEpoch: 0, bearer: 'synthetic', leadTotal: 0, leadPageSize: 20,
    leadStatusLabels: {}, URLSearchParams, console: {error() {}},
    $: id => {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);},
    document: {createElement: element},
    conversationApi: path => {assert.match(path, /^\/companies\/1\/conversations\?lead_id=7&limit=50$/); return new Promise((resolve, reject) => pending.push({resolve, reject}));},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  const loading = context.showLeadDetail({id: 7, company_id: 1, name: 'Synthetic lead'});
  pending[0].reject(new Error('private failure'));
  await loading;
  assert.match(context.$('lead-conversations-status').textContent, /não foi possível carregar/i);
  assert.equal(context.$('lead-conversations-retry').hidden, false);

  const retry = context.$('lead-conversations-retry').click();
  assert.equal(pending.length, 2);
  assert.equal(context.$('lead-conversations-retry').hidden, true);
  pending[1].resolve([{id: 11, lead_id: 7, channel: 'web', status: 'open'}]);
  await retry;
  assert.equal(context.$('lead-conversations-status').textContent, '');
  assert.equal(context.$('lead-conversations-list').children[0].textContent, '#11 · web · open');
}

run().catch(error => {console.error(error); process.exitCode = 1;});
