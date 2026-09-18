// prepare-probe.cjs — 只写不执行,协调者审核后运行。
// 可行性:headless 下 OS 原生取消需真实用户在窗口操作,Playwright 无 cancel API,
// 故预期产出 BLOCKED_HEADLESS_NATIVE_CANCEL;脚本仅忠实记录原始观察。
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const OUT = process.env.T1_OUT;
const t0 = Date.now();
const left = () => Math.max(1, 30000 - (Date.now() - t0));

const PROBE_HTML = `<!doctype html><meta charset="utf-8"><button id="choose">choose</button>
<input type="file" id="file" hidden>
<script>
const log=(e)=>console.log('NATIVE_PROBE:'+JSON.stringify({type:e.type,isTrusted:e.isTrusted,filesLength:e.target.files?e.target.files.length:-1}));
document.getElementById('file').addEventListener('cancel',log);
document.getElementById('file').addEventListener('change',log);
document.getElementById('choose').addEventListener('click',()=>document.getElementById('file').click());
</script>`;

function dump(page, tag, arr) {
  // 读取 console 中的原始观察并落盘
  return page.evaluate(() => window.__probeEvents || []).then(ev => {
    for (const e of ev) { arr.push(e); fs.appendFileSync(path.join(OUT, 'events.jsonl'), JSON.stringify({ tag, ...e }) + '\n'); }
  });
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'probe.html'), PROBE_HTML);
  fs.writeFileSync(path.join(OUT, 'events.jsonl'), '');
  const { createHarness } = require(process.env.T1_REFERENCE ? path.resolve(process.env.T1_REFERENCE, 'harness.cjs') : './harness.cjs');
  const t = await createHarness();
  const page = t.page;
  const observations = [];
  let classification = 'BLOCKED_HEADLESS_NATIVE_CANCEL', reason = '';
  try {
    // 注入 console 捕获,页面自身监听器产生日志,不合成事件
    await page.addInitScript(() => {
      window.__probeEvents = [];
      const orig = console.log;
      console.log = (...a) => { if (String(a[0]).startsWith('NATIVE_PROBE:')) window.__probeEvents.push(JSON.parse(String(a[0]).slice(13))); orig(...a); };
    });
    await page.goto(pathToFileURL(path.join(OUT, 'probe.html')).href, { timeout: 3000 });

    // ---- 测试一:无 filechooser 监听,纯真实点击 ----
    await page.reload({ timeout: 3000 });
    const mode1 = [];
    await page.click('#choose', { timeout: 3000 });
    await page.waitForTimeout(500);
    await dump(page, 'no-listener', mode1).catch(() => {});
    await page.screenshot({ path: path.join(OUT, 'shot-mode1.png'), timeout: 3000 });
    // isTrusted=true 的 cancel 若在无人操作时自动出现,只能算浏览器自动取消
    if (mode1.some(e => e.type === 'cancel' && e.isTrusted)) {
      classification = 'BROWSER_AUTO_CANCEL';
      reason = 'headless下无用户操作时出现isTrusted cancel,记为浏览器自动取消,非用户在真实原生窗口点取消';
    } else {
      reason = '无拦截时也未出现原生取消事件';
    }

    // ---- 测试二:filechooser 监听 + Escape(发给网页,非OS对话框) ----
    await page.reload({ timeout: 3000 });
    const mode2 = [];
    let apiNames = [];
    const fc = await Promise.race([
      (async () => { const c = await page.waitForEvent('filechooser', { timeout: 3000 }); await page.click('#choose', { timeout: 3000 }); return c; })(),
      new Promise((_, rej) => setTimeout(() => rej(new Error('filechooser timeout')), 3000))
    ]).catch(() => null);
    if (fc) {
      // 仅反射原型公开方法名,不触碰私有字段
      apiNames = [...new Set([...Object.getOwnPropertyNames(Object.getPrototypeOf(fc)),
        ...(Object.getPrototypeOf(Object.getPrototypeOf(fc)) ? Object.getOwnPropertyNames(Object.getPrototypeOf(Object.getPrototypeOf(fc))) : [])])]
        .filter(n => { try { return typeof fc[n] === 'function'; } catch { return false; } });
    }
    await page.keyboard.press('Escape', { timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(500);
    await dump(page, 'with-listener-escape', mode2).catch(() => {});
    await page.screenshot({ path: path.join(OUT, 'shot-mode2.png'), timeout: 3000 });

    const nativeCancel = [...mode1, ...mode2].some(e => e.type === 'cancel' && e.isTrusted);
    if (!nativeCancel) {
      classification = 'BLOCKED_HEADLESS_NATIVE_CANCEL';
      reason = '仅有filechooser公开对象' + (apiNames.join(',') || '(无方法)') + '及网页级Escape,无用户在真实原生窗口取消的证据;Playwright公开API无cancel,headless无可见窗口供用户操作';
    }
    fs.writeFileSync(path.join(OUT, 'probe-results.json'), JSON.stringify({
      observations: [{ mode: 'no-listener', events: mode1 }, { mode: 'with-listener-escape', events: mode2, filechooserApiMethods: apiNames }],
      classification, nativeUserCancelProven: false, reason, apiCancelMethodAvailable: apiNames.some(n => /cancel/i.test(n))
    }, null, 2));
  } finally {
    await t.close();
  }
  console.log('DONE', classification);
})().catch(e => { console.error('FAILED', e); process.exit(1); });
