const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let replyTemplateLoadVersion = 0;');
const end = source.indexOf('\n\n  let replyTemplateSaving = false;', start);
assert(start >= 0 && end > start);

function setup(templates) {
  const list = {
    children: [], attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
  };
  const search = {value: '', handlers: {}, addEventListener(event, handler) { this.handlers[event] = handler; }, focus() { this.focused = true; }};
  const clearSearch = {disabled: true, addEventListener(event, handler) { this.handler = handler; }};
  const filterStatus = {textContent: ''};
  const loadStatus = {textContent: ''};
  const retry = {hidden: false, disabled: false, addEventListener() {}};
  const elements = {
    'reply-template-list': list,
    'reply-template-search': search,
    'reply-template-search-clear': clearSearch,
    'reply-template-filter-status': filterStatus,
    'reply-template-load-status': loadStatus,
    'reply-template-load-retry': retry,
  };
  const context = {
    bearer: 'synthetic-token', company: 3,
    $: id => elements[id] || null,
    templateApi: async (path, method) => method === 'GET' ? templates : null,
    confirm: () => true,
    notify() {},
    loadReplyTemplates() {},
    document: {
      createElement(tag) {
        return {
          tagName: tag, className: '', textContent: '', attributes: {}, children: [], dataset: {}, hidden: false,
          setAttribute(name, value) { this.attributes[name] = value; },
          appendChild(child) { this.children.push(child); },
          addEventListener(event, handler) { this.handlers ||= {}; this.handlers[event] = handler; },
          remove() { const index = list.children.indexOf(this); if (index >= 0) list.children.splice(index, 1); },
          click() { this.handlers?.click?.(); },
        };
      },
    },
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end) + '\nthis.loadReplyTemplateList = loadReplyTemplateList; this.deleteReplyTemplate = deleteReplyTemplate;', context);
  return {context, list, search, clearSearch, filterStatus};
}

async function run() {
  const ui = setup([
    {id: 1, name: 'Saudação', content: 'Olá, tudo bem?'},
    {id: 2, name: 'Encerramento', content: 'Obrigado pelo contato.'},
  ]);
  await ui.context.loadReplyTemplateList();
  assert.equal(ui.list.children.length, 2);

  ui.search.value = 'obrigado';
  ui.search.handlers.input();
  assert.deepEqual(ui.list.children.map(item => item.hidden), [true, false]);
  assert.equal(ui.filterStatus.textContent, '1 template corresponde à busca.');

  ui.search.value = 'saudacao';
  ui.search.handlers.input();
  assert.deepEqual(ui.list.children.map(item => item.hidden), [false, true]);
  assert.equal(ui.filterStatus.textContent, '1 template corresponde à busca.');

  ui.search.value = 'a';
  ui.search.handlers.input();
  assert.deepEqual(ui.list.children.map(item => item.hidden), [false, false]);
  assert.equal(ui.filterStatus.textContent, '2 templates correspondem à busca.');

  ui.search.value = 'inexistente';
  ui.search.handlers.input();
  assert.deepEqual(ui.list.children.map(item => item.hidden), [true, true]);
  assert.equal(ui.filterStatus.textContent, 'Nenhum template corresponde à busca.');
  assert.equal(ui.clearSearch.disabled, false);

  ui.search.value = '';
  ui.search.handlers.input();
  let escapePrevented = false;
  ui.search.handlers.keydown({key: 'Escape', currentTarget: ui.search, preventDefault() { escapePrevented = true; }});
  assert.equal(escapePrevented, false);
  assert.equal(ui.search.value, '');

  ui.search.value = 'inexistente';
  ui.search.handlers.input();
  escapePrevented = false;
  ui.search.handlers.keydown({key: 'Escape', currentTarget: ui.search, preventDefault() { escapePrevented = true; }});
  assert.equal(escapePrevented, true);
  assert.equal(ui.search.value, '');
  assert.deepEqual(ui.list.children.map(item => item.hidden), [false, false]);
  assert.equal(ui.filterStatus.textContent, '');
  assert.equal(ui.clearSearch.disabled, true);

  ui.search.value = 'inexistente';
  ui.search.handlers.input();
  escapePrevented = false;
  ui.search.handlers.keydown({key: 'Enter', currentTarget: ui.search, preventDefault() { escapePrevented = true; }});
  assert.equal(escapePrevented, false);
  assert.equal(ui.search.value, 'inexistente');
  assert.deepEqual(ui.list.children.map(item => item.hidden), [true, true]);

  ui.clearSearch.handler();
  assert.equal(ui.search.value, '');
  assert.equal(ui.search.focused, true);
  assert.deepEqual(ui.list.children.map(item => item.hidden), [false, false]);
  assert.equal(ui.filterStatus.textContent, '');
  assert.equal(ui.clearSearch.disabled, true);

  ui.search.value = 'saudação';
  ui.search.handlers.input();
  await ui.context.deleteReplyTemplate(1, ui.list.children[0], ui.list.children[0].children[1]);
  assert.deepEqual(ui.list.children.map(item => item.hidden), [true]);
  assert.equal(ui.filterStatus.textContent, 'Nenhum template corresponde à busca.');

  await ui.context.deleteReplyTemplate(2, ui.list.children[0], ui.list.children[0].children[1]);
  assert.equal(ui.list.children.length, 1);
  assert.equal(ui.list.children[0].textContent, 'Nenhum template salvo.');
  assert.equal(ui.filterStatus.textContent, '');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
