const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  $("save-edit-button").addEventListener');
const end = source.indexOf('  // WP-278 — Create conversation from opportunity', start);
assert(start >= 0 && end > start);
function setup() {
  const fields = new Map(), pending = [], notices = [];
  const context = {selectedId: 1, selectionVersion: 1, sessionEpoch: 0,
    opportunities: [{id: 1, title: 'first', description: 'first description'}, {id: 2, title: 'second', description: 'second description'}],
    ApiFailure: class extends Error {},
    $: id => {
      if (!fields.has(id)) fields.set(id, {value: '', addEventListener(event, fn) {this[event] = fn;}});
      return fields.get(id);
    },
    showList: () => notices.push(['render']),
    notify: (...args) => notices.push(args),
    api: (path, options) => new Promise((resolve, reject) => pending.push({path, options, resolve, reject})),
  };
  context.$('edit-description').value = 'description';
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {c: context, pending, notices, field: context.$('edit-title'), button: context.$('save-edit-button')};
}
async function race(mode, fails, oldFirst) {
  const {c, pending, notices, field, button} = setup();
  field.value = ' old draft ';
  const old = button.click();
  assert.equal(pending[0].path, '/opportunities/1');
  assert.equal(pending[0].options.method, 'PATCH');
  assert.equal(pending[0].options.body.title, 'old draft');
  if (mode === 'session') c.sessionEpoch++;
  else {c.selectionVersion++; c.selectedId = mode === 'switch' ? 2 : mode === 'close' ? null : 1;}
  field.value = 'current draft'; c.$('edit-description').value = 'current description';
  let current;
  if (c.selectedId !== null) current = button.click();
  const snapshot = () => JSON.stringify({field: field.value, description: c.$('edit-description').value,
    records: c.opportunities, notices});
  const finishOld = async () => {
    fails ? pending[0].reject(new c.ApiFailure('old failure')) :
      pending[0].resolve({id: 1, title: 'OLD', description: 'OLD description'});
    await old;
  };
  if (oldFirst || !current) {const before = snapshot(); await finishOld(); assert.equal(snapshot(), before);}
  if (current) {
    pending[1].resolve({id: c.selectedId, title: 'CURRENT', description: 'CURRENT description'}); await current;
    assert.equal(field.value, 'CURRENT'); assert.equal(c.$('edit-description').value, 'CURRENT description');
    assert.equal(c.opportunities.find(o => o.id === c.selectedId).title, 'CURRENT');
    assert.equal(notices.length, 2); assert.equal(notices[0][0], 'Oportunidade atualizada.');
    if (!oldFirst) {const before = snapshot(); await finishOld(); assert.equal(snapshot(), before);}
  }
}
async function recovery() {
  const {c, pending, notices, field, button} = setup();
  c.selectedId = null; await button.click(); assert.equal(pending.length, 0);
  c.selectedId = 1; field.value = 'draft';
  for (const error of [new Error('private failure'), new c.ApiFailure('API failure')]) {
    const save = button.click(); pending.at(-1).reject(error); await save;
    assert.equal(field.value, 'draft'); assert.equal(c.opportunities[0].title, 'first');
    assert.equal(notices.at(-1)[1], true);
    assert.equal(notices.at(-1)[0], error instanceof c.ApiFailure ? 'API failure' : 'Falha ao salvar alterações.');
  }
  for (const [title, description] of [['  ', 'description'], ['title', '  ']]) {
    field.value = title; c.$('edit-description').value = description;
    const count = pending.length; await button.click();
    assert.equal(pending.length, count); assert.equal(notices.at(-1)[1], true);
  }
  field.value = ' retry '; c.$('edit-description').value = ' retry description ';
  const save = button.click();
  assert.equal(pending.at(-1).options.body.title, 'retry');
  assert.equal(pending.at(-1).options.body.description, 'retry description');
  pending.at(-1).resolve({id: 1, title: 'retry', description: 'retry description'}); await save;
  assert.equal(field.value, 'retry'); assert.equal(c.$('edit-description').value, 'retry description');
  assert.equal(c.opportunities[0].title, 'retry');

}
(async () => {
  for (const mode of ['switch', 'reopen', 'close', 'session'])
    for (const fails of [false, true])
      for (const oldFirst of [false, true]) await race(mode, fails, oldFirst);
  await recovery();
})().catch(error => {console.error(error); process.exitCode = 1;});
