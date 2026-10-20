"""SQLite 存储层。每次操作单独连接，写入事务自动提交或回滚。"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .models import Expense


class StorageError(Exception):
    """数据库不可用或操作失败。"""


class ExpenseRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser().resolve()
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS expenses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        expense_date TEXT NOT NULL,
                        category TEXT NOT NULL CHECK(category IN ('餐饮','交通','学习','购物','娱乐','其他')),
                        amount_cents INTEGER NOT NULL CHECK(typeof(amount_cents) = 'integer' AND amount_cents > 0 AND amount_cents <= 99999999),
                        note TEXT NOT NULL DEFAULT '' CHECK(length(note) <= 200)
                    )
                """)
                connection.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date)")
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS monthly_budgets (
                        month TEXT PRIMARY KEY NOT NULL,
                        amount_cents INTEGER NOT NULL CHECK(typeof(amount_cents) = 'integer' AND amount_cents > 0 AND amount_cents <= 99999999)
                    )
                """)
        except (sqlite3.Error, OSError) as exc:
            raise StorageError("无法初始化数据库，请检查路径、写入权限及数据库文件格式。") from exc

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def list_month(self, start_date: str, end_date: str) -> tuple[Expense, ...]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT id, expense_date, category, amount_cents, note FROM expenses "
                    "WHERE expense_date >= ? AND expense_date < ? ORDER BY expense_date DESC, id DESC",
                    (start_date, end_date),
                ).fetchall()
            return tuple(Expense(**dict(row)) for row in rows)
        except sqlite3.Error as exc:
            raise StorageError("读取消费记录失败，请检查数据库是否可用。") from exc

    def add(self, expense_date: str, category: str, amount_cents: int, note: str) -> int:
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO expenses(expense_date, category, amount_cents, note) VALUES (?, ?, ?, ?)",
                    (expense_date, category, amount_cents, note),
                )
                return int(cursor.lastrowid)
        except sqlite3.Error as exc:
            raise StorageError("新增消费记录失败，请检查数据库权限或稍后重试。") from exc

    def update(self, expense_id: int, expense_date: str, category: str, amount_cents: int, note: str) -> bool:
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "UPDATE expenses SET expense_date=?, category=?, amount_cents=?, note=? WHERE id=?",
                    (expense_date, category, amount_cents, note, expense_id),
                )
                return cursor.rowcount == 1
        except sqlite3.Error as exc:
            raise StorageError("修改消费记录失败，请检查数据库权限或稍后重试。") from exc

    def delete(self, expense_id: int) -> bool:
        try:
            with self._connect() as connection:
                return connection.execute("DELETE FROM expenses WHERE id=?", (expense_id,)).rowcount == 1
        except sqlite3.Error as exc:
            raise StorageError("删除消费记录失败，请检查数据库权限或稍后重试。") from exc

    def get_budget(self, month: str) -> int | None:
        try:
            with self._connect() as connection:
                row = connection.execute("SELECT amount_cents FROM monthly_budgets WHERE month=?", (month,)).fetchone()
                return None if row is None else row["amount_cents"]
        except sqlite3.Error as exc:
            raise StorageError("读取月预算失败，请检查数据库是否可用。") from exc

    def set_budget(self, month: str, amount_cents: int) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO monthly_budgets(month, amount_cents) VALUES (?, ?) "
                    "ON CONFLICT(month) DO UPDATE SET amount_cents=excluded.amount_cents",
                    (month, amount_cents),
                )
        except sqlite3.Error as exc:
            raise StorageError("保存月预算失败，请检查数据库权限或稍后重试。") from exc

    def clear_budget(self, month: str) -> None:
        try:
            with self._connect() as connection:
                connection.execute("DELETE FROM monthly_budgets WHERE month=?", (month,))
        except sqlite3.Error as exc:
            raise StorageError("清除月预算失败，请检查数据库权限或稍后重试。") from exc
