'use strict';
// Shared by the Node tests: the repository, the vendored Board Generator, and
// a way to run the extractor's command (needs python3; PYTHON overrides it).
const path = require('path');
const fs = require('fs');
const { spawnSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const BG = require('../vendor/board-generator/src/board.js');
const PYTHON = process.env.PYTHON || 'python3';

function python(args, input) {
  const r = spawnSync(PYTHON, args, { cwd: ROOT, input, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  if (r.error) throw r.error;
  return r;
}
// The command: settings and records (or one record) in, { code, out, err } back.
function extract(...args) {
  const r = python(['-m', 'board_extractor', ...args]);
  return { code: r.status, out: r.stdout, err: r.stderr };
}
const file = (...p) => path.join(ROOT, ...p);
const read = (...p) => fs.readFileSync(file(...p), 'utf8');

module.exports = { ROOT, BG, PYTHON, python, extract, file, read };
