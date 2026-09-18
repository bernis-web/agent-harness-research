// harness.cjs — CommonJS，保存为 harness.cjs
const { chromium } = require(process.env.T1_PLAYWRIGHT);
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const { pathToFileURL } = require('url');

const OUT = process.env.T1_OUT;
const FILE_URL = pathToFileURL(process.env.T1_REFERENCE).href;
const LAUNCH = {
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true, chromiumSandbox: true, ignoreDefaultArgs: true,
  args: ['--headless=new','--remote-debugging-pipe','--user-data-dir='+OUT+'/profile','--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-component-update','--disable-sync','--disable-extensions','--enable-automation','--window-size=1280,800'],
  downloadsPath: OUT + '/downloads', acceptDownloads: true, offline: true,
  serviceWorkers: 'block', viewport: {width:1280,height:800}, timeout: 30000,
  env: {...process.env, TEMP:OUT+'/temp', TMP:OUT+'/temp', HOME:OUT+'/home', USERPROFILE:OUT+'/home', APPDATA:OUT+'/home/AppData/Roaming', LOCALAPPDATA:OUT+'/home/AppData/Local'}
};
const S0 = '中心主题\n  分支一\n  分支二\n    细节甲\n    细节乙\n  分支三';
const TREE = (() => { const r={title:'中心主题',children:[]}; const b1={title:'分支一',children:[]}, b2={title:'分支二',children:[{title:'细节甲',children:[]},{title:'细节乙',children:[]}]}, b3={title:'分支三',children:[]}; r.children.push(b1,b2,b3); return r; })();
const clone = (x) => JSON.parse(JSON.stringify(x));
const ap = (p) => fs.promises.mkdir(p, {recursive:true});

