import pytest
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox

from expense_app.repository import ExpenseRepository, StorageError
from expense_app.service import ExpenseService
from expense_app.ui import ExpenseWindow


@pytest.fixture
def window(app, dialogs, tmp_path):
    service = ExpenseService(ExpenseRepository(tmp_path / "test.sqlite3"))
    service.add_expense("2026-10-15", "学习", "12.50", "旧备注")
    widget = ExpenseWindow(service)
    widget.month_edit.setDate(QDate(2026, 10, 1))
    widget.refresh()
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_deselect_clears_old_form(window):
    window.table.selectRow(0)
    assert window.selected_id is not None
    assert window.amount_edit.text() == "12.50"
    window.table.clearSelection()
    assert window.selected_id is None
    assert window.amount_edit.text() == "", "取消选择进入新增模式时不应保留旧记录金额"
    assert window.note_edit.toPlainText() == ""


@pytest.mark.parametrize("operation", ["add", "update", "delete"])
def test_committed_write_then_refresh_failure_remains_visible(window, dialogs, monkeypatch, operation):
    if operation in ("update", "delete"):
        window.table.selectRow(0)
    else:
        window.amount_edit.setText("3.21")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    def fail_report(_):
        raise StorageError("读取失败：测试故障")
    monkeypatch.setattr(window.service, "month_report", fail_report)
    if operation == "delete": window.delete_record()
    else: window.save_record()
    assert dialogs and "读取失败" in dialogs[-1]
    status = window.status_label.text()
    assert "失败" in status or "未刷新" in status, "写入后刷新失败不应被无条件成功状态覆盖"
    assert "已" in status or "成功" in status, "状态还应说明写入已经提交，避免用户重复操作"
