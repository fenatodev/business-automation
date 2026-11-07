const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  async function loadOpportunityLeads');
const end = source.indexOf('  async function loadOpportunityCustomers', start);
assert(start >= 0 && end > start);

function element() {
  return {
    hidden: false,
    disabled: false,
    children: [],
    attributes: {},
    textContent: '',
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
    append(...children) { this.children.push(...children); },
    setAttribute(name, value) { this.attributes[name] = value; },
    addEventListener(event, callback) {
      this[event] = callback;
      if (event === 'click') this.click = () => { if (!this.disabled) return callback(); };
    },
  };
}

function setup() {
  const elements = new Map();
  const requests = [];
  const context = {
    sessionEpoch: 1,
    selectionVersion: 4,
    selectedId: 12,
    opportunityLeadId: null,
    opportunityCompanyId: null,
    opportunityContactType: null,
    $: id => {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    document: {createElement: element},
    api(path) {
      let resolve;
      let reject;
      const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
      requests.push({path, resolve, reject, promise});
      return promise;
    },
    showLeadDetail() {},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {context, elements, requests};
}

async function run() {
  const {context, requests} = setup();
  const list = context.$('opp-leads-list');
  const status = context.$('opp-leads-status');
  const retry = context.$('opp-leads-retry');

  const failedLoad = context.loadOpportunityLeads(12, 4);
  assert.equal(requests[0].path, '/opportunities/12/linked-leads');
  assert.equal(status.textContent, 'Carregando leads…');
  assert.equal(retry.hidden, true);
  assert.equal(retry.disabled, true);
  assert.equal(list.attributes['aria-busy'], 'true');
  requests[0].reject(new Error('private backend details'));
  await failedLoad;
  assert.equal(status.textContent, 'Falha ao carregar leads da oportunidade.');
  assert.equal(retry.hidden, false);
  assert.equal(retry.disabled, false);
  assert.equal(list.attributes['aria-busy'], 'false');
  assert(!status.textContent.includes('private'));

  retry.click();
  retry.click();
  assert.equal(requests.length, 2);
  assert.equal(requests[1].path, '/opportunities/12/linked-leads');
  assert.equal(retry.hidden, true);
  assert.equal(retry.disabled, true);
  requests[1].resolve([{id: 21, name: 'Synthetic lead', company_id: 1}]);
  await requests[1].promise;
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(status.textContent, '');
  assert.equal(retry.disabled, false);
  assert.equal(list.children[0].children[0].textContent, 'Synthetic lead');

  const staleLoad = context.loadOpportunityLeads(12, 4);
  context.selectionVersion = 5;
  context.selectedId = 13;
  requests[2].resolve([{id: 22, name: 'Stale lead', company_id: 1}]);
  await staleLoad;
  assert.equal(list.children[0].children[0].textContent, 'Synthetic lead');

  context.selectionVersion = 6;
  context.selectedId = 12;
  const staleSessionLoad = context.loadOpportunityLeads(12, 6);
  context.sessionEpoch += 1;
  requests[3].resolve([{id: 23, name: 'Prior session lead', company_id: 1}]);
  await staleSessionLoad;
  assert.equal(list.children[0].children[0].textContent, 'Synthetic lead');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
