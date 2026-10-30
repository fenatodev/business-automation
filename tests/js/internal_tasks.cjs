// Execute the delivered UI with synthetic DOM/fetch; validate internal tasks panel.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor() {
    this.listeners = {};
    this.value = '';
    this.textContent = '';
    this.disabled = false;
    this.hidden = false;
    this.classList = {add() {}, remove() {}, toggle() {}};
  }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  replaceChildren() {}
  append() {}
  reset() {}
  setAttribute() {}
  querySelector() { return new Element(); }
}
const html = fs.readFileSync('app/operator_ui/index.html', 'utf8');
const elements = new Map([...html.matchAll(/id="([^"]+)"/g)].map(m => [m[1], new Element()]));
const el = id => { assert(elements.has(id), `Missing HTML id: ${id}`); return elements.get(id); };
const requests = [];
const context = vm.createContext({
  document: {getElementById: el, createElement: () => new Element()},
  window: {addEventListener() {}},
  fetch: async (path, options) => {
    requests.push({path, options});
    let body;
    if (path === '/opportunities') body = [];
    else if (path === '/review-queue/summary') body = {pending: 0, approve: 0, reject: 0};
    else if (path === '/review-queue/aging') body = {overdue_pending: 0};
    else if (path.startsWith('/review-queue/')) body = [];
    else if (path === '/internal-tasks/' || path.startsWith('/internal-tasks/?')) {
      body = [
        {id: 1, status: 'queued', event_id: 'evt-1', error_code: null, created_at: '2026-10-30T00:00:00Z'},
        {id: 2, status: 'running', event_id: 'evt-2', error_code: null, created_at: '2026-10-30T01:00:00Z'},
        {id: 3, status: 'failed', event_id: 'evt-3', error_code: 'lease_expired', created_at: '2026-10-29T00:00:00Z'},
      ];
    } else if (path === '/internal-tasks/summary') {
      body = {queued: 1, running: 1, succeeded: 0, failed: 1, overdue_queued: 0, expired_running: 0};
    } else throw new Error(`Unexpected fetch ${path}`);
    return {ok: true, status: 200, json: async () => body};
  },
});
let script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
// Test-only access to closures
script = script.replace(/\}\)\(\);\s*$/, 'globalThis.testTaskApi = taskApi; globalThis.testRefreshInternalTasks = refreshInternalTasks; })();');
vm.runInContext(script, context);

(async () => {
  // Connect
  el('operator-token').value = 'synthetic-token';
  el('access-form').listeners.submit({preventDefault() {}});
  for (let attempt = 0; attempt < 20 && el('connect-button').disabled; attempt++) {
    await new Promise(resolve => setImmediate(resolve));
  }
  assert.equal(el('access-status').textContent, 'Conectado');

  // Verify internal tasks were loaded on connect
  assert(requests.some(r => r.path === '/internal-tasks/'));
  assert(requests.some(r => r.path === '/internal-tasks/summary'));

  // Verify fetch options
  for (const {options} of requests) {
    assert.equal(options.headers.Authorization, 'Bearer synthetic-token');
    assert.equal(options.credentials, 'omit');
    assert.equal(options.redirect, 'error');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.referrerPolicy, 'no-referrer');
  }

  // Test filter change triggers filtered request
  const before = requests.length;
  el('it-filter').value = 'queued';
  el('it-filter').listeners.change();
  await new Promise(resolve => setImmediate(resolve));
  assert(requests.some(r => r.path === '/internal-tasks/?status=queued'));

  // Test invalid routes rejected before fetch
  for (const path of [
    'https://example.invalid/internal-tasks/', '//example.invalid/internal-tasks/',
    '/internal-tasks/?status=invalid', '/internal-tasks/?status=queued&extra=1',
    '/internal-tasks/\n', '/internal-tasks/999',
  ]) {
    const before = requests.length;
    await assert.rejects(context.testTaskApi(path));
    assert.equal(requests.length, before, `Rejected before fetch: ${path}`);
  }

  // Test valid routes accepted
  for (const path of [
    '/internal-tasks/', '/internal-tasks/?status=queued',
    '/internal-tasks/?status=running', '/internal-tasks/?status=succeeded',
    '/internal-tasks/?status=failed', '/internal-tasks/summary',
  ]) {
    await context.testTaskApi(path);
    assert.equal(requests.at(-1).path, path);
  }

  // Test disconnect clears task panel
  el('disconnect-button').listeners.click();
  assert.equal(el('it-count').textContent, '—');
  assert.equal(el('it-summary').textContent, 'Resumo indisponível.');
  assert.equal(el('it-filter').value, '');

  console.log('PASS internal tasks panel: connect, filter, invalid routes rejected, disconnect');
})().catch(error => { console.error(error); process.exitCode = 1; });
