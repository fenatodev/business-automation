const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = script.indexOf('  $("leads-export-csv").addEventListener("click", () => {');
assert(start >= 0);
const end = script.indexOf('\n  });', start);
assert(end > start);
const elements = new Map();
for (const [id, value] of Object.entries({
  'lead-sort': 'name', 'lead-filter-status': 'new', 'lead-filter-source': 'synthetic & source',
  'lead-search': ' synthetic & sample ', 'lead-from-date': '2026-11-01',
  'lead-to-date': '2026-11-05',
})) elements.set(id, {value});
let click;
elements.set('leads-export-csv', {addEventListener(event, callback) {assert.equal(event, 'click'); click = callback;}});
const downloads = [];
vm.runInNewContext(script.slice(start, end + '\n  });'.length), {
  $: id => elements.get(id), encodeURIComponent, notify() {},
  downloadCsv: (url, filename) => downloads.push({url, filename}),
});
for (const sort of ['id', 'created_at', 'name', 'status']) {
  elements.get('lead-sort').value = sort;
  click();
  const {url, filename} = downloads.at(-1);
  const parsed = new URL(url, 'http://localhost');
  assert.equal(filename, 'leads.csv');
  assert.equal(parsed.pathname, '/leads/export.csv');
  assert.deepEqual(Object.fromEntries(parsed.searchParams), {
    sort, status: 'new', source: 'synthetic & source', q: 'synthetic & sample', from_date: '2026-11-01', to_date: '2026-11-05',
  });
}
console.log('PASS lead CSV button exports current sort and filters');
