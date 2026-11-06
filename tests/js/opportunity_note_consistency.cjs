const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  $("save-opp-note").addEventListener');
const end = source.indexOf('  // WP-093 — Save opportunity title', start);
assert(start >= 0 && end > start);
function setup() {
  const fields = new Map(), pending = [], notices = [];
  const context = {selectedId: 1, selectionVersion: 1, sessionEpoch: 0,
    opportunities: [{id: 1, triage_note: 'first'}, {id: 2, triage_note: 'second'}],
    ApiFailure: class extends Error {},
    $: id => {
      if (!fields.has(id)) fields.set(id, {value: '', addEventListener(event, fn) {this[event] = fn;}});
      return fields.get(id);
    },
    notify: (...args) => notices.push(args),
    api: (path, options) => new Promise((resolve, reject) => pending.push({path, options, resolve, reject})),
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {c: context, pending, notices, field: context.$('opp-note'), button: context.$('save-opp-note')};
}
async function race(mode, fails, oldFirst) {
  const {c, pending, notices, field, button} = setup();
  field.value = ' old draft ';
  const old = button.click();
  assert.equal(pending[0].path, '/opportunities/1');
  assert.equal(pending[0].options.method, 'PATCH');
  assert.equal(pending[0].options.body.triage_note, 'old draft');
  if (mode === 'session') c.sessionEpoch++;
  else {c.selectionVersion++; c.selectedId = mode === 'switch' ? 2 : mode === 'close' ? null : 1;}
  field.value = 'current draft'; c.$('triage-note').value = 'current triage';
  let current;
  if (c.selectedId !== null) current = button.click();
  const snapshot = () => JSON.stringify({field: field.value, triage: c.$('triage-note').value,
    records: c.opportunities, notices});
  const finishOld = async () => {
    fails ? pending[0].reject(new c.ApiFailure('old failure')) :
      pending[0].resolve({id: 1, triage_note: 'OLD'});
    await old;
  };
  if (oldFirst || !current) {const before = snapshot(); await finishOld(); assert.equal(snapshot(), before);}
  if (current) {
    pending[1].resolve({id: c.selectedId, triage_note: 'CURRENT'}); await current;
    assert.equal(field.value, 'CURRENT'); assert.equal(c.$('triage-note').value, 'CURRENT');
    assert.equal(c.opportunities.find(o => o.id === c.selectedId).triage_note, 'CURRENT');
    assert.equal(notices.length, 1); assert.equal(notices[0][0], 'Nota salva.');
    if (!oldFirst) {const before = snapshot(); await finishOld(); assert.equal(snapshot(), before);}
  }
}
async function recovery() {
  const {c, pending, notices, field, button} = setup();
  c.selectedId = null; await button.click(); assert.equal(pending.length, 0);
  c.selectedId = 1; field.value = 'draft';
  for (const error of [new Error('private failure'), new c.ApiFailure('API failure')]) {
    const save = button.click(); pending.at(-1).reject(error); await save;
    assert.equal(field.value, 'draft'); assert.equal(c.opportunities[0].triage_note, 'first');
    assert.equal(notices.at(-1)[1], true);
    assert.equal(notices.at(-1)[0], error instanceof c.ApiFailure ? 'API failure' : 'Falha ao salvar nota.');
  }
  field.value = '  '; const save = button.click();
  assert.equal(pending.at(-1).options.body.triage_note, null);
  pending.at(-1).resolve({id: 1, triage_note: null}); await save;
  assert.equal(field.value, ''); assert.equal(c.$('triage-note').value, '');
}
(async () => {
  for (const mode of ['switch', 'reopen', 'close', 'session'])
    for (const fails of [false, true])
      for (const oldFirst of [false, true]) await race(mode, fails, oldFirst);
  await recovery();
})().catch(error => {console.error(error); process.exitCode = 1;});
