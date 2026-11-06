const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const rows = JSON.parse(fs.readFileSync(0, 'utf8'));
function element() {
  return {
    children: [], textContent: '', style: {}, classList: {toggle() {}},
    append(...nodes) {this.children.push(...nodes);},
    replaceChildren() {this.children = [];},
    setAttribute() {}, addEventListener(event, fn) {this[event] = fn;},
  };
}
const elements = new Map();
const selected = [];
const context = {
  opportunities: rows, selectedId: rows[0]?.id ?? null,
  selectedOpportunityIds: new Set(rows.length ? [rows[0].id] : []),
  actionLabels: {}, updateBulkTriageBar() {},
  selectOpportunity: async id => selected.push(id), notify() {},
  $: id => {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);},
  document: {createElement: element},
};
vm.createContext(context);
vm.runInContext(script.slice(script.indexOf('  function showList()'), script.indexOf('  function readBriefForm()')), context);
const original = JSON.stringify(rows);
context.showList();
const list = context.$('opportunity-list');
if (rows.length) {
  assert.deepEqual(list.children.map(row => row.children[1].children[0].children[0].textContent),
    rows.map(row => '#' + row.id + ' · ' + row.title));
  assert.equal(list.children[0].children[0].checked, true);
  for (const row of list.children) row.children[1].click({target: row.children[1]});
  assert.deepEqual(selected, rows.map(row => row.id));
} else {
  assert.equal(list.children[0].textContent, 'Nenhuma oportunidade registrada.');
}
context.showList();
assert.equal(list.children.length, rows.length || 1);
assert.equal(JSON.stringify(rows), original);
