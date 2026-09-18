// public-chain.cjs — 公开验收链 步骤 1—11、12a—12d
// 所有期望为本地纯对象，不从 DOM 取 oracle。
const assert = require('assert');

const N = (title, children = []) => ({ title, children });

// 步骤 6 非法文本：第 1 行顶格"X"，第 2 行 4 空格"Y"，构成跳层
const INVALID = 'X\n    Y';

module.exports = async (t) => {
  // —— 本地期望状态推演 ——
  const s2 = N('中心主题', [N('分支一'), N('分支二', [N('细节甲'), N('细节乙')]), N('分支三')]);
  const s3 = t.clone(s2); s3.children[1].title = '分支贰';                          // 步骤 3 后
  const s4 = t.clone(s3); s4.children[0].children.push(N('细节丙'));                 // 步骤 4 后（7 节点）
  const s5 = t.clone(s4); s5.children[1].children.splice(1, 1);                     // 步骤 5 删"细节乙"
  const s7 = t.clone(s5); s7.children[1].children.splice(1, 0, N('细节乙'));         // 步骤 7 撤销删除
  const s8 = t.clone(s7); s8.children[0].children.pop();                            // 步骤 8 撤销添加（= s3 内容）
  const s10add = t.clone(s8); s10add.children[2].children.push(N('细节丁'));          // 步骤 10 添加"细节丁"后
  const s12c = t.clone(s3);                                                         // 步骤 12c 导入恢复目标

  await t.step('1', async () => {
    await t.check(null); // 空状态，无 pageerror / console.error，不自动加载
  });

  await t.step('2', async () => {
    await t.gen(t.S0);
    await t.check(s2); // 6 节点
  });

  await t.step('3', async () => {
    await t.rename([1], '分支贰');
    await t.check(s3); // 仅该标题变化
  });

  await t.step('4', async () => {
    await t.add([0], '细节丙');
    await t.check(s4); // "分支一"末尾新增，共 7 节点
  });

  await t.step('5', async () => {
    await t.del([1, 1]);
    await t.check(s5); // "细节乙"消失，余 6 节点
  });

  await t.step('6', async () => {
    await t.gen(INVALID);
    const msg = t.page.locator('#msg');
    const text = (await msg.textContent() || '').trim();
    assert.ok(text.length > 0, '#msg 无错误文本');
    assert.ok(await msg.isVisible(), '#msg 不可见');
    await t.check(s5); // 导图仍为步骤 5 后 6 节点；撤销栈不变由步骤 7/8 回退结果证明
  });

  await t.step('7', async () => {
    await t.undo();
    await t.check(s7); // "细节乙"复现于"分支贰"第 2 位，共 7 节点
  });

  await t.step('8', async () => {
    await t.undo();
    await t.check(s8); // "细节丙"消失，余 6 节点
  });

  await t.step('9', async () => {
    const exported = await t.exportMap(); // 真实点击下载，原件与哈希由 harness 存证
    assert.deepStrictEqual(exported, t.clone(s8), '导出 JSON 与当前 6 节点导图不同构');
  });

  await t.step('10', async () => {
    await t.add([2], '细节丁');
    await t.check(s10add); // 先确认 7 节点
    await t.snap('10-before-import'); // 导入前留证
    await t.importSaved();
    await t.check(s8); // 整体替换为导出时刻内容，"细节丁"消失，撤销清空
  });

  await t.unverified('11', 'Headless file chooser true cancellation not verified', async () => {
    // 真实 click 打开 filechooser，Playwright 接管后不提交、不 setFiles([]) 冒充取消
    const [fc] = await Promise.all([
      t.page.waitForEvent('filechooser'),
      t.page.click('button:has-text("导入")'),
    ]);
    t.note('11', 'filechooser opened via real click and abandoned without setFiles; true native cancel path unverified in headless');
    await t.undo();
    await t.check(s8); // 无变化、不报错，仍 6 节点
  });

  await t.step('12a', async () => {
    await t.reopen();
    await t.check(null); // 空状态
    await t.undo();
    await t.check(null); // 撤销无效果
  });

  await t.step('12b', async () => {
    await t.gen('临时根');
    await t.check(N('临时根'));
    await t.rename([], '临时根改名');
    await t.check(N('临时根改名')); // 单节点导图，撤销记录含 1 条
  });

  await t.step('12c', async () => {
    await t.importSaved(); // 显式导入步骤 9 保存的 t1-map.json
    await t.check(s12c);   // 恢复 6 节点，第 2 子"分支贰"，临时图消失
  });

  await t.step('12d', async () => {
    await t.undo();
    await t.check(s12c); // 导入清栈，撤销无效果
  });
};
