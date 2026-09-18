// diagnosis.cjs — Windows Chrome file:// download "canceled" minimal diagnosis (A/B/C three fixed groups)
const { chromium } = require('D:/projects/npm-cache/_npx/cbf1b8a072280925/node_modules/playwright-core');
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const { pathToFileURL } = require('url');

const OUT = __dirname;
const EXPECTED = JSON.parse(fs.readFileSync(path.join(OUT, 'expected.json'), 'utf8'));
const EXPECTED_BYTES = JSON.stringify(EXPECTED, null, 2);
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PAGE_URL = () => pathToFileURL(path.join(OUT, 'diag.html')).href;

fs.mkdirSync(path.join(OUT, 'evidence-originals'), { recursive: true });

// 唯一诊断页
fs.writeFileSync(path.join(OUT, 'diag.html'), `<!doctype html><meta charset="utf-8">
<button id="data">data</button><button id="blob">blob</button>
<script>
document.getElementById('data').onclick = () => {
  const a = document.createElement('a');
  a.href = 'data:application/json;charset=utf-8,' + encodeURIComponent(BYTES);
  a.download = 'mindmap.json'; document.body.appendChild(a); a.click(); a.remove();
};
document.getElementById('blob').onclick = () => {
  const u = URL.createObjectURL(new Blob([BYTES], { type: 'application/json' }));
  const a = document.createElement('a');
  a.href = u; a.download = 'mindmap.json'; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(u), 1000);
};
</script>`);

const sha256 = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const within = (p, dir) => path.resolve(p).toLowerCase().startsWith(path.resolve(dir).toLowerCase() + path.sep);

