// launch-guard.cjs — required BEFORE harness.cjs (i.e. before playwright-core loads)
'use strict';
const cp = require('child_process');
const fs = require('fs');
const path = require('path');

const TARGET_EXE = 'c:/program files/google/chrome/application/chrome.exe';

function normCmd(c) {
  return String(c).replace(/\\/g, '/').replace(/^\u0022|\u0022$/g, '').toLowerCase();
}

function writeJsonSafe(file, obj) {
  const tmp = file + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(obj, null, 2), 'utf8');
  fs.renameSync(tmp, file);
}

function install(out) {
  const profileArg = '--user-data-dir=' + out + '/profile';
  const guard = {
    _child: null,
    _launch: null,
    _verified: false,
    state() {
      return {
        captured: !!this._child,
        pid: this._launch ? this._launch.pid : null,
        verified: this._verified,
        childAlive: !!this._child && this._child.exitCode === null && this._child.signalCode === null,
      };
    },
    verify(cdpPid) {
      if (!this._launch) throw new Error('launch-guard: no owned launch captured');
      if (this._child.exitCode !== null || this._child.signalCode !== null) throw new Error('owned Chrome child already exited');
      const identityPath = path.join(__dirname, 'identity.py');
      const r = cp.spawnSync('python', [identityPath,
        path.join(out, 'launch.json'), path.join(out, 'identity-before.json')], {
        cwd: out, timeout: 10000, windowsHide: true, encoding: 'utf8',
      });
      if (r.status !== 0) {
        throw new Error('launch-guard: identity.py failed status=' + r.status + ' stderr=' + (r.stderr || '').slice(0, 200));
      }
      const identity = JSON.parse(fs.readFileSync(path.join(out, 'identity-before.json'), 'utf8'));
      if (!identity.passed || identity.pid !== this._launch.pid) {
        throw new Error('launch-guard: identity mismatch identity.pid=' + identity.pid + ' owned pid=' + this._launch.pid);
      }
      this._verified = true;
      const mapping = Object.assign({}, this._launch, {
        cdpPid,
        cdpEqualsSpawn: cdpPid === this._launch.pid,
        identity,
      });
      writeJsonSafe(path.join(out, 'launch.json'), mapping);
      return identity;
    },
  };

  const origSpawn = cp.spawn;
  let launched = false;
  cp.spawn = function (command, args, spawnOptions) {
    const isTarget = normCmd(command) === TARGET_EXE && Array.isArray(args) && args.includes(profileArg);
    if (!isTarget) return origSpawn.apply(this, arguments);
    if (launched) throw new Error('launch-guard: multiple owned launches not allowed');
    launched = true;
    const before = Date.now();
    const child = origSpawn.apply(this, arguments);
    const after = Date.now();
    guard._child = child;
    guard._launch = {
      pid: child.pid, driverPid: process.pid,
      exe: String(command), profile: out + '/profile',
      spawnBeforeMs: before, spawnAfterMs: after,
    };
    writeJsonSafe(path.join(out, 'launch.json'), guard._launch);
    return child;
  };
  return guard;
}

module.exports = { install };
