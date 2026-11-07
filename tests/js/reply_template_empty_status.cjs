const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let replyTemplateLoadVersion = 0;');
const end = source.indexOf('\n\n  $("reply-template-load-retry")', start);
assert(start >= 0 && end > start);

function setup(templates) {
  const list = {
    children: [],
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
  };
  const status = {textContent: ''};
  const search = {value: 'saudacao', addEventListener() {}};
  const clearSearch = {disabled: false, addEventListener() {}};
  const filterStatus = {textContent: '1 template corresponde à busca.'};
  const retry = {hidden: false, disabled: false, addEventListener() {}};
  const context = {
    bearer: 'synthetic-token',
    company: 3,
    $: id => ({
      'reply-template-list': list,
      'reply-template-load-status': status,
      'reply-template-load-retry': retry,
      'reply-template-search': search,
      'reply-template-search-clear': clearSearch,
      'reply-template-filter-status': filterStatus,
    })[id] || null,
    templateApi: async () => templates,
    document: {
      createElement(tag) {
        return {
          tagName: tag, className: '', textContent: '', attributes: {}, children: [],
          setAttribute(name, value) { this.attributes[name] = value; },
          appendChild(child) { this.children.push(child); },
          addEventListener() {},
        };
      },
    },
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end) + '\nthis.loadReplyTemplateList = loadReplyTemplateList;', context);
  return {context, list, status, clearSearch, filterStatus};
}

async function run() {
  const empty = setup([]);
  await empty.context.loadReplyTemplateList();
  assert.equal(empty.list.attributes['aria-busy'], 'false');
  assert.equal(empty.list.children.length, 1);
  assert.equal(empty.list.children[0].textContent, 'Nenhum template salvo.');
  assert.equal(empty.list.children[0].attributes.role, 'status');
  assert.equal(empty.status.textContent, '');
  assert.equal(empty.clearSearch.disabled, true);
  assert.equal(empty.filterStatus.textContent, '');

  const populated = setup([{id: 1, name: 'Saudação', content: 'Olá'}]);
  await populated.context.loadReplyTemplateList();
  assert.equal(populated.list.attributes['aria-busy'], 'false');
  assert.equal(populated.list.children.length, 1);
  assert.notEqual(populated.list.children[0].textContent, 'Nenhum template salvo.');
  assert.equal(populated.list.children[0].attributes.role, undefined);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
