const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  async function deleteReplyTemplate(');
const end = source.indexOf('\n\n  let replyTemplateSaving', start);
assert(start >= 0 && end > start);

function setup() {
  const requests = [];
  const search = {focused: false, focus() { this.focused = true; }};
  const list = {children: []};
  const context = {
    bearer: 'synthetic-token', company: 3,
    confirm: () => true,
    templateApi(path, method) {
      return new Promise(resolve => requests.push({path, method, resolve}));
    },
    notify() {},
    loadReplyTemplates() {},
    applyReplyTemplateFilter() {},
    $(id) {
      if (id === 'reply-template-list') return list;
      if (id === 'reply-template-search') return search;
      return null;
    },
    document: {createElement: () => ({className: '', textContent: '', setAttribute() {}})},
  };
  vm.createContext(context);
  vm.runInContext('function applyReplyTemplateFilter() {}\n' + source.slice(start, end) +
    '\nthis.deleteReplyTemplate = deleteReplyTemplate;', context);
  return {context, list, search, requests};
}

async function run() {
  const ui = setup();
  const nextButton = {focused: false, focus() { this.focused = true; }};
  const nextItem = {
    className: 'reply-template-item', hidden: false,
    querySelector: selector => selector === '.danger' ? nextButton : null,
  };
  const currentItem = {remove() { ui.list.children.shift(); }};
  ui.list.children.push(currentItem, nextItem);
  const deleted = ui.context.deleteReplyTemplate(10, currentItem, {disabled: false});
  ui.requests[0].resolve({});
  await deleted;
  assert.equal(nextButton.focused, true);
  assert.equal(ui.search.focused, false);

  const lastUi = setup();
  const lastItem = {remove() { lastUi.list.children.shift(); }};
  lastUi.list.children.push(lastItem);
  const deleteLast = lastUi.context.deleteReplyTemplate(11, lastItem, {disabled: false});
  lastUi.requests[0].resolve({});
  await deleteLast;
  assert.equal(lastUi.search.focused, true);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
