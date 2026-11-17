const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('app/operator_ui/app.js', 'utf8');

const searchEl = {value: 'saudação', _focused: false, handlers: {}, hidden: false, addEventListener(event, callback) { this.handlers[event] = callback; }};
function element(value = '') {
  return {
    value, textContent: '', hidden: true, disabled: false, handlers: {},
    addEventListener(event, callback) { this.handlers[event] = callback; },
    focus() { this._focused = true; },
    reset() {},
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

let createdEditButtonFocused = false;
const list = {
  children: [originalItem],
  _setCreated(createdTemplate, hidden) {
    const createdItem = {
      className: 'reply-template-item',
      dataset: {templateId: String(createdTemplate.id), templateName: createdTemplate.name, searchText: createdTemplate.name.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')},
      children: [{
        className: 'secondary reply-template-edit',
        focus() { createdEditButtonFocused = true; },
      }],
      hidden: hidden || false,
    };
    this.children = [originalItem, createdItem];
  },
};

let promptValue = 'Cópia de Saudação';
let promptCalls = 0;
let apiCalls = 0;
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

// Mock loadReplyTemplateList — created item hidden by filter
context.loadReplyTemplateList = async function() {
  list._setCreated({id: 99, name: promptValue, content: 'Olá'}, true);
};

// Extract functions needed by duplicateReplyTemplate
function extractFn(name) {
  const s = source.indexOf('  ' + (name.includes('async ') ? '' : '') + name + '(');
  if (s < 0) return '';
  let d = 0, e;
  for (let i = s; i < source.length; i++) {
    if (source[i] === '{') d++;
    if (source[i] === '}') { d--; if (d === 0) { e = i + 1; break; } }
  }
  return source.slice(s, e);
}

const normFn = extractFn('function normalizeReplyTemplateSearchText');
const suggestFn = extractFn('function suggestReplyTemplateDuplicateName');
const setDupFn = extractFn('function setReplyTemplateDuplicateButtonsDisabled');
const dupFn = extractFn('async function duplicateReplyTemplate');
const applyFilter = '  function applyReplyTemplateFilter() {}';

const code = normFn + '\n' + suggestFn + '\n' + setDupFn + '\n' + dupFn + '\n' + applyFilter + `
  let editingReplyTemplateId = null;
  let replyTemplateDuplicating = false;
  this.duplicateReplyTemplate = duplicateReplyTemplate;
`;

vm.createContext(context);
vm.runInContext(code, context);

async function run() {
  // Test 1: Duplicate with active filter — search cleared when new item hidden
  promptValue = 'Cópia de Saudação';
  apiCalls = 0;
  promptCalls = 0;
  searchEl.value = 'saudação';
  createdEditButtonFocused = false;
  list.children = [originalItem];

  await context.duplicateReplyTemplate({id: 10, name: 'Saudação', content: 'Olá'}, {disabled: false});
  assert.equal(apiCalls, 1, 'API called once');
  assert.equal(searchEl.value, '', 'Search cleared when duplicated item hidden by filter');
  assert.equal(createdEditButtonFocused, true, 'Edit button of created item focused');

  // Test 2: Duplicate with no filter — search not affected
  apiCalls = 0;
  searchEl.value = '';
  createdEditButtonFocused = false;
  // Make created item visible
  context.loadReplyTemplateList = async function() {
    list._setCreated({id: 99, name: promptValue, content: 'Olá'}, false);
  };
  list.children = [originalItem];
  await context.duplicateReplyTemplate({id: 10, name: 'Saudação', content: 'Olá'}, {disabled: false});
  assert.equal(searchEl.value, '', 'Search remains empty when no filter active');
  assert.equal(createdEditButtonFocused, true, 'Edit button focused when item visible');
}

run().catch(error => { console.error(error); process.exitCode = 1; });
