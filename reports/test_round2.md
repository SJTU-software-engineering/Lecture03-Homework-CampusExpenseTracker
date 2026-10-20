# R2 修复与全面测试报告

日期：2026-10-20（Asia/Shanghai）。被测业务版本：`727c519`。角色 TestEngineer；独立编写 tests 与 requirements-dev.txt，未修改业务实现，未访问旧天气项目。本轮执行结束后才通知主控可开始 R3，避免混用预算扩展中的源码。

## 实际结果

| 执行 | 通过 / 总数 | 失败 / 错误 / 跳过 | 终端耗时 | 证据 |
| --- | --- | --- | --- | --- |
| R1 初版缺陷定向回归 | 0 / 4 | 4 / 0 / 0 | 4.23s | round1_regressions.log / .xml，保留未覆盖 |
| R2 同一组缺陷回归 | 4 / 4 | 0 / 0 / 0 | 0.70s | round2_regressions.log / .xml |
| R2 全面测试（含上述回归） | **96 / 96，100%** | **0 / 0 / 0** | **2.59s** | round2_full.log / .xml |

**B1、B2 均由实际失败转为通过，无待处理测试缺陷。** 完整逐项用例列表、参数和值、测试状态均在最终日志/XML。未运行覆盖率测量，不将通过率描述成源码覆盖率。

## 环境与隔离

Windows x64；Anaconda Python 3.13.9；pytest 9.1.1；PyQt6 6.8.1、Qt 6.8.2；解释器 `.venv\Scripts\python.exe`。使用 `QT_QPA_PLATFORM=offscreen` 的真实 QApplication/QTableWidget/QDateEdit，调用实际按钮点击、表格选择信号与服务/SQLite 存储。

全部数据库位于 pytest `tmp_path`，每个用例独立，重开 repository 验证持久化；没有使用应用默认数据路径，没有触碰用户已有数据库，不访问外网。弹窗 warning 由 monkeypatch 捕获；删除确认明确模拟 No/Yes 两条分支，并检查默认选项 No。

## 命令

项目根目录 `E:\Code\sofwar_engineing\CampusExpenseTracker`：

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt 2>&1 | Tee-Object -FilePath reports/dependency_install.log
.\.venv\Scripts\python.exe -m pytest tests/test_regressions.py -v --junitxml=reports/round2_regressions.xml 2>&1 | Tee-Object -FilePath reports/round2_regressions.log
.\.venv\Scripts\python.exe -m pytest -v --junitxml=reports/round2_full.xml 2>&1 | Tee-Object -FilePath reports/round2_full.log
```

安装检查和两次测试均 exit code 0。安装验证基于现有环境，没有宣称全新机器安装测试。

## 用例范围

| 测试文件 | 内容 | 结果 |
| --- | --- | --- |
| tests/test_regressions.py | 取消选择清空旧金额/备注；新增/修改/删除写入后刷新失败同时保留提交成功与刷新失败提示 | 4/4 通过 |
| tests/test_service.py | 金额 0.01 / 999999.99 边界、0.29 精度、格式/非数值/科学计数法/负数/多位小数拒绝；1900/2100 日期边界、闰年和无效日期；月份排他上界及 2100-12；备注中文/换行/200 字边界、控制字符/201 字拒绝、SQL 注入作为原文持久化；CRUD 重开持久化、跨月移动、按日/id降序、分类与月总分统计；无记录/不存在 id；数据库约束失败保持旧数据、多语句事务回滚、损坏数据库各操作转换 StorageError、非法存储路径 | 全部通过 |
| tests/test_ui.py | 新增→选择→修改→取消删除→确认删除完整链路；清空取消编辑与切月表单状态；无效金额/备注不写入且保留用户输入；无选中删除提示；新增/修改/删除/刷新 StorageError 可见并且不误写数据 | 全部通过 |

## 缺陷闭环

1. **B1 取消选择残留表单**：R1 清空选择后 selected_id=None 但旧金额 12.50 未清空，回归实际失败。CodeWriter R2 修复后同一用例通过，进入新增模式时金额及备注清空。
2. **B2 写入后刷新失败误报**：R1 新增/修改/删除三种分支都覆盖错误状态，三用例失败。R2 修复后状态同时表达写入已经提交和刷新失败，三用例均通过。

原始失败堆栈及复现步骤详见 test_round1.md。未通过改断言、xfail、skip 或修改业务实现使测试通过。

## 限制

- Qt 验证为实际 offscreen 功能测试，没有进行人工屏幕审查、截图验收、不同 DPI 或原生平台视觉验收。
- 数据库错误以受控损坏文件/路径错误/约束错误和注入 StorageError 验证，没有长时间锁竞争、进程断电或磁盘耗尽压力测试。
- 此报告仅对应 R2 的 CRUD 与月统计，R3 预算和 R4 CSV 应另补增量测试与证据。
