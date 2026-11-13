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
  elements.get('reply-template-form').reset = () => {
    elements.get('reply-template-name').value = '';
    elements.get('reply-template-content').value = '';
  };
  const requests = [];
  const listeners = [];
  const document = {
    addEventListener(event, callback) { listeners.push({event, callback}); },
    createElement() {
      return {
        className: '',
        textContent: '',
        children: [],
        appendChild(el) { this.children.push(el); },
        replaceChildren() {},
        addEventListener() {},
        setAttribute() {},
        hidden: false,
      };
    },
    getElementById(id) { return elements.get(id) || null; },
  };
  const context = {
    bearer: 'synthetic-token',
    company: 3,
    document,
    $(id) { return elements.get(id) || element(); },
    updateReplyTemplateCharacterCount() {},
    templateApi(path, method, body) {
      return new Promise((resolve, reject) => requests.push({path, method, body, resolve, reject}));
    },
    notify() {},
    loadReplyTemplateList: async () => {},
    loadReplyTemplates() {},
  };
  vm.createContext(context);
  vm.runInContext(
    'let editingReplyTemplateId = null; function resetReplyTemplateForm() { $("reply-template-form").reset(); }\n' +
      source.slice(start, end),
    context,
  );
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
