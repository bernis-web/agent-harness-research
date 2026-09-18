'use strict';
/* T1 hidden acceptance cases H1-H9.
 * Uses only the provided harness API (t), fs, path. No globals, no app internals.
 * Fixture files are materialized ONLY under OUT/fixtures from ./fixtures.json.
 * Expected trees are built in-test, independent of the actual UI.
 * Node paths are zero-based child-index arrays: [] = root, [1] = root's second child, [1,0] = that child's first child.
 */
const fs = require('fs');
const path = require('path');

const N = (title, children = []) => ({ title, children });
const FIX = require('./fixtures.json');
const fx = (name) => FIX.files.find((f) => f.name === name).content;

async function materialize(OUT) {
  const dir = path.join(OUT, 'fixtures');
  await fs.promises.mkdir(dir, { recursive: true });
  for (const f of FIX.files) {
    await fs.promises.writeFile(path.join(dir, f.name), f.content, 'utf8');
  }
  return dir;
}

function nodeAt(tree, p) {
  let n = tree;
  for (const i of p) n = n.children[i];
  return n;
}

module.exports = async function (t, OUT) {
  const fdir = await materialize(OUT);
  const fp = (name) => path.join(fdir, name);

  const S0 = () => N('中心主题', [N('分支一'), N('分支二', [N('细节甲'), N('细节乙')]), N('分支三')]);
  const S0R = () => N('临时根', [N('分支一'), N('分支二', [N('细节甲'), N('细节乙')]), N('分支三')]);

  // ---------- H1: empty-input generation rejected, undo record preserved ----------
  const h1 = async (id, data) => {
    await t.step(id + '-reset', null, async () => { await t.reset(); });
    await t.step(id + '-gen-S0', S0(), async () => { await t.gen(fx('S0.txt')); });
    await t.step(id + '-rename-root', S0R(), async () => { await t.rename([], '临时根'); });
    await t.step(id + '-reject', S0R(), async () => { await t.gen(data); }, { messageError: true });
    await t.step(id + '-undo', S0(), async () => { await t.undo(); });
  };
  await h1('H1-empty-textbox', fx('H1-empty.txt'));
  await h1('H1-three-blank-lines', fx('H1-blank3.txt'));

  // ---------- H2: single-root input is legal ----------
  await t.step('H2-reset', null, async () => { await t.reset(); });
  await t.step('H2-gen-single-root', N('根A'), async () => { await t.gen(fx('H2-rootA.txt')); });
  await t.step('H2-undo-noop', N('根A'), async () => { await t.undo(); });

  // ---------- H3: format violations all rejected, S0 and empty undo record intact ----------
  const h3 = [
    ['H3-indent-first-line', 'H3-1.txt'],
    ['H3-jump-level', 'H3-2.txt'],
    ['H3-tab-middle', 'H3-3.txt'],
    ['H3-tab-leading', 'H3-4.txt'],
    ['H3-tab-trailing', 'H3-5.txt']
  ];
  for (const [id, fn] of h3) {
    await t.step(id + '-reset', null, async () => { await t.reset(); });
    await t.step(id + '-gen-S0', S0(), async () => { await t.gen(fx('S0.txt')); });
    await t.step(id + '-reject', S0(), async () => { await t.gen(fx(fn)); }, { messageError: true });
    await t.step(id + '-undo-noop', S0(), async () => { await t.undo(); });
  }

  // ---------- H4: duplicate titles identified by position ----------
  const h4a = () => N('根', [N('待办'), N('组', [N('待办')])]);
  const h4b = () => N('根', [N('待办改'), N('组', [N('待办')])]);
  await t.step('H4-reset', null, async () => { await t.reset(); });
  await t.step('H4-gen-dup', h4a(), async () => { await t.gen(fx('H4.txt')); });
  await t.step('H4-rename-first-dup', h4b(), async () => { await t.rename([0], '待办改'); });

  // ---------- H5: invalid imports rejected, undo record preserved ----------
  const h5pre = async (id) => {
    await t.step(id + '-reset', null, async () => { await t.reset(); });
    await t.step(id + '-gen-S0', S0(), async () => { await t.gen(fx('S0.txt')); });
    await t.step(id + '-rename-root', S0R(), async () => { await t.rename([], '临时根'); });
  };
  for (let i = 1; i <= 3; i++) {
    const id = 'H5-f' + i;
    await h5pre(id);
    await t.step(id + '-import-reject', S0R(), async () => { await t.importFile(fp('H5-f' + i + '.json')); }, { messageError: true });
    await t.step(id + '-undo', S0(), async () => { await t.undo(); });
  }
  await h5pre('H5-f4-6');
  for (let i = 4; i <= 6; i++) {
    await t.step('H5-f' + i + '-import-reject', S0R(), async () => { await t.importFile(fp('H5-f' + i + '.json')); }, { messageError: true });
  }
  await t.step('H5-f4-6-undo', S0(), async () => { await t.undo(); });

  // ---------- H6: successful import = whole replace + stack cleared ----------
  const F1 = () => N('导入根A', [N('子一')]);
  const F1T = () => N('导入根A', [N('子一'), N('临时')]);
  const F2 = () => N('导入根B');
  await t.step('H6-reset', null, async () => { await t.reset(); });
  await t.step('H6-gen-S0', S0(), async () => { await t.gen(fx('S0.txt')); });
  await t.step('H6-rename-root', N('改根', [N('分支一'), N('分支二', [N('细节甲'), N('细节乙')]), N('分支三')]), async () => { await t.rename([], '改根'); });
  await t.step('H6-import-F1', F1(), async () => { await t.importFile(fp('H6-f1.json')); });
  await t.step('H6-undo-noop-after-F1', F1(), async () => { await t.undo(); });
  await t.step('H6-add-temp', F1T(), async () => { await t.add([], '临时'); });
  await t.step('H6-import-F2', F2(), async () => { await t.importFile(fp('H6-f2.json')); });
  await t.step('H6-undo-noop-after-F2', F2(), async () => { await t.undo(); });

  // ---------- H7: deep tree, subtree delete, full restore ----------
  const H7full = () => N('主', [N('支一', [N('叶一', [N('子叶一')]), N('叶二')]), N('支二')]);
  await t.step('H7-reset', null, async () => { await t.reset(); });
  await t.step('H7-gen-deep', H7full(), async () => { await t.gen(fx('H7.txt')); });
  await t.step('H7-del-zhi1', N('主', [N('支二')]), async () => { await t.del([0]); });
  await t.step('H7-undo-restore', H7full(), async () => { await t.undo(); });

  // ---------- H8: undo depth exactly at public lower bound 10 ----------
  const edits = [
    ['add', [], '附4'],
    ['rename', [3], '附肆'],
    ['add', [0], '附1'],
    ['rename', [1, 0], '改甲'],
    ['add', [1, 1], '附2'],
    ['add', [1], '附3'],
    ['rename', [2], '改三'],
    ['add', [2], '附5'],
    ['rename', [], '改根'],
    ['add', [0], '附6']
  ];
  await t.step('H8-reset', null, async () => { await t.reset(); });
  await t.step('H8-gen-S0', S0(), async () => { await t.gen(fx('S0.txt')); });
  let cur = S0();
  const snaps = [t.clone(cur)]; // snaps[k] = full expected tree before edit k+1
  for (let k = 0; k < 10; k++) {
    const [op, p, title] = edits[k];
    if (op === 'add') nodeAt(cur, p).children.push(N(title));
    else nodeAt(cur, p).title = title;
    const after = t.clone(cur);
    const kn = k + 1;
    await t.step('H8-edit' + kn, after, async () => {
      if (op === 'add') await t.add(p, title);
      else await t.rename(p, title);
    });
    snaps.push(after);
  }
  for (let j = 1; j <= 10; j++) {
    await t.step('H8-undo' + j, t.clone(snaps[10 - j]), async () => { await t.undo(); });
  }
  await t.step('H8-undo11-noop', t.clone(snaps[0]), async () => { await t.undo(); });

  // ---------- H9: invalid edits (empty/tab titles) never enter the undo stack ----------
  const H9a = () => N('中心主题', [N('合法1'), N('分支二', [N('细节甲'), N('细节乙')]), N('分支三')]);
  await t.step('H9-reset', null, async () => { await t.reset(); });
  await t.step('H9-gen-S0', S0(), async () => { await t.gen(fx('S0.txt')); });
  await t.step('H9-rename-valid', H9a(), async () => { await t.rename([0], '合法1'); });
  const h9inv = [
    ['H9-empty-title', 'H9-empty.txt'],
    ['H9-tab-leading', 'H9-tab1.txt'],
    ['H9-tab-trailing', 'H9-tab2.txt'],
    ['H9-tab-middle', 'H9-tab3.txt']
  ];
  for (const [id, fn] of h9inv) {
    await t.step(id + '-reject', H9a(), async () => { await t.rename([1], fx(fn)); });
  }
  await t.step('H9-undo', S0(), async () => { await t.undo(); });
};
