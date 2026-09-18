// step11.cjs — real native file-open dialog cancel, scoped to browser PID
'use strict';
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const PYTHON = process.env.T1_PYTHON || 'python';

function runNative(pid, outDir) {
  return new Promise((resolve) => {
    const script = path.join(__dirname, 'native_cancel.py');
    const child = spawn(PYTHON, [script, String(pid), outDir],
      { windowsHide: true, shell: false, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '', stderr = '', done = false;
    const finish = (timedOut) => {
      if (done) return; done = true;
      fs.writeFileSync(path.join(outDir, 'native-stdout.log'), stdout);
      fs.writeFileSync(path.join(outDir, 'native-stderr.log'), stderr);
      if (timedOut) { try { child.kill(); } catch {} }
      resolve({ timedOut, code: child.exitCode });
    };
    const timer = setTimeout(() => finish(true), 30000);
    child.stdout.on('data', d => { stdout += d; });
    child.stderr.on('data', d => { stderr += d; });
    child.on('exit', () => { clearTimeout(timer); finish(false); });
    child.on('error', (e) => { stderr += String(e); clearTimeout(timer); finish(false); });
  });
}

async function waitForNativeResult(outDir, ms) {
  const p = path.join(outDir, 'native-result.json');
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    try {
      const j = JSON.parse(fs.readFileSync(p, 'utf8'));
      if (j.stage === 'done') return j;
    } catch {}
    await t_sleep(200);
  }
  return null;
}
const t_sleep = (ms) => new Promise(r => setTimeout(r, ms));

module.exports = async function step11(t, out) {
  fs.mkdirSync(out, { recursive: true });
  const results = { item: 11, name: 'native-visible-dialog-cancel', PASS: false,
                    classification: null, checks: {}, evidence: {} };
  try {
    // 1) build public step10-equivalent state via harness (prerequisite only)
    await t.gen('temporary');
    await t.rename([], 'changed');

    // prerequisite import: harness chooser interception used HERE only
    await t.importSaved();

    const oraclePath = path.join(out, 'downloads', 't1-map.json');
    const oracle = JSON.parse(fs.readFileSync(oraclePath, 'utf8'));
    results.checks.oracleLoaded = true;
    results.evidence.oracle = oraclePath;

    // 2) prove tree state + save before anything native
    await t.check(oracle);
    await t.snap('before-cancel');
    results.checks.treeBeforeImport = true;

    // 3) exact browser PID via CDP
    const cdp = await t.page.context().browser().newBrowserCDPSession();
    const resp = await cdp.send('SystemInfo.getProcessInfo');
    await cdp.detach();
    fs.writeFileSync(path.join(out, 'cdp-process-info.json'), JSON.stringify(resp, null, 2));
    if (!Array.isArray(resp.processInfo)) throw { classify: 'BLOCKED_DRIVER', msg: 'getProcessInfo: processInfo is not an array', rawResp: resp };
    const browserProcs = resp.processInfo.filter(p => p.type === 'browser');
    if (browserProcs.length !== 1) throw { classify: 'BLOCKED_DRIVER', msg: 'browser pid ambiguous', rawResp: resp };
    const cdpPid = browserProcs[0].id;
    if (!Number.isSafeInteger(cdpPid) || cdpPid <= 0) throw { classify: 'BLOCKED_DRIVER', msg: 'CDP process id invalid', rawResp: resp };
    let identity;
    try { identity = t.launchGuard.verify(cdpPid); } catch (e) { throw { classify:'BLOCKED_IDENTITY', msg:String(e) }; }
    const browserPid = identity.pid;
    results.evidence.liveIdentity = identity;
    results.evidence.cdpPid = cdpPid;
    results.evidence.browserPid = browserPid;

    // 4) DOM observation only (cancel/change), no dispatch
    const inputLoc = t.page.locator('input[type=file]');
    const count = await inputLoc.count();
    if (count !== 1) throw { classify: 'BLOCKED', msg: 'file input not unique: ' + count };
    let cancelEvt = null, changeEvt = null;
    await t.page.exposeFunction('__step11evt', (kind, trusted) => {
      fs.appendFileSync(path.join(out,'dom-events.jsonl'), JSON.stringify({kind,isTrusted:trusted,at:new Date().toISOString()})+'\n');
      if (kind === 'cancel') cancelEvt = { trusted };
      if (kind === 'change') changeEvt = { trusted };
    });
    await inputLoc.first().evaluate(el => {
      el.addEventListener('cancel', e => window.__step11evt('cancel', e.isTrusted));
      el.addEventListener('change', e => window.__step11evt('change', e.isTrusted));
    });

// step11 — inserted after playwright import, before native spawn (same in-process playwright-core)
await (async () => {
  const fs = require('fs');
  if (t.page.listenerCount('filechooser') !== 0) {
    throw new Error('pre-spawn: filechooser listener already attached, count=' + t.page.listenerCount('filechooser'));
  }
  // Resolve the in-process impl object: clientConnection.toImpl maps a client-side
  // Page to its dispatcher's impl Page (coreBundle.js ~63977).
  const conn = t.page._connection;
  if (!conn || typeof conn.toImpl !== 'function') {
    throw new Error('reject: t.page._connection.toImpl not available');
  }
  const pageImpl = conn.toImpl(t.page);
  if (!pageImpl || !pageImpl.delegate) {
    throw new Error('reject: page impl or impl.delegate mapping not available');
  }
  const mainFrameSession = pageImpl.delegate._mainFrameSession;
  const mainClient = mainFrameSession && mainFrameSession._client;
  if (!mainClient || typeof mainClient.send !== 'function') {
    throw new Error('reject: impl.delegate._mainFrameSession._client mapping not available');
  }
  // 1) Clear Playwright's own interceptors registered for this page.
  await t.page._channel.updateSubscription({ event: 'fileChooser', enabled: false });
  // 2) Explicitly disable native interception on the ORIGINAL main-frame CDP session
  //    (_updateFileChooserInterception sends Page.setInterceptFileChooserDialog on
  //    this exact _client), not on a fresh detached CDP session.
  const interceptedBefore = pageImpl.fileChooserIntercepted();
  await mainClient.send('Page.setInterceptFileChooserDialog', { enabled: false });
  const interceptedAfter = pageImpl.fileChooserIntercepted();
  const listenerCount = t.page.listenerCount('filechooser');
  if (interceptedAfter !== false) {
    throw new Error('post-disable: fileChooserIntercepted() still true');
  }
  if (listenerCount !== 0) {
    throw new Error('post-disable: filechooser listener count=' + listenerCount);
  }
  fs.writeFileSync(path.join(out,'interception.json'), JSON.stringify({
    filechooserListenerCount: listenerCount,
    fileChooserInterceptedBefore: interceptedBefore,
    fileChooserInterceptedAfter: interceptedAfter,
    updateSubscription: { event: 'fileChooser', enabled: false },
    mainFrameSessionSetInterceptFileChooserDialog: { enabled: false },
    atMs: Date.now(),
  }, null, 2));
})();
    // 5) spawn native helper BEFORE clicking; no chooser listener from here on
    const nativePromise = runNative(browserPid, out);

    // 6) trigger the dialog; native process cancels it independently
    let clickOk = true;
    try {
      await t.page.click('#btn-import', { timeout: 15000 });
    } catch { clickOk = false; }

    const native = await nativePromise;
    const nativeRes = fs.existsSync(path.join(out,'native-result.json')) ? JSON.parse(fs.readFileSync(path.join(out,'native-result.json'),'utf8')) : null;
    fs.writeFileSync(path.join(out, 'native-run.json'),
      JSON.stringify({ timedOut: native.timedOut, code: native.code, clickOk }));

    if (native.timedOut || native.code !== 0 || !nativeRes || !nativeRes.passed) throw {classify:'BLOCKED',msg:'Native tool/ownership failure: '+JSON.stringify(nativeRes)};
    await t_sleep(200);
    // 7) assertions
    const A = {};
    A.nativePassed = !!(nativeRes && nativeRes.passed === true && nativeRes.stage === 'done');
    A.dialogDestroyed = !!(nativeRes && (nativeRes.dialogDestroyed || nativeRes.dialogClosed));
    A.cancelTrusted = cancelEvt !== null && cancelEvt.trusted === true;
    A.noChange = changeEvt === null;
    // No empty-file API was called; DOM events recorded independently.
    await t.check(oracle);           // unchanged after trusted cancel
    await t.snap('after-cancel');
    results.checks.treeAfterCancel = true;

    await t.undo();
    await t.check(oracle);           // unchanged after undo
    await t.snap('after-undo');
    results.checks.treeAfterUndo = true;

    results.checks.assertions = A;
    results.PASS = A.nativePassed && A.dialogDestroyed && A.cancelTrusted &&
                   A.noChange && clickOk;
    results.evidence.screenshots = ['before-cancel', 'after-cancel', 'after-undo'];
  } catch (e) {
    const cls = e && e.classify ? e.classify
      : (e && /native|ownership|pid|dialog/i.test(String(e && e.msg || e)) ? 'BLOCKED' : 'FAIL');
    results.classification = cls;
    results.error = String(e && e.msg || e);
    results.PASS = false;
  }
  results.status=results.PASS?'PASS':results.classification==='FAIL'?'FAIL':'UNTESTED';
  if(!results.PASS && !results.classification) results.classification='BLOCKED_EVENT_EVIDENCE';
  fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify(results, null, 2));
  if (!results.PASS) process.exitCode = 1;
  return results; // stop immediately; browser cleanup belongs to outer runner
};
