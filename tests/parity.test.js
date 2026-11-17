'use strict';
// Requirement 15: the extractor applies every rule of the Board Generator's
// board file and card file itself. Its rules (board_extractor/rules.py) must
// say exactly what the Board Generator's own reader says, message for message,
// on the same file. Thousands of files, each a sample with a few things
// changed at random, are read by both.
const test = require('node:test');
const assert = require('node:assert/strict');
const { BG, python, read } = require('./node-helpers.js');

const BASE_BOARD = JSON.parse(read('expected', 'shop.board.json'));
Object.assign(BASE_BOARD, {
  summary: ['Launch in 3 weeks'],
  style: { card_lines: 3, colours: { accent: '#4B5320', column: '#F6F7EF' } },
});
BASE_BOARD.cards[2].text = 'A description.';
BASE_BOARD.cards[3].link = 'https://example.com/53';
BASE_BOARD.buttons.push({ name: 'Ask', action: 'ask', ask: { label: 'Why?', required: true, long: false }, strip_only: true });
const BASE_CARD = JSON.parse(read('expected', 'shop.card-43.json'));
BASE_CARD.sections.push({ title: 'About', type: 'text', text: 'Some text.' }, { title: 'Steps', type: 'list', numbered: true, items: [{ text: 'One', link: 'https://example.com/1' }] });

const VALUES = [
  null, true, false, 0, 1, 2, 3, -1, 1.5, 1e21, 1e-7, 123456789012, '', ' ', ' ', '﻿', 'x', 'Doing', 'done', 'Ideas', 'Fix', 'feature',
  '2026-03-10', '2026-02-30', '2026-03-10 14:05', '2026-03-10T24:00', '10 March', '#FFFFFF', '#075056', '#FFF', '#ff5b04',
  'https://example.com/{id}', 'https://example.com/a b', 'http://x', 'ftp://x', 'auto', 'off', 'checklist', 'timeline', 'text', 'grid',
  'x'.repeat(13), 'x'.repeat(25), 'x'.repeat(61), 'x'.repeat(201), '🧭'.repeat(31), 'é'.repeat(61), 'x'.repeat(2001), 'x'.repeat(5001),
  'line\nbreak', 'quote " and \\ back', '\u0007bell',
  [], [1], ['Fix'], ['Nowhere'], ['Doing', 'done'], ['a', 'b', 'c', 'd', 'e', 'f', 'g'], [{}], [{ text: 'i' }], [{ label: 'L', value: 'V' }],
  {}, { name: 'N' }, { label: 'L' }, { label: 'x'.repeat(61) }, { label: 'Q', required: 'yes' }, { name: 'Needs you', show: 0 },
  { card_lines: 2 }, { colours: { ink: '#FFFFFF' } }, { colours: { pink: '#FF00FF', 2: 'x', soon: '#FFFF00' } }, { colours: 'red' },
];

// A small random generator with a fixed seed, so a failure can be repeated.
function generator(seed) {
  let s = seed >>> 0;
  const next = () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  return { int: n => Math.floor(next() * n), pick: a => a[Math.floor(next() * a.length)] };
}
// Every place in a file that can be changed: [parent, key].
function places(o, out = []) {
  for (const k of Object.keys(o)) {
    out.push([o, k]);
    if (o[k] && typeof o[k] === 'object') places(o[k], out);
  }
  return out;
}
function mutate(base, g) {
  const f = JSON.parse(JSON.stringify(base));
  for (let n = 1 + g.int(4); n > 0; n--) {
    const spots = places(f);
    if (!spots.length) break;
    const [parent, k] = g.pick(spots);
    const what = g.int(10);
    if (what === 0 && !Array.isArray(parent)) delete parent[k];
    else if (what === 1 && Array.isArray(parent[k])) parent[k].push(JSON.parse(JSON.stringify(g.pick(parent[k].length ? parent[k] : VALUES))));
    else if (what === 2 && parent[k] && typeof parent[k] === 'object' && !Array.isArray(parent[k])) parent[k][g.pick(['name', 'link', 'action', 'ask', 'confirm', 'main', 'kinds', 'columns', 'total', 'in_strip', 'done', 'when', 'who', 'collapsed'])] = JSON.parse(JSON.stringify(g.pick(VALUES)));
    else parent[k] = JSON.parse(JSON.stringify(g.pick(VALUES)));
  }
  return f;
}

function compare(cases) {
  const r = python(['tests/port_check.py'], JSON.stringify(cases));
  assert.equal(r.status, 0, r.stderr);
  const py = JSON.parse(r.stdout);
  let checked = 0, failing = 0;
  cases.forEach((c, i) => {
    const js = 'board' in c ? BG.read(JSON.stringify(c.board)) : BG.readCard(JSON.stringify(c.card), c.opened);
    const want = js.ok ? [] : js.errors;
    if (want.length) failing++;
    assert.deepEqual(py[i], want, `case ${i}: ${JSON.stringify(c).slice(0, 400)}`);
    checked++;
  });
  return { checked, failing };
}

test('board files: the Python rules say what the Board Generator says', () => {
  const g = generator(31);
  const cases = [{ board: BASE_BOARD }];
  for (let i = 0; i < 3000; i++) cases.push({ board: mutate(BASE_BOARD, g) });
  const { failing } = compare(cases);
  assert.ok(failing > 2000, `only ${failing} files had problems`);
});

test('card files: the Python rules say what the Board Generator says', () => {
  const g = generator(15);
  const cases = [{ card: BASE_CARD, opened: '43' }];
  for (let i = 0; i < 3000; i++) cases.push({ card: mutate(BASE_CARD, g), opened: g.pick(['43', '43', '44', 43]) });
  const { failing } = compare(cases);
  assert.ok(failing > 2000, `only ${failing} files had problems`);
});

test('the limits, reported alone', () => {
  const many = JSON.parse(JSON.stringify(BASE_BOARD));
  many.cards = Array.from({ length: 5001 }, (_, i) => ({ id: String(i), title: 't', column: 'Ideas' }));
  const cols = JSON.parse(JSON.stringify(BASE_BOARD));
  cols.columns = Array.from({ length: 13 }, (_, i) => ({ name: `C${i}` }));
  compare([{ board: many }, { board: cols }]);
});
