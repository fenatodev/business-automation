const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  // WP-459 — Insert a template without discarding the current reply draft');
const end = source.indexOf('  $("conv-note-save").addEventListener', start);
assert(start >= 0 && end > start);

const elements = new Map();
const context = {
  $: id => {
    if (!elements.has(id)) elements.set(id, {});
    return elements.get(id);
  },
};
const select = context.$('reply-template-select');
select.addEventListener = (event, callback) => { select.change = callback; };
const reply = context.$('reply-message');
reply.value = 'Olá, cliente!';
reply.selectionStart = 5;
reply.selectionEnd = 5;
reply.setSelectionRange = (start, end) => {
  reply.selectionStart = start;
  reply.selectionEnd = end;
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);

select.change({target: {
  value: '4',
  selectedIndex: 0,
  options: [{dataset: {content: 'bom dia'}}],
}});
assert.equal(reply.value, 'Olá, bom diacliente!');
assert.equal(reply.selectionStart, 12);
assert.equal(reply.selectionEnd, 12);

reply.value = 'Olá cliente';
reply.selectionStart = 4;
reply.selectionEnd = 11;
select.change({target: {
  value: '5',
  selectedIndex: 0,
  options: [{dataset: {content: 'equipe'}}],
}});
assert.equal(reply.value, 'Olá equipe');
assert.equal(reply.selectionStart, 10);
assert.equal(reply.selectionEnd, 10);

reply.value = '';
reply.selectionStart = 0;
reply.selectionEnd = 0;
select.change({target: {
  value: '6',
  selectedIndex: 0,
  options: [{dataset: {content: 'Olá!'}}],
}});
assert.equal(reply.value, 'Olá!');
assert.equal(reply.selectionStart, 4);

reply.value = 'Rascunho';
select.change({target: {value: '', options: []}});
assert.equal(reply.value, 'Rascunho');
