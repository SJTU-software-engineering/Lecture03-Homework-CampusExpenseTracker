"""校园消费记账入口：python main.py [--db 数据库路径]。"""
import argparse
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from expense_app.repository import ExpenseRepository, StorageError
from expense_app.service import ExpenseService
from expense_app.ui import ExpenseWindow

DEFAULT_DB = Path(__file__).resolve().parent / "data" / "expenses.sqlite3"


def main(argv=None):
    parser = argparse.ArgumentParser(description="校园消费记账桌面应用")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite 文件路径，默认项目 data/expenses.sqlite3")
    args = parser.parse_args(argv)
    app = QApplication(sys.argv[:1])
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "app-icon.ico")))
    try:
        service = ExpenseService(ExpenseRepository(args.db))
    except (StorageError, OSError, ValueError) as exc:
        QMessageBox.critical(None, "启动失败", str(exc))
        return 1
    window = ExpenseWindow(service)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
