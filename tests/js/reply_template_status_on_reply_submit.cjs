const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  $("human-reply-form").addEventListener("submit"');
const end = source.indexOf('\n\n  $("conv-list").replaceChildren();', start);
assert(start >= 0 && end > start);

function setup({fail = false} = {}) {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, {});
    return elements.get(id);
  };
  const form = get('human-reply-form');
  const submitButton = {};
  form.addEventListener = (event, callback) => {
    if (event === 'submit') form.submit = callback;
  };
  form.querySelector = () => submitButton;
  form.reset = () => { get('reply-message').value = ''; };
  get('reply-conv-id').value = '12';
  get('reply-message').value = 'Bom dia';
  get('reply-template-insert-status').textContent = 'Template "Saudação" inserido na resposta.';
  let submittedBody;
  const notifications = [];
  const context = {
    $: get,
    withButton: async (button, operation) => {
      try { await operation(); } catch {}
    },
    replyApi: async (path, method, body) => {
      submittedBody = {path, method, body};
      if (fail) throw new Error('synthetic failure');
    },
    notify: message => notifications.push(message),
    selectConversation: async () => {},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {form, elements, notifications, get submittedBody() { return submittedBody; }};
}

async function run() {
  const success = setup();
  await success.form.submit({preventDefault() {}});
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(JSON.parse(JSON.stringify(success.submittedBody)), {
    path: '/conversations/12/messages',
    method: 'POST',
    body: {sender_type: 'human', content: 'Bom dia'},
  });
  assert.equal(success.elements.get('reply-message').value, '');
  assert.equal(success.elements.get('reply-template-insert-status').textContent, '');
  assert.deepEqual(success.notifications, ['Mensagem enviada na conversa #12.']);

  const failure = setup({fail: true});
  await failure.form.submit({preventDefault() {}});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(failure.elements.get('reply-message').value, 'Bom dia');
  assert.equal(
    failure.elements.get('reply-template-insert-status').textContent,
    'Template "Saudação" inserido na resposta.',
  );
}

run().catch(error => { console.error(error); process.exitCode = 1; });
