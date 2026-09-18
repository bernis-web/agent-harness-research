// harness.cjs — reusable hidden-validation harness (no H-case execution here)
const CHILD_PROCESS = require('child_process');
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const { pathToFileURL } = require('url');

const OUT = process.env.T1_OUT;
if (!OUT) throw new Error('T1_OUT not set');
const CHROME_EXE = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PROFILE_DIR = path.win32.normalize(path.join(OUT, 'profile'));
const FILE_URL = pathToFileURL(process.env.T1_REFERENCE).href;

// --- spawn wrapper installed BEFORE loading Playwright: capture only our Chrome ---
const owned = { pid: null, startedAt: null, exe: null, parentPid: process.pid };
let chromeLaunched = false;
const realSpawn = CHILD_PROCESS.spawn;
CHILD_PROCESS.spawn = function (cmd, args, opts) {
  const exe = String(cmd || '');
  const argStr = Array.isArray(args) ? args.join(' ') : String(args || '');
  const norm = (s) => path.win32.normalize(String(s)).toLowerCase();
  const isOurs = norm(exe) === norm(CHROME_EXE) && Array.isArray(args) && args.includes('--user-data-dir=' + PROFILE_DIR);
  if (isOurs) {
    if (chromeLaunched) throw new Error('REJECTED: a second owned Chrome launch attempted');
    chromeLaunched = true;
    const child = realSpawn.call(this, cmd, args, { ...opts, windowsHide: true });
    owned.pid = child.pid; owned.startedAt = new Date().toISOString(); owned.exe = exe;
    if (!owned.pid) throw new Error('REJECTED: owned Chrome launch produced no pid');
    // SAFE metadata only: redact any arg value embedding a local path; env recorded as key names, never values
    const SAFE_ARGS = (Array.isArray(args) ? args.map(String) : [String(args)]).map(a => a.includes(OUT) ? a.split('=')[0] + '=<redacted>' : a);
    const ENV_KEYS = Object.keys((opts && opts.env) || {});
    fs.writeFileSync(path.join(OUT, 'chrome-process.json'), JSON.stringify({ ...owned, browserArgs: SAFE_ARGS, envKeys: ENV_KEYS, guardedBy: 'normalized exe + exact --user-data-dir match', windowsHide: true }, null, 2));
    child.once('exit', (code) => { owned.exitedAt = new Date().toISOString(); owned.exitCode = code;
      fs.writeFileSync(path.join(OUT, 'chrome-process.json'), JSON.stringify(owned, null, 2)); });
    return child;
  }
  return realSpawn.call(this, cmd, args, opts);
};

// --- load Playwright only after wrapper is installed ---
const { chromium } = require(process.env.T1_PLAYWRIGHT || 'D:/projects/npm-cache/_npx/cbf1b8a072280925/node_modules/playwright-core');

// --- env allowlist: only system Windows variables, no inherited API secrets ---
const SYS_KEYS = ['ALLUSERSPROFILE','APPDATA','COMMONPROGRAMFILES','COMMONPROGRAMFILES(X86)','COMPUTERNAME','COMSPEC','DRIVERDATA','HOMEDRIVE','HOMEPATH','LOCALAPPDATA','NUMBER_OF_PROCESSORS','OS','PATH','PATHEXT','PROCESSOR_ARCHITECTURE','PROCESSOR_IDENTIFIER','PROCESSOR_LEVEL','PROCESSOR_REVISION','PROGRAMDATA','PROGRAMFILES','PROGRAMFILES(X86)','SYSTEMDRIVE','SYSTEMROOT','TEMP','TMP','USERDOMAIN','USERNAME','USERPROFILE','WINDIR'];
function buildEnv() {
  const env = {};
  for (const k of SYS_KEYS) if (process.env[k] !== undefined) env[k] = process.env[k];
  env.TEMP = OUT + '/temp'; env.TMP = OUT + '/temp';
  env.HOME = OUT + '/home'; env.USERPROFILE = OUT + '/home';
  env.APPDATA = OUT + '/home/AppData/Roaming'; env.LOCALAPPDATA = OUT + '/home/AppData/Local';
  return env;
}

