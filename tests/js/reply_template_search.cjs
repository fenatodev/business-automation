const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let replyTemplateLoadVersion = 0;');
const end = source.indexOf('\n\n  $("reply-template-load-retry")', start);
assert(start >= 0 && end > start);

function setup(templates) {
  const list = {
    children: [], attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
  };
  const search = {value: '', addEventListener(event, handler) { this.handler = handler; }};
  const filterStatus = {textContent: ''};
  const loadStatus = {textContent: ''};
  const retry = {hidden: false, disabled: false, addEventListener() {}};
  const elements = {
    'reply-template-list': list,
    'reply-template-search': search,
    'reply-template-filter-status': filterStatus,
    'reply-template-load-status': loadStatus,
    'reply-template-load-retry': retry,
  };
  const context = {
    bearer: 'synthetic-token', company: 3,
    $: id => elements[id] || null,
    templateApi: async () => templates,
    document: {
      createElement(tag) {
        return {
          tagName: tag, className: '', textContent: '', attributes: {}, children: [], dataset: {}, hidden: false,
          setAttribute(name, value) { this.attributes[name] = value; },
          appendChild(child) { this.children.push(child); },
          addEventListener() {},
        };
      },
    },
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end) + '\nthis.loadReplyTemplateList = loadReplyTemplateList;', context);
  return {context, list, search, filterStatus};
}

async function run() {
  const ui = setup([
    {id: 1, name: 'Saudação', content: 'Olá, tudo bem?'},
    {id: 2, name: 'Encerramento', content: 'Obrigado pelo contato.'},
  ]);
  await ui.context.loadReplyTemplateList();
  assert.equal(ui.list.children.length, 2);

  ui.search.value = 'obrigado';
  ui.search.handler();
  assert.deepEqual(ui.list.children.map(item => item.hidden), [true, false]);
  assert.equal(ui.filterStatus.textContent, '');

  ui.search.value = 'inexistente';
  ui.search.handler();
  assert.deepEqual(ui.list.children.map(item => item.hidden), [true, true]);
  assert.equal(ui.filterStatus.textContent, 'Nenhum template corresponde à busca.');

  ui.search.value = '';
  ui.search.handler();
  assert.deepEqual(ui.list.children.map(item => item.hidden), [false, false]);
  assert.equal(ui.filterStatus.textContent, '');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