async function createHarness() {
  for (const d of ['/profile','/downloads','/temp','/home','/home/AppData/Roaming','/home/AppData/Local']) await ap(OUT + d);
  const errors = [];
  const actions = [];
  const items = [...Array.from({length:11},(_,i)=>String(i+1)),'12a','12b','12c','12d','A1','A2','A3','A4','B1','B2','B3'].map(id => ({id,status:'UNTESTED',evidence:null,reason:null}));
  const notes = {};
  let ctx, page, cdp;

  const logAction = (a) => { actions.push({...a, ts: Date.now()}); fs.appendFileSync(path.join(OUT,'actions.jsonl'), JSON.stringify(actions[actions.length-1])+'\n'); };
  const writeResults = () => fs.writeFileSync(path.join(OUT,'results.json'), JSON.stringify({items, notes, summary:{PASS:items.filter(i=>i.status==='PASS').length, FAIL:items.filter(i=>i.status==='FAIL').length, UNTESTED:items.filter(i=>i.status==='UNTESTED').length}}, null, 2));

  async function newPage(url) {
    const p = await ctx.newPage();
    p.setDefaultTimeout(10000);
    p.on('pageerror', e => errors.push('pageerror: ' + e.message));
    p.on('console', m => { if (m.type() === 'error') errors.push('console.error: ' + m.text()); });
    await p.goto(url, {waitUntil:'load'});
    return p;
  }

  ctx = await chromium.launchPersistentContext(OUT + '/profile', LAUNCH);
  await ctx.route(/^https?:\/\//, r => r.abort());
  try { await ctx.setOffline(true); } catch (e) {}
  cdp = await ctx.newCDPSession(await ctx.pages()[0] || await ctx.newPage());
  await cdp.send('Browser.setDownloadBehavior', {behavior:'allowAndName', downloadPath: OUT + '/downloads', eventsEnabled:true});
  page = ctx.pages()[0] || await ctx.newPage();
  page.setDefaultTimeout(10000);
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console.error: ' + m.text()); });
  await page.goto('about:blank');
  await page.screenshot({path: path.join(OUT,'snap-about-blank.png'), fullPage:true});
  await page.goto(FILE_URL, {waitUntil:'load'});
  logAction({action:'open', url:FILE_URL});

  const t = {};
  t.page = page; t.S0 = S0; t.TREE = clone(TREE); t.clone = clone; t.note = (k,v) => { notes[k]=v; writeResults(); };

  t.tree = async () => {
    const rootUl = page.locator('#map > ul > li').first();
    if (!(await page.locator('#map .empty').count()) && !(await rootUl.count())) return null;
    if (!(await rootUl.count())) return null;
    return rootUl.evaluate((li) => {
      function build(n) {
        const row = n.querySelector(':scope > .node-row > .title');
        const kids = [];
        const ul = n.querySelector(':scope > ul');
        if (ul) for (const c of ul.children) if (c.tagName === 'LI') kids.push(build(c));
        return {title: row ? row.textContent : null, children: kids};
      }
      return build(li);
    });
  };

  t.check = async (expected) => {
    const got = await t.tree();
    const treeOk = JSON.stringify(got) === JSON.stringify(expected);
    const emptyVisible = got === null ? await page.locator('#map .empty').isVisible() : false;
    if (!treeOk || errors.length || (got === null && !emptyVisible)) throw new Error('check失败: tree=' + JSON.stringify(got) + ' errors=' + JSON.stringify(errors));
    return true;
  };

  const promptDialog = (pageRef, value) => new Promise((res, reject) => pageRef.once('dialog', d => { logAction({action:'dialog',type:d.type(),value}); d.accept(value).then(res,reject); }));

  t.gen = async (text) => { await page.fill('#src', text); logAction({action:'gen'}); await page.click('#btn-gen'); await page.waitForTimeout(100); };
  t.rename = async (indexPath, title) => { const li = liAt(indexPath); const p = promptDialog(page, title); await li.locator(':scope > .node-row > button', {hasText:'重命名'}).first().click(); await p; await page.waitForTimeout(100); logAction({action:'rename', indexPath, title}); };
  t.add = async (indexPath, title) => { const li = liAt(indexPath); const p = promptDialog(page, title); await li.locator(':scope > .node-row > button', {hasText:'+子节点'}).first().click(); await p; await page.waitForTimeout(100); logAction({action:'add', indexPath, title}); };
  t.del = async (indexPath) => { const li = liAt(indexPath); await li.locator(':scope > .node-row > button', {hasText:'删除'}).first().click(); await page.waitForTimeout(100); logAction({action:'del', indexPath}); };
  t.undo = async () => { await page.click('#btn-undo'); await page.waitForTimeout(100); logAction({action:'undo'}); };

  function liAt(indexPath) {
    let sel = '#map > ul > li';
    for (const i of indexPath) sel += `:nth-child(${i+1}) > ul > li`;
    if (indexPath.length) sel = sel.replace('#map > ul > li', '#map > ul > li');
    let loc = page.locator('#map > ul > li');
    for (const i of indexPath) loc = loc.locator(':scope > ul > li').nth(i);
    return loc;
  }

  t.reopen = async () => { await page.close(); page = await newPage(FILE_URL); t.page = page; logAction({action:'reopen'}); };

  t.exportMap = async () => {
    const evProm = new Promise(res => cdp.on('Browser.downloadWillBegin', e => res(e)));
    const doneProm = new Promise(res => cdp.on('Browser.downloadProgress', e => { if (e.state === 'completed') res(e); }));
    const dl = page.waitForEvent('download', {timeout:10000});
    await page.click('#btn-export');
    const begin = await evProm, done = await doneProm;
    const orig = done.filePath || path.join(OUT,'downloads', begin.guid);
    const saved = path.join(OUT,'downloads','t1-map.json');
    await page.waitForTimeout(300);
    const savedPath = path.join(OUT,'downloads','t1-map.json');
    // 保留原件 + saveAs 到 t1-map.json
    const download = await dl;
    await download.saveAs(savedPath);
    const origExists = fs.existsSync(orig) || fs.existsSync(download.path ? await download.path() : '');
    const origPath = fs.existsSync(orig) ? orig : await download.path();
    const inScope = path.resolve(origPath).startsWith(path.resolve(OUT)+path.sep);
    fs.writeFileSync(path.join(OUT,'download-evidence.json'),JSON.stringify({begin,done,playwrightPath:await download.path(),original:origPath,saved:savedPath,originalSHA256:crypto.createHash('sha256').update(fs.readFileSync(origPath)).digest('hex'),savedSHA256:crypto.createHash('sha256').update(fs.readFileSync(savedPath)).digest('hex')},null,2));
    if (!fs.existsSync(origPath) || !inScope) throw new Error('导出原件缺失或越界: ' + origPath);
    const buf = fs.readFileSync(origPath);
    const json = JSON.parse(fs.readFileSync(savedPath,'utf-8'));
    logAction({action:'export', orig:origPath, saved:savedPath, hash:crypto.createHash('sha256').update(buf).digest('hex')});
    return json;
  };

  t.importSaved = async () => {
    const msgBefore = await page.locator('#msg').textContent();
    const [fc] = await Promise.all([ page.waitForEvent('filechooser'), page.click('#btn-import') ]);
    await fc.setFiles(path.join(OUT,'downloads','t1-map.json'));
    await page.waitForFunction(([prev]) => {
      const m = document.querySelector('#msg');
      return m && m.textContent !== prev && m.textContent.indexOf('导入成功') !== -1;
    }, [msgBefore], {timeout:10000});
    logAction({action:'importSaved'});
  };

  t.snap = async (label) => {
    const safe = String(label).replace(/[^\w-]/g,'_');
    await page.screenshot({path: path.join(OUT, `snap-${safe}.png`), fullPage:true});
    const tree = await t.tree().catch(() => null);
    fs.writeFileSync(path.join(OUT, `snap-${safe}.json`), JSON.stringify({tree, errors, message:await page.locator("#msg").textContent()}, null, 2));
    logAction({action:'snap', label});
  };

  t.step = async (id, fn) => {
    try { await fn(t); await t.snap(id);
      const it = items.find(i => i.id === id); if (it) { it.status='PASS'; it.evidence=`snap-${id}.png`; }
      if (/^B[12]-/.test(id)) { const parent=items.find(i=>i.id===id.split('-')[0]); (parent.substeps ||= []).push({id,status:'PASS',evidence:`snap-${id}.png`}); if(parent.substeps.length===10){parent.status='PASS';parent.evidence=parent.substeps.map(s=>s.evidence);} }
      writeResults(); logAction({action:'step', id, status:'PASS'});
    } catch (e) {
      await t.snap(id + '-fail').catch(()=>{});
      const it = items.find(i => i.id === id.split('-')[0]); if (it) { it.status='FAIL'; it.evidence=`snap-${id}-fail.png`; it.reason=String(e.message||e); }
      writeResults();
      fs.writeFileSync(path.join(OUT, `error-${id}.json`), JSON.stringify({id, error:String(e.message||e), errors}, null, 2));
      logAction({action:'step', id, status:'FAIL', error:String(e.message||e)});
      throw e;
    }
  };

  t.unverified = async (id, reason, fn) => {
    try { await fn(t); await t.snap(id + '-unverified'); }
    catch (e) {
      await t.snap(id + '-fail').catch(()=>{});
      writeResults();
      fs.writeFileSync(path.join(OUT, `error-${id}.json`), JSON.stringify({id, error:String(e.message||e), errors}, null, 2));
      throw e;
    }
    const it = items.find(i => i.id === id); if (it) { it.status='UNTESTED'; it.reason=reason; it.evidence=`snap-${id}-unverified.png`; }
    writeResults(); logAction({action:'unverified', id, reason});
  };

  t.close = async () => {
    writeResults();
    try { await ctx.close(); } catch (e) {}
  };

  writeResults();
  return t;
}
module.exports = { createHarness };