const LAUNCH = {
  executablePath: CHROME_EXE,
  headless: true, chromiumSandbox: true, ignoreDefaultArgs: true,
  args: ['--headless=new', '--remote-debugging-pipe', '--user-data-dir=' + PROFILE_DIR,
    '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
    '--disable-component-update', '--disable-sync', '--disable-extensions',
    '--enable-automation', '--window-size=1280,800'],
  downloadsPath: OUT + '/downloads', acceptDownloads: true, offline: true,
  serviceWorkers: 'block', viewport: { width: 1280, height: 800 }, timeout: 30000,
  env: buildEnv()
};
// launch trace: options without env values
fs.writeFileSync(path.join(OUT, 'launch-options.json'), JSON.stringify({ ...LAUNCH, env: '<omitted>' }, null, 2));

const S0 = '中心主题\n  分支一\n  分支二\n    细节甲\n    细节乙\n  分支三';
const TREE = (() => {
  const r = { title: '中心主题', children: [] };
  const b1 = { title: '分支一', children: [] };
  const b2 = { title: '分支二', children: [{ title: '细节甲', children: [] }, { title: '细节乙', children: [] }] };
  const b3 = { title: '分支三', children: [] };
  r.children.push(b1, b2, b3); return r;
})();
const clone = (x) => JSON.parse(JSON.stringify(x));
const ap = (p) => fs.promises.mkdir(p, { recursive: true });

