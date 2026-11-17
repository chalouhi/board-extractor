'use strict';
// Requirement 26: the Board Generator is kept at release 1.1, unchanged, with
// its licence. Every vendored file matches the SHA-256 listed in vendor/README.md.
// The front page's picture is the example board as the tools make it.
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('crypto');
const fs = require('fs');
const { file, read } = require('./node-helpers.js');

test('vendored files are the listed ones, unchanged', () => {
  const rows = [...read('vendor', 'README.md').matchAll(/^\| `(board-generator\/[^`]+)` \| `[^`]+` \| `([0-9a-f]{64})` \|$/gm)];
  assert.ok(rows.length >= 8);
  for (const [, name, hash] of rows) {
    const got = crypto.createHash('sha256').update(fs.readFileSync(file('vendor', name))).digest('hex');
    assert.equal(got, hash, name);
  }
  const listed = new Set(rows.map(r => r[1]));
  const walk = (d, p = '') => fs.readdirSync(d, { withFileTypes: true }).flatMap(e => (e.isDirectory() ? walk(`${d}/${e.name}`, `${p}${e.name}/`) : [`${p}${e.name}`]));
  assert.deepEqual(walk(file('vendor', 'board-generator')).map(n => `board-generator/${n}`).filter(n => !listed.has(n)), []);
  assert.match(read('vendor', 'board-generator', 'LICENSE'), /^MIT License/);
});

test('docs/example.svg is the example board as tools/make-picture.js draws it', async () => {
  const { picture } = require('../tools/make-picture.js');
  assert.equal(read('docs', 'example.svg'), await picture(), 'run: node tools/make-picture.js');
});

test('the repository holds what requirement 29 lists', () => {
  for (const p of ['LICENSE', 'README.md', 'docs/guide.md', 'docs/input-format.md', 'board_extractor/__init__.py',
    'board_extractor/cli.py', 'bin/board-extractor', 'example/serve.py', 'example/reset.py', 'samples/shop/settings.json',
    'samples/shop/records.json', 'samples/shop/card-43.record.json', 'samples/broken/settings.json', 'samples/broken/records.json',
    'expected/shop.board.json', 'expected/shop.card-43.json', 'expected/broken.problems.txt', 'pyproject.toml']) {
    assert.ok(fs.existsSync(file(p)), p);
  }
  assert.match(read('LICENSE'), /^MIT License/);
});
