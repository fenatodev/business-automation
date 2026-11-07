const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
function section(start, end) {
  const pos = script.indexOf(start), finish = script.indexOf(end, pos);
  assert(pos >= 0 && finish > pos);
  return script.slice(pos, finish);
}
function element() {
  return {hidden: false, disabled: false, textContent: '', children: [], attributes: {},
    classList: {add() {}}, setAttribute(name, value) {this.attributes[name] = value;},
    replaceChildren() {this.children = [];}, append(...children) {this.children.push(...children);},
    addEventListener(event, fn) {this[event] = fn;}};
}
async function main() {
  const elements = new Map(), pending = [];
  const context = {selectedConvId: 7, sessionEpoch: 0, messageLoadEpoch: 0,
    msgOffset: 50, msgPageSize: 50, msgTotal: 100,
    senderLabels: {customer: 'Cliente'},
    $: id => {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);},
    document: {createElement: element},
    conversationApi(url, method = 'GET') {
      assert.equal(method, 'GET');
      return new Promise((resolve, reject) => pending.push({url, resolve, reject}));
    }};
  vm.createContext(context);
  vm.runInContext(section('  async function loadMessages(id)', '  // WP-140 — Conversation internal notes') +
    section('  $("conv-messages-retry").addEventListener', '  function updateMessagePagination()'), context);

  const firstAttempt = context.loadMessages(7);
  assert.equal(context.$('conv-messages-status').textContent, 'Carregando mensagens...');
  assert.equal(context.$('conv-messages-retry').hidden, true);
  assert.equal(context.$('conv-messages-retry').disabled, true);
  assert.equal(context.$('conv-messages').attributes['aria-busy'], 'true');
  pending[0].reject(new Error('internal detail'));
  await firstAttempt;
  assert.equal(context.$('conv-messages-status').textContent,
    'Não foi possível carregar as mensagens desta conversa.');
  assert.equal(context.$('conv-messages-retry').hidden, false);
  assert.equal(context.$('conv-messages-retry').disabled, false);
  assert.equal(context.$('conv-messages').attributes['aria-busy'], 'false');

  context.$('conv-messages-retry').click();
  assert.equal(pending.length, 4);
  assert.equal(context.$('conv-messages-retry').disabled, true);
  assert.equal(new URL(pending[2].url, 'http://localhost').searchParams.get('offset'), '50');
  assert.equal(new URL(pending[3].url, 'http://localhost').searchParams.get('offset'), '50');
  pending[2].resolve([{sender_type: 'customer', content: 'Mensagem sintética'}]);
  pending[3].resolve({total: 73});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(context.$('conv-messages-status').textContent, '');
  assert.equal(context.$('conv-messages-retry').hidden, true);
  assert.equal(context.$('conv-messages-retry').disabled, false);
  assert.equal(context.$('conv-messages').children[0].children[1].textContent, 'Mensagem sintética');
  assert.equal(context.msgTotal, 73);
}
main().catch(error => {console.error(error); process.exitCode = 1;});
