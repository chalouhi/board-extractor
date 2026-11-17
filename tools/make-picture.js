#!/usr/bin/env node
'use strict';
// Makes docs/example.svg, the front page's picture: the example board as it
// is when new, drawn by the Board Generator 1.1 kept in vendor/.
//   node tools/make-picture.js            writes docs/example.svg
//   node tools/make-picture.js --check    exits 1 when docs/example.svg is out of date
const fs = require('fs');
const path = require('path');
const { BG, python, file } = require('../tests/node-helpers.js');

async function picture() {
  const r = python([file('tools', 'example-files.py')]);
  if (r.status !== 0) throw new Error(r.stderr);
  const got = BG.read(JSON.parse(r.stdout).board);
  if (!got.ok) throw new Error(got.errors.join('\n'));
  const V = file('vendor', 'board-generator');
  return require(path.join(V, 'src', 'picture.js')).svg(got.board, {
    fontkit: require(path.join(V, 'vendor', 'fontkit.umd.min.js')),
    regular: fs.readFileSync(path.join(V, 'fonts', 'Carlito-Regular.ttf')),
    bold: fs.readFileSync(path.join(V, 'fonts', 'Carlito-Bold.ttf')),
    width: 1280,
  });
}

if (require.main === module) {
  picture().then(svg => {
    const target = file('docs', 'example.svg');
    if (process.argv.includes('--check')) {
      const same = fs.existsSync(target) && fs.readFileSync(target, 'utf8') === svg;
      process.stdout.write(same ? 'docs/example.svg is up to date\n' : 'docs/example.svg is out of date\n');
      process.exitCode = same ? 0 : 1;
    } else {
      fs.writeFileSync(target, svg);
      process.stdout.write('wrote docs/example.svg\n');
    }
  }, e => { process.stderr.write(String(e.stack || e) + '\n'); process.exitCode = 2; });
}
module.exports = { picture };
