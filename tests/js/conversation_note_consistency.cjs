const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
function section(start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a);
  assert(a >= 0 && b > a);
  return source.slice(a, b);
}
function setup() {
  const elements = new Map(), pending = [], messages = [];
  const context = {selectedConvId: null, conversationNoteVersion: 0,
    conversationNoteReady: false, sessionEpoch: 0, msgOffset: 0,
    conversations: [], channelLabels: {}, showConversationList() {},
    loadMessages: () => new Promise(resolve => messages.push(resolve)),
    loadReplyTemplates: async () => {},
    $: id => {
      if (!elements.has(id)) elements.set(id, {value: '', textContent: '', hidden: false,
        disabled: false, readOnly: false, addEventListener(event, fn) {this[event] = fn;}});
      return elements.get(id);
    },
    conversationApi: (path, method = 'GET', body) => new Promise((resolve, reject) =>
      pending.push({path, method, body, resolve, reject})),
  };
  vm.createContext(context);
  vm.runInContext(section('  async function selectConversation(id)', '  async function loadMessages(id)') +
    section('  async function loadConversationNote(', '  // WP-264') +
    section('  $("conv-note-save").addEventListener', '  // WP-147'), context);
  return {context, pending, messages, field: context.$('conv-note-text'),
    button: context.$('conv-note-save'), status: context.$('conv-note-status')};
}
async function races(mode, fails, oldFirst, saving) {
  const {context: c, pending, messages, field, button, status} = setup();
  const firstSelection = c.selectConversation(1);
  // Notes load immediately, even while messages are pending.
  assert.equal(pending[0].path, '/conversations/1/note');
  assert.equal(field.value, ''); assert(field.readOnly); assert(button.disabled);
  await button.click(); assert.equal(pending.length, 1);
  let old = firstSelection;
  if (saving) {
    pending[0].resolve({note: 'first'}); messages[0](); await firstSelection;
    field.value = 'edited'; old = button.click();
    assert.equal(pending[1].path, '/conversations/1');
    assert.equal(pending[1].method, 'PATCH');
    assert.equal(pending[1].body.note, 'edited');
    await button.click(); assert.equal(pending.length, 2, 'duplicate save blocked');
  }
  const oldIndex = saving ? 1 : 0;
  if (mode === 'session') c.sessionEpoch++;
  if (mode === 'close') c.selectedConvId = null;
  let current;
  if (mode !== 'close') current = c.selectConversation(mode === 'switch' ? 2 : 1);
  const snapshot = () => JSON.stringify({field, button, status});
  const finishOld = async () => {
    fails ? pending[oldIndex].reject(new Error('private detail')) : pending[oldIndex].resolve({note: 'OLD'});
    if (!saving) messages[0]();
    await old;
  };
  if (oldFirst || !current) {const before = snapshot(); await finishOld(); assert.equal(snapshot(), before);}
  if (current) {
    pending.at(-1).resolve({note: 'CURRENT'}); messages.at(-1)(); await current;
    assert.equal(field.value, 'CURRENT'); assert(!field.readOnly); assert(!button.disabled);
    assert.equal(status.textContent, '');
    if (!oldFirst) {const before = snapshot(); await finishOld(); assert.equal(snapshot(), before);}
  }
}
async function recovery() {
  const {context: c, pending, messages, field, button, status} = setup();
  let selection = c.selectConversation(1);
  pending[0].reject(new Error('private error')); messages[0](); await selection;
  assert.match(status.textContent, /Selecione a conversa novamente/);
  assert(!status.textContent.includes('private')); assert(field.readOnly); assert(button.disabled);
  await button.click(); assert.equal(pending.length, 1);
  selection = c.selectConversation(1);
  pending[1].resolve({note: null}); messages[1](); await selection;
  assert.equal(field.value, ''); assert(!button.disabled);
  field.value = 'draft'; let save = button.click();
  pending[2].reject(new Error('private error')); await save;
  assert.equal(field.value, 'draft'); assert(!button.disabled); assert(!field.readOnly);
  assert.match(status.textContent, /Falha ao salvar/);
  save = button.click(); pending[3].resolve({}); await save;
  assert.equal(status.textContent, 'Nota salva.');
}
(async () => {
  for (const mode of ['switch', 'reopen', 'session', 'close'])
    for (const fails of [false, true])
      for (const oldFirst of [false, true])
        for (const saving of [false, true]) await races(mode, fails, oldFirst, saving);
  await recovery();
})().catch(error => {console.error(error); process.exitCode = 1;});
