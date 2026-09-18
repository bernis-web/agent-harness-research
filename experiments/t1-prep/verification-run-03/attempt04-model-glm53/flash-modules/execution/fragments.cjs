// fragments.cjs — A1-A4 + B1-B3
module.exports = async (t) => {
  const S0 = t.S0;

  // ---------- 片段 A ----------
  await t.step('A1', async () => {
    await t.gen(S0);
    await t.del([1]); // 删除根第2子"分支二"(含2孙)
    const exp = t.clone(t.TREE);
    exp.children.splice(1, 1);
    await t.check(exp); // 根剩 分支一/分支三 共3节点
    await t.snap('A1');
  });

  await t.step('A2', async () => {
    await t.undo();
    await t.check(t.clone(t.TREE)); // 回S0六节点
    await t.snap('A2');
  });

  await t.step('A3', async () => {
    await t.del([]); // 删除根
    await t.check(null); // empty可见
    await t.snap('A3');
  });

  await t.step('A4', async () => {
    await t.undo();
    await t.check(t.clone(t.TREE)); // 恢复S0六节点
    await t.snap('A4');
  });

  // ---------- 片段 B ----------
  await t.gen(S0); // UI重置
  let cur = t.clone(t.TREE);
  const pre = [];

  const edits = [
    async () => { pre.push(t.clone(cur)); cur.children[0].title = '甲一'; await t.rename([0], '甲一'); },
    async () => { pre.push(t.clone(cur)); cur.children[0].children.push({ title: '临时1', children: [] }); await t.add([0], '临时1'); },
    async () => { pre.push(t.clone(cur)); cur.children[1].title = '甲二'; await t.rename([1], '甲二'); },
    async () => { pre.push(t.clone(cur)); cur.children[1].children.push({ title: '临时2', children: [] }); await t.add([1], '临时2'); },
    async () => { pre.push(t.clone(cur)); cur.children[2].title = '甲三'; await t.rename([2], '甲三'); },
    async () => { pre.push(t.clone(cur)); cur.children[1].children[0].children.push({ title: '临时3', children: [] }); await t.add([1, 0], '临时3'); },
    async () => { pre.push(t.clone(cur)); cur.children[1].children[0].title = '甲细'; await t.rename([1, 0], '甲细'); },
    async () => { pre.push(t.clone(cur)); cur.children.push({ title: '临时根', children: [] }); await t.add([], '临时根'); },
    async () => { pre.push(t.clone(cur)); cur.children[1].children[1].title = '甲乙'; await t.rename([1, 1], '甲乙'); },
    async () => { pre.push(t.clone(cur)); cur.children[2].children.push({ title: '临时4', children: [] }); await t.add([2], '临时4'); },
  ];

  // B1: 严格依次10次编辑
  for (let i = 0; i < 10; i++) {
    const id = 'B1';
    const label = 'B1-edit' + String(i + 1).padStart(2, '0');
    await t.step(id + '-e' + (i + 1), async () => {
      await edits[i]();
      await t.check(t.clone(cur));
      await t.snap(label);
    });
  }

  // B2: 逐步undo回各pre-state
  for (let i = 9; i >= 0; i--) {
    const label = 'B2-undo' + String(10 - i).padStart(2, '0');
    await t.step('B2-u' + (10 - i), async () => {
      await t.undo();
      await t.check(t.clone(pre[i]));
      await t.snap(label);
    });
  }

  // B3: 再undo一次,无效果无错,回到初始S0
  await t.step('B3', async () => {
    await t.undo();
    await t.check(t.clone(t.TREE)); // 初始树
    await t.snap('B3');
  });
};
