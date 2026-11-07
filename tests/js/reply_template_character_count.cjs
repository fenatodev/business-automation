const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  function updateReplyTemplateCharacterCount(');
const end = source.indexOf('\n\n  function applyReplyTemplateFilter()', start);
assert(start >= 0 && end > start);

function input(value) {
  return {
    value,
    addEventListener(event, handler) { this.handlers ||= {}; this.handlers[event] = handler; },
  };
}

const elements = new Map([
  ['reply-template-name', input('Olá')],
  ['reply-template-name-count', {textContent: ''}],
  ['reply-template-content', input('')],
  ['reply-template-content-count', {textContent: ''}],
]);
const context = {$: id => elements.get(id) || null};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);

assert.equal(elements.get('reply-template-name-count').textContent, '3/100 caracteres');
assert.equal(elements.get('reply-template-content-count').textContent, '0/4000 caracteres');

elements.get('reply-template-name').value = 'Saudação';
elements.get('reply-template-name').handlers.input();
assert.equal(elements.get('reply-template-name-count').textContent, '8/100 caracteres');

elements.get('reply-template-content').value = 'Resposta pronta';
elements.get('reply-template-content').handlers.input();
assert.equal(elements.get('reply-template-content-count').textContent, '15/4000 caracteres');
