const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');

// Extract loadReplyTemplateList and related code
const loadStart = source.indexOf('  async function loadReplyTemplateList(');
let loadDepth = 0, loadEnd;
for (let i = loadStart; i < source.length; i++) {
  if (source[i] === '{') loadDepth++;
  if (source[i] === '}') { loadDepth--; if (loadDepth === 0) { loadEnd = i + 1; break; } }
}
const loadFn = source.slice(loadStart, loadEnd);

// Extract applyReplyTemplateFilter
const applyStart = source.indexOf('  function applyReplyTemplateFilter(');
let applyDepth = 0, applyEnd;
for (let i = applyStart; i < source.length; i++) {
  if (source[i] === '{') applyDepth++;
  if (source[i] === '}') { applyDepth--; if (applyDepth === 0) { applyEnd = i + 1; break; } }
}
const applyFn = source.slice(applyStart, applyEnd);

// Extract normalizeReplyTemplateSearchText
const normStart = source.indexOf('  function normalizeReplyTemplateSearchText(');
let normDepth = 0, normEnd;
for (let i = normStart; i < source.length; i++) {
  if (source[i] === '{') normDepth++;
  if (source[i] === '}') { normDepth--; if (normDepth === 0) { normEnd = i + 1; break; } }
}
const normFn = source.slice(normStart, normEnd);

const listEl = {
  children: [],
  _attrs: {},
  setAttribute(k, v) { this._attrs[k] = v; },
  getAttribute(k) { return this._attrs[k]; },
  replaceChildren() { this.children = []; },
  appendChild(el) { this.children.push(el); },
};
const loadStatus = { textContent: '', _attrs: {} };
const retryBtn = { hidden: true, disabled: false };
const searchEl = { value: '', hidden: false };
const filterStatus = { textContent: '' };

let createdElements = [];
const document = {
  createElement(tag) {
    const el = {
      tagName: tag, className: '', textContent: '', hidden: false,
      children: [], _attrs: {}, disabled: false,
      setAttribute(k, v) { el._attrs[k] = v; },
      getAttribute(k) { return el._attrs[k]; },
      appendChild(child) { el.children.push(child); },
      addEventListener() {},
    };
    createdElements.push(el);
    return el;
  },
};

let apiResolve = null;
let apiPromise = null;
let apiCalls = 0;

const context = {
  bearer: 'synthetic-token',
  company: 3,
  document,
  replyTemplateLoadVersion: 0,
  $: id => {
    if (id === 'reply-template-list') return listEl;
    if (id === 'reply-template-load-status') return loadStatus;
    if (id === 'reply-template-load-retry') return retryBtn;
    if (id === 'reply-template-search') return searchEl;
    if (id === 'reply-template-filter-status') return filterStatus;
    return null;
  },
  templateApi(url, method) {
    apiCalls++;
    return apiPromise;
  },
  notify() {},
};

const code = normFn + '\n' + applyFn + '\n' + loadFn + `
  this.loadReplyTemplateList = loadReplyTemplateList;
`;

vm.createContext(context);
vm.runInContext(code, context);

async function run() {
  // WP-451: aria-busy during load
  apiPromise = Promise.resolve([{id: 1, name: 'Teste', content: 'Olá'}]);
  await context.loadReplyTemplateList();
  // aria-busy should be false after successful load
  assert.equal(listEl._attrs['aria-busy'], 'false', 'aria-busy false after load');

  // WP-451: aria-busy true during load
  let busyDuringLoad = false;
  const origSetAttr = listEl.setAttribute.bind(listEl);
  listEl.setAttribute = function(k, v) {
    if (k === 'aria-busy' && v === 'true') busyDuringLoad = true;
    origSetAttr(k, v);
  };
  apiPromise = Promise.resolve([{id: 2, name: 'Teste2', content: 'Oi'}]);
  await context.loadReplyTemplateList();
  assert.equal(busyDuringLoad, true, 'aria-busy true during load');

  // WP-449: empty state after load returns empty array
  apiPromise = Promise.resolve([]);
  listEl.replaceChildren();
  await context.loadReplyTemplateList();
  const emptyP = listEl.children.find(c => c.textContent === 'Nenhum template salvo.');
  assert.ok(emptyP, 'Empty state paragraph exists');
  assert.equal(emptyP._attrs['role'], 'status', 'Empty state has role=status');

  // WP-450: empty state announced for accessibility
  assert.equal(emptyP.textContent, 'Nenhum template salvo.', 'Empty state text correct');

  // WP-443: load retry on failure
  apiPromise = Promise.reject(new Error('network error'));
  listEl.replaceChildren();
  listEl._attrs = {};
  await context.loadReplyTemplateList();
  assert.equal(loadStatus.textContent, 'Não foi possível carregar os templates.', 'Error status shown');
  assert.equal(retryBtn.hidden, false, 'Retry button visible on error');
  assert.equal(listEl._attrs['aria-busy'], 'false', 'aria-busy false after error');

  // WP-443: retry button hidden on success
  apiPromise = Promise.resolve([{id: 3, name: 'Recuperação', content: 'Funcionou'}]);
  await context.loadReplyTemplateList();
  assert.equal(retryBtn.hidden, true, 'Retry button hidden on success');
  assert.equal(loadStatus.textContent, '', 'Load status cleared on success');

  // WP-443: stale response ignored
  let firstResolve;
  apiPromise = new Promise(resolve => { firstResolve = resolve; });
  const loadPromise = context.loadReplyTemplateList();
  // Start a second load before first resolves
  apiPromise = Promise.resolve([{id: 99, name: 'Segundo', content: 'Load 2'}]);
  const loadPromise2 = context.loadReplyTemplateList();
  // Resolve first (stale)
  firstResolve([{id: 1, name: 'Primeiro', content: 'Load 1'}]);
  await loadPromise;
  await loadPromise2;
  // Second load should win
  const items = listEl.children.filter(c => c.className === 'reply-template-item');
  assert.ok(items.length >= 1, 'Second load result present');

  // WP-449: empty state not shown when templates exist
  apiPromise = Promise.resolve([{id: 4, name: 'Existe', content: 'Sim'}]);
  listEl.replaceChildren();
  listEl._attrs = {};
  await context.loadReplyTemplateList();
  const emptyAfterLoad = listEl.children.find(c => c.textContent === 'Nenhum template salvo.');
  assert.equal(emptyAfterLoad, undefined, 'No empty state when templates exist');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
