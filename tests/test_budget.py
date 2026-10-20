import sqlite3

import pytest
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMessageBox

from expense_app.repository import ExpenseRepository, StorageError
from expense_app.service import ExpenseService, ValidationError, calculate_budget_status
from expense_app.ui import ExpenseWindow


@pytest.fixture
def service(tmp_path):
    return ExpenseService(ExpenseRepository(tmp_path / "budget.sqlite3"))


@pytest.mark.parametrize("budget,spent,level,remaining", [(None, 0, "unset", None),
    (None, 123, "unset", None), (10000, 0, "normal", 10000), (10000, 7999, "normal", 2001),
    (10000, 8000, "near", 2000), (10000, 9999, "near", 1), (10000, 10000, "exhausted", 0),
    (10000, 10001, "over", -1), (3, 2, "normal", 1), (3, 3, "exhausted", 0),
    (5, 4, "near", 1), (1, 0, "normal", 1), (1, 1, "exhausted", 0),
    (99999999, 79999999, "normal", 20000000), (99999999, 80000000, "near", 19999999)])
def test_budget_precise_thresholds(budget, spent, level, remaining):
    result = calculate_budget_status(budget, spent)
    assert (result.budget_cents, result.spent_cents, result.remaining_cents, result.level) == (budget, spent, remaining, level)


@pytest.mark.parametrize("budget,spent", [(0, 0), (-1, 0), (100000000, 0), (True, 0),
    (1.0, 0), (1, -1), (1, True), (None, 1.2), (1, "10")])
def test_budget_invalid_cents(budget, spent):
    with pytest.raises(ValidationError): calculate_budget_status(budget, spent)


def test_budget_monthly_persistence_and_clear_preserves_records(service):
    service.set_budget("2026-10", "100.00")
    service.set_budget("2026-11", "200.00")
    service.set_budget("2026-10", "99.99")
    identifier = service.add_expense("2026-10-20", "餐饮", "79.99")
    other = ExpenseService(ExpenseRepository(service.repository.db_path))
    assert other.get_budget("2026-10") == 9999
    assert other.get_budget("2026-11") == 20000 and other.get_budget("2026-12") is None
    # 7999 / 9999 is just below 80%; exact integer comparison must stay normal.
    assert other.budget_status("2026-10").level == "normal"
    other.clear_budget("2026-10")
    other.clear_budget("2026-10")
    assert service.get_budget("2026-10") is None and service.get_budget("2026-11") == 20000
    assert service.month_report("2026-10").records[0].id == identifier
    assert service.budget_status("2026-10").spent_cents == 7999


def test_budget_recalculates_after_crud_and_cross_month_move(service):
    service.set_budget("2026-10", "100")
    service.set_budget("2026-11", "50")
    identifier = service.add_expense("2026-10-01", "餐饮", "80")
    assert service.budget_status("2026-10").level == "near"
    service.update_expense(identifier, "2026-10-01", "餐饮", "100")
    assert service.budget_status("2026-10").level == "exhausted"
    service.update_expense(identifier, "2026-10-01", "餐饮", "100.01")
    assert service.budget_status("2026-10").remaining_cents == -1
    service.update_expense(identifier, "2026-11-01", "餐饮", "100.01")
    assert service.budget_status("2026-10").level == "normal"
    assert service.budget_status("2026-11").level == "over"
    service.delete_expense(identifier)
    assert service.budget_status("2026-11").spent_cents == 0


@pytest.mark.parametrize("amount", ["0", "-1", "1.001", "1000000", "", "NaN"])
def test_invalid_budget_keeps_previous_value(service, amount):
    service.set_budget("2026-10", "100")
    with pytest.raises(ValidationError): service.set_budget("2026-10", amount)
    assert service.get_budget("2026-10") == 10000


@pytest.mark.parametrize("method", ["get_budget", "clear_budget", "budget_status", "set_budget"])
def test_budget_month_validation(service, method):
    with pytest.raises(ValidationError):
        if method == "set_budget": service.set_budget("2101-01", "10")
        else: getattr(service, method)("2101-01")
    service.set_budget("2100-12", "0.01")
    assert service.get_budget("2100-12") == 1


def test_budget_reuses_supplied_report_total(service, monkeypatch):
    service.set_budget("2026-10", "100")
    def forbidden(_): pytest.fail("unnecessary second monthly read")
    monkeypatch.setattr(service, "month_report", forbidden)
    assert service.budget_status("2026-10", 8000).level == "near"