async function runGroup(name, useCDP, normalizePath) {
  const dir = path.join(OUT, name);
  ['profile', 'downloads', 'temp', 'home', 'home/AppData/Roaming', 'home/AppData/Local'].forEach(s => fs.mkdirSync(path.join(dir, s), { recursive: true }));
  const dp = dir + '/downloads';
  const result = { group: name, cdpDownloadPath: null, commandLineFlags: [], events: [], downloads: [], errors: [], saved: {}, byteMatch: {}, deepMatch: {} };
  const evl = fs.createWriteStream(path.join(dir, 'cdp-events.jsonl'));
  const bounded = (p, ms) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error('timeout ' + ms + 'ms')), ms))]);

  const launch = {
    executablePath: CHROME, headless: true, chromiumSandbox: true, ignoreDefaultArgs: true,
    args: ['--headless=new', '--remote-debugging-pipe', '--user-data-dir=' + dir + '/profile', '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--disable-extensions', '--enable-automation', '--window-size=1280,800'],
    downloadsPath: dp, acceptDownloads: true, offline: true, serviceWorkers: 'block',
    viewport: { width: 1280, height: 800 }, timeout: 30000,
    env: { ...process.env, TEMP: dir + '/temp', TMP: dir + '/temp', HOME: dir + '/home', USERPROFILE: dir + '/home', APPDATA: dir + '/home/AppData/Roaming', LOCALAPPDATA: dir + '/home/AppData/Local' }
  };
  const browser = await chromium.launchPersistentContext(dir + '/profile', launch);
  try {
    const cdp = await browser.newBrowserCDPSession();
    const cl = await cdp.send('Browser.getBrowserCommandLine');
    result.commandLineFlags = cl.arguments.filter(a => /no-sandbox|disable-security/.test(a));
    if (useCDP) {
      const dpath = normalizePath ? path.win32.normalize(dp) : dp; // A: forward slashes; B: normalized (backslashes)
      result.cdpDownloadPath = dpath;
      await cdp.send('Browser.setDownloadBehavior', { behavior: 'allowAndName', downloadPath: dpath, eventsEnabled: true });
    } else {
      result.cdpDownloadPath = null; // C: 未调用 Browser.setDownloadBehavior，无 CDP 下载事件（诚实说明）
    }
    cdp.on('Browser.downloadWillBegin', e => { result.events.push({ t: Date.now(), ev: 'downloadWillBegin', ...e }); evl.write(JSON.stringify({ ev: 'downloadWillBegin', ...e }) + '\n'); });
    cdp.on('Browser.downloadProgress', e => { result.events.push({ t: Date.now(), ev: 'downloadProgress', ...e }); evl.write(JSON.stringify({ ev: 'downloadProgress', ...e }) + '\n'); });

    const page = await browser.newPage();
    page.on('pageerror', e => result.errors.push('pageerror: ' + e.message));
    page.on('console', m => { if (m.type() === 'error') result.errors.push('console.error: ' + m.text()); });
    await page.route(/^https?:\/\//, r => r.abort());
    await page.setOffline(true);
    await page.screenshot({ path: path.join(dir, 's0-about-blank.png') });
    await page.goto(PAGE_URL());

    for (const kind of ['data', 'blob']) {
      const d = { source: kind, url: null, suggestedFilename: null, path: null, failure: null, saveAs: null, filePathCDP: null };
      try {
        const dlPromise = page.waitForEvent('download', { timeout: 20000 });
        await bounded(page.click('#' + kind), 20000);
        const dl = await bounded(dlPromise, 20000);
        d.url = dl.url(); d.suggestedFilename = dl.suggestedFilename();
        try { d.path = await bounded(dl.path(), 20000); } catch (e) { d.pathError = String(e.message).slice(0, 200); }
        try { d.failure = dl.failure(); } catch (e) { /* still running */ }
        if (d.path && within(d.path, dir) && fs.existsSync(d.path)) {
          d.sha256Original = sha256(d.path);
          const copy = path.join(dir, 'evidence-originals', kind + '-mindmap.json');
          fs.copyFileSync(d.path, copy);
          const saved = path.join(dir, 'saved', kind + '.json');
          fs.mkdirSync(path.join(dir, 'saved'), { recursive: true });
          fs.copyFileSync(d.path, saved);
          d.saveAs = saved; d.sha256Saved = sha256(saved);
          result.byteMatch[kind] = fs.readFileSync(saved, 'utf8') === EXPECTED_BYTES;
          result.deepMatch[kind] = JSON.stringify(JSON.parse(fs.readFileSync(saved, 'utf8')), null, 2) === EXPECTED_BYTES;
        } else if (d.path) { d.pathOutsideOrMissing = true; }
      } catch (e) { d.failure = d.failure || String(e.message).slice(0, 300); }
      result.downloads.push(d);
      try { await page.screenshot({ path: path.join(dir, 'after-' + kind + '.png') }); } catch (e) { /* ignore */ }
    }
  } catch (e) { result.errors.push(String(e.message).slice(0, 300)); }
  finally {
    evl.end();
    await browser.close().catch(() => {});
  }
  fs.writeFileSync(path.join(dir, 'result.json'), JSON.stringify(result, null, 2));
  return { group: name, cdpDownloadPath: result.cdpDownloadPath, downloads: result.downloads.map(d => ({ source: d.source, url: d.url, suggestedFilename: d.suggestedFilename, failure: d.failure, path: d.path, saveAs: d.saveAs, byteMatch: result.byteMatch[d.source], deepMatch: result.deepMatch[d.source] })), errors: result.errors };
}

(async () => {
  const results = [];
  for (const [name, useCDP, norm] of [['A', true, false], ['B', true, true], ['C', false, false]]) {
    if (Date.now() - start > 180000) { results.push({ group: name, skipped: '180s budget exhausted' }); continue; }
    results.push(await runGroup(name, useCDP, norm));
  }
  fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify(results, null, 2));
  console.log('diagnosis collection complete (exit 0 = collection done, not acceptance)');
  process.exit(0);
})().catch(e => { console.error('fatal:', e.message); process.exit(0); });
const start = Date.now();
