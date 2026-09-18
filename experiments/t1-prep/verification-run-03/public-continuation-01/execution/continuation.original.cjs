// continuation.cjs — 公开步骤 10、11、12a-d（A/B 复用 fragments.cjs）
module.exports = async (t) => {
  // 10: 添加"细节丁"→快照→导入导出文件→整体替换回 6 节点
  await t.step('10', async () => {
    await t.add([2], '细节丁');
    await t.check({ title: '中心主题', children: [
      { title: '分支一', children: [] },
      { title: '分支贰', children: [ { title: '细节甲', children: [] }, { title: '细节乙', children: [] } ] },
      { title: '分支三', children: [ { title: '细节丁', children: [] } ] },
    ]});
    await t.snap('snap10-before-import');
    await t.importSaved(); // 显式导入步骤 9 保存的 t1-map.json
    await t.check(t.clone(t.TREE)); // 恢复导出时刻 6 节点
  });

  // 11: 真实点击导入但无原生取消能力（headless 无 filechooser 监听 → 浏览器自动取消）→ 标记 UNTESTED
  await t.unverified('11', 'BLOCKED_HEADLESS_NATIVE_CANCEL: 本轮禁止可见窗，无 filechooser 监听的 headless click 为浏览器自动取消（isTrusted cancel），非用户真实原生取消；FileChooser 无 cancel 接口。仅能记录"自动取消/撤销清空"的部分证据。', async () => {
    await t.page.click('#btn-import'); // 不监听 filechooser、不 setFiles 空数组、不 dispatch
    await t.page.waitForTimeout(500);
    await t.check(t.clone(t.TREE)); // 自动取消后应仍为 6 节点（部分证据）
    await t.undo(); // 撤销应无效果
    await t.check(t.clone(t.TREE)); // 撤销清空的部分证据
    // 若以上任一树不符，check 已 throw，驱动停止
  });
  // 11 未验证不阻止独立 12/A/B（授权调整）

  // 12a: 关闭标签页重开 → 空状态 + 撤销无效果
  await t.step('12a', async () => {
    await t.reopen();
    await t.check(null);
    await t.undo();
    await t.check(null);
  });

  // 12b: 生成单节点"临时根"→改名→撤销一条（不可直接读内部栈，用 UI 行为证明）
  await t.step('12b', async () => {
    await t.gen('临时根');
    await t.rename([], '临时根改名');
    await t.check({ title: '临时根改名', children: [] });
    // UI 行为验证撤销栈恰有 1 条：undo 后回"临时根"，再 undo 不变（栈已空）
    await t.undo();
    await t.check({ title: '临时根', children: [] });
    await t.undo();
    await t.check({ title: '临时根', children: [] });
    // 真实 rename 回"临时根改名"以重建目标状态
    await t.rename([], '临时根改名');
    await t.check({ title: '临时根改名', children: [] });
    await t.note('12b-undo-probe', 'undo→临时根; 再undo不变(栈空); rename重建为临时根改名');
  });

  // 12c: 导入步骤 9 的 t1-map.json → 完整恢复 6 节点
  await t.step('12c', async () => {
    await t.importSaved();
    await t.check({ title: '中心主题', children: [
      { title: '分支一', children: [] },
      { title: '分支贰', children: [ { title: '细节甲', children: [] }, { title: '细节乙', children: [] } ] },
      { title: '分支三', children: [] },
    ]});
  });

  // 12d: 导入后撤销无效果
  await t.step('12d', async () => {
    await t.undo();
    await t.check({ title: '中心主题', children: [
      { title: '分支一', children: [] },
      { title: '分支贰', children: [ { title: '细节甲', children: [] }, { title: '细节乙', children: [] } ] },
      { title: '分支三', children: [] },
    ]});
  });
};
