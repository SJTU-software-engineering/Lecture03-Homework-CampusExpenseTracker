# 校园消费记账：最终完整测试报告

日期：2026-10-20（Asia/Shanghai）  
角色：TestEngineer，独立读取源码、编写测试并在终端执行。  
最终业务基线：R4 `24333c8`（R1 `2b71669`，R2 `727c519`，R3 `2ba9b32`）。测试执行完成后的变化仅为文档和预览脚本，不改变被测业务逻辑。

## 最终结论

**177 / 177 个自动化用例通过，通过率 100%；失败 0、错误 0、跳过 0。** 最终 pytest 终端耗时 **14.23 秒**（JUnit suite 计时为13.135秒，两者口径不同）。其中79个基础服务/存储用例、13个基础界面用例、4个缺陷回归、48个预算增量用例、33个CSV/分类筛选增量用例。通过率是已执行用例的通过比例，未测量源码覆盖率。

所有自动化用例离线执行，数据库及导出文件位于 pytest tmp_path。没有触碰用户正式数据库，没有读写旧 PyQtWeatherApp 项目。本轮测试及预览只在新项目 CampusExpenseTracker 下交付文件。

发现的两类业务缺陷已完成“真实失败→上报主控→CodeWriter修复→同一测试通过”闭环。预算和CSV测试未发现新的待修复业务问题。R3 有一次测试自身算术期望写错，已公开记录、更正并保留首次失败证据。

## 各轮真实执行结果

| 轮次/基线 | 结果 | 耗时 | 证据 |
| --- | --- | --- | --- |
| R1 初版缺陷定向复现 2b71669 | 0通过、4失败、0错误/跳过 | 4.23s | round1_regressions.log / .xml；test_round1.md |
| R2 同一4条回归 727c519 | 4/4通过 | 0.70s | round2_regressions.log / .xml |
| R2 全面验证 727c519 | 96/96通过 | 2.59s | round2_full.log / .xml；test_round2.md |
| R3 首次 2ba9b32 | 143通过、1测试自身错误期望失败 | 8.13s | round3_initial_test_error.log / .xml |
| R3 更正测试期望后 2ba9b32 | 144/144通过 | 9.41s | round3_full.log / .xml；test_round3.md |
| R4 最终 24333c8 | **177/177通过** | **14.23s** | pytest_output.txt / junit.xml；同内容round4_full.log / .xml |

R1只有4个针对已识别缺陷的定向用例实际执行，不把该结果描述成全部功能失败，也不声称R1初版通过96个全面用例。各轮运行期间主控暂停修改源码，完成运行后才进入下一轮。

## 环境与命令

Windows x64；Anaconda Python 3.13.9；pytest 9.1.1；pluggy 1.7.0；PyQt6 6.8.1 / Qt 6.8.2；PyQt6-sip 13.13.0。解释器为项目 `.venv\Scripts\python.exe`。Qt测试在导入Qt前通过 tests/conftest.py 设置 `QT_QPA_PLATFORM=offscreen`，使用实际 QApplication、窗口、表格、日期/分类控件和Qt信号。提示对话框通过 monkeypatch 捕获，确认操作分别模拟 No/Yes。

