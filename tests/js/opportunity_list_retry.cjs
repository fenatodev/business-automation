const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const elements = new Map();
const calls = [];
let failuresRemaining = 1;
const context = {
  selectedId: 12,
  $: id => {
    if (!elements.has(id)) elements.set(id, {
      hidden: false, textContent: '', attributes: {},
      setAttribute(key, value) {this.attributes[key] = value;},
      addEventListener(event, handler) {this[event] = handler;},
    });
    return elements.get(id);
  },
  async loadOpportunityList(id) {
    calls.push(id);
    if (failuresRemaining-- > 0) throw new Error('synthetic internal detail');
  },
  withButton(_button, handler) {return handler();},
};
vm.createContext(context);
const wrapperStart = script.indexOf('  async function refreshList(preferId = selectedId) {');
const wrapperEnd = script.indexOf('  async function loadOpportunityList(', wrapperStart);
vm.runInContext(script.slice(wrapperStart, wrapperEnd), context);
const handlersStart = script.indexOf('  $("refresh-button").addEventListener');
const handlersEnd = script.indexOf('  $("capture-form").addEventListener', handlersStart);
vm.runInContext(script.slice(handlersStart, handlersEnd), context);

(async () => {
  const list = context.$('opportunity-list');
  assert.equal(await context.refreshList(), false);
  assert.equal(list.attributes['aria-busy'], 'false');
  assert.equal(context.$('opp-load-retry').hidden, false);
  assert.match(context.$('opp-load-status').textContent, /Não foi possível atualizar/);
  assert.doesNotMatch(context.$('opp-load-status').textContent, /synthetic internal detail/);

  await context.$('opp-load-retry').click();
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(calls, [12, 12]);
  assert.equal(context.$('opp-load-retry').hidden, true);
  assert.equal(context.$('opp-load-status').textContent, '');
})().catch(error => {console.error(error); process.exitCode = 1;});
