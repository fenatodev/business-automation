const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));
function setup() {
  const pending = [], rendered = [], disconnected = [];
  const status = {textContent: ''};
  const context = {
    bearer: 'synthetic', sessionEpoch: 1, dashboardIntervalId: null,
    ApiFailure: class ApiFailure extends Error {constructor(status) {super(String(status)); this.status = status;}},
    $: id => {assert.equal(id, 'dashboard-status'); return status;},
    fetch(url, options) {
      assert.equal(url, '/internal-tasks/dashboard');
      assert.equal(options.headers.Authorization, 'Bearer synthetic');
      return new Promise((resolve, reject) => pending.push({resolve, reject}));
    },
    renderDashboard(data) {rendered.push(data);},
    disconnect(message) {disconnected.push(message); context.sessionEpoch++; context.bearer = null;},
    clearInterval() {}, setInterval() {return 1;},
  };
  vm.createContext(context);
  vm.runInContext(script.slice(script.indexOf('  const DASHBOARD_REFRESH_MS'),
    script.indexOf('  function renderDashboard(')), context);
  return {context, pending, rendered, disconnected, status};
}
const response = (status, data) => ({status, ok: status === 200, async json() {return data;}});
(async () => {
  for (const oldFirst of [false, true]) {
    for (const oldStatus of [200, 403, 503]) {
      const {context, pending, rendered, disconnected} = setup();
      const older = context.refreshDashboard(), newer = context.refreshDashboard();
      if (oldFirst) {pending[0].resolve(response(oldStatus, 'old')); await older;}
      assert.deepEqual(rendered, []);
      pending[1].resolve(response(200, 'current')); await newer;
      if (!oldFirst) {pending[0].resolve(response(oldStatus, 'old')); await older;}
      assert.deepEqual(rendered, ['current']);
      assert.deepEqual(disconnected, []);
    }
  }
  // Parsing a response body can itself finish after a newer poll.
  {
    const {context, pending, rendered} = setup();
    let finishBody;
    const older = context.refreshDashboard();
    pending[0].resolve({status: 200, ok: true,
      json: () => new Promise(resolve => {finishBody = resolve;})});
    await tick();
    const newer = context.refreshDashboard();
    pending[1].resolve(response(200, 'current')); await newer;
    finishBody('old'); await older;
    assert.deepEqual(rendered, ['current']);
  }
  for (const phase of ['headers', 'body']) {
    for (const invalidate of ['stop', 'session']) {
      const {context, pending, rendered, disconnected} = setup();
      let finishBody;
      const request = context.refreshDashboard();
      if (phase === 'body') {
        pending[0].resolve({status: 200, ok: true,
          json: () => new Promise(resolve => {finishBody = resolve;})});
        await tick();
      }
      if (invalidate === 'stop') context.stopDashboardRefresh();
      else context.sessionEpoch++;
      if (phase === 'body') finishBody('old');
      else pending[0].resolve(response(403, 'old'));
      await request;
      assert.deepEqual(rendered, []);
      assert.deepEqual(disconnected, []);
    }
  }
  // Preserve handling of a current forbidden response and recovery after failure.
  {
    const {context, pending, disconnected} = setup();
    const request = context.refreshDashboard();
    pending[0].resolve(response(403)); await request;
    assert.equal(disconnected.length, 1);
  }
  {
    const {context, pending, rendered, status} = setup();
    const request = context.refreshDashboard();
    pending[0].reject(new Error('synthetic network failure'));
    await assert.rejects(request);
    assert.match(status.textContent, /Falha ao atualizar/);
    const retry = context.refreshDashboard();
    pending[1].resolve(response(200, 'recovered')); await retry;
    assert.deepEqual(rendered, ['recovered']);
    assert.equal(status.textContent, '');
  }
  {
    const {context, pending, rendered, status} = setup();
    const request = context.refreshDashboard();
    pending[0].resolve(response(503));
    await assert.rejects(request);
    assert.match(status.textContent, /Falha ao atualizar/);
    assert.deepEqual(rendered, []);
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
