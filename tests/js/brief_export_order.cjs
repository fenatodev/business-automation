const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = script.indexOf('  $("briefs-export-csv").addEventListener("click", () => {');
assert(start >= 0);
const end = script.indexOf('\n  });', start);
assert(end > start);
let click;
let url;
const elements = {
  'briefs-export-csv': {addEventListener(event, callback) {click = callback;}},
  'briefs-sort': {value: 'id'},
  'briefs-status-filter': {value: 'draft'}, 'briefs-opportunity-filter': {value: '3'},
  'briefs-search': {value: ' synthetic & sample '},
  'briefs-from-date': {value: '2026-11-01'}, 'briefs-to-date': {value: '2026-11-03'},
};
vm.runInNewContext(script.slice(start, end + '\n  });'.length), {
  $: id => elements[id], encodeURIComponent, notify() {},
  downloadCsv(value, filename) {url = value; assert.equal(filename, 'proposal-briefs.csv');},
});
for (const sort of ['id', 'created_at', 'status', 'title']) {
  elements['briefs-sort'].value = sort;
  click();
  const parsed = new URL(url, 'http://localhost');
  assert.equal(parsed.pathname, '/proposal-briefs/export.csv');
  assert.deepEqual(Object.fromEntries(parsed.searchParams), {
    sort, status: 'draft', opportunity_id: '3', q: 'synthetic & sample',
    from_date: '2026-11-01', to_date: '2026-11-03',
  });
}
delete elements['briefs-sort'];
click();
assert.equal(new URL(url, 'http://localhost').searchParams.get('sort'), 'created_at');
