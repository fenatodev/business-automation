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
select.options = [{dataset: {content: 'Bom dia'}, textContent: 'Saudação'}];
select.selectedIndex = 0;
const reply = context.$('reply-message');
reply.value = 'Olá!';
reply.selectionStart = 5;
reply.selectionEnd = 5;
reply.setSelectionRange = (start, end) => {
  reply.selectionStart = start;
  reply.selectionEnd = end;
};
reply.focus = () => { reply.focused = true; };
const status = context.$('reply-template-insert-status');
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);

select.change({target: select});
assert.equal(reply.value, 'Olá!Bom dia');
assert.equal(reply.selectionStart, 12);
assert.equal(reply.focused, true);
assert.equal(status.textContent, 'Template "Saudação" inserido na resposta.');
assert.equal(select.value, '');

status.textContent = '';
select.value = '';
select.options = [];
select.change({target: select});
assert.equal(reply.value, 'Olá!Bom dia');
assert.equal(status.textContent, '');
