// Execute the delivered UI with synthetic DOM/fetch; no browser/network required.
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
    else if (path === '/review-queue/summary') body = {pending: 101, approve: 0, reject: 0};
    else if (path === '/review-queue/aging') body = {overdue_pending: 0};
    else if (path.startsWith('/review-queue/')) body = [];
    else throw new Error(`Unexpected fetch ${path}`);
    return {ok: true, status: 200, json: async () => body};
  },
});
let script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
// Test-only access to the closure; delivered script receives no global API.
script = script.replace(/\}\)\(\);\s*$/, 'globalThis.testReviewApi = reviewApi; })();');
vm.runInContext(script, context);

(async () => {
  el('operator-token').value = 'synthetic-token';
  el('access-form').listeners.submit({preventDefault() {}});
  for (let attempt = 0; attempt < 20 && el('connect-button').disabled; attempt++) {
    await new Promise(resolve => setImmediate(resolve));
  }
  assert.equal(el('access-status').textContent, 'Conectado');
  assert(requests.some(r => r.path === '/review-queue/?limit=50&offset=0'));
  await el('rq-next').listeners.click();
  assert(requests.some(r => r.path === '/review-queue/?limit=50&offset=50'));
  await el('rq-prev').listeners.click();
  assert.equal(requests.filter(r => r.path === '/review-queue/?limit=50&offset=0').length, 2);
  for (const {options} of requests) {
    assert.equal(options.headers.Authorization, 'Bearer synthetic-token');
    assert.equal(options.credentials, 'omit');
    assert.equal(options.redirect, 'error');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.referrerPolicy, 'no-referrer');
  }
  for (const path of [
    'https://example.invalid/review-queue/', '//example.invalid/review-queue/',
    '/review-queue/?limit=0&offset=0', '/review-queue/?limit=101&offset=0',
    '/review-queue/?limit=50&offset=-1', '/review-queue/?limit=50&offset=0&extra=1',
    '/review-queue/?limit=50&offset=0&offset=1', '/review-queue/?limit=50&offset=0#fragment',
    '/review-queue/?limit=50&offset=0\n', '/review-queue/\n',
    '/review-queue/?offset=0&limit=50',
  ]) {
    const before = requests.length;
    await assert.rejects(context.testReviewApi(path));
    assert.equal(requests.length, before, `Rejected before fetch: ${path}`);
  }
  for (const path of ['/review-queue/', '/review-queue/?limit=1&offset=0',
                      '/review-queue/?limit=100&offset=100']) {
    await context.testReviewApi(path);
    assert.equal(requests.at(-1).path, path);
  }
  console.log('PASS connected pagination 0->50->0; invalid routes rejected before fetch');
})().catch(error => { console.error(error); process.exitCode = 1; });
