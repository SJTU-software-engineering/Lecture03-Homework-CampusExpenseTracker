# 校园消费记账

基于 Python 3.10+、PyQt6 和 SQLite 的中文桌面作业。记录消费日期、分类、金额与备注，支持新增、选择记录编辑、确认删除、按月份查看流水、月总支出及六类消费统计。数据保存在本地，退出重启后保留。

## 安装与启动

在本项目目录使用 PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

已有虚拟环境时可跳过创建步骤。Qt 采用在本机 Python 3.13 环境验证过的 PyQt6 6.8.1 / Qt6 6.8.2 固定组合。默认数据库为项目目录下 `data/expenses.sqlite3`，启动时自动创建目录与表；无网络要求。可以通过参数指定另一个持久化数据库：

```powershell
.\.venv\Scripts\python.exe main.py --db .\tmp\demo.sqlite3
```

相对 `--db` 路径按启动命令当前工作目录解析。建议每份数据使用独立文件；数据库文件是个人消费数据，请自行备份。

## 使用

1. 输入消费日期、分类、金额和可选备注，点击“新增记录”。
2. 点击流水中的一行，表单进入编辑模式，按钮变为“保存修改”；修改后保存。
3. “取消编辑 / 清空”返回新增模式。切换月份或刷新流水也会清空未保存表单，清除选择并返回新增模式。
4. 选中记录后点击“删除所选记录”，确认后删除，默认选择“不删除”。
5. 月份控件选择年、月（可使用键盘与上下按钮）；流水按日期和记录编号倒序排列。月总支出和分类统计包括该月全部记录，空月显示零。
6. 编辑日期跨月份后，界面切换到保存记录所在月份并回到新增模式。

消费分类为餐饮、交通、学习、购物、娱乐、其他。日期范围 1900-01-01 至 2100-12-31，允许补记或预先记账。金额范围 0.01～999999.99 元，仅接受普通十进制数字和最多两位小数；不支持负数、千位分隔符、货币符号或科学计数法。备注最多 200 字符，首尾空白会清理。金额使用 Decimal 解析并以整数分存储、累计、格式化，避免浮点累计误差。校验或数据库操作失败会显示提示，未成功保存的表单保留。

## 源码设计与接口

| 模块 | 职责 / 主要接口 |
| --- | --- |
| `main.py` | 入口，支持 `--db`，默认路径与工作目录无关 |
| `expense_app/models.py` | `Expense`、`MonthReport`、分类常量与 `format_amount(cents)` |
| `expense_app/repository.py` | `ExpenseRepository(db_path)`，SQLite 初始化、参数化 CRUD、事务及存储错误包装 |
| `expense_app/service.py` | `ExpenseService(repository)`，输入校验、整数分转换、月度统计 |
| `expense_app/ui.py` | `ExpenseWindow(service)`，中文 Qt 界面、表单状态、删除确认与错误提示 |

业务层可直接调用 `add_expense(day, category, amount, note='') -> id`、`update_expense(id, day, category, amount, note='')`、`delete_expense(id)` 和 `month_report('YYYY-MM') -> MonthReport`。日期与金额传字符串，返回的金额均为整数分；`ValidationError` 为输入或记录不存在错误，`StorageError` 为数据库错误。仓储支持注入临时文件路径，界面支持注入服务，便于测试隔离。仓储为底层接口，校验应通过业务层执行。

数据库每次操作使用独立连接，写事务自动提交或回滚；设置 5 秒 SQLite 锁等待，失败后向用户提示。记录量较大或数据库锁竞争时，界面可能短暂等待，适用于个人规模本地记账。初版不含月预算提醒、分类筛选和 CSV 导出，留待后续功能迭代；也不含账户登录、多币种、退款负数或云同步。

## 验证说明

本轮 CodeWriter 仅编写业务代码并做基础语法自检，单元测试和测试报告由独立 TestEngineer 提供。建议覆盖金额精度、日期/月边界、输入限制、CRUD 持久化、跨月编辑、空月汇总、删除取消、参数化 SQL 与数据库错误展示。
