import pytest
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox

from expense_app.repository import ExpenseRepository, StorageError
from expense_app.service import ExpenseService
from expense_app.ui import ExpenseWindow


@pytest.fixture
def window(app, dialogs, tmp_path):
    widget = ExpenseWindow(ExpenseService(ExpenseRepository(tmp_path / "ui.sqlite3")))
    widget.month_edit.setDate(QDate(2026, 10, 1))
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def add_record(window, amount="12.50", note="午餐"):
    window.date_edit.setDate(QDate(2026, 10, 20))
    window.category_combo.setCurrentText("餐饮")
    window.amount_edit.setText(amount)
    window.note_edit.setPlainText(note)
    window.save_button.click()


def test_ui_add_select_edit_delete_and_confirmation_cancel(window, monkeypatch):
    add_record(window)
    assert window.table.rowCount() == 1 and "12.50" in window.total_label.text()
    assert window.selected_id is None and window.amount_edit.text() == ""
    window.table.selectRow(0)
    identifier = window.selected_id
    assert identifier is not None and window.delete_button.isEnabled()
    assert window.amount_edit.text() == "12.50" and window.note_edit.toPlainText() == "午餐"
    assert "编辑" in window.form_state_label.text()
    window.amount_edit.setText("13.29")
    window.note_edit.setPlainText("修改备注")
    window.save_button.click()
    assert window.table.rowCount() == 1 and window.table.item(0, 2).text() == "13.29"
    assert window.table.item(0, 3).text() == "修改备注"
    window.table.selectRow(0)
    questions = []
    def reject(*args):
        questions.append(args)
        return QMessageBox.StandardButton.No
    monkeypatch.setattr(QMessageBox, "question", reject)
    window.delete_button.click()
    assert len(questions) == 1 and window.table.rowCount() == 1 and window.selected_id == identifier
    assert questions[0][-1] == QMessageBox.StandardButton.No
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    window.delete_button.click()
    assert window.table.rowCount() == 0 and "0.00" in window.total_label.text()
    assert window.selected_id is None and not window.delete_button.isEnabled()


def test_ui_cancel_edit_and_switch_month(window):
    add_record(window)
    window.table.selectRow(0)
    window.new_button.click()
    assert window.selected_id is None and window.amount_edit.text() == ""
    assert window.note_edit.toPlainText() == "" and not window.delete_button.isEnabled()
    window.table.selectRow(0)
    window.month_edit.setDate(QDate(2026, 11, 1))
    assert window.table.rowCount() == 0 and window.selected_id is None
    assert window.amount_edit.text() == "" and window.date_edit.date() == QDate(2026, 11, 1)
    window.month_edit.setDate(QDate(2026, 10, 1))
    assert window.table.rowCount() == 1


@pytest.mark.parametrize("amount", ["", "0", "-1", "1.001", "1000000", "1e2"])
def test_invalid_amount_preserves_form_without_write(window, dialogs, amount):
    add_record(window, amount)
    assert dialogs and window.table.rowCount() == 0
    assert window.amount_edit.text() == amount and window.note_edit.toPlainText() == "午餐"
    assert window.service.month_report("2026-10").records == ()


def test_invalid_note_and_delete_without_selection(window, dialogs):
    add_record(window, note="字" * 201)
    assert dialogs and window.table.rowCount() == 0
    window.delete_record()
    assert "选择" in dialogs[-1]


@pytest.mark.parametrize("operation", ["add", "update", "delete", "refresh"])
def test_ui_storage_error_visible_and_no_unintended_write(window, dialogs, monkeypatch, operation):
    add_record(window)
    window.table.selectRow(0)
    identifier = window.selected_id
    def fail(*args): raise StorageError("存储故障测试")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    if operation == "refresh":
        monkeypatch.setattr(window.service, "month_report", fail)
        window.refresh_button.click()
        assert window.table.rowCount() == 0 and "读取失败" in window.total_label.text()
    elif operation == "delete":
        monkeypatch.setattr(window.service, "delete_expense", fail)
        window.delete_button.click()
    else:
        if operation == "add": window.new_button.click()
        window.amount_edit.setText("3.00")
        monkeypatch.setattr(window.service, "add_expense" if operation == "add" else "update_expense", fail)
        window.save_button.click()
    assert dialogs[-1] == "存储故障测试" and "存储故障" in window.status_label.text()
    rows = window.service.repository.list_month("2026-10-01", "2026-11-01")
    assert len(rows) == 1 and rows[0].id == identifier and rows[0].amount_cents == 1250