async function createHarness() {
  for (const d of ['/profile', '/downloads', '/temp', '/home', '/home/AppData/Roaming', '/home/AppData/Local']) await ap(OUT + d);

  let errors = [];
  const steps = [];
  let ctx, page, cdp;

  const writeResults = () => fs.writeFileSync(path.join(OUT, 'results.json'),
    JSON.stringify({ steps, errors, owned, summary: {
      total: steps.length,
      PASS: steps.filter(s => s.status === 'PASS').length,
      REFERENCE_FAILURE: steps.filter(s => s.status === 'REFERENCE_FAILURE').length,
      DRIVER_ERROR: steps.filter(s => s.status === 'DRIVER_ERROR').length
    } }, null, 2));
  const logAction = (a) => fs.appendFileSync(path.join(OUT, 'actions.jsonl'), JSON.stringify({ ...a, ts: Date.now() }) + '\n');

  async function attachListeners(p) {
    p.setDefaultTimeout(10000);
    p.on('pageerror', e => errors.push('pageerror: ' + e.message));
    p.on('console', m => { if (m.type() === 'error') errors.push('console.error: ' + m.text()); });
    return p;
  }

  ctx = await chromium.launchPersistentContext(PROFILE_DIR, LAUNCH);
  ownedContext.ctx = ctx;
  if (!owned.pid) throw new Error('launch succeeded but owned Chrome was not captured by spawn wrapper');
  await ctx.route(/^https?:\/\//, r => r.abort());
  try { await ctx.setOffline(true); } catch (e) {}
  page = ctx.pages()[0] || await ctx.newPage();
  await attachListeners(page);
  cdp = await ctx.newCDPSession(page);
  cdp.on('Browser.downloadWillBegin', e => logAction({ action: 'cdp-willBegin', guid: e.guid }));
  cdp.on('Browser.downloadProgress', e => logAction({ action: 'cdp-progress', state: e.state }));
  await cdp.send('Browser.setDownloadBehavior', { behavior: 'allowAndName', downloadPath: path.win32.normalize(OUT + '/downloads'), eventsEnabled: true });
  await page.goto('about:blank');

  const t = {};
  t.page = page; t.S0 = S0; t.TREE = clone(TREE); t.clone = clone;

  function liAt(indexPath) {
    let loc = page.locator('#map > ul > li');
    for (const i of indexPath) loc = loc.locator(':scope > ul > li').nth(i);
    return loc;
  }

  // DOM visible tree only; every descendant title must be visible
  t.tree = async () => {
    const rootUl = page.locator('#map > ul > li').first();
    if (!(await page.locator('#map .empty').count()) && !(await rootUl.count())) return null;
    if (!(await rootUl.count())) return null;
    return rootUl.evaluate((li) => {
      function visible(n) { const r = document.createRange(); r.selectNodeContents(n); const rect = r.getBoundingClientRect(); return !!(n.offsetParent !== null || rect.width || rect.height) && getComputedStyle(n).visibility !== 'hidden' && getComputedStyle(n).display !== 'none'; }
      function build(n) {
        const row = n.querySelector(':scope > .node-row > .title');
        if (row && !visible(row)) throw new Error('hidden title: ' + row.textContent);
        const kids = [];
        const ul = n.querySelector(':scope > ul');
        if (ul) for (const c of ul.children) if (c.tagName === 'LI') kids.push(build(c));
        return { title: row ? row.textContent : null, children: kids };
      }
      return build(li);
    });
  };

  const msgState = async () => {
    const loc = page.locator('#msg');
    const visible = await loc.isVisible().catch(() => false);
    const text = visible ? (await loc.textContent() || '').trim() : '';
    // errors render via inline color '#c22' (no 'error' class) => computed rgb(204, 34, 34)
    const color = visible ? await loc.evaluate(el => getComputedStyle(el).color).catch(() => '') : '';
    return { visible, text, color, isError: visible && text.length > 0 && color === 'rgb(204, 34, 34)' };
  };

  async function snap(label, extra, bestEffort = false) {
    const safe = String(label).replace(/[^\w-]/g, '_');
    // screenshot failures must surface on pass; catch path may pass bestEffort=true
    if (bestEffort) await page.screenshot({ path: path.join(OUT, `snap-${safe}.png`), fullPage: true }).catch(() => {});
    else await page.screenshot({ path: path.join(OUT, `snap-${safe}.png`), fullPage: true });
    const tree = await t.tree().catch(() => null);
    const ms = await msgState().catch(() => ({}));
    fs.writeFileSync(path.join(OUT, `snap-${safe}.json`), JSON.stringify({ label, tree, errors, message: ms, ...extra }, null, 2));
  }

  const promptDialog = (value) => new Promise((res, rej) => page.once('dialog', d => { logAction({ action: 'dialog', type: d.type(), value }); d.accept(value).then(res, rej); }));

  t.gen = async (text) => { await page.fill('#src', text); await page.click('#btn-gen'); await page.waitForTimeout(100); logAction({ action: 'gen' }); };
  t.rename = async (indexPath, title) => { const p = promptDialog(title); await liAt(indexPath).locator(':scope > .node-row > button', { hasText: '重命名' }).first().click(); await p; await page.waitForTimeout(100); logAction({ action: 'rename', indexPath, title }); };
  t.add = async (indexPath, title) => { const p = promptDialog(title); await liAt(indexPath).locator(':scope > .node-row > button', { hasText: '+子节点' }).first().click(); await p; await page.waitForTimeout(100); logAction({ action: 'add', indexPath, title }); };
  t.del = async (indexPath) => { await liAt(indexPath).locator(':scope > .node-row > button', { hasText: '删除' }).first().click(); await page.waitForTimeout(100); logAction({ action: 'del', indexPath }); };
  t.undo = async () => { await page.click('#btn-undo'); await page.waitForTimeout(100); logAction({ action: 'undo' }); };

  t.importFile = async (fixturePath) => {
    const [fc] = await Promise.all([page.waitForEvent('filechooser'), page.click('#btn-import')]);
    // DOM-only #msg observation via MutationObserver, installed BEFORE setFiles; the promise is
    // created but NOT awaited until after setFiles, so the observation window is never missed.
    const observed = page.evaluate(() => new Promise((resolve) => {
      let done = false;
      const finish = (v) => { if (!done) { done = true; resolve(v); } };
      const target = document.querySelector('#msg') || document.documentElement;
      const obs = new MutationObserver(() => {
        const cur = (target.textContent || '').trim();
        if (cur.length > 0) { obs.disconnect(); finish(cur); } // visible nonempty success or error text
      });
      obs.observe(target, { childList: true, characterData: true, subtree: true });
      // bounded timer: disconnect observer and resolve null on timeout
      setTimeout(() => { obs.disconnect(); finish(null); }, 12000);
    }));
    await fc.setFiles(fixturePath);
    const msg = await observed; // actual DOM mutation, success or error
    if (!msg) throw new Error('importFile: no #msg DOM feedback after file selection');
    await page.waitForTimeout(100);
    logAction({ action: 'importFile', fixturePath, messageObserved: true });
  };

  t.reset = async () => {
    const oldErrors = errors.slice(); // inspected before reset
    if (oldErrors.length) {
      fs.appendFileSync(path.join(OUT, 'errors-history.jsonl'), JSON.stringify({ ts: Date.now(), errors: oldErrors }) + '\n');
      throw new Error('reset: prior errors present; refusing to clear silently: ' + JSON.stringify(oldErrors));
    }
    try { await page.close(); } catch (e) {}
    page = await ctx.newPage();
    await attachListeners(page);
    t.page = page;
    errors = [];
    await page.goto('about:blank');
    await page.goto(FILE_URL, { waitUntil: 'load' });
    const tree = await t.tree();
    const emptyVisible = await page.locator('#map .empty').isVisible().catch(() => false);
    if (tree !== null || !emptyVisible) throw new Error('reset: fresh DOM not empty; tree=' + JSON.stringify(tree));
    logAction({ action: 'reset', clearedErrors: oldErrors.length });
  };

  // step(id, expected, action, {messageError?}) — action is an async fn(t)
  t.step = async (id, expected, action, opts = {}) => {
    const rec = { id, expected: clone(expected), status: null, timestamp: new Date().toISOString(), actionCount: 0 };
    const before = fs.existsSync(path.join(OUT, 'actions.jsonl')) ? fs.readFileSync(path.join(OUT, 'actions.jsonl'), 'utf8').split('\n').filter(Boolean).length : 0;
    const countLines = () => fs.existsSync(path.join(OUT, 'actions.jsonl')) ? fs.readFileSync(path.join(OUT, 'actions.jsonl'), 'utf8').split('\n').filter(Boolean).length : 0;
    try {
      if (action) await action(t);
      // tree/visibility inspection exceptions classify as REFERENCE_FAILURE, not DRIVER_ERROR
      let got;
      try { got = await t.tree(); } catch (e) { throw new Error('REFERENCE_FAILURE: tree inspection failed: ' + (e.message || e)); }
      const ms = await msgState();
      const treeOk = JSON.stringify(got) === JSON.stringify(expected);
      // expected === null requires the visible .empty indicator
      const emptyVisible = expected === null ? await page.locator('#map .empty').isVisible().catch(() => false) : null;
      const assertions = { treeMatches: treeOk, nodeCount: got ? (function count(n){return 1+n.children.reduce((a,c)=>a+count(c),0);})(got) : 0, message: ms };
      if (expected === null) assertions.emptyVisible = emptyVisible;
      if (opts.messageError === true) assertions.messageErrorShown = ms.isError;
      else if (opts.messageError === false) assertions.messageErrorShown = !ms.isError;
      const pass = treeOk && errors.length === 0 && (expected !== null || emptyVisible === true) && (opts.messageError !== true || ms.isError);
      rec.actual = got; rec.nodeCount = assertions.nodeCount; rec.uiMessage = ms; rec.errors = errors.slice(); rec.assertions = assertions;
      if (pass) { rec.status = 'PASS'; }
      else {
        rec.status = 'REFERENCE_FAILURE';
        rec.reason = 'tree=' + JSON.stringify(got) + ' expected=' + JSON.stringify(expected) + (expected === null && emptyVisible !== true ? ' .empty not visible' : '') + (opts.messageError === true && !ms.isError ? ' messageError not shown' : '') + (errors.length ? ' errors=' + JSON.stringify(errors) : '');
      }
      rec.actionCount = countLines() - before; // recorded BEFORE snap so JSON metadata agrees with results.json
      await snap(id, { step: rec });
      steps.push(rec); writeResults();
      if (!pass) throw new Error('REFERENCE_FAILURE[' + id + ']: ' + rec.reason);
      logAction({ action: 'step', id, status: 'PASS' });
      return rec;
    } catch (e) {
      const isDriver = rec.status !== 'REFERENCE_FAILURE' && !(e.message || '').startsWith('REFERENCE_FAILURE');
      rec.status = isDriver ? 'DRIVER_ERROR' : rec.status || 'REFERENCE_FAILURE';
      rec.reason = rec.reason || String(e.message || e);
      rec.errors = errors.slice();
      rec.actionCount = countLines() - before;
      await snap(id + '-fail', { step: rec }, true).catch(() => {}); // best-effort snap; preserve reason
      if (!steps.includes(rec)) steps.push(rec); writeResults(); // avoid duplicate failure record
      fs.writeFileSync(path.join(OUT, `error-${String(id).replace(/[^\w-]/g, '_')}.json`), JSON.stringify({ id, status: rec.status, error: String(e.message || e), errors: errors.slice() }, null, 2));
      throw e;
    }
  };

  t.close = async () => {
    writeResults();
    const pageUrls = ctx.pages().map(p => { try { return p.url(); } catch (e) { return '<closed>'; } });
    let closeError = null;
    try { await ctx.close(); } catch (e) { closeError = String(e.message || e); }
    let pagesAfterClose = null;
    try { pagesAfterClose = ctx.pages().map(p => { try { return p.url(); } catch (e) { return '<closed>'; } }); } catch (e) { pagesAfterClose = '<context-unavailable>'; }
    const ownedExit = { pid: owned.pid, exitedAt: owned.exitedAt || null, exitCode: owned.exitCode === undefined ? null : owned.exitCode };
    fs.writeFileSync(path.join(OUT, 'close-evidence.json'), JSON.stringify({ ownedExit, pages: pageUrls, pagesAfterClose, closeError, closedAt: new Date().toISOString(), note: 'context-scoped close only; no global kill' }, null, 2));
    if (closeError) throw new Error('close: ' + closeError);
  };

  writeResults();
  return t;
}

// coordinator fallback: scoped ctx.close available even if createHarness fails after launch
const ownedContext = { ctx: null };
async function emergencyClose() {
  const c = ownedContext.ctx;
  if (!c) { fs.writeFileSync(path.join(OUT, 'emergency-close.json'), JSON.stringify({ closed: false, note: 'no owned context was recorded' }, null, 2)); return { closed: false }; }
  const pagesBefore = c.pages().map(p => { try { return p.url(); } catch (e) { return '<closed>'; } });
  let closeError = null;
  try { await c.close(); } catch (e) { closeError = String(e.message || e); }
  let pagesAfterClose = null;
  try { pagesAfterClose = c.pages().map(p => { try { return p.url(); } catch (e) { return '<closed>'; } }); } catch (e) { pagesAfterClose = '<context-unavailable>'; }
  const ownedExit = { pid: owned.pid, exitedAt: owned.exitedAt || null, exitCode: owned.exitCode === undefined ? null : owned.exitCode };
  fs.writeFileSync(path.join(OUT, 'emergency-close.json'), JSON.stringify({ closed: !closeError, ownedExit, pagesBefore, pagesAfterClose, closeError, closedAt: new Date().toISOString(), note: 'context-scoped emergency close only; no global kill' }, null, 2));
  if (closeError) throw new Error('emergencyClose: ' + closeError);
  return { closed: true };
}

module.exports = { createHarness, emergencyClose };
