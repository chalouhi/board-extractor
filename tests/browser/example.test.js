'use strict';
// Scenario 3 in a real browser: the whole chain on one machine. The example's
// own service (python3) is started with its own command; the page is drawn by
// the Board Generator 1.1. Needs Playwright with Chromium; skipped when it is
// not installed. Run with no network: tests/browser/run-offline.sh.
//   SHOTS=<folder> also saves screenshots there.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const net = require('net');
const { spawn, spawnSync } = require('child_process');

const ROOT = path.join(__dirname, '..', '..');
const PYTHON = process.env.PYTHON || 'python3';
let chromium = null;
try { ({ chromium } = require('playwright')); } catch (e) { /* skipped below */ }
const skip = chromium ? false : 'Playwright is not installed';
const SHOTS = process.env.SHOTS;

let browser, dir, port, service;
const freePort = () => new Promise(r => { const s = net.createServer().listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => r(p)); }); });
function start() {
  return new Promise((resolve, reject) => {
    service = spawn(PYTHON, [path.join(ROOT, 'example', 'serve.py'), '--port', String(port), '--db', path.join(dir, 'shop.db')], { cwd: dir });
    let out = '';
    service.stdout.on('data', d => { out += d; if (out.includes('http://127.0.0.1:')) resolve(); });
    service.stderr.on('data', d => { out += d; });
    service.on('exit', code => reject(new Error(`the example stopped (${code}): ${out}`)));
  });
}
function stop() {
  return new Promise(r => { if (!service || service.exitCode !== null) return r(); service.removeAllListeners('exit'); service.on('exit', () => r()); service.kill('SIGINT'); });
}
const reset = () => spawnSync(PYTHON, [path.join(ROOT, 'example', 'reset.py'), '--db', path.join(dir, 'shop.db')], { encoding: 'utf8' });

test.before(async () => {
  if (skip) return;
  dir = fs.mkdtempSync(path.join(os.tmpdir(), 'example-'));
  port = await freePort();
  await start();
  browser = await chromium.launch();
});
test.after(async () => {
  if (browser) await browser.close();
  await stop();
  if (dir) fs.rmSync(dir, { recursive: true, force: true });
});

async function open(width, height = 900) {
  const context = await browser.newContext({ viewport: { width, height } });
  const page = await context.newPage();
  const errors = [], requests = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('request', r => requests.push(r.url()));
  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: 'load' });
  await drawn(page);
  return { page, context, errors, requests };
}
async function until(page, fn, arg, ms = 8000) {
  const end = Date.now() + ms;
  for (;;) {
    if (await page.evaluate(fn, arg)) return;
    if (Date.now() > end) throw new Error('timed out waiting for ' + fn);
    await new Promise(r => setTimeout(r, 25));
  }
}
const drawn = page => until(page, () => !!(document.querySelector('#board').shadowRoot && document.querySelector('#board').shadowRoot.querySelector('.bg')));
// The board as drawn: title, the strip, and each column's name, count, "n more" and cards (ids).
const board = page => page.evaluate(() => {
  const host = document.querySelector('#board').shadowRoot.querySelector('.bg');
  const txt = el => (el ? el.textContent.replace(/\s+/g, ' ').trim() : null);
  const ids = s => [...s.querySelectorAll('[data-i]')].map(c => /#([^:]+):/.exec(c.getAttribute('aria-label'))[1]);
  const strip = host.querySelector('.bg-strip');
  return {
    title: txt(host.querySelector('.bg-title, h1')),
    strip: strip && { name: txt(strip.querySelector('.bg-name')), count: txt(strip.querySelector('.bg-count')), ids: ids(strip) },
    cols: Object.fromEntries([...host.querySelectorAll('.bg-col, .bg-ncol')].map(s => [txt(s.querySelector('.bg-name')), {
      count: txt(s.querySelector('.bg-count')), over: s.querySelector('.bg-count').classList.contains('bg-over'),
      red: getComputedStyle(s.querySelector('.bg-count')).color, more: txt(s.querySelector('.bg-more')), ids: ids(s),
    }])),
    refresh: txt(host.querySelector('.bg-refresh')),
  };
});
const card = page => page.evaluate(() => {
  const d = document.querySelector('#board').shadowRoot.querySelector('.bg-dialog');
  if (!d) return null;
  // the words of every piece of text inside, joined by spaces
  const txt = el => { if (!el) return null; const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), out = []; while (w.nextNode()) out.push(w.currentNode.nodeValue); return out.join(' ').replace(/\s+/g, ' ').trim(); };
  return {
    status: txt(d.querySelector('.bg-status')),
    sections: [...d.querySelectorAll('.bg-sec')].map(s => ({ head: txt(s.querySelector('.bg-sh')), items: [...s.querySelectorAll('li')].map(txt) })),
    buttons: [...d.querySelectorAll('.bg-actions .bg-btn')].map(txt),
  };
});
async function openCard(page, id) {
  await page.locator(`#board >> [data-i][aria-label*="#${id}:"]`).first().click();
  await until(page, () => !!document.querySelector('#board').shadowRoot.querySelector('.bg-dialog'));
}
const filledIn = page => until(page, () => { const d = document.querySelector('#board').shadowRoot.querySelector('.bg-dialog'); return d && !d.querySelector('.bg-status'); });
const closed = page => until(page, () => !document.querySelector('#board').shadowRoot.querySelector('.bg-dialog'));
const press = (page, name) => page.locator('#board >> .bg-dialog .bg-btn', { hasText: name }).first().click();
async function shot(page, name) { if (SHOTS) await page.screenshot({ path: path.join(SHOTS, name + '.png'), fullPage: true }); }
const onlyHere = requests => requests.filter(u => !u.startsWith(`http://127.0.0.1:${port}/`));