def test_migration_adds_budget_table_without_changing_old_expenses(tmp_path):
    path = tmp_path / "old.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE expenses(id INTEGER PRIMARY KEY AUTOINCREMENT, expense_date TEXT NOT NULL, category TEXT NOT NULL, amount_cents INTEGER NOT NULL, note TEXT NOT NULL)")
        connection.execute("INSERT INTO expenses VALUES (42,'2026-10-01','学习',1234,'旧版中文流水')")
    repository = ExpenseRepository(path)
    assert repository.get_budget("2026-10") is None
    repository.set_budget("2026-10", 10000)
    records = repository.list_month("2026-10-01", "2026-11-01")
    assert len(records) == 1 and records[0].id == 42 and records[0].note == "旧版中文流水"
    assert records[0].amount_cents == 1234
    assert repository.add("2026-10-02", "其他", 1, "新增") > 42


def test_budget_constraint_failure_keeps_previous_value(service):
    service.set_budget("2026-10", "100")
    with pytest.raises(StorageError): service.repository.set_budget("2026-10", 0)
    assert service.get_budget("2026-10") == 10000


@pytest.mark.parametrize("operation", ["get_budget", "set_budget", "clear_budget"])
def test_budget_storage_error_wrapped(service, operation):
    service.repository.db_path.write_bytes(b"corrupt database")
    with pytest.raises(StorageError):
        if operation == "set_budget": service.repository.set_budget("2026-10", 10000)
        else: getattr(service.repository, operation)("2026-10")


@pytest.fixture
def window(app, dialogs, service):
    widget = ExpenseWindow(service)
    widget.month_edit.setDate(QDate(2026, 10, 1))
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_budget_ui_thresholds_crud_switch_month_and_clear(window, monkeypatch):
    assert "未设置" in window.budget_label.text()
    window.budget_edit.setText("100")
    window.budget_save_button.click()
    assert "正常" in window.budget_warning_label.text()
    window.date_edit.setDate(QDate(2026, 10, 20))
    window.amount_edit.setText("80")
    window.save_button.click()
    assert "80%" in window.budget_warning_label.text() and "20.00" in window.budget_label.text()
    window.table.selectRow(0)
    window.amount_edit.setText("100")
    window.save_button.click()
    assert "100%" in window.budget_warning_label.text() and "用完" in window.budget_warning_label.text()
    window.table.selectRow(0)
    window.amount_edit.setText("100.01")
    window.save_button.click()
    assert "超支" in window.budget_warning_label.text() and "0.01" in window.budget_label.text()
    window.month_edit.setDate(QDate(2026, 11, 1))
    assert "未设置" in window.budget_label.text() and window.budget_edit.text() == ""
    window.month_edit.setDate(QDate(2026, 10, 1))
    assert "超支" in window.budget_warning_label.text() and window.budget_edit.text() == "100.00"
    window.table.selectRow(0)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    window.delete_button.click()
    assert "正常" in window.budget_warning_label.text()
    window.amount_edit.setText("3")
    window.save_button.click()
    window.budget_clear_button.click()
    assert "未设置" in window.budget_label.text() and window.table.rowCount() == 1
    assert window.service.month_report("2026-10").total_cents == 300


def test_budget_ui_invalid_input_and_read_failure(window, dialogs, monkeypatch):
    window.budget_edit.setText("0")
    window.budget_save_button.click()
    assert dialogs and window.service.get_budget("2026-10") is None
    def fail(*args): raise StorageError("预算读取失败测试")
    monkeypatch.setattr(window.service, "budget_status", fail)
    window.refresh_button.click()
    assert "读取失败" in window.budget_label.text() and window.budget_warning_label.text() == ""
    assert "预算读取失败测试" in window.status_label.text()


@pytest.mark.parametrize("operation", ["set_budget", "clear_budget"])
def test_budget_ui_storage_write_failure(window, dialogs, monkeypatch, operation):
    def fail(*args): raise StorageError("预算写入失败测试")
    monkeypatch.setattr(window.service, operation, fail)
    window.budget_edit.setText("100")
    (window.budget_save_button if operation == "set_budget" else window.budget_clear_button).click()
    assert dialogs[-1] == "预算写入失败测试" and "写入失败" in window.status_label.text()


@pytest.mark.parametrize("operation", ["set", "clear"])
def test_budget_ui_committed_write_refresh_failure(window, dialogs, monkeypatch, operation):
    window.service.set_budget("2026-10", "50")
    def fail(*args): raise StorageError("预算刷新失败测试")
    monkeypatch.setattr(window.service, "month_report", fail)
    window.budget_edit.setText("100")
    (window.budget_save_button if operation == "set" else window.budget_clear_button).click()
    assert "已完成" in window.status_label.text() and "刷新失败" in window.status_label.text()
    assert window.service.get_budget("2026-10") == (10000 if operation == "set" else None)
