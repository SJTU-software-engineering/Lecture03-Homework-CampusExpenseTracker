"""Reproduce a real Qt offscreen preview using isolated synthetic data only."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QDate
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from expense_app.repository import ExpenseRepository
from expense_app.service import ExpenseService
from expense_app.ui import ExpenseWindow


def main():
    application = QApplication.instance() or QApplication([])
    # Qt offscreen can lack system font discovery; explicitly load a CJK font.
    font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyh.ttc"
    if font_path.exists():
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            application.setFont(QFont(families[0], 10))
    with tempfile.TemporaryDirectory(prefix="campus-expense-preview-") as directory:
        service = ExpenseService(ExpenseRepository(Path(directory) / "synthetic.sqlite3"))
        for day, category, amount, note in (
            ("2026-10-02", "餐饮", "26.50", "合成示例：校园食堂午餐"),
            ("2026-10-08", "交通", "12.00", "合成示例：周末公交出行"),
            ("2026-10-12", "学习", "168.80", "合成示例：教材与实验用品"),
            ("2026-10-16", "购物", "129.90", "合成示例：日常用品"),
            ("2026-10-20", "餐饮", "80.00", "合成示例：同学聚餐"),
            ("2026-10-21", "娱乐", "32.80", "合成示例：电影活动"),
        ):
            service.add_expense(day, category, amount, note)
        service.set_budget("2026-10", "500.00")
        window = ExpenseWindow(service)
        window.setWindowTitle("校园消费记账 · 合成示例数据")
        window.month_edit.setDate(QDate(2026, 10, 1))
        window.refresh()
        window.status_label.setText("预览使用临时数据库及合成示例账目；未读取或修改正式数据。")
        window.show()
        application.processEvents()
        window.resize(max(window.width(), window.minimumSizeHint().width()),
                      max(window.height(), window.minimumSizeHint().height()))
        application.processEvents()
        output = ROOT / "reports" / "app_preview.png"
        output.parent.mkdir(exist_ok=True)
        if not window.grab().save(str(output)):
            raise RuntimeError("Could not save Qt preview")
        print(output)
        window.close()
        application.processEvents()


if __name__ == "__main__":
    main()
