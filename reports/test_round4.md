# R4 分类筛选与CSV测试报告

业务基线：`24333c8`；日期：2026-10-20（Asia/Shanghai）；角色TestEngineer。

新增 `tests/test_csv.py` 33个用例，并执行全部既有测试。**最终177/177通过，0失败/错误/跳过，终端耗时14.23秒，exit code 0。** 本轮未发现待修复业务缺陷，业务源码未由TestEngineer修改。

证据：`reports/round4_full.log`、`reports/round4_full.xml`（与最终pytest_output.txt/junit.xml同内容）。R1/R2/R3历史证据未覆盖。范围包含月份+分类筛选、全月预算不变、选择切换清空、中文/BOM/两位金额/引号换行/公式前置空白防护/原备注不变、空结果/取消/覆盖确认/错误、数据库.csv与hardlink同文件保护、原子写失败保留旧文件并清理临时文件。

完整环境、实际命令、各轮结果、R3测试自身算术纠正、两个业务缺陷闭环、真实Qt预览与offscreen字体修复、限制及证据索引统一见 `reports/test_report.md`。
