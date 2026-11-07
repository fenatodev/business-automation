const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  async function deleteReplyTemplate(');
const end = source.indexOf('\n\n  let replyTemplateSaving', start);
assert(start >= 0 && end > start);

function setup(confirmed = true) {
  const requests = [];
  const notifications = [];
  const removed = [];
  const emptyMessages = [];
  const loadStatus = {textContent: ""};
  const list = {
    children: [{}],
    appendChild(element) {
      this.children.push(element);
      emptyMessages.push(element.textContent);
    },
  };
  let confirmations = 0;
  const context = {
    bearer: 'synthetic-token',
    company: 3,
    confirm() {
      confirmations += 1;
      return confirmed;
    },
    templateApi(path, method) {
      let resolve;
      let reject;
      const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
      requests.push({path, method, resolve, reject, promise});
      return promise;
    },
    notify: message => notifications.push(message),
    loadReplyTemplates() {},
    $(id) {
      if (id === 'reply-template-list') return list;
      if (id === 'reply-template-load-status') return loadStatus;
      return null;
    },
    document: {
      createElement(tag) {
        assert.equal(tag, 'p');
        return {
          className: '', textContent: '', attributes: {},
          setAttribute(name, value) { this.attributes[name] = value; },
        };
      },
    },
  };
  vm.createContext(context);
  vm.runInContext('function applyReplyTemplateFilter() {}\n' + source.slice(start, end) + '\nthis.deleteReplyTemplate = deleteReplyTemplate;', context);
  const button = {disabled: false};
  const item = {remove() { removed.push(true); list.children.pop(); }};
  return {context, button, item, list, loadStatus, emptyMessages, requests, notifications, removed, get confirmations() { return confirmations; }};
}

async function run() {
  const success = setup();
  const firstDelete = success.context.deleteReplyTemplate(10, success.item, success.button);
  const duplicateDelete = success.context.deleteReplyTemplate(10, success.item, success.button);
  assert.equal(success.confirmations, 1);
  assert.equal(success.requests.length, 1);
  assert.equal(success.requests[0].path, '/companies/3/reply-templates/10');
  assert.equal(success.requests[0].method, 'DELETE');
  assert.equal(success.button.disabled, true);
  assert.equal(success.loadStatus.textContent, 'Excluindo template');
  success.requests[0].resolve({});
  await Promise.all([firstDelete, duplicateDelete]);
  assert.equal(success.button.disabled, false);
  assert.deepEqual(success.removed, [true]);
  assert.deepEqual(success.emptyMessages, ['Nenhum template salvo.']);
  assert.equal(success.list.children.at(-1).attributes.role, 'status');
  assert.equal(success.loadStatus.textContent, 'Template excluído.');
  assert.deepEqual(success.notifications, ['Template excluído.']);

  const failure = setup();
  const failedDelete = failure.context.deleteReplyTemplate(11, failure.item, failure.button);
  assert.equal(failure.button.disabled, true);
  assert.equal(failure.loadStatus.textContent, 'Excluindo template');
  failure.requests[0].reject(new Error('synthetic failure'));
  await failedDelete;
  assert.equal(failure.button.disabled, false);
  assert.deepEqual(failure.removed, []);
  assert.equal(failure.loadStatus.textContent, 'Não foi possível excluir o template.');
  assert.deepEqual(failure.emptyMessages, []);
  assert.deepEqual(failure.notifications, ['Erro ao excluir template.']);

  const cancelled = setup(false);
  await cancelled.context.deleteReplyTemplate(12, cancelled.item, cancelled.button);
  assert.equal(cancelled.requests.length, 0);
  assert.equal(cancelled.button.disabled, false);
  assert.deepEqual(cancelled.removed, []);
  assert.equal(cancelled.loadStatus.textContent, '');

  const remaining = setup();
  remaining.list.children = [{}, {}, {}];
  const removeOne = remaining.context.deleteReplyTemplate(13, remaining.item, remaining.button);
  remaining.requests[0].resolve({});
  await removeOne;
  assert.deepEqual(remaining.emptyMessages, []);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
