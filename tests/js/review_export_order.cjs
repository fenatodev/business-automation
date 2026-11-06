const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = script.indexOf('  $("rq-export-csv").addEventListener("click", () => {');
assert(start >= 0);
const end = script.indexOf('\n  });', start);
assert(end > start);
const elements = new Map();
for (const [id, value] of Object.entries({
  'rq-sort': 'created_at', 'rq-status-filter': 'pending',
  'rq-search': ' synthetic & sample ', 'rq-from-date': '2026-11-01',
  'rq-to-date': '2026-11-05',
})) elements.set(id, {value});
let click;
elements.set('rq-export-csv', {addEventListener(event, callback) {assert.equal(event, 'click'); click = callback;}});
const downloads = [];
vm.runInNewContext(script.slice(start, end + '\n  });'.length), {
  $: id => elements.get(id), encodeURIComponent, notify() {},
  downloadCsv: (url, filename) => downloads.push({url, filename}),
});
for (const sort of ['id', 'created_at', 'status']) {
  elements.get('rq-sort').value = sort;
  click();
  const {url, filename} = downloads.at(-1);
  const parsed = new URL(url, 'http://localhost');
  assert.equal(filename, 'review-queue.csv');
  assert.equal(parsed.pathname, '/review-queue/export.csv');
  assert.deepEqual(Object.fromEntries(parsed.searchParams), {
    sort, status: 'pending', q: 'synthetic & sample', from_date: '2026-11-01', to_date: '2026-11-05',
  });
}
console.log('PASS review CSV button exports current sort and filters');
