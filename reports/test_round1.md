# R1 初版缺陷复现报告

日期：2026-10-20（Asia/Shanghai）。TestEngineer 在初版提交 `2b71669` 上独立读取源码并编写实际 Qt GUI 回归；未修改业务源码。仅操作 CampusExpenseTracker 项目，测试数据库为 pytest tmp_path 的隔离 SQLite，未访问任何用户数据库。

## 初版实际结果

执行命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_regressions.py -v --junitxml=reports/round1_regressions.xml 2>&1 | Tee-Object -FilePath reports/round1_regressions.log
```

**4 个用例，0 通过、4 失败、0 错误、0 跳过，通过率 0%，耗时 4.23 秒，exit code 1。** 这是针对已识别缺陷的定向回归结果，不代表全部功能失败；R1 全面功能测试尚未在初版上执行，后续扩展用例将于 R2 修复后统一运行。

环境：Windows x64、Anaconda Python 3.13.9、pytest 9.1.1、PyQt6 6.8.1 / Qt 6.8.2，`QT_QPA_PLATFORM=offscreen`。实际 QApplication、QTableWidget 选择信号及按钮/槽调用已运行；对话框通过 monkeypatch 捕获并提供确认值，不做人工视觉验收。

## 可复现缺陷

| 编号 | 触发步骤 | 实际结果 | 期望行为 | 失败用例 |
| --- | --- | --- | --- | --- |
| B1 | 创建 2026-10-15 学习 12.50 元、备注“旧备注”；选中表格记录，再 clearSelection | selected_id 已清空、显示新增模式，但金额仍 12.50、备注仍为旧记录值，可能误新增重复记录 | 取消选择进入新增模式时清空旧表单内容 | test_deselect_clears_old_form |
| B2 | 新增实际提交后，将服务 month_report 注入 StorageError“读取失败：测试故障” | warning 捕获到了错误，但底部状态被覆盖为“消费记录已新增。” | 持续显示“写入已提交，但刷新失败”，避免错误消失和重复操作 | test_committed_write_then_refresh_failure_remains_visible[add] |
| B2 | 修改实际提交后注入同样的刷新错误 | 底部状态为“修改已保存。” | 同时保留写成功与刷新失败信息 | 上述 [update] |
| B2 | 确认 Yes 删除实际提交后注入同样刷新错误 | 底部状态为“记录已删除。” | 同时保留删除成功与刷新失败信息 | 上述 [delete] |

证据：`reports/round1_regressions.log` 含实际断言失败与终端摘要，`reports/round1_regressions.xml` 含机器可读结果。Windows 终端中文转码可能显示乱码，XML 和本报告保留文字语义。上述文件保留 R1 原始证据，后续回归使用其他文件名。

TestEngineer 已将两类缺陷及复现交主控，等待 CodeWriter R2 修复。额外编写 `tests/test_service.py`、`tests/test_ui.py` 覆盖金额/日期/月边界、SQLite CRUD/事务、UI CRUD/错误处理等；未执行之前不宣称这些用例通过。
