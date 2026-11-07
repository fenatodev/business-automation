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

function setup(name, content) {
  const elements = new Map([
    ['reply-template-form', element()],
    ['reply-template-name', element(name)],
    ['reply-template-content', element(content)],
    ['reply-template-save', element()],
    ['reply-template-save-status', element()],
  ]);
  const requests = [];
  const context = {
    bearer: 'synthetic-token',
    company: 3,
    $: id => elements.get(id) || element(),
    templateApi(...args) { requests.push(args); },
    notify() {},
    loadReplyTemplateList: async () => {},
    loadReplyTemplates() {},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {elements, requests};
}

async function run() {
  const blankName = setup('   ', ' Olá! ');
  await blankName.elements.get('reply-template-form').submit({preventDefault() {}});
  assert.equal(blankName.requests.length, 0);
  assert.equal(blankName.elements.get('reply-template-save-status').textContent,
    'Preencha o nome e o conteúdo do template.');
  assert.equal(blankName.elements.get('reply-template-name').focused, true);
  assert.equal(blankName.elements.get('reply-template-content').focused, false);
  assert.equal(blankName.elements.get('reply-template-name').value, '   ');
  assert.equal(blankName.elements.get('reply-template-save').disabled, false);

  const blankContent = setup(' Saudação ', '   ');
  await blankContent.elements.get('reply-template-form').submit({preventDefault() {}});
  assert.equal(blankContent.requests.length, 0);
  assert.equal(blankContent.elements.get('reply-template-content').focused, true);
  assert.equal(blankContent.elements.get('reply-template-name').focused, false);
  assert.equal(blankContent.elements.get('reply-template-content').value, '   ');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
