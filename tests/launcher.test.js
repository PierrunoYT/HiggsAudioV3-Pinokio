const assert = require('node:assert/strict');
const test = require('node:test');
const launcher = require('../pinokio.js');
const install = require('../install.js');
const start = require('../start.js');
const reset = require('../reset.js');
const torch = require('../torch.js');

function info(files = [], running = [], local = {}) {
  return { exists: p => files.includes(p), running: p => running.includes(p), local: () => local };
}

test('partial downloads cannot expose Start', async () => {
  const menu = await launcher.menu(null, info(['app/env', 'app/models/higgs-audio-v3-tts-4b']));
  assert.equal(menu[0].href, 'install.js');
});

test('update and reset remain visible while install artifacts disappear', async () => {
  for (const script of ['update.js', 'reset.js']) {
    const menu = await launcher.menu(null, info([], [script]));
    assert.equal(menu[0].href, script);
    assert.equal(menu[0].default, true);
  }
});

test('completed install opens the captured web UI', async () => {
  const files = ['app/.installed', 'app/env', 'app/ui-env', 'app/models/higgs-audio-v3-tts-4b'];
  const menu = await launcher.menu(null, info(files, ['start.js'], {url: 'http://127.0.0.1:7860'}));
  assert.equal(menu[0].href, 'http://127.0.0.1:7860');
});

test('completion marker is written after package checks and removed on reset', () => {
  const marker = install.run.findIndex(s => s.method === 'fs.write' && s.params.path === 'app/.installed');
  const check = install.run.findIndex(s => s.params?.message === 'uv pip check');
  assert.ok(marker > check && check >= 0);
  assert.equal(install.run[0].params.path, 'app/.installed');
  assert.ok(reset.run.some(s => s.params.path === 'app/.installed'));
  assert.ok(reset.run.some(s => s.params.path === 'app/ui-env'));
});

test('frontend and backend use separate environments', () => {
  assert.equal(start.run.find(s => s.id === 'frontend').params.venv, 'ui-env');
  assert.equal(install.run.find(s => s.params?.message === 'uv pip install -r requirements.txt').params.venv, 'ui-env');
  assert.equal(install.run.find(s => s.params?.uri === 'torch.js').when, "{{platform !== 'linux'}}");
});

test('URL capture works and passes the first capture to local.set', () => {
  for (const step of start.run.filter(s => s.params?.on)) {
    const pattern = step.params.on[0].event;
    const match = new RegExp(pattern.slice(1, -1)).exec('Running on http://127.0.0.1:7860');
    assert.equal(match[1], 'http://127.0.0.1:7860');
    assert.equal(step.params.on[0].done, true);
  }
  assert.equal(start.run.at(-1).params.url, '{{input.event[1]}}');
});

test('torch installs include dependencies and no stale Windows flash wheel', () => {
  assert.ok(!JSON.stringify(torch).includes('--no-deps'));
  assert.ok(!JSON.stringify(torch).includes('cu128torch2.7'));
  assert.ok(JSON.stringify(torch).includes('rocm6.4'));
});

test('backends bind to localhost only', () => {
  const linux = start.run.find(s => s.when === "{{platform === 'linux'}}");
  assert.match(linux.params.message.join(' '), /--host 127\.0\.0\.1(\s|$)/);
});

test('SGLang-Omni backend listens on loopback only', () => {
  const linux = start.run.find(s => s.when === "{{platform === 'linux'}}");
  assert.match(linux.params.message[0], /--host 127\.0\.0\.1/);
});
