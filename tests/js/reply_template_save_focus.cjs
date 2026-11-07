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
  const context = {
    bearer: 'synthetic-token',
    company: 3,
    $(id) { return elements.get(id) || element(); },
    templateApi(path, method, body) {
      return new Promise((resolve, reject) => requests.push({path, method, body, resolve, reject}));
    },
    notify() {},
    loadReplyTemplateList: async () => {},
    loadReplyTemplates() {},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {elements, requests};
}

async function run() {
  const success = setup();
  const successSubmit = success.elements.get('reply-template-form').submit({preventDefault() {}});
  success.requests[0].resolve({id: 10});
  await successSubmit;
  assert.equal(success.elements.get('reply-template-name').value, '');
  assert.equal(success.elements.get('reply-template-content').value, '');
  assert.equal(success.elements.get('reply-template-name').focused, true);

  const failure = setup();
  const failureSubmit = failure.elements.get('reply-template-form').submit({preventDefault() {}});
  failure.requests[0].reject(new Error('synthetic failure'));
  await failureSubmit;
  assert.equal(failure.elements.get('reply-template-name').value, ' Saudação ');
  assert.equal(failure.elements.get('reply-template-content').value, ' Olá! ');
  assert.equal(failure.elements.get('reply-template-name').focused, false);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
