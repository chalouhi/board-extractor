'use strict';
// Requirements 3 and 31: the Board Generator's own reader (release 1.1, kept
// in vendor/) accepts every file the extractor writes, with no problem.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { BG, extract, file, read, python } = require('./node-helpers.js');

const SHOP = file('samples', 'shop', 'settings.json');
const RECORDS = file('samples', 'shop', 'records.json');
const BOARDS = [
  ['the shop sample', []], ['with today', ['--today', '2026-03-10']], ['group "Website"', ['--group', 'Website']],
  ['the waiting cards', ['--waiting']], ['kind "Decision"', ['--kind', 'Decision']], ['kind "Feature"', ['--kind', 'Feature']],
  ['group "Stockroom", kind "Fix"', ['--group', 'Stockroom', '--kind', 'Fix']], ['a group with no cards', ['--group', 'Nowhere']],
];

test('the Board Generator 1.1 is the one kept in vendor/', () => assert.equal(BG.VERSION, '1.1.0'));

for (const [name, opts] of BOARDS) {
  test(`board file, ${name}: accepted by the Board Generator's reader`, () => {
    const r = extract(SHOP, RECORDS, ...opts);
    assert.equal(r.code, 0, r.err);
    const got = BG.read(r.out);
    assert.deepEqual(got.ok ? [] : got.errors, []);
    assert.equal(got.board.columns.length, 5);
  });
}

test('card file of card 43: accepted by the Board Generator\'s reader', () => {
  const r = extract(SHOP, file('samples', 'shop', 'card-43.record.json'));
  assert.equal(r.code, 0, r.err);
  const got = BG.readCard(r.out, '43');
  assert.deepEqual(got.ok ? [] : got.errors, []);
  assert.equal(got.card.sections.length, 3);
});

test('the expected files themselves are accepted', () => {
  assert.ok(BG.read(read('expected', 'shop.board.json')).ok);
  assert.ok(BG.readCard(read('expected', 'shop.card-43.json'), '43').ok);
});

test('the example board\'s files are accepted: the board and every card', () => {
  const r = python([file('tools', 'example-files.py')]);
  assert.equal(r.status, 0, r.stderr);
  const { board, cards } = JSON.parse(r.stdout);
  const got = BG.read(board);
  assert.deepEqual(got.ok ? [] : got.errors, []);
  assert.equal(Object.keys(cards).length, 16);
  for (const [id, text] of Object.entries(cards)) {
    const c = BG.readCard(text, id);
    assert.deepEqual(c.ok ? [] : c.errors, [], `card ${id}`);
  }
});

test('records made up at random: whatever the extractor returns, the reader accepts', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'extractor-'));
  try {
    let rnd = 208;
    const next = n => { rnd = (rnd * 1103515245 + 12345) % 2147483648; return rnd % n; };
    const pick = a => a[next(a.length)];
    const stages = ['idea', 'ready', 'doing', 'checking', 'rework', 'done'];
    for (let round = 0; round < 20; round++) {
      const records = Array.from({ length: 1 + next(60) }, (_, i) => {
        const r = { id: String(i + 1), title: pick(['A', 'Gift wrapping', 'x'.repeat(200), '🧭 Courier', '<b>bold</b>']), stage: pick(stages) };
        if (next(2)) r.kind = pick(['Feature', 'Fix', 'Task', 'Decision', 'Spike']);
        if (next(2)) r.group = pick(['Website', 'Stockroom', 'Launch day']);
        if (next(3) === 0) r.due = `2026-0${1 + next(9)}-1${next(10)}`;
        if (next(4) === 0) r.waiting = true;
        if (next(2)) r.order = next(100) - 20;
        if (next(2)) r.changed = `2026-03-0${1 + next(9)}T1${next(10)}:00`;
        if (next(5) === 0) r.note = 'n'.repeat(next(61));
        return r;
      });
      fs.writeFileSync(path.join(dir, 'r.json'), JSON.stringify({ records, totals: next(2) ? { done: 500 } : {} }));
      const opts = pick([[], ['--waiting'], ['--kind', 'Fix'], ['--group', 'Website']]);
      const r = extract(SHOP, path.join(dir, 'r.json'), ...opts);
      assert.equal(r.code, 0, r.err);
      const got = BG.read(r.out);
      assert.deepEqual(got.ok ? [] : got.errors, [], `round ${round}`);
    }
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
