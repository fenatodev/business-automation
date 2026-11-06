const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = script.indexOf('  $("opp-export-csv").addEventListener("click", () => {');
assert(start >= 0);
const end = script.indexOf('\n  });', start);
assert(end > start);
let click;
let url;
const elements = {
  'opp-export-csv': {addEventListener(event, callback) {click = callback;}},
  'show-archived': {checked: false}, 'opp-sort': {value: 'id'},
  'opp-source-filter': {value: 'manual'}, 'opp-search': {value: ' synthetic & sample '},
  'opp-from-date': {value: '2026-11-01'}, 'opp-to-date': {value: '2026-11-03'},
  'opp-priority-filter': {value: 'medium'},
};
vm.runInNewContext(script.slice(start, end + '\n  });'.length), {
  $: id => elements[id], encodeURIComponent, notify() {}, oppPipelineFilter: 'follow',
  downloadCsv(value, filename) {url = value; assert.equal(filename, 'opportunities.csv');},
});
for (const sort of ['id', 'created_at', 'next_action', 'priority']) {
  elements['opp-sort'].value = sort;
  click();
  const parsed = new URL(url, 'http://localhost');
  assert.equal(parsed.pathname, '/opportunities/export.csv');
  assert.deepEqual(Object.fromEntries(parsed.searchParams), {
    sort, exclude_archived: 'true', next_action: 'follow', source: 'manual',
    q: 'synthetic & sample', from_date: '2026-11-01', to_date: '2026-11-03', priority_level: 'medium',
  });
}