从项目根目录执行最终测试：

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -v --junitxml=reports/junit.xml 2>&1 | Tee-Object -FilePath reports/pytest_output.txt
```

最终测试 exit code 0。依赖安装检查在R2执行成功，详细输出 reports/dependency_install.log；后续业务扩展未添加依赖。验证基于已有虚拟环境，没有声称全新机器或全新虚拟环境安装验收。

## 测试代码和覆盖范围

| 文件 / 数量 | 测试范围 |
| --- | --- |
| tests/conftest.py | offscreen、会话级QApplication、对话框捕获 |
| tests/test_service.py / 79 | 金额Decimal转整数分，0.01与999999.99边界、0.29精度、负数/多位小数/科学计数法/非数值拒绝；1900/2100日期边界、闰年、2100-12排他上界；中文/引号/SQL注入备注持久化与控制字符/长度拒绝；CRUD重开持久化、跨月编辑、排序、分类/月总分统计；不存在id；数据库约束失败保留旧数据、多语句事务回滚、损坏库读写删和初始化失败 |
| tests/test_ui.py / 13 | 新增→选择→编辑→删除取消→删除确认；默认确认No；取消编辑清空、切月重置；无效金额/备注保持表单不写入；无选中删除提示；新增/修改/删除/刷新StorageError可见且不误写 |
| tests/test_regressions.py / 4 | 取消选择残留表单；新增/修改/删除实际提交后，刷新失败保持提交成功与刷新失败双重提示 |
| tests/test_budget.py / 48 | 未设置/正常/接近/用完/超支；79.99/80/99.99/100/100.01%边界、最小1分、小预算非整数阈值、最大预算阈值；非法分值与金额；按月独立、更新持久化、幂等清除保留流水；CRUD与跨月移动重算；旧版仅expenses表的库加法迁移保留id/中文/金额；预算存储异常；真实界面预算设置、提醒、CRUD刷新、切月、清除及错误状态 |
| tests/test_csv.py / 33 | 月份与分类组合筛选、空结果、不改变全月预算；CSV UTF-8 BOM、中文表头、金额两位、小数精度、引号/逗号/换行、记录顺序；公式 `= + - @` 开头及前导空格/Tab/换行/全角空格防护，原备注不变；分类/空月份导出；大小写.csv、无效路径；原子replace/fsync/csv.writer失败保留原文件并清理临时文件；数据库命名.csv及真实hardlink同文件保护；UI筛选清空选择与表单、全月总额/预算不受筛选影响；文件选择取消、覆盖No/Yes、空文件表头提示、导出错误可见 |

完整参数化用例名称、每项PASS及实际输出见 reports/pytest_output.txt 和 reports/junit.xml。预算/导出测试使用受控临时文件，未向用户目录生成示例数据。对事务的测试包括一次事务先成功INSERT、后约束失败，断言两条都未保留，避免只测试单条失败而误称多语句回滚。

## 缺陷闭环与测试自身纠正

| 编号 | R1可复现步骤 / 实际结果 | 修复验证 |
| --- | --- | --- |
| B1 | 在临时库创建学习12.50元“旧备注”，选中记录后clearSelection；selected_id变None、显示新增模式，但旧金额/备注残留，可能误新增重复记录 | 上报主控，由CodeWriter在R2统一新增模式重置表单；原用例在R2/R3/R4持续通过 |
| B2 | 新增/修改/确认删除实际提交后，让month_report抛StorageError；warning被捕获，但底部被覆盖成“已新增/已保存/已删除” | 上报主控，由CodeWriter让refresh返回成功状态，保留“写入已完成但刷新失败”提示；三条原回归在R2/R3/R4持续通过，预算同类路径也验证通过 |

详细失败堆栈见R1日志/XML。没有用xfail、skip或只修改断言使业务缺陷消失；TestEngineer未修改业务实现。

R3测试自身错误：最初将79.99元支出/99.99元预算期望为near，实际为79.9979998%而未达到80%，正确业务结果normal。独立计算 `7999*100 < 9999*80` 后修正该单一用例期望，原始143通过+1失败证据保留。真正80/100/>100边界参数化用例均在初次就通过。该事件不算新增业务bug。

## 可复现的界面预览

脚本 `tools/render_preview.py` 使用 TemporaryDirectory 创建独立SQLite、合成六条2026-10中文账目，总支出450.00元、预算500.00元，分类筛选全部，展示near提醒；窗口标题、每条备注与底部提示明确为合成数据。截图后临时库自动删除，没有给正式data目录填充数据。

脚本已从项目外的Temp工作目录实际执行成功，证明不依赖调用者cwd：

```powershell
& 'E:\Code\sofwar_engineing\CampusExpenseTracker\.venv\Scripts\python.exe' 'E:\Code\sofwar_engineing\CampusExpenseTracker\tools\render_preview.py'
```

输出 `reports/app_preview.png`。初次offscreen截图全部文字为方框：这是offscreen字体发现问题，不能当作可读预览交付。仅修改预览脚本，通过QFontDatabase显式载入Windows `C:/Windows/Fonts/msyh.ttc` 并将实际加载family设置为应用字体后重新生成；业务代码未改。TestEngineer与主控分别使用view_image检查修复后的1000×800 PNG，中文/数字、near预算提示、6条账目、全部分类、表单与按钮可读，无明显裁切或重叠。此为对实际offscreen渲染图片的检查，不宣称完成原生Windows人工GUI验收。

## 交付证据索引

- 最终测试：reports/pytest_output.txt、reports/junit.xml；同内容R4存档round4_full.log/xml。
- 分轮报告：reports/test_round1.md、test_round2.md、test_round3.md、test_round4.md。
- 历史证据：round1_regressions、round2_regressions、round2_full、round3_initial_test_error、round3_full各自.log/.xml，全部保留。
- 环境安装：reports/dependency_install.log。
- 可复现预览：tools/render_preview.py、reports/app_preview.png。

## 现实限制

- 功能测试与截图采用offscreen；未进行真实桌面交互、不同DPI/分辨率、跨平台或全新机器安装验证。
- SQLite异常通过真实约束/损坏文件/路径错误与受控故障注入覆盖，未进行断电、磁盘耗尽、长时锁竞争和多进程压力测试。
- CSV原子失败与同文件保护已测试；没有在实际Excel/WPS中打开逐项验证其对单引号和公式防护的展示方式。
- 预算提醒为当前应用内提示，未测试后台定时通知或系统通知。
- 测试覆盖已定义范围，不能据177个用例通过推断所有潜在缺陷均不存在；没有执行源码覆盖率、性能基准或安全渗透测试。
