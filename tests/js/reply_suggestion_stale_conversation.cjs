const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  // WP-226 — Suggest agent reply');
const end = source.indexOf('  // WP-226 — Copy suggestion to reply form', start);
assert(start >= 0 && end > start);

function setup(fetchImpl) {
  const elements = new Map();
  const notices = [];
  const context = {
    bearer: 'synthetic-token',
    $: id => {
      if (!elements.has(id)) elements.set(id, {});
      return elements.get(id);
    },
    fetch: fetchImpl,
    notify: message => notices.push(message),
    withButton: (_button, callback) => callback(),
  };
  const button = context.$('conv-suggest-reply');
  button.addEventListener = (_event, callback) => { button.click = callback; };
  context.$('reply-conv-id').value = '12';
  context.$('conv-suggestion').hidden = true;
  context.$('conv-suggestion-text').textContent = '';
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  return {context, notices};
}

async function run() {
  let resolveFetch;
  const pending = setup(() => new Promise(resolve => { resolveFetch = resolve; }));
  const request = pending.context.$('conv-suggest-reply').click();
  pending.context.$('reply-conv-id').value = '13';
  resolveFetch({ok: true, status: 200, json: async () => ({suggestion: 'Resposta antiga'})});
  await request;
  assert.equal(pending.context.$('conv-suggestion').hidden, true);
  assert.equal(pending.context.$('conv-suggestion-text').textContent, '');
  assert.deepEqual(pending.notices, []);

  let resolveJson;
  const parsing = setup(() => Promise.resolve({
    ok: true,
    status: 200,
    json: () => new Promise(resolve => { resolveJson = resolve; }),
  }));
  const parsingRequest = parsing.context.$('conv-suggest-reply').click();
  await new Promise(resolve => setImmediate(resolve));
  parsing.context.$('reply-conv-id').value = '13';
  resolveJson({suggestion: 'Resposta antiga'});
  await parsingRequest;
  assert.equal(parsing.context.$('conv-suggestion').hidden, true);
  assert.equal(parsing.context.$('conv-suggestion-text').textContent, '');
  assert.deepEqual(parsing.notices, []);
}

run().catch(error => { console.error(error); process.exitCode = 1; });
