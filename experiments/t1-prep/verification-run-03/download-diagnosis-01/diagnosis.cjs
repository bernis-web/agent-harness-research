// diagnosis.cjs — Windows Chrome file:// download "canceled" minimal diagnosis (A/B/C three fixed groups)
const { chromium } = require('D:/projects/npm-cache/_npx/cbf1b8a072280925/node_modules/playwright-core');
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const { pathToFileURL } = require('url');

const OUT = __dirname;
const EXPECTED = JSON.parse(fs.readFileSync(path.join(OUT, 'expected.json'), 'utf8'));
const EXPECTED_BYTES = JSON.stringify(EXPECTED, null, 2);
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PAGE_URL = () => pathToFileURL(path.join(OUT, 'diag.html')).href;
const START = Date.now();
let currentContext = null;
const BUDGET_MS = 180000, DL_DEADLINE_MS = 20000;
const FORBIDDEN = ['--no-sandbox', '--disable-web-security', '--disable-site-isolation-trials', '--allow-running-insecure-content'];

// 诊断页（BYTES 在 html 内定义）
fs.writeFileSync(path.join(OUT, 'diag.html'), `<!doctype html><meta charset="utf-8">
<button id="data">data</button><button id="blob">blob</button>
<script>
const BYTES = ${JSON.stringify(EXPECTED_BYTES)};
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

// bounded：每一步限时且 finally 清理定时器
async function bounded(p, ms, label) {
  if (ms <= 0) throw new Error('deadline exceeded before ' + label);
  let t;
  const timer = new Promise((_, rej) => { t = setTimeout(() => rej(new Error('timeout ' + label + ' ' + Math.round(ms) + 'ms')), ms); });
  try { return await Promise.race([Promise.resolve(p), timer]); }
  finally { clearTimeout(t); }
}

async function runGroup(name, useCDP, normalizePath) {
  const dir = path.join(OUT, name);
  ['profile', 'downloads', 'temp', 'home', 'home/AppData/Roaming', 'home/AppData/Local', 'evidence-originals', 'saved']
    .forEach(s => fs.mkdirSync(path.join(dir, s), { recursive: true }));
  const dp = path.join(dir, 'downloads').replaceAll('\\', '/'); // 完整正斜杠
  const result = { group: name, cdpDownloadPath: null, commandLineFlags: [], events: [], downloads: [], errors: [], saved: {}, byteMatch: {}, deepMatch: {} };
  const evl = fs.createWriteStream(path.join(dir, 'events.jsonl'), { flags: 'a' });
  const ev = (o) => { const line = { t: Date.now(), ...o }; result.events.push(line); evl.write(JSON.stringify(line) + '\n'); };

  const launch = {
    executablePath: CHROME, headless: true, chromiumSandbox: true, ignoreDefaultArgs: true,
    args: ['--headless=new', '--remote-debugging-pipe', '--user-data-dir=' + dir + '/profile', '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--disable-extensions', '--enable-automation', '--window-size=1280,800'],
    downloadsPath: dp, acceptDownloads: true, offline: true, serviceWorkers: 'block',
    viewport: { width: 1280, height: 800 }, timeout: 30000,
    env: { ...process.env, TEMP: dir + '/temp', TMP: dir + '/temp', HOME: dir + '/home', USERPROFILE: dir + '/home', APPDATA: dir + '/home/AppData/Roaming', LOCALAPPDATA: dir + '/home/AppData/Local' }
  };
  console.log('[launch]', name, 'exe=' + CHROME, 'user-data-dir=' + dir + '/profile', 'downloads-path=' + dp);
  const context = await chromium.launchPersistentContext(dir + '/profile', launch);
  currentContext=context;
  result.launch={args:launch.args,downloadsPath:launch.downloadsPath,chromiumSandbox:true,ignoreDefaultArgs:true};
  try {
    const page = context.pages()[0] || await context.newPage();
    const cdp = await context.newCDPSession(page); // BrowserContext 无 newBrowserCDPSession，须基于 page
    const cl = await cdp.send('Browser.getBrowserCommandLine');
    result.actualCommandLine=cl.arguments;
    result.commandLineFlags = cl.arguments.filter(a => FORBIDDEN.some(f => a.toLowerCase().startsWith(f)) || /no-sandbox|disable-security/.test(a));
    const bad = cl.arguments.filter(a => FORBIDDEN.some(f => a.toLowerCase().startsWith(f)));
    if (bad.length) throw new Error('forbidden flags present: ' + bad.join(' ')); // 实际断言抛出
    if (useCDP) {
      const dpath = normalizePath ? path.win32.normalize(dp) : dp; // A: 正斜杠; B: 仅 normalize CDP 路径
      result.cdpDownloadPath = dpath;
      await cdp.send('Browser.setDownloadBehavior', { behavior: 'allowAndName', downloadPath: dpath, eventsEnabled: true });
    }
    // CDP 下载事件实时 JSONL
    const guidPath = {};
    cdp.on('Browser.downloadWillBegin', e => { guidPath[e.guid] = null; ev({ ev: 'downloadWillBegin', ...e }); });
    cdp.on('Browser.downloadProgress', e => {
      ev({ ev: 'downloadProgress', ...e });
      if (e.state === 'completed' && e.filePath) { guidPath[e.guid] = e.filePath; }
    });

    // PW 事件实时 JSONL
    page.on('download', dl => ev({ ev: 'pw-download', url: dl.url(), suggestedFilename: dl.suggestedFilename() }));
    page.on('pageerror', e => { ev({ ev: 'pageerror', message: String(e.message).slice(0, 300) }); result.errors.push('pageerror: ' + e.message); });
    page.on('console', m => { if (m.type() === 'error') ev({ ev: 'console.error', text: m.text() }); });
    // 严禁任何网页网络：route 与 offline 都在 context 上
    await context.route(/^https?:\/\//, r => r.abort());
    await context.setOffline(true);
    await page.screenshot({ path: path.join(dir, 's0-about-blank.png') });
    await page.goto(PAGE_URL());

    for (const kind of ['data', 'blob']) {
      const d = { source: kind, url: null, suggestedFilename: null, path: null, failure: null, saveAs: null, filePathCDP: null };
      const dlDeadline = Date.now() + DL_DEADLINE_MS; // 每个下载总 20s
      const remaining = () => dlDeadline - Date.now();
      try {
        const dlP = page.waitForEvent('download', { timeout: remaining() });
        await bounded(page.click('#' + kind), remaining(), 'click'); // 真实 UI 点击
        const dl = await bounded(dlP, remaining(), 'download-event');
        d.url = dl.url(); d.suggestedFilename = dl.suggestedFilename();
        try { d.path = await bounded(dl.path(), remaining(), 'dl.path'); } catch (e) { d.pathError = String(e.message).slice(0, 200); }
        try { d.failure = (await bounded(dl.failure(), remaining(), 'dl.failure')) || null; } catch (e) { /* 超时则继续按失败处理 */ }
        if (d.path && !d.failure && fs.existsSync(d.path)) {
          if (!within(d.path, dir)) throw new Error('original outside sandbox, refusing to read: ' + d.path); // 越界 throw 不读
          d.sha256Original = sha256(d.path);
          const preserved = path.join(dir, 'evidence-originals', kind + '-mindmap.json');
          fs.copyFileSync(d.path, preserved); d.preservedOriginal = preserved; // 原件保留，另存副本
          const saved = path.join(dir, 'saved', kind + '.json');
          await bounded(dl.saveAs(saved), remaining(), 'saveAs'); // 真正 saveAs
          d.saveAs = saved; d.sha256Saved = sha256(saved);
          result.byteMatch[kind] = fs.readFileSync(saved, 'utf8') === EXPECTED_BYTES;
          result.deepMatch[kind] = JSON.stringify(JSON.parse(fs.readFileSync(saved, 'utf8')), null, 2) === EXPECTED_BYTES;
        } else if (d.path && !within(d.path, dir)) { d.pathOutside = true; }
        // CDP guid 完成事件 filePath 匹配（不猜路径）
        const begin=result.events.find(e=>e.ev==='downloadWillBegin' && e.url===d.url);
        const doneGuid=begin && guidPath[begin.guid] ? [begin.guid,guidPath[begin.guid]] : null;
        d.guid=begin?.guid||null;
        if (doneGuid) {
          const [, fp] = doneGuid; d.filePathCDP = fp;
          if (fs.existsSync(fp) && within(fp, dir)) d.sha256CDPFile = sha256(fp);
        }
        if (!d.failure && !d.sha256Original && !d.sha256CDPFile) d.failure = d.failure || 'no completed file (canceled?)';
      } catch (e) { d.failure = d.failure || String(e.message).slice(0, 300); }
      result.downloads.push(d);
      ev({ev:'download-outcome',...d});
      fs.writeFileSync(path.join(dir,'result.json'),JSON.stringify(result,null,2));
      await page.screenshot({ path: path.join(dir, 'after-' + kind + '.png') }).catch(() => {}); // 截图完成后再落盘 result
    }
  } catch (e) { result.errors.push(String(e.message).slice(0, 300)); }
  finally {
    evl.end();
    await context.close().catch(() => {});
    currentContext=null;
  }
  fs.writeFileSync(path.join(dir, 'result.json'), JSON.stringify(result, null, 2));
  return { group: name, cdpDownloadPath: result.cdpDownloadPath, downloads: result.downloads.map(d => ({ source: d.source, url: d.url, suggestedFilename: d.suggestedFilename, failure: d.failure, path: d.path, saveAs: d.saveAs, preservedOriginal: d.preservedOriginal, filePathCDP: d.filePathCDP, sha256Original: d.sha256Original, sha256Saved: d.sha256Saved, byteMatch: result.byteMatch[d.source], deepMatch: result.deepMatch[d.source] })), errors: result.errors };
}

const start = Date.now(); // 必须在 IIFE 前定义（避免 TDZ）
(async () => {
  const results = [];
  // currentContext is shared with runGroup
  const watchdog = setTimeout(async () => { // 独立 180s watchdog：关 context 并写部分结果
    try { if (currentContext) await currentContext.close(); } catch (e) {}
    fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify({ partial: true, reason: '180s budget exhausted', results }, null, 2));
    console.error('watchdog: 180s budget exhausted, partial results written');
    process.exit(1);
  }, BUDGET_MS - (Date.now() - start));

  for (const [name, useCDP, norm] of [['A', true, false], ['B', true, true], ['C', false, false]]) {
    if (Date.now() - start > BUDGET_MS) { results.push({ group: name, skipped: '180s budget exhausted' }); continue; }
    const r = await runGroup(name, useCDP, norm);
    results.push(r);
  }
  clearTimeout(watchdog);
  fs.writeFileSync(path.join(OUT, 'results.json'), JSON.stringify(results, null, 2));
  const failed = results.some(r => r.errors && r.errors.length);
  console.log('summary:', JSON.stringify(results.map(r => ({ group: r.group, downloads: (r.downloads || []).map(d => d.failure ? d.source + ':FAIL' : d.source + ':OK'), errors: r.errors })), null, 2));
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error('fatal:', e.message); process.exit(1); }); // 出错退出非 0
