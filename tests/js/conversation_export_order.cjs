const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/operator_ui/app.js', 'utf8');
const start = script.indexOf('  $("conv-export-csv").addEventListener("click", () => {');
assert(start >= 0);
const end = script.indexOf('\n  });', start);
assert(end > start);
let click;
const downloads = [];
const context = {
  $: () => ({addEventListener(event, callback) {assert.equal(event, 'click'); click = callback;}}),
  encodeURIComponent, notify() {},
  downloadCsv: (url, filename) => downloads.push({url, filename}),
  convFilterChannel: 'web', convFilterStatus: 'open', convFilterQuery: 'synthetic & sample',
  convFilterCustomerId: '12', convFilterLeadId: '', convFilterFromDate: '2026-11-01',
  convFilterToDate: '2026-11-05', opportunities: [{company_id: 7}],
};
vm.runInNewContext(script.slice(start, end + '\n  });'.length), context);
for (const sort of ['id', 'created_at', 'last_message']) {
  context.convFilterSort = sort;
  click();
  const {url, filename} = downloads.at(-1);
  const parsed = new URL(url, 'http://localhost');
  assert.equal(filename, 'conversations.csv');
  assert.equal(parsed.pathname, '/companies/7/conversations/export.csv');
  assert.deepEqual(Object.fromEntries(parsed.searchParams), {
    sort, channel: 'web', status: 'open', q: 'synthetic & sample', customer_id: '12',
    from_date: '2026-11-01', to_date: '2026-11-05',
  });
}
context.convFilterCustomerId = '';
context.convFilterLeadId = '9';
click();
assert.equal(new URL(downloads.at(-1).url, 'http://localhost').searchParams.get('lead_id'), '9');
console.log('PASS conversation CSV button exports selected order and filters');
