'use strict';
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const {chromium}=require('D:/projects/npm-cache/_npx/cbf1b8a072280925/node_modules/playwright-core');
const out=__dirname, report={started:new Date().toISOString(),scope:'environment-only; no reference page or acceptance execution',status:'RUNNING',events:[],network:[]};
let context;
const inside=p=>{const r=path.relative(out,path.resolve(p));assert(!r.startsWith('..')&&!path.isAbsolute(r),'Path outside run03');return p;};
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 try {
  for(const d of ['browser-home','browser-home/AppData/Roaming','browser-home/AppData/Local'])await fs.mkdir(path.join(out,d),{recursive:true});
  const profile=path.join(out,'browser-profile');
  const args=['--headless=new','--remote-debugging-pipe','--user-data-dir='+profile,'--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-component-update','--disable-sync','--disable-extensions','--enable-automation','--window-size=1280,800'];
  report.launch={executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args,chromiumSandbox:true,ignoreDefaultArgs:true,downloadsPath:path.join(out,'downloads'),TEMP:path.join(out,'temp'),TMP:path.join(out,'temp')};
  context=await chromium.launchPersistentContext(profile,{executablePath:report.launch.executablePath,headless:true,chromiumSandbox:true,ignoreDefaultArgs:true,args,downloadsPath:report.launch.downloadsPath,acceptDownloads:true,offline:true,serviceWorkers:'block',viewport:{width:1280,height:800},timeout:30000,env:{...process.env,TEMP:report.launch.TEMP,TMP:report.launch.TMP,HOME:path.join(out,'browser-home'),USERPROFILE:path.join(out,'browser-home'),APPDATA:path.join(out,'browser-home/AppData/Roaming'),LOCALAPPDATA:path.join(out,'browser-home/AppData/Local')}});
  await context.route(/^https?:\/\//,async r=>{report.network.push({url:r.request().url(),action:'abort'});await r.abort('blockedbyclient');});
  const page=context.pages()[0]||await context.newPage();page.setDefaultTimeout(10000);
  await page.goto('about:blank');await page.screenshot({path:path.join(out,'evidence/preflight-blank.png')});
  report.blankScreenshot={status:'PASS',bytes:(await fs.stat(path.join(out,'evidence/preflight-blank.png'))).size};
  const cdp=await context.newCDPSession(page);
  report.browserVersion=await cdp.send('Browser.getVersion');
  report.actualCommandLine=await cdp.send('Browser.getBrowserCommandLine');
  assert(!report.actualCommandLine.arguments.some(a=>/^--(?:no-sandbox|disable-web-security|disable-site-isolation-trials|allow-running-insecure-content)(?:=|$)/.test(a)),'Forbidden safety switch');
  let completeResolve;const completed=new Promise(r=>completeResolve=r);
  cdp.on('Browser.downloadWillBegin',e=>report.events.push({type:'willBegin',...e}));
  cdp.on('Browser.downloadProgress',e=>{report.events.push({type:'progress',...e});if(e.state==='completed')completeResolve(e);});
  await cdp.send('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:path.join(out,'downloads'),eventsEnabled:true});
  await page.goto(pathToFileURL(path.join(out,'preflight-download.html')).href);
  report.navigatorOfflineIndicator=await page.evaluate(()=>navigator.onLine===false); // diagnostic only; effective isolation verified by blocked request below
  await context.setOffline(true);
  const waitDownload=page.waitForEvent('download');await page.locator('#download').click();const download=await waitDownload;
  assert.equal(await download.failure(),null);
  const actual=inside(await download.path());const saved=inside(path.join(out,'downloads/preflight-saveAs.txt'));
  await download.saveAs(saved);
  const event=await Promise.race([completed,new Promise((_,reject)=>setTimeout(()=>reject(Error('CDP completion timeout')),10000))]);
  const raw=inside(event.filePath||path.join(out,'downloads',event.guid));
  const originalBytes=await fs.readFile(raw),savedBytes=await fs.readFile(saved);
  assert.equal(originalBytes.toString(),'T1_RUN03_DOWNLOAD_PREFLIGHT');assert.deepEqual(originalBytes,savedBytes);
  report.download={status:'PASS',actualTemporaryPath:actual,cdpOriginalPath:raw,saveAsPath:saved,sha256:hash(originalBytes),savedSha256:hash(savedBytes),suggestedFilename:download.suggestedFilename()};
  await page.screenshot({path:path.join(out,'evidence/preflight-file-download.png')});
  try{await page.goto('https://t1-preflight.invalid/network-block-check',{timeout:8000});throw Error('Network probe unexpectedly navigated');}catch(e){report.networkProbe={message:e.message};assert(/ERR_INTERNET_DISCONNECTED|ERR_BLOCKED_BY_CLIENT|ERR_FAILED/.test(e.message));}
  report.status='PASS';
 }catch(e){report.status='TOOL_ERROR';report.error={name:e.name,message:e.message,stack:e.stack};}
 finally{if(context)await context.close().catch(e=>report.closeError=e.message);report.ended=new Date().toISOString();await fs.writeFile(path.join(out,'preflight.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,error:report.error?.message,download:report.download}));process.exitCode=report.status==='PASS'?0:1;}
})();
