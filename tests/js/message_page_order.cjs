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
async function run(oldFails, newFails, oldFirst, failedRequest) {
  const elements = new Map(), pending = [], notices = [];
  function element() {
    return {hidden: false, disabled: false, textContent: '', children: [],
      classList: {add() {}},
      setAttribute(name, value) {this[name] = value;},
      replaceChildren() {this.children = [];},
      append(...children) {this.children.push(...children);},
      addEventListener(event, fn) {this[event] = fn;}};
  }
  const context = {selectedConvId: 1, sessionEpoch: 0, messageLoadEpoch: 0,
    msgOffset: 0, msgPageSize: 50, msgTotal: 151, senderLabels: {customer: 'Cliente'},
    $: id => {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);},
    document: {createElement: element}, notify: (...args) => notices.push(args),
    conversationApi(url, method = 'GET') {
      assert.equal(method, 'GET');
      return new Promise((resolve, reject) => pending.push({url, resolve, reject}));
    }};
  vm.createContext(context);
  vm.runInContext(section('  async function loadMessages(id)', '  // WP-140 — Conversation internal notes') +
    section('  // WP-136 — Message pagination\n', '  $("conv-close-toggle").addEventListener'), context);
  context.$('conv-messages').append({textContent: 'previous'});
  context.$('msg-page').textContent = 'previous page';
  context.$('msg-next').click();
  context.$('msg-next').click();
  assert.equal(new URL(pending[0].url, 'http://localhost').searchParams.get('offset'), '50');
  assert.equal(new URL(pending[2].url, 'http://localhost').searchParams.get('offset'), '100');
  const settle = (index, fails, content) => {
    for (let n = 0; n < 2; n++) {
      if (fails && n === failedRequest) pending[index+n].reject(new Error('private failure'));
      else pending[index+n].resolve(n ? {total: 151} : [{sender_type: 'customer', content}]);
    }
  };
  const snapshot = () => JSON.stringify({elements: [...elements], total: context.msgTotal, notices});
  if (oldFirst) {
    const before = snapshot();
    settle(0, oldFails, 'old'); await tick();
    assert.equal(snapshot(), before);
  }
  settle(2, newFails, 'latest'); await tick();
  const current = snapshot();
  if (!oldFirst) {settle(0, oldFails, 'old'); await tick();}
  assert.equal(snapshot(), current);
  if (newFails) {
    assert.equal(context.$('conv-messages').children[0].textContent, 'previous');
    assert.equal(context.$('msg-page').textContent, 'previous page');
    assert.equal(context.$('conv-messages-status').textContent,
      'Não foi possível carregar as mensagens desta conversa.');
    assert.equal(notices.length, 0);
    // Moving back recovers through the delivered pagination handler.
    context.$('msg-prev').click();
    settle(4, false, 'recovered'); await tick();
    assert.equal(context.$('conv-messages').children[0].children[1].textContent, 'recovered');
    assert.match(context.$('msg-page').textContent, /Página 2 de 4/);
  } else {
    assert.equal(context.$('conv-messages').children[0].children[1].textContent, 'latest');
    assert.match(context.$('msg-page').textContent, /Página 3 de 4/);
    assert.equal(notices.length, 0);
  }
  // A result from an ended session cannot update a newly selected conversation.
  const request = context.loadMessages(1);
  context.sessionEpoch++;
  const before = snapshot();
  settle(pending.length - 2, false, 'ended session'); await request;
  assert.equal(snapshot(), before);
}
(async () => {
  for (const oldFails of [false, true])
    for (const newFails of [false, true])
      for (const oldFirst of [false, true])
        for (const failedRequest of [0, 1])
          await run(oldFails, newFails, oldFirst, failedRequest);
})().catch(error => {console.error(error); process.exitCode = 1;});
