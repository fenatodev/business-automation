const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');

const searchEl = {value: '', _focused: false, addEventListener() {}, hidden: false};
function element(value = '') {
  return {
    value, textContent: '', hidden: true, disabled: false, handlers: {},
    addEventListener(event, callback) { this.handlers[event] = callback; },
    focus() { this._focused = true; },
    reset() {
      elements.get('reply-template-name').value = '';
      elements.get('reply-template-content').value = '';
    },
    _focused: false,
  };
}

const elements = new Map([
  ['reply-template-form', element()],
  ['reply-template-name', element()],
  ['reply-template-content', element()],
  ['reply-template-name-count', element()],
  ['reply-template-content-count', element()],
  ['reply-template-save', element()],
  ['reply-template-cancel-edit', element()],
  ['reply-template-save-status', element()],
  ['reply-template-load-status', element()],
  ['reply-template-search', searchEl],
  ['reply-template-filter-status', element()],
]);

const originalItem = {
  className: 'reply-template-item',
  dataset: {templateId: '10', templateName: 'Saudação', searchText: 'saudação'},
  children: [],
  hidden: false,
};

// After loadReplyTemplateList, the list contains the created item
let createdEditButtonFocused = false;
const list = {
  children: [originalItem],
  _setCreated(createdTemplate) {
    const createdItem = {
      className: 'reply-template-item',
      dataset: {templateId: String(createdTemplate.id), templateName: createdTemplate.name, searchText: createdTemplate.name.toLowerCase()},
      children: [{
        className: 'secondary reply-template-edit',
        focus() { createdEditButtonFocused = true; },
      }],
      hidden: false,
    };
    this.children = [originalItem, createdItem];
  },
};

let promptValue = 'Cópia de Saudação';
let promptCalls = 0;
let apiCalls = 0;
let editingReplyTemplateId = null;
let replyTemplateDuplicating = false;
const document = {createElement() { return {className: '', setAttribute() {}, textContent: '', hidden: false, children: [], querySelector() {}}; }};

const context = {
  bearer: 'synthetic-token', company: 3, document,
  $: id => elements.get(id) || (id === 'reply-template-list' ? list : null),
  confirm() { return true; },
  templateApi() { apiCalls++; return Promise.resolve({id: 99, name: promptValue, content: 'Olá'}); },
  updateReplyTemplateCharacterCount() {},
  notify() {},
  loadReplyTemplates() {},
  addEventListener() {},
  prompt(msg, defaultVal) { promptCalls++; return promptValue; },
};

// Mock loadReplyTemplateList that populates the created item
context.loadReplyTemplateList = async function() {
  list._setCreated({id: 99, name: promptValue, content: 'Olá'});
};

// Extract suggestReplyTemplateDuplicateName
const suggestStart = source.indexOf('  function suggestReplyTemplateDuplicateName(');
let suggestDepth = 0, suggestEnd;
for (let i = suggestStart; i < source.length; i++) {
  if (source[i] === '{') suggestDepth++;
  if (source[i] === '}') { suggestDepth--; if (suggestDepth === 0) { suggestEnd = i + 1; break; } }
}
const suggestFn = source.slice(suggestStart, suggestEnd);

// Extract setReplyTemplateDuplicateButtonsDisabled
const setDupStart = source.indexOf('  function setReplyTemplateDuplicateButtonsDisabled(');
let setDupDepth = 0, setDupEnd;
for (let i = setDupStart; i < source.length; i++) {
  if (source[i] === '{') setDupDepth++;
  if (source[i] === '}') { setDupDepth--; if (setDupDepth === 0) { setDupEnd = i + 1; break; } }
}
const setDupFn = source.slice(setDupStart, setDupEnd);

// Extract duplicateReplyTemplate
const dupStart = source.indexOf('  async function duplicateReplyTemplate(');
let dupDepth = 0, dupEnd;
for (let i = dupStart; i < source.length; i++) {
  if (source[i] === '{') dupDepth++;
  if (source[i] === '}') { dupDepth--; if (dupDepth === 0) { dupEnd = i + 1; break; } }
}
const dupFn = source.slice(dupStart, dupEnd);

// Extract normalizeReplyTemplateSearchText
const normStart = source.indexOf('  function normalizeReplyTemplateSearchText(');
let normDepth = 0, normEnd;
for (let i = normStart; i < source.length; i++) {
  if (source[i] === '{') normDepth++;
  if (source[i] === '}') { normDepth--; if (normDepth === 0) { normEnd = i + 1; break; } }
}
const normFn = source.slice(normStart, normEnd);

// Extract applyReplyTemplateFilter (minimal stub)
const applyFilter = `
  function applyReplyTemplateFilter() {}
`;

const code = normFn + '\n' + suggestFn + '\n' + setDupFn + '\n' + dupFn + '\n' + applyFilter + `
  let editingReplyTemplateId = null;
  let replyTemplateDuplicating = false;
  this.duplicateReplyTemplate = duplicateReplyTemplate;
`;

vm.createContext(context);
vm.runInContext(code, context);

async function run() {
  // Test 1: duplicateReplyTemplate focuses edit button of created item
  promptValue = 'Cópia de Saudação';
  apiCalls = 0;
  promptCalls = 0;
  createdEditButtonFocused = false;
  list.children = [originalItem];
  await context.duplicateReplyTemplate({id: 10, name: 'Saudação', content: 'Olá'}, {disabled: false});
  assert.equal(apiCalls, 1, 'API called once');
  assert.equal(promptCalls, 1, 'Prompt called once');
  assert.equal(createdEditButtonFocused, true, 'Edit button of created item focused');

  // Test 2: duplicate with hidden item clears search
  apiCalls = 0;
  searchEl.value = 'filtro';
  // Make the created item hidden
  list._setCreated = function(t) {
    const createdItem = {
      className: 'reply-template-item',
      dataset: {templateId: String(t.id), templateName: t.name, searchText: t.name.toLowerCase()},
      children: [{
        className: 'secondary reply-template-edit',
        focus() { createdEditButtonFocused = true; },
      }],
      hidden: true,
    };
    this.children = [originalItem, createdItem];
  };
  createdEditButtonFocused = false;
  await context.duplicateReplyTemplate({id: 10, name: 'Saudação', content: 'Olá'}, {disabled: false});
  assert.equal(searchEl.value, '', 'Search cleared when created item hidden by filter');
  assert.equal(createdEditButtonFocused, true, 'Edit button focused even when hidden');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
