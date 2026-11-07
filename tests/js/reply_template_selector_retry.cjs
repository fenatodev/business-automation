const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  // WP-264 — Load reply templates for the current company');
const end = source.indexOf('  // WP-459 — Insert a template without discarding the current reply draft', start);
assert(start >= 0 && end > start);

function element() {
  return {
    hidden: false,
    disabled: false,
    textContent: '',
    children: [],
    attributes: {},
    dataset: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    appendChild(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
    addEventListener(event, callback) {
      if (event === 'click') this.click = () => { if (!this.disabled) return callback(); };
    },
  };
}

const elements = new Map();
const requests = [];
const context = {
  opportunities: [{company_id: 7}],
  $: id => {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  },
  templateApi(path) {
    let resolve;
    let reject;
    const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
    requests.push({path, resolve, reject, promise});
    return promise;
  },
  document: {
    createElement() { return element(); },
  },
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);

async function run() {
  const select = context.$('reply-template-select');
  const section = context.$('reply-template-section');
  const status = context.$('reply-template-status');
  const retry = context.$('reply-template-retry');
  const existingOption = element();
  existingOption.value = 'existing';
  select.children = [existingOption];

  const failedLoad = context.loadReplyTemplates();
  assert.equal(requests[0].path, '/companies/7/reply-templates');
  assert.equal(status.textContent, 'Carregando templates de resposta');
  assert.equal(status.attributes['aria-busy'], 'true');
  assert.equal(retry.hidden, true);
  requests[0].reject(new Error('private backend details'));
  await failedLoad;
  assert.equal(status.textContent, 'Não foi possível carregar os templates de resposta.');
  assert.equal(status.textContent.includes('private backend details'), false);
  assert.equal(status.attributes['aria-busy'], 'false');
  assert.equal(section.hidden, false);
  assert.equal(retry.hidden, false);
  assert.equal(retry.disabled, false);
  assert.equal(select.children[0], existingOption);

  retry.click();
  assert.equal(requests.length, 2);
  assert.equal(retry.hidden, true);
  requests[1].resolve([{id: 3, name: 'Sintético', content: 'Resposta'}]);
  await requests[1].promise;
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(status.textContent, '');
  assert.equal(retry.hidden, true);
  assert.equal(section.hidden, false);
  assert.equal(select.children.length, 2);
  assert.equal(select.children[1].value, '3');
  assert.equal(select.children[1].textContent, 'Sintético');

  const oldLoad = context.loadReplyTemplates();
  const newLoad = context.loadReplyTemplates();
  requests[2].resolve([{id: 4, name: 'Antigo', content: 'antigo'}]);
  await oldLoad;
  requests[3].resolve([{id: 5, name: 'Atual', content: 'atual'}]);
  await newLoad;
  assert.equal(select.children[1].textContent, 'Atual');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
