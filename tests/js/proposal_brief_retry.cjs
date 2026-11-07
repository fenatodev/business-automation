const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  async function loadBrief');
const end = source.indexOf('  async function selectOpportunity', start);
assert(start >= 0 && end > start);

function element() {
  return {
    hidden: false,
    disabled: false,
    textContent: '',
    addEventListener(event, callback) {
      if (event === 'click') this.click = () => { if (!this.disabled) return callback(); };
    },
  };
}

function setup() {
  const elements = new Map();
  const requests = [];
  const displayed = [];
  const context = {
    sessionEpoch: 1,
    selectionVersion: 4,
    selectedId: 12,
    ApiFailure: class ApiFailure extends Error {},
    $: id => {
      if (!elements.has(id)) elements.set(id, element());
      return elements.get(id);
    },
    displayBrief: brief => displayed.push(brief),
    notify() {},
    api(path) {
      let resolve;
      let reject;
      const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
      requests.push({path, resolve, reject, promise});
      return promise;
    },
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {context, requests, displayed};
}

async function run() {
  const {context, requests, displayed} = setup();
  const retry = context.$('brief-load-retry');
  const status = context.$('brief-status');

  const failedLoad = context.loadBrief(12, 4);
  assert.equal(requests[0].path, '/opportunities/12/proposal-brief');
  assert.equal(status.textContent, 'Carregando');
  assert.equal(retry.hidden, true);
  assert.equal(retry.disabled, true);
  requests[0].reject(new Error('private backend details'));
  await failedLoad;
  assert.equal(status.textContent, 'Consulta indisponível');
  assert.equal(retry.hidden, false);
  assert.equal(retry.disabled, false);

  retry.click();
  retry.click();
  assert.equal(requests.length, 2);
  assert.equal(requests[1].path, '/opportunities/12/proposal-brief');
  requests[1].resolve({status: 'draft'});
  await requests[1].promise;
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(displayed, [{status: 'draft'}]);
  assert.equal(retry.hidden, true);

  const staleLoad = context.loadBrief(12, 4);
  context.sessionEpoch += 1;
  requests[2].resolve({status: 'ready_for_review'});
  await staleLoad;
  assert.deepEqual(displayed, [{status: 'draft'}]);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
