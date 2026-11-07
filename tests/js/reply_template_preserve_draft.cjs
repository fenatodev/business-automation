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
select.value = '4';
select.options = [{dataset: {content: 'bom dia'}}];
select.selectedIndex = 0;
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

select.change({target: select});
assert.equal(reply.value, 'Olá, bom diacliente!');
assert.equal(reply.selectionStart, 12);
assert.equal(reply.selectionEnd, 12);
assert.equal(select.value, '');

select.value = '4';
select.change({target: select});
assert.equal(reply.value, 'Olá, bom diabom diacliente!');
assert.equal(reply.selectionStart, 19);
assert.equal(select.value, '');

reply.value = 'Olá cliente';
reply.selectionStart = 4;
reply.selectionEnd = 11;
select.value = '5';
select.options = [{dataset: {content: 'equipe'}}];
select.change({target: select});
assert.equal(reply.value, 'Olá equipe');
assert.equal(reply.selectionStart, 10);
assert.equal(reply.selectionEnd, 10);
assert.equal(select.value, '');

reply.value = '';
reply.selectionStart = 0;
reply.selectionEnd = 0;
select.value = '6';
select.options = [{dataset: {content: 'Olá!'}}];
select.change({target: select});
assert.equal(reply.value, 'Olá!');
assert.equal(reply.selectionStart, 4);
assert.equal(select.value, '');

reply.value = 'Rascunho';
select.value = '';
select.options = [];
select.change({target: select});
assert.equal(reply.value, 'Rascunho');
