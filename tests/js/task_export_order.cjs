const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = script.indexOf('  $("tasks-export-csv").addEventListener("click", () => {');
assert(start >= 0);
const end = script.indexOf('\n  });', start);
assert(end > start);
const elements = new Map();
for (const [id, value] of Object.entries({
  'task-sort': 'attempts', 'task-status-filter': 'failed',
  'task-search': ' synthetic & sample ', 'task-from-date': '2026-11-01',
  'task-to-date': '2026-11-05',
})) elements.set(id, {value});
let click;
elements.set('tasks-export-csv', {addEventListener(event, callback) {assert.equal(event, 'click'); click = callback;}});
const downloads = [];
vm.runInNewContext(script.slice(start, end + '\n  });'.length), {
  $: id => elements.get(id), encodeURIComponent, notify() {},
  downloadCsv: (url, filename) => downloads.push({url, filename}),
});
for (const sort of ['id', 'created_at', 'status', 'attempts']) {
  elements.get('task-sort').value = sort;
  click();
  const {url, filename} = downloads.at(-1);
  const parsed = new URL(url, 'http://localhost');
  assert.equal(filename, 'internal-tasks.csv');
  assert.equal(parsed.pathname, '/internal-tasks/export.csv');
  assert.deepEqual(Object.fromEntries(parsed.searchParams), {
    sort, status: 'failed', q: 'synthetic & sample', from_date: '2026-11-01', to_date: '2026-11-05',
  });
}
console.log('PASS task CSV button exports current sort and filters');
