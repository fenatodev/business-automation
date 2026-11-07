const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let replyTemplateSaving = false;');
const end = source.indexOf('\n})();', start);
assert(start >= 0 && end > start);

function element(value = '') {
  return {
    value,
    disabled: false,
    attributes: {},
    focused: false,
    addEventListener(event, callback) {
      if (event === 'submit') this.submit = callback;
    },
    setAttribute(name, value) { this.attributes[name] = value; },
    focus() { this.focused = true; },
  };
}

function setup() {
  const elements = new Map([
    ['reply-template-form', element()],
    ['reply-template-name', element(' Saudação ')],
    ['reply-template-content', element(' Olá! ')],
    ['reply-template-save', element()],
    ['reply-template-save-status', element()],
  ]);
  const requests = [];
  const notifications = [];
  const context = {
    bearer: 'synthetic-token',
    company: 3,
    $: id => elements.get(id) || element(),
    templateApi(path, method, body) {
      let resolve;
      let reject;
      const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
      requests.push({path, method, body, resolve, reject, promise});
      return promise;
    },
    notify: message => notifications.push(message),
    loadReplyTemplateList: async () => {},
    loadReplyTemplates: () => {},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {elements, requests, notifications};
}

async function run() {
  const {elements, requests, notifications} = setup();
  const form = elements.get('reply-template-form');
  const button = elements.get('reply-template-save');
  const status = elements.get('reply-template-save-status');
  const event = {preventDefault() {}};

  const firstSubmit = form.submit(event);
  const secondSubmit = form.submit(event);
  assert.equal(requests.length, 1);
  assert.equal(requests[0].path, '/companies/3/reply-templates');
  assert.equal(requests[0].method, 'POST');
  assert.equal(requests[0].body.name, 'Saudação');
  assert.equal(requests[0].body.content, 'Olá!');
  assert.equal(button.disabled, true);
  assert.equal(status.attributes['aria-busy'], 'true');
  assert.equal(status.textContent, 'Salvando template');
  requests[0].resolve({id: 10});
  await Promise.all([firstSubmit, secondSubmit]);
  assert.equal(button.disabled, false);
  assert.equal(status.attributes['aria-busy'], 'false');
  assert.equal(status.textContent, 'Template salvo.');
  assert.equal(elements.get('reply-template-name').value, '');
  assert.equal(elements.get('reply-template-content').value, '');
  assert.equal(elements.get('reply-template-name').focused, true);
  assert.deepEqual(notifications, ['Template salvo.']);

  const failedSetup = setup();
  const failedSubmit = failedSetup.elements.get('reply-template-form').submit(event);
  assert.equal(failedSetup.elements.get('reply-template-save').disabled, true);
  assert.equal(failedSetup.elements.get('reply-template-save-status').attributes['aria-busy'], 'true');
  failedSetup.requests[0].reject(new Error('synthetic failure'));
  await failedSubmit;
  assert.equal(failedSetup.elements.get('reply-template-save').disabled, false);
  assert.equal(failedSetup.elements.get('reply-template-save-status').attributes['aria-busy'], 'false');
  assert.equal(failedSetup.elements.get('reply-template-save-status').textContent, 'Não foi possível salvar o template.');
  assert.equal(failedSetup.elements.get('reply-template-name').value, ' Saudação ');
  assert.deepEqual(failedSetup.notifications, ['Erro ao salvar template.']);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
