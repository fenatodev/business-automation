const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = source.indexOf('  let editingReplyTemplateId = null;');
const end = source.indexOf('\n})();', start);
assert(start >= 0 && end > start);

function element(value = '') {
  return {
    value, textContent: '', hidden: false, handlers: {}, focused: false,
    addEventListener(event, callback) { this.handlers[event] = callback; },
    focus() { this.focused = true; },
    reset() {},
  };
}

function setup({hidden}) {
  const elements = new Map([
    ['reply-template-form', element()],
    ['reply-template-name', element()],
    ['reply-template-content', element()],
    ['reply-template-name-count', element()],
    ['reply-template-content-count', element()],
    ['reply-template-save', element()],
    ['reply-template-cancel-edit', element()],
    ['reply-template-save-status', element()],
    ['reply-template-search', element('saudação')],
  ]);
  const item = element();
  item.className = 'reply-template-item';
  item.hidden = hidden;
  const search = elements.get('reply-template-search');
  let filterApplications = 0;
  const context = {
    $: id => elements.get(id) || null,
    confirm: () => true,
    updateReplyTemplateCharacterCount() {},
    applyReplyTemplateFilter() {
      filterApplications += 1;
      item.hidden = search.value !== '';
    },
  };
  vm.createContext(context);
  vm.runInContext(
    source.slice(start, end) + '\nthis.beginReplyTemplateEdit = beginReplyTemplateEdit; this.cancelReplyTemplateEdit = cancelReplyTemplateEdit;',
    context,
  );
  const trigger = element();
  trigger.isConnected = true;
  trigger.closest = selector => selector === '.reply-template-item' ? item : null;
  context.beginReplyTemplateEdit({id: 7, name: 'Saudação', content: 'Olá'}, trigger);
  return {context, elements, item, trigger, get filterApplications() { return filterApplications; }};
}

const hidden = setup({hidden: true});
hidden.context.cancelReplyTemplateEdit();
assert.equal(hidden.elements.get('reply-template-search').value, '');
assert.equal(hidden.item.hidden, false);
assert.equal(hidden.trigger.focused, true);
assert.equal(hidden.filterApplications, 1);

const visible = setup({hidden: false});
visible.context.cancelReplyTemplateEdit();
assert.equal(visible.elements.get('reply-template-search').value, 'saudação');
assert.equal(visible.trigger.focused, true);
assert.equal(visible.filterApplications, 0);