test('scenario 3: the whole chain on one machine', { skip }, async () => {
  const { page, context, errors, requests } = await open(1280);
  let b = await board(page);
  assert.equal(b.title, 'Shop relaunch');
  assert.deepEqual(b.strip, { name: 'Needs you', count: '2', ids: ['41', '38'] });
  assert.deepEqual([b.cols.Doing.count, b.cols.Doing.over, b.cols.Doing.red], ['3 / 2', true, 'rgb(198, 40, 40)']);
  assert.deepEqual([b.cols.Done.count, b.cols.Done.more, b.cols.Done.ids], ['48', '45 more', ['40', '39', '37']]);
  assert.deepEqual([b.cols.Ready.count, b.cols.Checking.count], ['3 / 4', '1']);
  assert.equal(b.refresh, 'Refresh');
  assert.match(await page.locator('#example-line').innerText(), /^An example with made-up cards/);
  await shot(page, '1-board');

  await openCard(page, '43');
  assert.ok(await card(page), 'card 43 opens at once');
  await filledIn(page);
  let c = await card(page);
  assert.deepEqual(c.sections.map(s => s.head), ['Requirements 2 of 3 done', 'Notes 2', 'History 6']);
  assert.deepEqual(c.buttons.sort(), ['Accept', 'Add note', 'Send back']);
  await shot(page, '2-card43');

  await press(page, 'Send back');
  await page.keyboard.type('Closing time wraps on a phone');
  await shot(page, '3-send-back');
  await press(page, 'Send back'); // confirms
  await closed(page);
  await until(page, () => /#43:/.test([...document.querySelector('#board').shadowRoot.querySelectorAll('.bg-col')].find(s => s.getAttribute('aria-label') === 'Ready').innerHTML));
  b = await board(page);
  assert.deepEqual([b.cols.Ready.count, b.cols.Ready.ids], ['4 / 4', ['47', '48', '49', '43']]);
  assert.equal(b.cols.Checking.count, '0');
  await shot(page, '4-after-send-back');

  await openCard(page, '43');
  await filledIn(page);
  c = await card(page);
  assert.equal(c.sections[1].head, 'Notes 3');
  assert.match(c.sections[1].items[0], /Closing time wraps on a phone$/);
  await page.keyboard.press('Escape');
  await closed(page);

  const before = await board(page);
  await page.locator('#board >> .bg-refresh').click();
  await until(page, () => document.querySelector('#board').shadowRoot.querySelector('.bg-refresh').textContent === 'Refresh');
  assert.deepEqual(await board(page), before);

  await stop();
  await start();
  await page.reload({ waitUntil: 'load' });
  await drawn(page);
  assert.deepEqual((await board(page)).cols.Ready.ids, ['47', '48', '49', '43']);

  const r = reset();
  assert.equal(r.status, 0, r.stderr);
  await page.reload({ waitUntil: 'load' });
  await drawn(page);
  b = await board(page);
  assert.deepEqual([b.cols.Checking.count, b.cols.Ready.count], ['1', '3 / 4']);
  assert.deepEqual(b.cols.Checking.ids, ['43']);
  assert.match(await page.locator('#example-line').innerText(), /made-up cards/);

  assert.deepEqual(onlyHere(requests), [], 'no request left the machine');
  assert.deepEqual(errors, []);
  await context.close();
});

test('Accept and Add note, and the board on a phone', { skip }, async () => {
  reset();
  const { page, context, errors, requests } = await open(1280);
  await openCard(page, '38');
  await filledIn(page);
  await press(page, 'Add note');
  await page.keyboard.type('Brighter set arrives Thursday');
  await press(page, 'Add note');
  await until(page, () => [...document.querySelector('#board').shadowRoot.querySelectorAll('.bg-dialog .bg-sec li')].some(li => li.textContent.includes('Brighter set arrives Thursday')));
  assert.ok(await card(page), 'Add note keeps the card open');
  await press(page, 'Accept');
  await closed(page);
  await until(page, () => /#38:/.test([...document.querySelector('#board').shadowRoot.querySelectorAll('.bg-col')].find(s => s.getAttribute('aria-label') === 'Done').innerHTML));
  const b = await board(page);
  assert.deepEqual([b.cols.Done.count, b.cols.Done.ids, b.strip.ids], ['49', ['38', '40', '39'], ['41']]);
  assert.deepEqual(onlyHere(requests), []);
  assert.deepEqual(errors, []);
  await context.close();

  reset();
  const phone = await open(390, 844);
  assert.ok(await phone.page.evaluate(() => !!document.querySelector('#board').shadowRoot.querySelector('.bg-ncol')), 'one list on a phone');
  assert.ok(await phone.page.evaluate(() => document.documentElement.scrollWidth <= 390));
  await shot(phone.page, '5-phone');
  assert.deepEqual(phone.errors, []);
  await phone.context.close();
});
