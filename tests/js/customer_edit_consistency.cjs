const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  $("customer-edit-form").addEventListener("submit"');
const end = source.indexOf('\n  // Create conversation from customer', start);
assert(start >= 0 && end > start);
const updateStart = source.indexOf('  async function updateCustomer(');
const updateEnd = source.indexOf('\n  // WP-110 — Edit customer form handlers', updateStart);
assert(updateStart >= 0 && updateEnd > updateStart);

function setup() {
  const fields = new Map(), pending = [], notices = [];
  const operation = {disabled: false};
  const form = {hidden: false, querySelector: () => operation, addEventListener(event, fn) {this[event] = fn;}};
  const context = {
    currentCustomerId: 1, customerSelectionVersion: 1, sessionEpoch: 0, bearer: 'synthetic',
    $: id => {
      if (!fields.has(id)) fields.set(id, id === 'customer-edit-form' ? form : {value: '', textContent: '', hidden: false});
      return fields.get(id);
    },
    updateCustomer: (id, data) => new Promise((resolve, reject) => pending.push({id, data, resolve, reject})),
    withButton(button, fn) {
      button.disabled = true;
      context.operation = (async () => {
        try {await fn();}
        catch (error) {notices.push([error.message, true]);}
        finally {button.disabled = false;}
      })();
      return context.operation;
    },
    hideCustomerEditForm() {form.hidden = true;},
    notify: (...args) => notices.push(args),
    refreshCustomers: async () => true,
    showCustomerDetail(customer) {context.currentCustomerId = customer.id;},
  };
  context.$('customer-edit-name').value = 'Updated';
  context.$('customer-edit-phone').value = '';
  context.$('customer-edit-email').value = '';
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {c: context, pending, notices, form, operation};
}

async function staleResponse(mode, fail) {
  const {c, pending, notices, form, operation} = setup();
  const submit = c.$('customer-edit-form').submit;
  let prevented = false;
  submit({preventDefault() {prevented = true;}});
  const save = c.operation;
  assert.equal(prevented, true);
  assert.equal(pending[0].id, 1);
  assert.deepEqual(JSON.parse(JSON.stringify(pending[0].data)), {name: 'Updated'});
  if (mode === 'session') c.sessionEpoch++;
  else {
    c.customerSelectionVersion++;
    c.currentCustomerId = mode === 'switch' ? 2 : mode === 'close' ? null : 1;
  }
  const before = JSON.stringify({notices, hidden: form.hidden});
  if (fail) pending[0].reject(new Error('synthetic failure'));
  else pending[0].resolve({id: 1, name: 'Updated'});
  await save;
  assert.equal(JSON.stringify({notices, hidden: form.hidden}), before);
}

async function noSelection() {
  const {c, pending} = setup();
  c.currentCustomerId = null;
  let prevented = false;
  c.$('customer-edit-form').submit({preventDefault() {prevented = true;}});
  assert.equal(prevented, true);
  assert.equal(pending.length, 0);
}

async function staleHttpFeedback() {
  const events = [];
  const context = {
    bearer: 'synthetic',
    $: () => ({value: 'synthetic-token'}),
    fetch: async () => ({status: 404, ok: false}),
    notify: (...args) => events.push(['notify', ...args]),
    disconnect: (...args) => events.push(['disconnect', ...args]),
  };
  vm.createContext(context);
  vm.runInContext(source.slice(updateStart, updateEnd), context);
  await context.updateCustomer(1, {name: 'x'}, () => false);
  assert.deepEqual(events, []);
  await context.updateCustomer(1, {name: 'x'}, () => true);
  assert.deepEqual(events, [['notify', 'Customer não encontrado.', true]]);
  context.fetch = async () => ({status: 403, ok: false});
  await context.updateCustomer(1, {name: 'x'}, () => false);
  assert.deepEqual(events, [['notify', 'Customer não encontrado.', true]]);
}

(async () => {
  for (const mode of ['switch', 'reopen', 'close', 'session'])
    for (const fail of [false, true]) await staleResponse(mode, fail);
  await noSelection();
  await staleHttpFeedback();
})().catch(error => {console.error(error); process.exitCode = 1;});
